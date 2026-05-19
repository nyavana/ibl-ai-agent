from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from .contracts import AskNotebookExecutePhase, AskPhaseMap, AskPhaseStatus, AskResultExtractPhase, PhaseKey
from ibl_ai_agent.ask.constants import (
    PHASE_CODE_VALIDATION,
    PHASE_NOTEBOOK_EXECUTE,
    PHASE_NOTEBOOK_RENDER,
    PHASE_PLAN,
    PHASE_RESULT_EXTRACT,
    PHASE_SKILL_CONTEXT,
    STATUS_PENDING,
    STATUS_SKIPPED,
)


def _phase(ok: bool, *, status: str, details: str = "") -> AskPhaseStatus:
    return AskPhaseStatus(
        ok=bool(ok),
        status=status,
        details=details.strip(),
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )


def init_phase_map() -> AskPhaseMap:
    return AskPhaseMap(
        **{
            PHASE_SKILL_CONTEXT: _phase(False, status=STATUS_PENDING),
            PHASE_PLAN: _phase(False, status=STATUS_PENDING),
            PHASE_CODE_VALIDATION: _phase(False, status=STATUS_PENDING),
            PHASE_NOTEBOOK_RENDER: _phase(False, status=STATUS_PENDING),
            PHASE_NOTEBOOK_EXECUTE: AskNotebookExecutePhase(
                **_phase(False, status=STATUS_SKIPPED).model_dump(mode="python"),
                requested=False,
                backend_requested="auto",
                backend_used="none",
                fallback_used=False,
                error="execution not requested",
            ),
            PHASE_RESULT_EXTRACT: AskResultExtractPhase(
                **_phase(False, status=STATUS_PENDING).model_dump(mode="python"),
                source="pending",
            ),
        }
    )


def transition_phase(
    phase_map: AskPhaseMap,
    key: PhaseKey,
    *,
    ok: bool,
    status: str,
    details: str = "",
    extras: dict[str, Any] | None = None,
) -> AskPhaseMap:
    payload = _phase(ok, status=status, details=details).model_dump(mode="python")
    if extras:
        payload.update(extras)

    if key == PHASE_NOTEBOOK_EXECUTE:
        next_phase = AskNotebookExecutePhase.model_validate(payload)
    elif key == PHASE_RESULT_EXTRACT:
        next_phase = AskResultExtractPhase.model_validate(payload)
    else:
        next_phase = AskPhaseStatus.model_validate(payload)

    data = phase_map.model_dump(mode="python")
    data[key] = next_phase.model_dump(mode="python")
    return AskPhaseMap.model_validate(data)


def phase_status(phase_map: AskPhaseMap, key: PhaseKey) -> AskPhaseStatus | AskNotebookExecutePhase | AskResultExtractPhase:
    return cast(AskPhaseStatus | AskNotebookExecutePhase | AskResultExtractPhase, getattr(phase_map, key))
