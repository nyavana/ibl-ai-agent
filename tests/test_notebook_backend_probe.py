from __future__ import annotations

from pathlib import Path

import ibl_ai_agent.ask.app.notebook_execution as nbexec
from ibl_ai_agent.ask.app.notebook_execution import CliLocalNotebookBackend, LocalNotebookBackend, McpNotebookBackend, NotebookExecutorRegistry


def test_auto_prefers_cli_local_then_local_then_mcp(monkeypatch, tmp_path: Path) -> None:
    notebook = tmp_path / "a.ipynb"
    notebook.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(CliLocalNotebookBackend, "probe", lambda self: (True, "ok"))
    monkeypatch.setattr(LocalNotebookBackend, "probe", lambda self: (True, "ok"))
    monkeypatch.setattr(McpNotebookBackend, "probe", lambda self: (True, "ok"))
    monkeypatch.setattr(nbexec, "_exec_cli_local", lambda _: ("cmd", 0, ""))

    reg = NotebookExecutorRegistry([CliLocalNotebookBackend(), LocalNotebookBackend(), McpNotebookBackend()])
    result = reg.execute(notebook, execution_backend="auto")
    assert result.ok is True
    assert result.backend_used == "cli-local"
    assert result.fallback_used is False
    assert result.backend_probe


def test_auto_skips_incompatible_mcp_probe_and_uses_local(monkeypatch, tmp_path: Path) -> None:
    notebook = tmp_path / "a.ipynb"
    notebook.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(CliLocalNotebookBackend, "probe", lambda self: (False, "missing jupyter"))
    monkeypatch.setattr(LocalNotebookBackend, "probe", lambda self: (True, "ok"))
    monkeypatch.setattr(McpNotebookBackend, "probe", lambda self: (False, "missing execute-notebook subcommand"))
    monkeypatch.setattr(nbexec, "_exec_local", lambda _: None)

    reg = NotebookExecutorRegistry([CliLocalNotebookBackend(), LocalNotebookBackend(), McpNotebookBackend()])
    result = reg.execute(notebook, execution_backend="auto")
    assert result.ok is True
    assert result.backend_used == "local"
    assert result.fallback_used is True
    mcp_probe = next(x for x in result.backend_probe if x["backend"] == "mcp")
    assert mcp_probe["supported"] is False
