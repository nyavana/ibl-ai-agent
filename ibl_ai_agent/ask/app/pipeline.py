from __future__ import annotations

from dataclasses import replace

from ibl_ai_agent.ask.constants import (
    PHASE_NOTEBOOK_EXECUTE,
    PHASE_NOTEBOOK_RENDER,
    PHASE_RESULT_EXTRACT,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_SKIPPED,
)
from ibl_ai_agent.ask.domain import AnalysisResultPayload, AskExecutionContext, AskPlanningContext, AskStructuredPlan, transition_phase
from ibl_ai_agent.ask.infra.io import read_json_object
from ibl_ai_agent.ask.notebook import export_notebook_html, render_notebook

from .notebook_execution import NotebookExecutorRegistry


def run_notebook_pipeline(
    *,
    planning_context: AskPlanningContext,
    execution_context: AskExecutionContext,
    plan: AskStructuredPlan,
    executor_registry: NotebookExecutorRegistry,
) -> tuple[AskExecutionContext, AnalysisResultPayload]:
    paths = execution_context.artifacts
    render_notebook(
        question=planning_context.question,
        question_filters=planning_context.question_filters,
        plan=plan.model_dump(mode="python"),
        out_ipynb=paths.notebook_ipynb,
        out_png=paths.notebook_png,
        result_json_path=paths.result_json_path,
        sessions_hint_path=execution_context.sessions_hint_path,
        max_sessions=planning_context.max_sessions,
    )
    phase_map = transition_phase(
        execution_context.phase_status,
        PHASE_NOTEBOOK_RENDER,
        ok=True,
        status=STATUS_COMPLETED,
    )

    if execution_context.execute_notebook:
        execute_status = executor_registry.execute(paths.notebook_ipynb, execution_backend=execution_context.execution_backend)
        phase_map = transition_phase(
            phase_map,
            PHASE_NOTEBOOK_EXECUTE,
            ok=execute_status.ok,
            status=STATUS_COMPLETED if execute_status.ok else STATUS_FAILED,
            extras=execute_status.model_dump(mode="python"),
        )
    else:
        phase_map = transition_phase(
            phase_map,
            PHASE_NOTEBOOK_EXECUTE,
            ok=False,
            status=STATUS_SKIPPED,
            details="execute_notebook=False",
            extras={
                "requested": False,
                "backend_requested": execution_context.execution_backend,
                "backend_used": "none",
                "fallback_used": False,  # Backend fallback across auto order is not applicable here.
                "ok": False,
                "error": "execution skipped by configuration",
            },
        )

    export_notebook_html(paths.notebook_ipynb, paths.notebook_html)

    result_payload = None
    if paths.result_json_path.exists():
        try:
            payload_obj = read_json_object(paths.result_json_path)
            result_payload = AnalysisResultPayload.model_validate(payload_obj)
            phase_map = transition_phase(
                phase_map,
                PHASE_RESULT_EXTRACT,
                ok=True,
                status=STATUS_COMPLETED,
                extras={"source": "result_json"},
            )
        except Exception as exc:
            phase_map = transition_phase(
                phase_map,
                PHASE_RESULT_EXTRACT,
                ok=False,
                status=STATUS_FAILED,
                details=str(exc),
                extras={"source": "parse_error"},
            )
    else:
        phase_map = transition_phase(
            phase_map,
            PHASE_RESULT_EXTRACT,
            ok=False,
            status=STATUS_FAILED,
            details="result JSON missing",
            extras={"source": "missing_result_json"},
        )
    if result_payload is None:
        result_payload = AnalysisResultPayload(
            answer=(
                "Notebook execution failed to produce result JSON. "
                "See manifest notebook_execute/result_extract diagnostics."
            ),
            evidence={},
        )

    failure_reason = execution_context.failure_reason
    if not phase_map.notebook_execute.ok and phase_map.notebook_execute.error:
        failure_reason = phase_map.notebook_execute.error
    if not phase_map.result_extract.ok and phase_map.result_extract.details:
        failure_reason = phase_map.result_extract.details

    return replace(execution_context, phase_status=phase_map, failure_reason=failure_reason), result_payload


def run_notebook_render_only_pipeline(
    *,
    planning_context: AskPlanningContext,
    execution_context: AskExecutionContext,
    plan: AskStructuredPlan,
) -> tuple[AskExecutionContext, AnalysisResultPayload]:
    paths = execution_context.artifacts
    render_notebook(
        question=planning_context.question,
        question_filters=planning_context.question_filters,
        plan=plan.model_dump(mode="python"),
        out_ipynb=paths.notebook_ipynb,
        out_png=paths.notebook_png,
        result_json_path=paths.result_json_path,
        sessions_hint_path=execution_context.sessions_hint_path,
        max_sessions=planning_context.max_sessions,
    )
    phase_map = transition_phase(
        execution_context.phase_status,
        PHASE_NOTEBOOK_RENDER,
        ok=True,
        status=STATUS_COMPLETED,
    )
    phase_map = transition_phase(
        phase_map,
        PHASE_NOTEBOOK_EXECUTE,
        ok=False,
        status=STATUS_SKIPPED,
        details="runtime_mode=plan_only",
        extras={
            "requested": False,
            "backend_requested": execution_context.execution_backend,
            "backend_used": "none",
            "fallback_used": False,
            "ok": False,
            "error": "execution skipped in plan-only mode",
        },
    )
    phase_map = transition_phase(
        phase_map,
        PHASE_RESULT_EXTRACT,
        ok=False,
        status=STATUS_SKIPPED,
        details="runtime_mode=plan_only",
        extras={"source": "plan_only"},
    )
    export_notebook_html(paths.notebook_ipynb, paths.notebook_html)
    result_payload = AnalysisResultPayload(
        answer=(
            "Plan-only draft generated. Notebook contains step-by-step code cells and has not been executed."
        ),
        evidence={},
    )
    return replace(execution_context, phase_status=phase_map, failure_reason=""), result_payload
