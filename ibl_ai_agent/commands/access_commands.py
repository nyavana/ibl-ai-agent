from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from ibl_ai_agent.commands.common import echo_json, parse_iso_date
from ibl_ai_agent.commands.kernel import run_or_fail
from ibl_ai_agent.core.access import (
    AccessError,
    AccessMode,
    AccessStatus,
    SessionQuery,
    connect_one,
    search_sessions,
)
from ibl_ai_agent.utils.envfile import load_env_file


def _connect_access(
    *,
    mode: AccessMode,
    base_url: str | None,
    username: str | None,
    password: str | None,
    cache_dir: str | None,
    env_file: Path,
    interactive: bool,
) -> tuple[Any, AccessStatus]:
    load_env_file(env_file, override=False)
    return connect_one(
        mode=mode,
        base_url=base_url,
        username=username,
        password=password,
        cache_dir=cache_dir,
        interactive=interactive,
    )


def register(access_app: typer.Typer) -> None:
    @access_app.command("check")
    def access_check(
        mode: AccessMode = typer.Option(AccessMode.public, help="Access mode: public or private"),
        base_url: str | None = typer.Option(None, help="Override Alyx base URL"),
        username: str | None = typer.Option(None, help="Alyx username"),
        password: str | None = typer.Option(None, help="Alyx password"),
        cache_dir: str | None = typer.Option(None, help="Optional ONE cache dir"),
        env_file: Path = typer.Option(
            Path(".env.private"), help="Auto-load credentials from this env file if present"
        ),
        interactive: bool = typer.Option(True, help="Allow interactive login when credentials missing"),
    ) -> None:
        """Validate ONE/Alyx connection."""
        _, status = run_or_fail(
            lambda: _connect_access(
                mode=mode,
                base_url=base_url,
                username=username,
                password=password,
                cache_dir=cache_dir,
                env_file=env_file,
                interactive=interactive,
            ),
            error_type=AccessError,
        )

        echo_json(
            {
                "mode": status.mode,
                "base_url": status.base_url,
                "interactive_auth": status.interactive_auth,
                "connected": status.connected,
                "user": status.user,
                "message": status.message,
            }
        )

    @access_app.command("search")
    def access_search(
        mode: AccessMode = typer.Option(AccessMode.public, help="Access mode: public or private"),
        base_url: str | None = typer.Option(None, help="Override Alyx base URL"),
        username: str | None = typer.Option(None, help="Alyx username"),
        password: str | None = typer.Option(None, help="Alyx password"),
        cache_dir: str | None = typer.Option(None, help="Optional ONE cache dir"),
        env_file: Path = typer.Option(
            Path(".env.private"), help="Auto-load credentials from this env file if present"
        ),
        interactive: bool = typer.Option(True, help="Allow interactive login when credentials missing"),
        subject: str | None = typer.Option(None, help="Subject nickname"),
        lab: str | None = typer.Option(None, help="Lab name"),
        task_protocol: str | None = typer.Option(None, help="Task protocol substring"),
        dataset: str | None = typer.Option(None, help="Dataset pattern, e.g. spikes.times"),
        date_start: str | None = typer.Option(None, help="Start date (YYYY-MM-DD)"),
        date_end: str | None = typer.Option(None, help="End date (YYYY-MM-DD)"),
        limit: int = typer.Option(20, min=1, max=500, help="Maximum sessions to return"),
    ) -> None:
        """Search sessions via ONE with optional filters."""

        def _run_search() -> tuple[Any, AccessStatus, list[dict[str, Any]]]:
            one, status = _connect_access(
                mode=mode,
                base_url=base_url,
                username=username,
                password=password,
                cache_dir=cache_dir,
                env_file=env_file,
                interactive=interactive,
            )
            rows = search_sessions(
                one,
                SessionQuery(
                    subject=subject,
                    lab=lab,
                    task_protocol=task_protocol,
                    dataset=dataset,
                    date_start=parse_iso_date("date_start", date_start, error_type=AccessError),
                    date_end=parse_iso_date("date_end", date_end, error_type=AccessError),
                    limit=limit,
                ),
            )
            return one, status, rows

        _, status, rows = run_or_fail(_run_search, error_type=AccessError)

        echo_json(
            {
                "mode": status.mode,
                "base_url": status.base_url,
                "count": len(rows),
                "sessions": rows,
            }
        )
