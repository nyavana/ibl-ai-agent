from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .contracts import AskPhaseMap, ExecutionBackend

RuntimeMode = Literal["plan_only", "full"]


@dataclass(frozen=True)
class AskRunResult:
    run_id: str
    run_dir: Path
    notebook_ipynb_path: Path
    notebook_html_path: Path
    notebook_edit_url: str
    answer_md_path: Path
    manifest_path: Path


@dataclass(frozen=True)
class AskPlanningContext:
    question: str
    question_filters: dict[str, object]
    max_sessions: int | None
    skill_context: str
    skill_files: list[str]


@dataclass(frozen=True)
class AskArtifacts:
    run_id: str
    run_dir: Path
    notebook_dir: Path
    notebook_ipynb: Path
    notebook_html: Path
    notebook_png: Path
    notebook_edit_url: str
    result_json_path: Path
    answer_md: Path
    manifest_path_out: Path


@dataclass(frozen=True)
class AskExecutionContext:
    artifacts: AskArtifacts
    manifest_path_in: Path
    snapshot_id: str
    plan_source: str
    phase_status: AskPhaseMap
    sessions_hint_path: Path | None
    execute_notebook: bool
    runtime_mode: RuntimeMode
    execution_backend: ExecutionBackend
    live_one_required: bool
    live_one_ok: bool | None
    auth_mode: str
    failure_reason: str


@dataclass(frozen=True)
class AskConfig:
    question: str
    manifest_path: Path
    report_dir: Path
    execute_notebook: bool = False
    run_name: str | None = None
    plan_source: str = "codex_skill"
    max_sessions: int | None = None
    execution_backend: ExecutionBackend = "auto"
    auth_mode: str = "public"
    auth_base_url: str | None = None
    runtime_mode: RuntimeMode = "plan_only"
    use_sessions_hint: bool = True
    retry_command: str = ""
    injected_plan: dict[str, object] | None = None
    plan_file: Path | None = None
