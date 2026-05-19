from __future__ import annotations

from dataclasses import replace

from ibl_ai_agent.ask.constants import (
    DEFAULT_PLANNER_SOURCE,
    PHASE_CODE_VALIDATION,
    PHASE_PLAN,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from ibl_ai_agent.ask.domain import AskConfig, AskRunResult, transition_phase
from ibl_ai_agent.ask.infra.persistence import RunArtifactsStore
from ibl_ai_agent.ask.validation import validate_analysis_code
from ibl_ai_agent.errors import ExecutionContractError

from .answer import write_answer
from .context_builder import prepare_contexts
from .notebook_execution import CliLocalNotebookBackend, LocalNotebookBackend, McpNotebookBackend, NotebookExecutorRegistry
from .pipeline import run_notebook_pipeline, run_notebook_render_only_pipeline
from .planner import InjectedPlanBackend, PlannerRegistry, PlannerRequest, load_plan_payload
from .preflight import format_actionable_error, run_preflight


def run_ask(config: AskConfig) -> AskRunResult:
    if not config.question.strip():
        raise ExecutionContractError("Question must be non-empty.")
    if config.max_sessions is not None and config.max_sessions < 1:
        raise ExecutionContractError("max_sessions must be >= 1.")

    planning_context, execution_context = prepare_contexts(config)
    if config.runtime_mode == "full":
        preflight = run_preflight(
            strict_auth=True,
            auth_mode=config.auth_mode,
            auth_base_url=config.auth_base_url,
            require_notebook=config.execute_notebook,
        )
        if not preflight.ok:
            raise ExecutionContractError(
                format_actionable_error(report=preflight, retry_command=config.retry_command)
            )
        execution_context = replace(
            execution_context,
            live_one_ok=preflight.live_one_ok,
        )

    payload = load_plan_payload(injected_plan=config.injected_plan, plan_file=config.plan_file)
    if payload is None:
        raise ExecutionContractError("ask runtime is execution-only: provide injected_plan or plan_file.")

    planner_registry = PlannerRegistry([InjectedPlanBackend()])
    planner_backend = planner_registry.resolve(DEFAULT_PLANNER_SOURCE)
    plan = planner_backend.build_plan(
        PlannerRequest(
            question=planning_context.question,
            planning_context=planning_context,
            payload=payload,
        )
    )
    execution_context = replace(
        execution_context,
        phase_status=transition_phase(
            execution_context.phase_status,
            PHASE_PLAN,
            ok=True,
            status=STATUS_COMPLETED,
        ),
    )

    validation_errors = validate_analysis_code(plan.analysis_code)
    if validation_errors:
        failed_context = replace(
            execution_context,
            phase_status=transition_phase(
                execution_context.phase_status,
                PHASE_CODE_VALIDATION,
                ok=False,
                status=STATUS_FAILED,
                details="; ".join(validation_errors),
            ),
        )
        RunArtifactsStore(
            planning_context=planning_context,
            execution_context=failed_context,
            planner_source=DEFAULT_PLANNER_SOURCE,
        ).persist_failed_manifest(plan=plan, errors=validation_errors)
        raise ExecutionContractError("Generated analysis code failed validation: " + "; ".join(validation_errors))

    execution_context = replace(
        execution_context,
        phase_status=transition_phase(
            execution_context.phase_status,
            PHASE_CODE_VALIDATION,
            ok=True,
            status=STATUS_COMPLETED,
        ),
    )

    if config.runtime_mode == "plan_only":
        execution_context = replace(
            execution_context,
            execute_notebook=False,
            live_one_required=False,
            live_one_ok=None,
            failure_reason="",
        )
        execution_context, result_payload = run_notebook_render_only_pipeline(
            planning_context=planning_context,
            execution_context=execution_context,
            plan=plan,
        )
    else:
        execution_context, result_payload = run_notebook_pipeline(
            planning_context=planning_context,
            execution_context=execution_context,
            plan=plan,
            executor_registry=NotebookExecutorRegistry([CliLocalNotebookBackend(), LocalNotebookBackend(), McpNotebookBackend()]),
        )

    paths = execution_context.artifacts
    short_answer = result_payload.answer.strip() or "No answer text available."
    write_answer(
        answer_md=paths.answer_md,
        question=planning_context.question,
        short_answer=short_answer,
        question_filters=planning_context.question_filters,
        planner="codex:injected",
        manifest_path=execution_context.manifest_path_in,
        notebook_ipynb=paths.notebook_ipynb,
        notebook_edit_url=paths.notebook_edit_url,
        notebook_html=paths.notebook_html,
        notebook_png=paths.notebook_png,
        result_json_path=paths.result_json_path,
        phase_status=execution_context.phase_status,
        run_id=paths.run_id,
        snapshot_id=execution_context.snapshot_id,
        plan_source=execution_context.plan_source,
    )

    return RunArtifactsStore(
        planning_context=planning_context,
        execution_context=execution_context,
        planner_source=DEFAULT_PLANNER_SOURCE,
    ).persist_success_artifacts(plan=plan, result_payload=result_payload)
