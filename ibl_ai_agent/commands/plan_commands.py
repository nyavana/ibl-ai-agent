from __future__ import annotations

from pathlib import Path

import typer
import yaml

from ibl_ai_agent.ask.plan_tools import load_and_validate_plan_file, load_plan_template_payload
from ibl_ai_agent.commands.kernel import run_or_fail
from ibl_ai_agent.errors import ExecutionContractError


def register(plan_app: typer.Typer) -> None:
    @plan_app.command("create")
    def plan_create(
        question: str = typer.Argument(..., help="Free-form scientific question about IBL data."),
        out: Path = typer.Option(Path("/tmp/ask_plan.yaml"), help="Output plan payload path."),
    ) -> None:
        """Create a question-tagged starter plan payload from the skill-owned template."""
        payload = run_or_fail(
            lambda: load_plan_template_payload(question=question),
            error_type=ExecutionContractError,
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        typer.echo(f"plan_file={out}")

    @plan_app.command("validate")
    def plan_validate(
        plan_file: Path = typer.Option(..., exists=True, readable=True, help="Plan payload YAML/JSON file."),
    ) -> None:
        """Validate a plan payload against ask runtime contract."""
        run_or_fail(lambda: load_and_validate_plan_file(plan_file), error_type=ExecutionContractError)
        typer.echo(f"valid=true plan_file={plan_file}")
