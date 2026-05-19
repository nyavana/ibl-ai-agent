from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

FIXTURE_PLAN_PATH = Path("tests/fixtures/ask/injected_plan.yaml")


def injected_plan(answer: str = "fixture answer") -> dict[str, Any]:
    payload = yaml.safe_load(FIXTURE_PLAN_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Invalid fixture payload: {FIXTURE_PLAN_PATH}")
    code = str(payload.get("analysis_code", "")).replace("__ANSWER__", answer)
    payload["analysis_code"] = code
    return payload
