from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import os
from pathlib import Path
import shutil

from ibl_ai_agent.core.access import AccessError, AccessMode, connect_one


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    ok: bool
    details: str
    severity: str = "fatal"
    fix_command: str = ""


@dataclass(frozen=True)
class PreflightReport:
    checks: list[PreflightCheck] = field(default_factory=list)
    live_one_ok: bool | None = None
    auth_mode: str = "public"

    @property
    def fatal(self) -> list[PreflightCheck]:
        return [c for c in self.checks if not c.ok and c.severity == "fatal"]

    @property
    def warnings(self) -> list[PreflightCheck]:
        return [c for c in self.checks if not c.ok and c.severity != "fatal"]

    @property
    def ok(self) -> bool:
        return not self.fatal

    @property
    def fix_commands(self) -> list[str]:
        out: list[str] = []
        for item in self.fatal + self.warnings:
            cmd = item.fix_command.strip()
            if cmd and cmd not in out:
                out.append(cmd)
        return out

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "checks": [
                {
                    "name": c.name,
                    "ok": c.ok,
                    "severity": c.severity,
                    "details": c.details,
                    "fix_command": c.fix_command,
                }
                for c in self.checks
            ],
            "fatal": [c.name for c in self.fatal],
            "warnings": [c.name for c in self.warnings],
            "fix_commands": self.fix_commands,
            "live_one_ok": self.live_one_ok,
            "auth_mode": self.auth_mode,
        }


def configure_runtime_env() -> dict[str, str]:
    defaults = {
        "UV_CACHE_DIR": ".uv-cache",
        "IPYTHONDIR": ".ipython",
        "MPLCONFIGDIR": ".mplconfig",
        "JUPYTER_RUNTIME_DIR": ".jupyter_runtime",
    }
    resolved: dict[str, str] = {}
    for key, default_value in defaults.items():
        value = os.environ.get(key, default_value).strip() or default_value
        os.environ[key] = value
        resolved[key] = value
    home_dir = os.environ.get("IBL_AGENT_HOME_DIR", ".home").strip() or ".home"
    os.environ["HOME"] = home_dir
    resolved["HOME"] = home_dir
    return resolved


def ensure_runtime_dirs(runtime_env: dict[str, str]) -> None:
    for value in runtime_env.values():
        Path(value).mkdir(parents=True, exist_ok=True)


def _check_import(module_name: str, fix_command: str, severity: str = "fatal") -> PreflightCheck:
    try:
        importlib.import_module(module_name)
        return PreflightCheck(name=f"import:{module_name}", ok=True, details="ok", severity=severity)
    except Exception as exc:
        return PreflightCheck(
            name=f"import:{module_name}",
            ok=False,
            details=str(exc),
            severity=severity,
            fix_command=fix_command,
        )


def _check_writable_dir(path: str) -> PreflightCheck:
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".ibl_ai_agent_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return PreflightCheck(name=f"writable:{p}", ok=True, details="ok")
    except Exception as exc:
        return PreflightCheck(
            name=f"writable:{p}",
            ok=False,
            details=str(exc),
            fix_command=f"mkdir -p {p}",
        )


def _check_jupyter_cli() -> PreflightCheck:
    if shutil.which("jupyter"):
        return PreflightCheck(name="backend:cli-local", ok=True, details="jupyter CLI found", severity="warning")
    return PreflightCheck(
        name="backend:cli-local",
        ok=False,
        severity="warning",
        details="jupyter CLI not found",
        fix_command="UV_CACHE_DIR=.uv-cache uv sync --extra notebook",
    )


def _check_auth(
    *,
    strict_auth: bool,
    auth_mode: str,
    auth_base_url: str | None,
    cache_dir: str | None,
) -> tuple[PreflightCheck, bool]:
    mode = AccessMode.private if auth_mode == "private" else AccessMode.public
    try:
        one, _ = connect_one(
            mode=mode,
            base_url=auth_base_url,
            cache_dir=cache_dir,
            interactive=False,
            silent=True,
        )
        one.search(limit=1)
        return (
            PreflightCheck(name="auth:one_alyx", ok=True, details="ok"),
            True,
        )
    except (AccessError, Exception) as exc:
        severity = "fatal" if strict_auth else "warning"
        return (
            PreflightCheck(
                name="auth:one_alyx",
                ok=False,
                severity=severity,
                details=str(exc),
                fix_command=(
                    "UV_CACHE_DIR=.uv-cache uv run ibl-ai-agent access check --mode "
                    f"{auth_mode} --interactive"
                ),
            ),
            False,
        )


def run_preflight(
    *,
    strict_auth: bool,
    auth_mode: str = "public",
    auth_base_url: str | None = None,
    require_notebook: bool = True,
) -> PreflightReport:
    runtime_env = configure_runtime_env()
    ensure_runtime_dirs(runtime_env)
    checks: list[PreflightCheck] = []
    checks.extend(
        [
            _check_import("one.api", "UV_CACHE_DIR=.uv-cache uv sync --extra ibl"),
            _check_import("brainbox.io.one", "UV_CACHE_DIR=.uv-cache uv sync --extra ibl"),
            _check_import("iblatlas.regions", "UV_CACHE_DIR=.uv-cache uv sync --extra ibl"),
        ]
    )
    if require_notebook:
        checks.extend(
            [
                _check_import("nbclient", "UV_CACHE_DIR=.uv-cache uv sync --extra notebook"),
                _check_jupyter_cli(),
            ]
        )
    for _, path in runtime_env.items():
        checks.append(_check_writable_dir(path))

    auth_check, live_one_ok = _check_auth(
        strict_auth=strict_auth,
        auth_mode=auth_mode,
        auth_base_url=auth_base_url,
        cache_dir=runtime_env.get("UV_CACHE_DIR"),
    )
    checks.append(auth_check)

    return PreflightReport(checks=checks, live_one_ok=live_one_ok, auth_mode=auth_mode)


def format_actionable_error(*, report: PreflightReport, retry_command: str) -> str:
    first = report.fatal[0] if report.fatal else None
    why = first.details if first else "unknown preflight error"
    fix_lines = report.fix_commands or ["UV_CACHE_DIR=.uv-cache uv sync --extra ibl --extra notebook"]
    retry = retry_command.strip() or "UV_CACHE_DIR=.uv-cache uv run ibl-ai-agent ask ... --plan-file ..."
    lines = [
        "What failed: ask preflight checks.",
        f"Why: {why}",
        "How to fix:",
        *[f"- {cmd}" for cmd in fix_lines],
        f"Retry command: {retry}",
    ]
    return "\n".join(lines)
