from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner
import yaml

from ibl_ai_agent.cli import app


def test_plan_create_writes_payload(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "plan.yaml"
    result = runner.invoke(app, ["plan", "create", "Compare PO and LP latency", "--out", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    payload = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert "plan_steps" in payload
    assert "analysis_code" in payload


def test_plan_validate_accepts_valid_payload(tmp_path: Path) -> None:
    payload = {
        "plan_steps": ["one", "two"],
        "required_outputs_json": {"answer": "string", "evidence": "object<string, any>"},
        "analysis_code": (
            "import json\n"
            "import matplotlib.pyplot as plt\n"
            "fig, ax = plt.subplots()\n"
            "ax.plot([0,1],[0,1])\n"
            "fig.savefig(FIGURE_PATH)\n"
            "analysis_result = {'answer': 'ok', 'evidence': {}}\n"
            "with open(RESULT_JSON_PATH, 'w', encoding='utf-8') as f:\n"
            "    json.dump(analysis_result, f)\n"
        ),
    }
    path = tmp_path / "valid_plan.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["plan", "validate", "--plan-file", str(path)])
    assert result.exit_code == 0
    assert "valid=true" in result.stdout


def test_plan_create_latency_question_uses_peth_operator(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "plan_latency.yaml"
    question = "Across PO, LP, and LGv, which region shows the shortest visual response latency and how does median firing rate differ?"
    result = runner.invoke(app, ["plan", "create", question, "--out", str(out)])
    assert result.exit_code == 0
    payload = yaml.safe_load(out.read_text(encoding="utf-8"))
    code = str(payload.get("analysis_code", ""))
    assert "calculate_peths" in code
    assert "latency_ms" in code
    assert "_first_column" not in code
    required = payload.get("required_outputs_json", {})
    assert "shortest_latency_region" in required
    assert "latency_ms_by_region" in required
