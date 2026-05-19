from __future__ import annotations

import ast
from pathlib import Path
import re

from .domain import AskPlanPayload, AskStructuredPlan, QuestionInterpretation
from ibl_ai_agent.errors import ExecutionContractError
from ibl_ai_agent.io import load_yaml

DEFAULT_REGION_ALIASES_PATH = Path("docs/ask/region_aliases.yaml")


def load_region_maps() -> tuple[set[str], dict[str, str]]:
    payload = load_yaml(DEFAULT_REGION_ALIASES_PATH)
    canonical_raw = payload.get("canonical_regions", [])
    canonical = {str(x) for x in canonical_raw if str(x).strip()}
    aliases_raw = payload.get("aliases", {})
    aliases: dict[str, str] = {}
    if isinstance(aliases_raw, dict):
        for k, v in aliases_raw.items():
            ks = str(k).strip()
            vs = str(v).strip()
            if ks and vs:
                aliases[ks.lower()] = vs
    for c in canonical:
        aliases[c.lower()] = c
    return canonical, aliases


def extract_regions(question: str, aliases: dict[str, str], canonical: set[str]) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9/-]*", question)
    out: list[str] = []
    seen: set[str] = set()
    for t in tokens:
        mapped = aliases.get(t.lower())
        if mapped and mapped in canonical and mapped.lower() != "root" and mapped not in seen:
            seen.add(mapped)
            out.append(mapped)
    return out


def extract_labs(question: str, known_labs: list[str]) -> list[str]:
    q = question.lower()
    return [lab for lab in known_labs if lab.lower() in q]


def validate_plan_payload(obj: dict[str, object]) -> AskPlanPayload:
    try:
        return AskPlanPayload.model_validate(obj)
    except Exception as exc:
        raise ExecutionContractError(f"Plan payload validation failed: {exc}") from exc


def build_structured_plan(
    *,
    question: str,
    filters: dict[str, object],
    planner_label: str,
    skill_files: list[str],
    plan_steps: list[str],
    required_outputs: dict[str, str],
    analysis_code: str,
    analysis_sections: dict[str, str] | None,
) -> AskStructuredPlan:
    return AskStructuredPlan(
        question_interpretation=QuestionInterpretation(
            original_question=question,
            inferred_filters=filters,
            planner=planner_label,
        ),
        load_plan=[
            "Connect to open Alyx via ONE and resolve EIDs from session hints or one.search.",
            "Load trials with SessionLoader and spike sorting with SpikeSortingLoader.",
            "Normalize regions to Beryl with BrainRegions.acronym2acronym.",
        ],
        analysis_ops=plan_steps,
        required_outputs_json=required_outputs,
        skills_used=skill_files,
        analysis_code=analysis_code,
        analysis_notebook_sections=analysis_sections,
    )


def validate_analysis_code(analysis_code: str) -> list[str]:
    errors: list[str] = []
    code = analysis_code.strip()
    if not code:
        return ["analysis_code is empty"]
    if len(code.splitlines()) > 450:
        errors.append("analysis_code exceeds 450 lines; keep code minimal")

    for token in ["analysis_result", "FIGURE_PATH", "RESULT_JSON_PATH"]:
        if token not in code:
            errors.append(f"analysis_code missing required token: {token}")

    if "savefig(" not in code:
        errors.append("analysis_code must save a plot with savefig(... FIGURE_PATH ...)")

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"analysis_code syntax error: {exc}"]

    banned_modules = {"subprocess", "socket", "requests", "httpx"}
    banned_call_names = {"eval", "exec", "compile", "__import__"}
    banned_attrs = {
        "os.system",
        "os.popen",
        "subprocess.run",
        "subprocess.Popen",
        "subprocess.call",
        "requests.get",
        "requests.post",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in banned_modules:
                    errors.append(f"forbidden import in analysis_code: {alias.name}")
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in banned_modules:
                errors.append(f"forbidden import-from in analysis_code: {node.module}")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in banned_call_names:
                errors.append(f"forbidden call in analysis_code: {node.func.id}()")
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                attr_name = f"{node.func.value.id}.{node.func.attr}"
                if attr_name in banned_attrs:
                    errors.append(f"forbidden call in analysis_code: {attr_name}()")

    return sorted(set(errors))
