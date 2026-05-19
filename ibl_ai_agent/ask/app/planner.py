from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ibl_ai_agent.ask.constants import DEFAULT_PLANNER_LABEL
from ibl_ai_agent.ask.domain import AskPlanPayload, AskPlanningContext, AskStructuredPlan
from ibl_ai_agent.ask.infra.io import read_yaml_object
from ibl_ai_agent.ask.validation import build_structured_plan, validate_plan_payload
from ibl_ai_agent.errors import ExecutionContractError


@dataclass(frozen=True)
class PlannerRequest:
    question: str
    planning_context: AskPlanningContext
    payload: AskPlanPayload


class PlannerBackend(Protocol):
    name: str

    def build_plan(self, request: PlannerRequest) -> AskStructuredPlan:
        ...


class InjectedPlanBackend:
    name = "injected_plan"

    def build_plan(self, request: PlannerRequest) -> AskStructuredPlan:
        analysis_sections = (
            request.payload.analysis_notebook_sections.model_dump(mode="python")
            if request.payload.analysis_notebook_sections
            else None
        )
        return build_structured_plan(
            question=request.question,
            filters=request.planning_context.question_filters,
            planner_label=DEFAULT_PLANNER_LABEL,
            skill_files=request.planning_context.skill_files,
            plan_steps=request.payload.plan_steps,
            required_outputs=request.payload.required_outputs_json,
            analysis_code=request.payload.analysis_code,
            analysis_sections=analysis_sections,
        )


class PlannerRegistry:
    def __init__(self, backends: list[PlannerBackend]) -> None:
        self._by_name = {backend.name: backend for backend in backends}

    def resolve(self, name: str) -> PlannerBackend:
        backend = self._by_name.get(name)
        if backend is None:
            supported = ", ".join(sorted(self._by_name.keys()))
            raise ExecutionContractError(f"Unknown planner backend '{name}'. Supported: {supported}")
        return backend


def load_plan_payload(*, injected_plan: dict[str, object] | None, plan_file: Path | None) -> AskPlanPayload | None:
    if injected_plan is not None and plan_file is not None:
        raise ExecutionContractError("Use either injected_plan or plan_file, not both.")
    if plan_file is not None:
        return validate_plan_payload(read_yaml_object(plan_file, error_prefix="Invalid plan payload"))
    if injected_plan is None:
        return None
    return validate_plan_payload(injected_plan)
