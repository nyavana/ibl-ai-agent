from __future__ import annotations

import json
from pathlib import Path

from ibl_ai_agent.ask.constants import REPORT_CAVEATS_PATH, REPORT_TEMPLATE_PATH
from ibl_ai_agent.ask.domain import AskPhaseMap
from ibl_ai_agent.ask.infra.io import write_text


def build_answer_markdown(
    *,
    question: str,
    short_answer: str,
    question_filters: dict[str, object],
    planner: str,
    manifest_path: Path,
    notebook_ipynb: Path,
    notebook_edit_url: str,
    notebook_html: Path,
    notebook_png: Path,
    result_json_path: Path,
    phase_status: AskPhaseMap,
    run_id: str,
    snapshot_id: str,
    plan_source: str,
) -> str:
    execution = phase_status.notebook_execute
    result_extract = phase_status.result_extract
    execution_summary = (
        f"backend_used={execution.backend_used}, "
        f"fallback_used={execution.fallback_used}, ok={execution.ok}"
    )
    template_note = (
        "- Report structure follows `skills/ibl-report/references/result_template.md`."
        if REPORT_TEMPLATE_PATH.exists()
        else ""
    )
    caveat_note = (
        "- Caveats checklist follows `skills/ibl-report/references/caveats_checklist.md`."
        if REPORT_CAVEATS_PATH.exists()
        else ""
    )
    lines = [
        "# IBL AI Agent Answer",
        "",
        f"Question: {question}",
        "",
        "Main finding:",
        short_answer,
        "",
        "Methods (short):",
        f"- Planner: `{planner}`",
        f"- Manifest: `{manifest_path}`",
        f"- Filters: `{json.dumps(question_filters, sort_keys=True)}`",
        "- Standard IBL APIs in setup: ONE, SessionLoader, SpikeSortingLoader, BrainRegions.",
        template_note,
        "",
        "Caveats:",
        "- Within the analyzed snapshot, conclusions may change with broader session coverage.",
        "- Given current QC filters, weak effects can be under-estimated.",
        "- Live ONE/Alyx access is required for full execution.",
        f"- Notebook execution status: `{execution_summary}`.",
        f"- Execution mode: `{execution.backend_requested}`; result source: `{result_extract.source}`.",
        caveat_note,
        "",
        "Provenance:",
        f"- run_id: `{run_id}`",
        f"- snapshot_id: `{snapshot_id}`",
        f"- plan_source: `{plan_source}`",
        "",
        "Artifacts:",
        f"- Notebook: `{notebook_ipynb}`",
        f"- Editable notebook URL: `{notebook_edit_url}`",
        f"- HTML preview: `{notebook_html}`",
        f"- Figure: `{notebook_png}`",
        f"- Result JSON: `{result_json_path}`",
    ]
    return "\n".join(line for line in lines if line != "") + "\n"


def write_answer(
    *,
    answer_md: Path,
    question: str,
    short_answer: str,
    question_filters: dict[str, object],
    planner: str,
    manifest_path: Path,
    notebook_ipynb: Path,
    notebook_edit_url: str,
    notebook_html: Path,
    notebook_png: Path,
    result_json_path: Path,
    phase_status: AskPhaseMap,
    run_id: str,
    snapshot_id: str,
    plan_source: str,
) -> None:
    write_text(
        answer_md,
        build_answer_markdown(
            question=question,
            short_answer=short_answer,
            question_filters=question_filters,
            planner=planner,
            manifest_path=manifest_path,
            notebook_ipynb=notebook_ipynb,
            notebook_edit_url=notebook_edit_url,
            notebook_html=notebook_html,
            notebook_png=notebook_png,
            result_json_path=result_json_path,
            phase_status=phase_status,
            run_id=run_id,
            snapshot_id=snapshot_id,
            plan_source=plan_source,
        ),
    )
