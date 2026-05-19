from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import ibl_ai_agent.ask.app.orchestrator as ask_app_orchestrator
from ibl_ai_agent.ask.app.preflight import PreflightCheck, PreflightReport
from ibl_ai_agent.ask import run_ask
from ibl_ai_agent.ask.constants import PLAN_PAYLOAD_TEMPLATE_PATH
from ibl_ai_agent.ask.domain import AskManifest, AskStructuredPlan
from tests.ask_test_utils import injected_plan


@pytest.fixture(autouse=True)
def _stub_preflight(monkeypatch) -> None:
    monkeypatch.setattr(
        ask_app_orchestrator,
        "run_preflight",
        lambda **_: PreflightReport(
            checks=[PreflightCheck(name="stub", ok=True, details="ok")],
            live_one_ok=True,
            auth_mode="public",
        ),
    )


def test_run_outputs_validate_against_plan_and_manifest_contracts(tmp_path: Path) -> None:
    result = run_ask(
        question="Compare PO and LP latency",
        manifest_path=Path("docs/ask/example_manifest.yaml"),
        report_dir=tmp_path / "ask_reports",
        execute_notebook=False,
        injected_plan=injected_plan(answer="typed answer"),
    )
    plan_full = yaml.safe_load((result.run_dir / "plan_full.yaml").read_text(encoding="utf-8"))
    plan = AskStructuredPlan.model_validate(plan_full)
    assert plan.question_interpretation.planner == "codex:injected"
    assert plan.analysis_code.strip()

    manifest_raw = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    manifest = AskManifest.model_validate(manifest_raw)
    assert manifest.planner_source == "injected_plan"
    assert "planner_mode" not in manifest_raw


def test_plan_payload_template_is_contract_compatible() -> None:
    template = yaml.safe_load(PLAN_PAYLOAD_TEMPLATE_PATH.read_text(encoding="utf-8"))
    assert isinstance(template, dict)
    plan = AskStructuredPlan.model_validate(
        {
            "question_interpretation": {
                "original_question": "template validation",
                "inferred_filters": {},
                "planner": "codex:injected",
            },
            "analysis_ops": template["plan_steps"],
            "required_outputs_json": template["required_outputs_json"],
            "skills_used": [],
            "analysis_code": template["analysis_code"],
        }
    )
    assert plan.analysis_ops
