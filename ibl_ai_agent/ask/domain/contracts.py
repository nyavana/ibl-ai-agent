from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ExecutionBackend = Literal["auto", "cli-local", "mcp", "local"]
ExecutionBackendUsed = Literal["cli-local", "mcp", "local", "none"]
PlannerSource = Literal["injected_plan"]
PlanSource = Literal["codex_skill"]
PhaseStatus = Literal["pending", "completed", "skipped", "failed"]
PhaseKey = Literal[
    "skill_context",
    "plan",
    "code_validation",
    "notebook_render",
    "notebook_execute",
    "result_extract",
]


class AnalysisNotebookSections(BaseModel):
    imports: str = ""
    constants: str = ""
    declarations: str = ""
    helper_functions: str = ""
    main_analysis: str = ""
    result_dump: str = ""


class AskPlanPayload(BaseModel):
    plan_steps: list[str] = Field(min_length=1)
    required_outputs_json: dict[str, str]
    analysis_code: str = Field(min_length=1)
    analysis_notebook_sections: AnalysisNotebookSections | None = None


class QuestionInterpretation(BaseModel):
    original_question: str
    inferred_filters: dict[str, Any] = Field(default_factory=dict)
    planner: str


class AskStructuredPlan(BaseModel):
    question_interpretation: QuestionInterpretation
    load_plan: list[str] = Field(default_factory=list)
    analysis_ops: list[str] = Field(min_length=1)
    required_outputs_json: dict[str, str]
    skills_used: list[str] = Field(default_factory=list)
    analysis_code: str = Field(min_length=1)
    analysis_notebook_sections: AnalysisNotebookSections | None = None


class AnalysisResultPayload(BaseModel):
    answer: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class AskPhaseStatus(BaseModel):
    ok: bool
    status: PhaseStatus
    details: str = ""
    timestamp_utc: str


class AskNotebookExecutePhase(AskPhaseStatus):
    requested: bool
    backend_requested: ExecutionBackend
    backend_used: ExecutionBackendUsed
    fallback_used: bool
    error: str
    backend_probe: list[dict[str, Any]] = Field(default_factory=list)
    command: str = ""
    exit_code: int | None = None
    stderr_tail: str = ""
    failure_reason: str = ""


class AskResultExtractPhase(AskPhaseStatus):
    source: Literal["pending", "plan_only", "result_json", "missing_result_json", "parse_error"]


class AskPhaseMap(BaseModel):
    skill_context: AskPhaseStatus
    plan: AskPhaseStatus
    code_validation: AskPhaseStatus
    notebook_render: AskPhaseStatus
    notebook_execute: AskNotebookExecutePhase
    result_extract: AskResultExtractPhase


class NotebookExecutionResult(BaseModel):
    requested: bool
    backend_requested: ExecutionBackend
    backend_used: ExecutionBackendUsed
    fallback_used: bool
    ok: bool
    error: str = ""
    backend_probe: list[dict[str, Any]] = Field(default_factory=list)
    command: str = ""
    exit_code: int | None = None
    stderr_tail: str = ""
    failure_reason: str = ""


class AskManifest(BaseModel):
    run_id: str
    question: str
    manifest_path: str
    snapshot_id: str
    plan_source: PlanSource | str
    planner_source: PlannerSource
    question_interpretation: QuestionInterpretation
    skills_used: list[str]
    phase_status: AskPhaseMap
    errors: list[str] = Field(default_factory=list)
    notebook_ipynb_path: str | None = None
    notebook_edit_url: str | None = None
    notebook_html_path: str | None = None
    figure_path: str | None = None
    result_json_path: str | None = None
    answer_md_path: str | None = None
    execution_backend: ExecutionBackend | None = None
    execute_notebook: bool | None = None
    runtime_mode: Literal["plan_only", "full"] | None = None
    live_one_required: bool | None = None
    live_one_ok: bool | None = None
    auth_mode: Literal["public", "private"] | None = None
    failure_reason: str | None = None
