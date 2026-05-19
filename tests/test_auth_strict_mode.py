from __future__ import annotations

from pathlib import Path

import pytest

import ibl_ai_agent.ask.app.orchestrator as ask_app_orchestrator
import ibl_ai_agent.ask.app.preflight as preflight
from ibl_ai_agent.ask import run_ask
from ibl_ai_agent.ask.app.preflight import PreflightCheck, PreflightReport
from ibl_ai_agent.core.access import AccessError
from ibl_ai_agent.errors import ExecutionContractError
from tests.ask_test_utils import injected_plan


def _mock_ibl_imports(monkeypatch) -> None:
    real_import = preflight.importlib.import_module

    def _fake_import(name: str):
        if name in {"one.api", "brainbox.io.one", "iblatlas.regions"}:
            return object()
        return real_import(name)

    monkeypatch.setattr(preflight.importlib, "import_module", _fake_import)


def test_preflight_auth_failure_is_fatal_in_strict_mode(monkeypatch) -> None:
    _mock_ibl_imports(monkeypatch)
    monkeypatch.setattr(preflight, "connect_one", lambda **_: (_ for _ in ()).throw(AccessError("bad auth")))
    report = preflight.run_preflight(strict_auth=True, auth_mode="public", require_notebook=False)
    assert report.ok is False
    assert any(c.name == "auth:one_alyx" for c in report.fatal)


def test_preflight_auth_failure_is_warning_when_fallback_enabled(monkeypatch) -> None:
    _mock_ibl_imports(monkeypatch)
    monkeypatch.setattr(preflight, "connect_one", lambda **_: (_ for _ in ()).throw(AccessError("bad auth")))
    report = preflight.run_preflight(strict_auth=False, auth_mode="public", require_notebook=False)
    assert report.ok is True
    assert any(c.name == "auth:one_alyx" for c in report.warnings)


def test_run_ask_fails_hard_on_strict_auth_preflight_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        ask_app_orchestrator,
        "run_preflight",
        lambda **_: PreflightReport(
            checks=[
                PreflightCheck(
                    name="auth:one_alyx",
                    ok=False,
                    severity="fatal",
                    details="invalid credentials",
                    fix_command="UV_CACHE_DIR=.uv-cache uv run ibl-ai-agent access check --mode public --interactive",
                )
            ],
            live_one_ok=False,
            auth_mode="public",
        ),
    )

    with pytest.raises(ExecutionContractError, match="What failed: ask preflight checks"):
        run_ask(
            question="Compare LP and PO latency",
            manifest_path=Path("docs/ask/example_manifest.yaml"),
            report_dir=tmp_path / "ask_reports",
            execute_notebook=False,
            runtime_mode="full",
            injected_plan=injected_plan(),
            retry_command="UV_CACHE_DIR=.uv-cache uv run ibl-ai-agent ask 'q' --plan-file '/tmp/p.yaml'",
        )
