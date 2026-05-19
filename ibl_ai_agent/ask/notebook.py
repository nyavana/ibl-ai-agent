from __future__ import annotations

import ast
import html
import json
import os
from pathlib import Path
import shlex
import subprocess
from typing import Any, Literal

from pydantic import BaseModel, Field

from .templates import (
    final_answer_code,
    hidden_result_dump_code,
    setup_constants_code,
    setup_diagnostics_code,
    setup_functions_code,
    setup_imports_code,
    setup_main_code,
    setup_objects_code,
    setup_summary_code,
)
from ibl_ai_agent.errors import ExecutionContractError


class NotebookCell(BaseModel):
    id: str
    cell_type: Literal["markdown", "code"]
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str
    execution_count: int | None = None
    outputs: list[dict[str, Any]] = Field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        payload = self.model_dump(mode="python")
        if self.cell_type == "markdown":
            payload.pop("execution_count", None)
            payload.pop("outputs", None)
        return payload


class NotebookDocument(BaseModel):
    cells: list[NotebookCell]
    metadata: dict[str, Any]
    nbformat: int = 4
    nbformat_minor: int = 5

    def to_json(self) -> str:
        payload = self.model_dump(mode="python")
        payload["cells"] = [cell.as_dict() for cell in self.cells]
        return json.dumps(payload, indent=2)


def hideable_metadata() -> dict[str, Any]:
    return {"tags": ["hide-input", "remove-input"], "jupyter": {"source_hidden": True}}


def new_markdown_cell(cell_id: str, source: str, *, hidden: bool = False) -> NotebookCell:
    metadata = hideable_metadata() if hidden else {}
    return NotebookCell(id=cell_id, cell_type="markdown", metadata=metadata, source=source)


def new_code_cell(cell_id: str, source: str, *, hidden: bool = False) -> NotebookCell:
    metadata = hideable_metadata() if hidden else {}
    return NotebookCell(
        id=cell_id,
        cell_type="code",
        metadata=metadata,
        source=source,
        execution_count=None,
        outputs=[],
    )


def infer_notebook_title(question: str) -> str:
    cleaned = " ".join(question.strip().split())
    return cleaned if cleaned else "IBL Analysis"


def split_analysis_code(
    analysis_code: str,
    sections_override: dict[str, str] | None,
) -> dict[str, str]:
    keys = ["imports", "constants", "declarations", "helper_functions", "main_analysis", "result_dump"]
    out = {k: "" for k in keys}
    if sections_override:
        for key in keys:
            value = sections_override.get(key, "").strip()
            if value:
                out[key] = value

    code = analysis_code.strip()
    if not code:
        return out
    if any(out.values()):
        if not out["main_analysis"]:
            out["main_analysis"] = code
        return out

    try:
        tree = ast.parse(code)
    except Exception:
        out["main_analysis"] = code
        return out

    lines = code.splitlines()
    imports: list[str] = []
    helpers: list[str] = []
    main_chunks: list[str] = []

    for node in tree.body:
        chunk = "\n".join(lines[node.lineno - 1 : node.end_lineno]).strip()
        if not chunk:
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(chunk)
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            helpers.append(chunk)
            continue
        main_chunks.append(chunk)

    out["imports"] = "\n\n".join(imports).strip()
    out["helper_functions"] = "\n\n".join(helpers).strip()
    out["main_analysis"] = "\n\n".join(main_chunks).strip()
    return out


def label_analysis_chunk(chunk: str) -> str:
    stripped = chunk.strip()
    if not stripped:
        return "Analysis Step"
    for line in stripped.splitlines():
        s = line.strip()
        if s.startswith("#"):
            title = s.lstrip("#").strip()
            if title:
                return title[:80]
            break
        if s:
            break
    lower = stripped.lower()
    if "groupby(" in lower or "median(" in lower:
        return "Compute Summary Metrics"
    if "target_regions" in lower or ".isin(" in lower or "is_good" in lower:
        return "Filter Data"
    if "plt." in lower or "savefig(" in lower or "subplots(" in lower or ".plot(" in lower:
        return "Create Plot"
    if "analysis_result" in lower or "result_json_path" in lower or "json.dump" in lower:
        return "Build Answer Payload"
    return "Run Analysis"


def split_main_analysis_into_cells(main_analysis: str) -> list[tuple[str, str]]:
    code = main_analysis.strip()
    if not code:
        return []
    try:
        tree = ast.parse(code)
    except Exception:
        return [("Run Analysis and Create Plot", code)]

    lines = code.splitlines()
    stmt_chunks: list[str] = []
    for node in tree.body:
        chunk = "\n".join(lines[node.lineno - 1 : node.end_lineno]).strip()
        if chunk:
            stmt_chunks.append(chunk)
    if not stmt_chunks:
        return [("Run Analysis and Create Plot", code)]
    if len(stmt_chunks) == 1:
        return [("Run Analysis and Create Plot", stmt_chunks[0])]

    grouped: list[tuple[str, str]] = []
    cur_label = label_analysis_chunk(stmt_chunks[0])
    cur_parts: list[str] = []
    for chunk in stmt_chunks:
        label = label_analysis_chunk(chunk)
        should_split = (
            (label != cur_label and (label != "Run Analysis" or cur_label != "Run Analysis"))
            or len(cur_parts) >= 3
        )
        if should_split and cur_parts:
            grouped.append((cur_label, "\n\n".join(cur_parts).strip()))
            cur_parts = []
            cur_label = label
        cur_parts.append(chunk)
    if cur_parts:
        grouped.append((cur_label, "\n\n".join(cur_parts).strip()))

    return grouped or [("Run Analysis and Create Plot", code)]


