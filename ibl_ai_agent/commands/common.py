from __future__ import annotations

from datetime import date
import json

import typer


def fail(message: str) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(1)


def echo_json(payload: object) -> None:
    typer.echo(json.dumps(payload, indent=2))


def parse_iso_date(name: str, value: str | None, *, error_type: type[Exception]) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise error_type(f"Invalid {name} '{value}', expected YYYY-MM-DD.") from exc
