from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import ibl_ai_agent.ask as ask_module
import ibl_ai_agent.ask.app.notebook_execution as ask_exec
import ibl_ai_agent.ask.app.orchestrator as ask_app_orchestrator
from ibl_ai_agent.ask.app.preflight import PreflightCheck, PreflightReport
from ibl_ai_agent.ask import run_ask
from ibl_ai_agent.ask.validation import validate_analysis_code
from ibl_ai_agent.errors import ExecutionContractError
from tests.ask_test_utils import injected_plan


@pytest.fixture(autouse=True)
def _stub_preflight(monkeypatch) -> None:
    monkeypatch.setattr(
        ask_app_orchestrator,
        "run_preflight",
        lambda **_: PreflightReport(
            checks=[PreflightCheck(name="stub", ok=True, details="ok")],
            live_one_ok=True,
            auth_mode="public",
        ),
    )


def test_run_ask_requires_injected_plan(tmp_path: Path) -> None:
    with pytest.raises(ExecutionContractError, match="execution-only"):
        run_ask(
            question="Compare LP and PO latency",
            manifest_path=Path("docs/ask/example_manifest.yaml"),
            report_dir=tmp_path / "ask_reports",
            execute_notebook=False,
        )


def test_run_ask_generates_notebook_and_answer(tmp_path: Path) -> None:
    result = run_ask(
        question="Which region has the fastest latency after stimulus onset, and which is slowest?",
        manifest_path=Path("docs/ask/example_manifest.yaml"),
        report_dir=tmp_path / "ask_reports",
        execute_notebook=False,
        injected_plan=injected_plan(answer="mock answer"),
    )

    assert result.run_dir.exists()
    assert result.notebook_ipynb_path.exists()
    assert result.notebook_html_path.exists()
    assert result.answer_md_path.exists()
    assert result.manifest_path.exists()
    assert result.notebook_edit_url.startswith("http://127.0.0.1:8888/lab/tree/")

    plan = yaml.safe_load((result.run_dir / "plan.yaml").read_text(encoding="utf-8"))
    assert plan["question_interpretation"]["planner"] == "codex:injected"
    assert "analysis_ops" in plan and isinstance(plan["analysis_ops"], list)
    assert any("skills/ibl-access/SKILL.md" in x for x in plan.get("skills_used", []))

    answer_text = result.answer_md_path.read_text(encoding="utf-8")
    assert "Main finding:" in answer_text
    assert "Notebook:" in answer_text
    assert "Editable notebook URL:" in answer_text
    assert (result.run_dir / "plan_full.yaml").exists()

    nb = json.loads(result.notebook_ipynb_path.read_text(encoding="utf-8"))
    cells = nb.get("cells", [])
    cell_ids = [c.get("id") for c in cells]
    assert "title" in cell_ids
    assert "setup-imports" in cell_ids
    assert "setup-constants" in cell_ids
    assert "setup-objects" in cell_ids
    assert "setup-functions" in cell_ids
    assert "setup-main" in cell_ids
    assert "analysis-main" in cell_ids
    assert "analysis-result-dump" in cell_ids
    assert "final-results" in cell_ids

    title_cell = next(c for c in cells if c.get("id") == "title")
    assert "Which region has the fastest latency after stimulus onset, and which is slowest?" in str(
        title_cell.get("source", "")
    )

    hidden_plan = next(c for c in cells if c.get("id") == "hidden-plan-vars")
    hidden_meta = hidden_plan.get("metadata", {})
    assert "hide-input" in hidden_meta.get("tags", [])
    assert hidden_meta.get("jupyter", {}).get("source_hidden") is True

    setup_constants = next(c for c in cells if c.get("id") == "setup-constants")
    setup_constants_src = str(setup_constants.get("source", ""))
    assert "SESSIONS_HINT_PATH = " in setup_constants_src
    assert "SESSIONS_HINT_PATH = '/" in setup_constants_src or "SESSIONS_HINT_PATH = None" in setup_constants_src
    assert "FALLBACK_CLUSTERS_CSV" not in setup_constants_src
    assert "FALLBACK_DECODING_CSV" not in setup_constants_src
    assert "ALLOW_FALLBACK_DATA" not in setup_constants_src

    analysis_runtime_constants = next(c for c in cells if c.get("id") == "analysis-runtime-constants")
    analysis_runtime_src = str(analysis_runtime_constants.get("source", ""))
    assert "FIGURE_PATH = '/" in analysis_runtime_src
    assert "RESULT_JSON_PATH = '/" in analysis_runtime_src