def assigned_names_in_code(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except Exception:
        return []
    names: list[str] = []
    seen: set[str] = set()

    def _add(name: str) -> None:
        if name and name not in seen:
            seen.add(name)
            names.append(name)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    _add(tgt.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                _add(node.target.id)
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                _add(node.target.id)
    return names


def append_dataframe_preview(code: str) -> str:
    assigned = assigned_names_in_code(code)
    if not assigned:
        return code
    names_json = json.dumps(assigned)
    preview = f"""

# Auto preview: show quick summaries for DataFrames created/updated in this cell.
for _name in {names_json}:
    _obj = globals().get(_name)
    if isinstance(_obj, pd.DataFrame):
        print(f"[preview] {{_name}}: shape={{_obj.shape}}")
"""
    return f"{code.rstrip()}\n{preview}".strip()


def render_notebook(
    *,
    question: str,
    question_filters: dict[str, Any],
    plan: dict[str, Any],
    out_ipynb: Path,
    out_png: Path,
    result_json_path: Path,
    sessions_hint_path: Path | None,
    max_sessions: int | None,
) -> None:
    title = infer_notebook_title(question)
    resolved_sessions_hint_path = sessions_hint_path.resolve() if sessions_hint_path else None
    resolved_out_png = out_png.resolve()
    resolved_result_json_path = result_json_path.resolve()
    load_plan_items = [f"- {x}" for x in plan.get("load_plan", [])]
    analysis_op_items = [f"- {x}" for x in plan.get("analysis_ops", [])]
    setup_constants = setup_constants_code(
        sessions_hint_path=resolved_sessions_hint_path,
        max_sessions=max_sessions,
    )
    analysis_sections = split_analysis_code(
        str(plan.get("analysis_code", "")),
        plan.get("analysis_notebook_sections")
        if isinstance(plan.get("analysis_notebook_sections"), dict)
        else None,
    )
    analysis_runtime_constants = "\n".join(
        [
            f"QUESTION = {question!r}",
            f"QUESTION_FILTERS = {question_filters!r}",
            f"FIGURE_PATH = {str(resolved_out_png)!r}",
            f"RESULT_JSON_PATH = {str(resolved_result_json_path)!r}",
        ]
    )
    hidden_plan_vars = "\n".join(
        [
            "_QUESTION_INTERPRETATION = "
            + json.dumps(plan.get("question_interpretation", {}), indent=2, sort_keys=True),
            "_REQUIRED_OUTPUTS_JSON = "
            + json.dumps(plan.get("required_outputs_json", {}), indent=2, sort_keys=True),
        ]
    )

    preview_dataframes = (
        os.environ.get("IBL_AGENT_NOTEBOOK_PREVIEW_DATAFRAMES", "0").strip()
        not in ("0", "false", "False", "")
    )

    cells: list[NotebookCell] = [
        new_markdown_cell("title", f"# {title}\n\nThis notebook documents one IBL ask run."),
        new_markdown_cell(
            "load-plan",
            "\n".join(["## Data Loading Plan", *load_plan_items]) if load_plan_items else "## Data Loading Plan",
        ),
        new_markdown_cell(
            "analysis-ops",
            "\n".join(["## Analysis Steps", *analysis_op_items]) if analysis_op_items else "## Analysis Steps",
        ),
        new_code_cell("hidden-plan-vars", hidden_plan_vars, hidden=True),
        new_markdown_cell("setup-imports-md", "## Setup 1: Imports"),
        new_code_cell("setup-imports", setup_imports_code()),
        new_markdown_cell("setup-constants-md", "## Setup 2: Constants"),
        new_code_cell("setup-constants", setup_constants),
        new_markdown_cell("setup-objects-md", "## Setup 3: Declare ONE and Atlas objects"),
        new_code_cell("setup-objects", setup_objects_code()),
        new_markdown_cell("setup-functions-md", "## Setup 4: Helper functions for loading data"),
        new_code_cell("setup-functions", setup_functions_code()),
        new_markdown_cell("setup-main-md", "## Setup 5: Load session data tables"),
        new_code_cell("setup-main", setup_main_code()),
        new_code_cell("setup-diagnostics", setup_diagnostics_code(), hidden=True),
        new_markdown_cell("setup-summary-md", "## Setup 6: Data Load Diagnostics"),
        new_code_cell("setup-summary", setup_summary_code()),
        new_markdown_cell(
            "analysis-intro",
            "## Question-Specific Analysis\n\nThe next cells implement analysis logic generated for the question.",
        ),
        new_code_cell("analysis-runtime-constants", analysis_runtime_constants),
    ]

    if analysis_sections["imports"]:
        cells.append(new_markdown_cell("analysis-imports-md", "### Analysis Imports"))
        cells.append(new_code_cell("analysis-imports", analysis_sections["imports"]))
    if analysis_sections["constants"]:
        cells.append(new_markdown_cell("analysis-constants-md", "### Analysis Constants"))
        cells.append(new_code_cell("analysis-constants", analysis_sections["constants"]))
    if analysis_sections["declarations"]:
        cells.append(new_markdown_cell("analysis-declarations-md", "### Analysis Object Declarations"))
        cells.append(new_code_cell("analysis-declarations", analysis_sections["declarations"]))
    if analysis_sections["helper_functions"]:
        cells.append(new_markdown_cell("analysis-functions-md", "### Analysis Functions"))
        cells.append(new_code_cell("analysis-functions", analysis_sections["helper_functions"]))

    analysis_main_cells = split_main_analysis_into_cells(analysis_sections["main_analysis"])
    if analysis_main_cells:
        for i, (section_title, section_code) in enumerate(analysis_main_cells, start=1):
            md_id = "analysis-main-md" if i == 1 else f"analysis-main-md-{i}"
            code_id = "analysis-main" if i == 1 else f"analysis-main-{i}"
            rendered_code = append_dataframe_preview(section_code) if preview_dataframes else section_code
            cells.append(new_markdown_cell(md_id, f"### {section_title}"))
            cells.append(new_code_cell(code_id, rendered_code))
    else:
        cells.append(new_markdown_cell("analysis-main-md", "### Run Analysis and Create Plot"))
        cells.append(new_code_cell("analysis-main", ""))

    if analysis_sections["result_dump"]:
        cells.append(new_markdown_cell("analysis-result-dump-md", "### Save computed outputs", hidden=True))
        cells.append(new_code_cell("analysis-result-dump", analysis_sections["result_dump"], hidden=True))
    else:
        cells.append(new_code_cell("analysis-result-dump", hidden_result_dump_code(), hidden=True))

    cells.extend(
        [
            new_markdown_cell(
                "final-results-md",
                "## Final Result\n\nThis final cell displays the concise answer and the generated figure.",
            ),
            new_code_cell("final-results", final_answer_code()),
        ]
    )

    notebook = NotebookDocument(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
    )
    out_ipynb.parent.mkdir(parents=True, exist_ok=True)
    out_ipynb.write_text(notebook.to_json(), encoding="utf-8")


def execute_notebook_local(notebook_path: Path) -> None:
    try:
        import nbformat
        from nbclient import NotebookClient
    except Exception as exc:
        raise ExecutionContractError(
            "Notebook execution dependencies missing. Install with: uv sync --extra notebook"
        ) from exc

    nb_node = nbformat.read(notebook_path, as_version=4)
    client = NotebookClient(nb_node, timeout=900, kernel_name="python3")
    client.execute()
    nbformat.write(nb_node, notebook_path)


def execute_notebook_mcp(notebook_path: Path) -> None:
    cmd_template = os.environ.get(
        "IBL_AGENT_JUPYTER_MCP_EXEC_CMD",
        "jupyter-mcp-server execute-notebook {notebook}",
    )
    cmd = cmd_template.format(notebook=str(notebook_path))
    proc = subprocess.run(  # noqa: S603
        shlex.split(cmd),
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        details = stderr or stdout or f"exit_code={proc.returncode}"
        raise ExecutionContractError(f"MCP notebook execution failed: {details}")


def execute_notebook_cli_local(notebook_path: Path, cmd_template: str | None = None) -> tuple[str, int, str]:
    template = cmd_template or os.environ.get(
        "IBL_AGENT_NOTEBOOK_EXEC_CMD",
        "jupyter nbconvert --to notebook --execute --inplace {notebook}",
    )
    cmd = template.format(notebook=str(notebook_path))
    proc = subprocess.run(  # noqa: S603
        shlex.split(cmd),
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    stderr_tail = (proc.stderr or "").strip()[-600:]
    if proc.returncode != 0:
        details = stderr_tail or (proc.stdout or "").strip() or f"exit_code={proc.returncode}"
        raise ExecutionContractError(f"CLI notebook execution failed: {details}")
    return cmd, proc.returncode, stderr_tail


def export_notebook_html(out_ipynb: Path, out_html: Path) -> None:
    html_out: str
    try:
        import nbformat
        from nbconvert import HTMLExporter

        nb_node = nbformat.read(out_ipynb, as_version=4)
        html_out, _ = HTMLExporter().from_notebook_node(nb_node)
    except Exception:
        html_out = (
            "<html><body><h1>IBL Ask Run Notebook</h1>"
            f"<p>Notebook path: {html.escape(str(out_ipynb))}</p>"
            "<p>Install notebook extras for rich HTML export: <code>uv sync --extra notebook</code></p>"
            "</body></html>"
        )
    out_html.write_text(html_out, encoding="utf-8")
