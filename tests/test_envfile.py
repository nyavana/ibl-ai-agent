from __future__ import annotations

import os
from pathlib import Path

from ibl_ai_agent.utils.envfile import load_env_file


def test_load_env_file_basic(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("IBL_ALYX_USERNAME", raising=False)
    envf = tmp_path / ".env.private"
    envf.write_text(
        "\n".join(
            [
                "# comment",
                "export IBL_ALYX_USERNAME=alice",
                "IBL_ALYX_PASSWORD='secret'",
            ]
        ),
        encoding="utf-8",
    )
    out = load_env_file(envf)
    assert out["IBL_ALYX_USERNAME"] == "alice"
    assert out["IBL_ALYX_PASSWORD"] == "secret"
    assert os.environ["IBL_ALYX_USERNAME"] == "alice"


def test_load_env_file_no_override(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("IBL_ALYX_USERNAME", "already_set")
    envf = tmp_path / ".env.private"
    envf.write_text("IBL_ALYX_USERNAME=from_file\n", encoding="utf-8")
    out = load_env_file(envf, override=False)
    assert "IBL_ALYX_USERNAME" not in out
    assert os.environ["IBL_ALYX_USERNAME"] == "already_set"
