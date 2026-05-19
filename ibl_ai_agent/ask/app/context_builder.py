from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path

from ibl_ai_agent.ask.constants import PHASE_SKILL_CONTEXT, SKILL_PATHS, STATUS_COMPLETED
from ibl_ai_agent.ask.domain import AskConfig, AskExecutionContext, AskPlanningContext, init_phase_map, transition_phase
from ibl_ai_agent.ask.infra.artifacts import RunArtifacts
from ibl_ai_agent.ask.infra.io import read_yaml_object
from ibl_ai_agent.ask.validation import extract_labs, extract_regions, load_region_maps
from ibl_ai_agent.errors import ExecutionContractError


def extract_question_filters(*, question: str, known_labs: list[str]) -> dict[str, object]:
    canonical, aliases = load_region_maps()
    return {
        "regions": extract_regions(question, aliases, canonical),
        "labs": extract_labs(question, sorted(known_labs)),
    }


def prepare_contexts(config: AskConfig) -> tuple[AskPlanningContext, AskExecutionContext]:
    artifact_service = RunArtifacts.create(report_dir=config.report_dir, question=config.question, run_name=config.run_name)
    manifest = read_yaml_object(config.manifest_path, error_prefix="Invalid manifest payload")
    artifacts = manifest.get("artifacts", {})
    if not isinstance(artifacts, dict):
        raise ExecutionContractError(f"Manifest artifacts section must be an object: {config.manifest_path}")

    sessions_file = artifacts.get("sessions_file")
    sessions_hint_path = Path(str(sessions_file)) if isinstance(sessions_file, str) and sessions_file.strip() else None
    disable_sessions_hint = (
        (not config.use_sessions_hint)
        or os.environ.get("IBL_AGENT_DISABLE_SESSIONS_HINTS", "").strip().lower() in {"1", "true", "yes", "on"}
    )
    if disable_sessions_hint:
        sessions_hint_path = None

    known_labs: list[str] = []
    if sessions_hint_path and sessions_hint_path.exists():
        payload = read_yaml_object(sessions_hint_path, error_prefix="Invalid sessions payload")
        sessions = payload.get("sessions", [])
        if isinstance(sessions, list):
            for row in sessions:
                if isinstance(row, dict):
                    lab = row.get("lab")
                    if isinstance(lab, str) and lab.strip() and lab not in known_labs:
                        known_labs.append(lab)

    question_filters = extract_question_filters(question=config.question, known_labs=known_labs)
    planning_context = AskPlanningContext(
        question=config.question,
        question_filters=question_filters,
        max_sessions=config.max_sessions,
        skill_context="",
        skill_files=[str(path) for path in SKILL_PATHS.values()],
    )

    execution_context = AskExecutionContext(
        artifacts=artifact_service.paths,
        manifest_path_in=config.manifest_path,
        snapshot_id=str(manifest.get("snapshot_id", "")),
        plan_source=config.plan_source.strip().lower(),
        phase_status=init_phase_map(),
        sessions_hint_path=sessions_hint_path,
        execute_notebook=config.execute_notebook,
        runtime_mode=config.runtime_mode,
        execution_backend=config.execution_backend,
        live_one_required=(config.runtime_mode == "full"),
        live_one_ok=None,
        auth_mode=config.auth_mode,
        failure_reason="",
    )
    execution_context = replace(
        execution_context,
        phase_status=transition_phase(
            execution_context.phase_status,
            PHASE_SKILL_CONTEXT,
            ok=True,
            status=STATUS_COMPLETED,
            details=f"files={len(planning_context.skill_files)}",
        ),
    )
    return planning_context, execution_context
