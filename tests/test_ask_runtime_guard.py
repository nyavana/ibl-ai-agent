from __future__ import annotations

import ast
from pathlib import Path

RUNTIME_ROOT = Path("ibl_ai_agent/ask")
DOMAIN_FILES = sorted((RUNTIME_ROOT / "domain").glob("*.py"))
APP_FILES = sorted((RUNTIME_ROOT / "app").glob("*.py"))
INFRA_FILES = sorted((RUNTIME_ROOT / "infra").glob("*.py"))
RUNTIME_FILES = DOMAIN_FILES + APP_FILES + INFRA_FILES + [RUNTIME_ROOT / "orchestrator.py"]

BANNED_MODULES = {
    "ollama",
    "openai",
    "anthropic",
    "litellm",
    "requests",
    "httpx",
    "urllib.request",
}


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    return names


def test_runtime_modules_do_not_import_planner_network_modules() -> None:
    for path in RUNTIME_FILES:
        for name in _imports(path):
            assert name not in BANNED_MODULES, f"{path} imports banned module: {name}"


def test_runtime_modules_do_not_reference_skills_tree_paths() -> None:
    for path in RUNTIME_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value.lower()
                assert not value.startswith("skills/"), f"{path} references skills path: {node.value}"


def test_domain_layer_does_not_import_infra_or_app() -> None:
    for path in DOMAIN_FILES:
        for name in _imports(path):
            assert "ibl_ai_agent.ask.infra" not in name, f"{path} imports infra layer: {name}"
            assert "ibl_ai_agent.ask.app" not in name, f"{path} imports app layer: {name}"


def test_only_infra_layer_writes_files_directly() -> None:
    disallowed = APP_FILES + DOMAIN_FILES + [RUNTIME_ROOT / "orchestrator.py"]
    allowed_writers = {str(RUNTIME_ROOT / "app" / "preflight.py")}
    for path in disallowed:
        if str(path) in allowed_writers:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr in {"write_text", "write_bytes", "mkdir"}:
                    assert False, f"{path} performs direct filesystem write via {node.func.attr}"
