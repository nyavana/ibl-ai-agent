from __future__ import annotations

from pathlib import Path

from ibl_ai_agent.ask.app.orchestrator import run_ask as _run_ask
from ibl_ai_agent.ask.constants import DEFAULT_ASK_MANIFEST_PATH, DEFAULT_ASK_REPORT_DIR, DEFAULT_EXECUTION_BACKEND
from ibl_ai_agent.ask.domain import AskConfig, AskRunResult, ExecutionBackend, RuntimeMode


def run_ask(
    *,
    question: str,
    manifest_path: Path = DEFAULT_ASK_MANIFEST_PATH,
    report_dir: Path = DEFAULT_ASK_REPORT_DIR,
    execute_notebook: bool = False,
    run_name: str | None = None,
    max_sessions: int | None = None,
    execution_backend: ExecutionBackend = DEFAULT_EXECUTION_BACKEND,
    auth_mode: str = "public",
    auth_base_url: str | None = None,
    runtime_mode: RuntimeMode = "plan_only",
    retry_command: str = "",
    injected_plan: dict[str, object] | None = None,
    plan_file: Path | None = None,
    config: AskConfig | None = None,
) -> AskRunResult:
    cfg = config or AskConfig(
        question=question,
        manifest_path=manifest_path,
        report_dir=report_dir,
        execute_notebook=execute_notebook,
        run_name=run_name,
        max_sessions=max_sessions,
        execution_backend=execution_backend,
        auth_mode=auth_mode,
        auth_base_url=auth_base_url,
        runtime_mode=runtime_mode,
        retry_command=retry_command,
        injected_plan=injected_plan,
        plan_file=plan_file,
    )
    return _run_ask(cfg)
