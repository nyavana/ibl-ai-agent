from __future__ import annotations

from pathlib import Path

from .constants import (
    DOC_ATLAS_BERYL_EXAMPLE,
    DOC_BRAINBOX_ONE,
    DOC_DATA_DOWNLOAD,
    DOC_IBLATLAS_REGIONS,
    DOC_LOADING_SPIKESORTING,
    DOC_ONE_QUICKSTART,
)

ASSETS_DIR = Path(__file__).with_name("template_assets")


def _read_asset(name: str) -> str:
    return (ASSETS_DIR / name).read_text(encoding="utf-8").strip()


def setup_imports_code() -> str:
    return _read_asset("setup_imports.txt")


def setup_constants_code(
    *,
    sessions_hint_path: Path | None,
    max_sessions: int | None,
) -> str:
    template = _read_asset("setup_constants.py.tmpl")
    return template.format(
        DOC_ONE_QUICKSTART=DOC_ONE_QUICKSTART,
        DOC_DATA_DOWNLOAD=DOC_DATA_DOWNLOAD,
        DOC_BRAINBOX_ONE=DOC_BRAINBOX_ONE,
        DOC_LOADING_SPIKESORTING=DOC_LOADING_SPIKESORTING,
        DOC_IBLATLAS_REGIONS=DOC_IBLATLAS_REGIONS,
        DOC_ATLAS_BERYL_EXAMPLE=DOC_ATLAS_BERYL_EXAMPLE,
        SESSIONS_HINT_PATH=repr(str(sessions_hint_path) if sessions_hint_path else None),
        MAX_SESSIONS=repr(max_sessions),
    )


def setup_objects_code() -> str:
    return _read_asset("setup_objects.txt")


def setup_functions_code() -> str:
    return _read_asset("setup_functions.txt")


def setup_main_code() -> str:
    return _read_asset("setup_main.txt")


def setup_diagnostics_code() -> str:
    return _read_asset("setup_diagnostics.txt")


def setup_summary_code() -> str:
    return _read_asset("setup_summary.txt")


def final_answer_code() -> str:
    return _read_asset("final_answer.txt")


def hidden_result_dump_code() -> str:
    return _read_asset("hidden_result_dump.txt")
