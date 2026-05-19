from __future__ import annotations

import json

from typer.testing import CliRunner

import ibl_ai_agent.commands.ask_commands as ask_commands
import ibl_ai_agent.ask.app.preflight as preflight
from ibl_ai_agent.cli import app


class _FakeOne:
    def search(self, limit: int = 1):
        return []


def test_run_preflight_reports_missing_dependency(monkeypatch) -> None:
    real_import = preflight.importlib.import_module

    def _fake_import(name: str):
        if name == "one.api":
            raise ModuleNotFoundError("No module named 'one'")
        return real_import(name)

    monkeypatch.setattr(preflight.importlib, "import_module", _fake_import)
    monkeypatch.setattr(preflight, "connect_one", lambda **_: (_FakeOne(), object()))

    report = preflight.run_preflight(strict_auth=True, auth_mode="public", require_notebook=False)
    assert report.ok is False
    assert "import:one.api" in [c.name for c in report.fatal]
    assert any("uv sync --extra ibl" in cmd for cmd in report.fix_commands)


def test_doctor_cli_outputs_required_schema(monkeypatch) -> None:
    monkeypatch.setattr(
        ask_commands,
        "run_preflight",
        lambda **_: preflight.PreflightReport(
            checks=[preflight.PreflightCheck(name="stub", ok=True, details="ok")],
            live_one_ok=True,
            auth_mode="public",
        ),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["doctor", "--auth-mode", "public"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(["ok", "checks", "fatal", "warnings", "fix_commands"]).issubset(payload.keys())
