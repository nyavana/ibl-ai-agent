from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import subprocess
from typing import Protocol

from ibl_ai_agent.ask.domain import ExecutionBackend, NotebookExecutionResult
from ibl_ai_agent.ask.notebook import execute_notebook_cli_local as _exec_cli_local
from ibl_ai_agent.ask.notebook import execute_notebook_local as _exec_local
from ibl_ai_agent.ask.notebook import execute_notebook_mcp as _exec_mcp
from ibl_ai_agent.errors import ExecutionContractError


class NotebookExecutorBackend(Protocol):
    name: str

    def execute(self, notebook_path: Path) -> NotebookExecutionResult:
        ...

    def probe(self) -> tuple[bool, str]:
        ...


class LocalNotebookBackend:
    name = "local"

    def execute(self, notebook_path: Path) -> NotebookExecutionResult:
        _exec_local(notebook_path)
        return NotebookExecutionResult(
            requested=True,
            backend_requested="local",
            backend_used="local",
            fallback_used=False,
            ok=True,
            error="",
        )

    def probe(self) -> tuple[bool, str]:
        try:
            import nbclient  # noqa: F401

            return True, "nbclient available"
        except Exception as exc:
            return False, str(exc)


class CliLocalNotebookBackend:
    name = "cli-local"

    def execute(self, notebook_path: Path) -> NotebookExecutionResult:
        command, exit_code, stderr_tail = _exec_cli_local(notebook_path)
        return NotebookExecutionResult(
            requested=True,
            backend_requested="cli-local",
            backend_used="cli-local",
            fallback_used=False,
            ok=True,
            error="",
            command=command,
            exit_code=exit_code,
            stderr_tail=stderr_tail,
        )

    def probe(self) -> tuple[bool, str]:
        cmd_template = os.environ.get(
            "IBL_AGENT_NOTEBOOK_EXEC_CMD",
            "jupyter nbconvert --to notebook --execute --inplace {notebook}",
        )
        try:
            tokens = shlex.split(cmd_template)
        except Exception as exc:
            return False, f"invalid command template: {exc}"
        if not tokens:
            return False, "empty command template"
        binary = tokens[0]
        if shutil.which(binary):
            return True, f"{binary} available"
        return False, f"{binary} not found"


class McpNotebookBackend:
    name = "mcp"

    def execute(self, notebook_path: Path) -> NotebookExecutionResult:
        _exec_mcp(notebook_path)
        return NotebookExecutionResult(
            requested=True,
            backend_requested="mcp",
            backend_used="mcp",
            fallback_used=False,
            ok=True,
            error="",
        )

    def probe(self) -> tuple[bool, str]:
        cmd_template = os.environ.get(
            "IBL_AGENT_JUPYTER_MCP_EXEC_CMD",
            "jupyter-mcp-server execute-notebook {notebook}",
        )
        try:
            tokens = shlex.split(cmd_template)
        except Exception as exc:
            return False, f"invalid MCP command template: {exc}"
        if not tokens:
            return False, "empty MCP command template"
        binary = tokens[0]
        if shutil.which(binary) is None:
            return False, f"{binary} not found"
        # Capability probe: validate command shape contains execute-notebook token.
        if "execute-notebook" not in tokens:
            return False, "missing execute-notebook subcommand"
        try:
            proc = subprocess.run(  # noqa: S603
                [binary, "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if proc.returncode != 0:
                return False, f"{binary} --help exited {proc.returncode}"
        except Exception as exc:
            return False, str(exc)
        return True, "mcp command looks compatible"


class NotebookExecutorRegistry:
    def __init__(self, backends: list[NotebookExecutorBackend]) -> None:
        self._by_name = {b.name: b for b in backends}

    def _resolve(self, name: str) -> NotebookExecutorBackend:
        backend = self._by_name.get(name)
        if backend is None:
            supported = ", ".join(sorted(self._by_name.keys()))
            raise ExecutionContractError(f"Unknown notebook backend '{name}'. Supported: {supported}")
        return backend

    def execute(self, notebook_path: Path, *, execution_backend: ExecutionBackend) -> NotebookExecutionResult:
        backend = str(execution_backend).strip().lower()
        if backend not in {"auto", "cli-local", "mcp", "local"}:
            raise ExecutionContractError(
                f"Invalid execution_backend '{execution_backend}'. Use one of: auto, cli-local, mcp, local"
            )

        if backend in {"cli-local", "mcp", "local"}:
            result = self._resolve(backend).execute(notebook_path)
            return result.model_copy(update={"backend_requested": backend, "backend_probe": self._probe_results()})

        probe = self._probe_results()
        order = ["cli-local", "local", "mcp"]
        failures: list[str] = []
        last_error = ""
        for i, name in enumerate(order):
            backend_probe = next((x for x in probe if x.get("backend") == name), {})
            if not backend_probe.get("supported"):
                failures.append(f"{name}_probe_failed: {backend_probe.get('reason', 'unsupported')}")
                continue
            try:
                result = self._resolve(name).execute(notebook_path)
                return result.model_copy(
                    update={
                        "backend_requested": "auto",
                        "fallback_used": i > 0,
                        "error": "; ".join(failures),
                        "backend_probe": probe,
                    }
                )
            except Exception as exc:
                last_error = str(exc)
                failures.append(f"{name}_failed: {exc}")

        return NotebookExecutionResult(
            requested=True,
            backend_requested="auto",
            backend_used="none",
            fallback_used=True,
            ok=False,
            error="; ".join(failures),
            backend_probe=probe,
            failure_reason=last_error or "all notebook backends unavailable",
        )

    def _probe_results(self) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        for name in ["cli-local", "local", "mcp"]:
            backend = self._by_name.get(name)
            if backend is None:
                out.append({"backend": name, "supported": False, "reason": "backend not registered"})
                continue
            supported, reason = backend.probe()
            out.append({"backend": name, "supported": supported, "reason": reason})
        return out
