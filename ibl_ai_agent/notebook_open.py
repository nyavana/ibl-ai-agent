from __future__ import annotations

from pathlib import Path
import re


NOTEBOOK_URL_RE = re.compile(
    r'http://127\.0\.0\.1:8888/lab/tree/[^\s"]*analysis\.ipynb(?:\?token=[^\s"]+)?'
)


def extract_notebook_url_from_log(log_text: str) -> str:
    matches = NOTEBOOK_URL_RE.findall(log_text)
    if matches:
        return matches[-1]
    key_matches = re.findall(r"notebook_edit_url=([^ \n]+)", log_text)
    if key_matches:
        return key_matches[-1].strip()
    return ""


def append_token_if_missing(url: str, token: str) -> str:
    if not url or not token or "token=" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}token={token}"


def notebook_url_from_log_file(log_path: Path, token: str = "") -> str:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return append_token_if_missing(extract_notebook_url_from_log(text), token)
