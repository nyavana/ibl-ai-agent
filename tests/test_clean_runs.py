from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from typer.testing import CliRunner

from ibl_ai_agent.cli import app


def _make_run(root: Path, name: str, age_days: int) -> Path:
    run_dir = root / name
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = run_dir / "payload.bin"
    payload.write_bytes(b"x" * 16)
    ts = (datetime.now() - timedelta(days=age_days)).timestamp()
    os.utime(run_dir, (ts, ts))
    os.utime(payload, (ts, ts))
    return run_dir


def test_clean_runs_dry_run_keeps_files(tmp_path: Path) -> None:
    runner = CliRunner()
    ask_dir = tmp_path / "reports" / "ask_runs"
    _make_run(ask_dir, "20260303T100000Z-a", age_days=10)
    _make_run(ask_dir, "20260303T090000Z-b", age_days=10)
    _make_run(ask_dir, "20260303T080000Z-c", age_days=10)

    result = runner.invoke(
        app,
        [
            "clean-runs",
            "--scope",
            "ask",
            "--ask-dir",
            str(ask_dir),
            "--keep-last",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert "mode=DRY-RUN" in result.stdout
    assert "selected=2" in result.stdout
    assert (ask_dir / "20260303T090000Z-b").exists()
    assert (ask_dir / "20260303T080000Z-c").exists()


def test_clean_runs_apply_deletes_selected(tmp_path: Path) -> None:
    runner = CliRunner()
    ask_dir = tmp_path / "reports" / "ask_runs"
    keep = _make_run(ask_dir, "20260303T100000Z-a", age_days=10)
    delete_1 = _make_run(ask_dir, "20260303T090000Z-b", age_days=10)
    delete_2 = _make_run(ask_dir, "20260303T080000Z-c", age_days=10)

    result = runner.invoke(
        app,
        [
            "clean-runs",
            "--scope",
            "ask",
            "--ask-dir",
            str(ask_dir),
            "--keep-last",
            "1",
            "--apply",
        ],
    )

    assert result.exit_code == 0
    assert "mode=APPLY" in result.stdout
    assert keep.exists()
    assert not delete_1.exists()
    assert not delete_2.exists()


def test_clean_runs_honors_age_cutoff(tmp_path: Path) -> None:
    runner = CliRunner()
    ask_dir = tmp_path / "reports" / "ask_runs"
    keep = _make_run(ask_dir, "20260303T100000Z-a", age_days=1)
    recent_extra = _make_run(ask_dir, "20260303T090000Z-b", age_days=1)
    old_extra = _make_run(ask_dir, "20260303T080000Z-c", age_days=30)

    result = runner.invoke(
        app,
        [
            "clean-runs",
            "--scope",
            "ask",
            "--ask-dir",
            str(ask_dir),
            "--keep-last",
            "1",
            "--older-than-days",
            "7",
            "--apply",
        ],
    )

    assert result.exit_code == 0
    assert "selected=1" in result.stdout
    assert keep.exists()
    assert recent_extra.exists()
    assert not old_extra.exists()
