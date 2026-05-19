from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ibl_ai_agent.errors import ExecutionContractError
from ibl_ai_agent.io import dump_yaml, load_yaml


def read_yaml_object(path: Path, *, error_prefix: str) -> dict[str, Any]:
    obj = load_yaml(path)
    if not isinstance(obj, dict):
        raise ExecutionContractError(f"{error_prefix}: expected YAML/JSON object at {path}")
    return obj


def write_yaml_object(path: Path, payload: dict[str, Any]) -> None:
    dump_yaml(path, payload)


def read_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return value


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def path_str(path: Path) -> str:
    return str(path)
