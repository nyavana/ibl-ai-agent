from __future__ import annotations

from pathlib import Path

DEFAULT_ASK_MANIFEST_PATH = Path("docs/ask/example_manifest.yaml")
DEFAULT_ASK_REPORT_DIR = Path("reports/ask_runs")
DEFAULT_EXECUTION_BACKEND = "auto"
DEFAULT_PLANNER_LABEL = "codex:injected"
DEFAULT_PLANNER_SOURCE = "injected_plan"

PHASE_SKILL_CONTEXT = "skill_context"
PHASE_PLAN = "plan"
PHASE_CODE_VALIDATION = "code_validation"
PHASE_NOTEBOOK_RENDER = "notebook_render"
PHASE_NOTEBOOK_EXECUTE = "notebook_execute"
PHASE_RESULT_EXTRACT = "result_extract"

STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"

SKILL_PATHS: dict[str, Path] = {
    "runtime": Path("AGENTS.md"),
    "ibl-access": Path("skills/ibl-access/SKILL.md"),
    "ibl-load": Path("skills/ibl-load/SKILL.md"),
    "ibl-analyze": Path("skills/ibl-analyze/SKILL.md"),
    "ibl-report": Path("skills/ibl-report/SKILL.md"),
}

REPORT_TEMPLATE_PATH = Path("skills/ibl-report/references/result_template.md")
REPORT_CAVEATS_PATH = Path("skills/ibl-report/references/caveats_checklist.md")
PLAN_PAYLOAD_TEMPLATE_PATH = Path("docs/ask/plan_payload_template.yaml")

DOC_ONE_QUICKSTART = "https://docs.internationalbrainlab.org/notebooks_external/one_quickstart.html"
DOC_DATA_DOWNLOAD = "https://docs.internationalbrainlab.org/notebooks_external/data_download.html"
DOC_BRAINBOX_ONE = "https://docs.internationalbrainlab.org/_autosummary/brainbox.io.one.html"
DOC_LOADING_SPIKESORTING = "https://docs.internationalbrainlab.org/notebooks_external/loading_spikesorting_data.html"
DOC_IBLATLAS_REGIONS = "https://docs.internationalbrainlab.org/_autosummary/iblatlas.regions.html"
DOC_ATLAS_BERYL_EXAMPLE = "https://docs.internationalbrainlab.org/notebooks_external/atlas_dorsal_cortex_flatmap.html"