def test_run_ask_no_execute_marks_skipped(tmp_path: Path) -> None:
    result = run_ask(
        question="Draft notebook only for LP vs PO",
        manifest_path=Path("docs/ask/example_manifest.yaml"),
        report_dir=tmp_path / "ask_reports",
        execute_notebook=False,
        injected_plan=injected_plan(),
    )
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    phase = manifest["phase_status"]["notebook_execute"]
    assert phase["status"] == "skipped"
    assert phase["requested"] is False
    assert manifest["execute_notebook"] is False


def test_run_ask_uses_keyword_filters_for_regions(tmp_path: Path) -> None:
    result = run_ask(
        question="For PO and LP only, which region decodes choice best around movement?",
        manifest_path=Path("docs/ask/example_manifest.yaml"),
        report_dir=tmp_path / "ask_reports",
        execute_notebook=False,
        injected_plan=injected_plan(),
    )
    plan = yaml.safe_load((result.run_dir / "plan.yaml").read_text(encoding="utf-8"))
    filters = plan["question_interpretation"]["inferred_filters"]
    assert set(filters["regions"]) == {"PO", "LP"}


def test_generated_code_validation_rejects_forbidden_calls() -> None:
    bad_code = "import subprocess\nsubprocess.run(['echo','x'])\n"
    errors = validate_analysis_code(bad_code)
    assert errors
    assert any("forbidden" in e for e in errors)


def test_auto_backend_falls_back_to_local(tmp_path: Path, monkeypatch) -> None:
    def _fail_cli(_: Path, cmd_template: str | None = None) -> tuple[str, int, str]:
        raise ask_module.ExecutionContractError("cli unavailable")

    def _fail_mcp(_: Path) -> None:
        raise ask_module.ExecutionContractError("mcp unavailable")

    def _ok_local(_: Path) -> None:
        return None

    monkeypatch.setattr(ask_exec, "_exec_cli_local", _fail_cli)
    monkeypatch.setattr(ask_exec, "_exec_mcp", _fail_mcp)
    monkeypatch.setattr(ask_exec, "_exec_local", _ok_local)

    result = run_ask(
        question="Compare LP and PO latency",
        manifest_path=Path("docs/ask/example_manifest.yaml"),
        report_dir=tmp_path / "ask_reports",
        execute_notebook=True,
        execution_backend="auto",
        runtime_mode="full",
        injected_plan=injected_plan(),
    )

    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    phase = manifest["phase_status"]["notebook_execute"]
    assert phase["ok"] is True
    assert phase["backend_used"] == "local"
    assert phase["fallback_used"] is True


def test_plan_only_does_not_call_preflight(tmp_path: Path, monkeypatch) -> None:
    def _boom(**_: object) -> PreflightReport:
        raise AssertionError("preflight should not be called in plan_only mode")

    monkeypatch.setattr(ask_app_orchestrator, "run_preflight", _boom)
    result = run_ask(
        question="Draft-only question",
        manifest_path=Path("docs/ask/example_manifest.yaml"),
        report_dir=tmp_path / "ask_reports",
        execute_notebook=False,
        injected_plan=injected_plan(),
        runtime_mode="plan_only",
    )
    assert result.notebook_ipynb_path.exists()

def test_plan_only_result_extract_source(tmp_path: Path) -> None:
    result = run_ask(
        question="Draft-only question",
        manifest_path=Path("docs/ask/example_manifest.yaml"),
        report_dir=tmp_path / "ask_reports",
        execute_notebook=False,
        injected_plan=injected_plan(),
        runtime_mode="plan_only",
    )
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["phase_status"]["notebook_execute"]["status"] == "skipped"
    assert manifest["phase_status"]["result_extract"]["status"] == "skipped"
    assert manifest["phase_status"]["result_extract"]["source"] == "plan_only"
