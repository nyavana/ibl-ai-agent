from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
from urllib.parse import quote

from ibl_ai_agent.ask.domain.models import AskArtifacts


@dataclass(frozen=True)
class RunArtifacts:
    paths: AskArtifacts

    @classmethod
    def create(cls, *, report_dir: Path, question: str, run_name: str | None) -> RunArtifacts:
        run_id = f"{_now_stamp()}-{_slugify(run_name or question)}"
        run_dir = report_dir / run_id
        notebook_dir = run_dir / "notebooks"
        notebook_ipynb = notebook_dir / "analysis.ipynb"
        notebook_html = notebook_dir / "analysis.html"
        notebook_png = notebook_dir / "analysis.png"
        notebook_edit_url = build_notebook_edit_url(notebook_ipynb)
        result_json_path = run_dir / "analysis_result.json"
        answer_md = run_dir / "answer.md"
        manifest_path_out = run_dir / "ask_manifest.yaml"
        run_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            paths=AskArtifacts(
                run_id=run_id,
                run_dir=run_dir,
                notebook_dir=notebook_dir,
                notebook_ipynb=notebook_ipynb,
                notebook_html=notebook_html,
                notebook_png=notebook_png,
                notebook_edit_url=notebook_edit_url,
                result_json_path=result_json_path,
                answer_md=answer_md,
                manifest_path_out=manifest_path_out,
            )
        )


def _slugify(value: str, max_len: int = 56) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not base:
        base = "question"
    return base[:max_len].rstrip("-") or "question"


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_notebook_edit_url(notebook_ipynb: Path) -> str:
    base_url = os.environ.get("IBL_AGENT_JUPYTER_BASE_URL", "http://127.0.0.1:8888").strip()
    root_raw = os.environ.get("IBL_AGENT_JUPYTER_ROOT", str(Path.cwd()))
    root = Path(root_raw).resolve()
    nb = notebook_ipynb.resolve()
    try:
        rel = nb.relative_to(root)
        path_part = rel.as_posix()
    except Exception:
        path_part = nb.as_posix().lstrip("/")
    return f"{base_url.rstrip('/')}/lab/tree/{quote(path_part)}"
