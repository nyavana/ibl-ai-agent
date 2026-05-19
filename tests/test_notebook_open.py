from pathlib import Path

from ibl_ai_agent.notebook_open import append_token_if_missing, extract_notebook_url_from_log, notebook_url_from_log_file


def test_extract_notebook_url_from_direct_url_line() -> None:
    log = "something http://127.0.0.1:8888/lab/tree/reports/ask_runs/r/notebooks/analysis.ipynb end"
    assert extract_notebook_url_from_log(log).endswith("/analysis.ipynb")


def test_extract_notebook_url_from_key_value_line() -> None:
    log = "run_id=x notebook_edit_url=http://127.0.0.1:8888/lab/tree/reports/a/notebooks/analysis.ipynb answer=y"
    assert extract_notebook_url_from_log(log).endswith("/analysis.ipynb")


def test_append_token_if_missing() -> None:
    url = "http://127.0.0.1:8888/lab/tree/reports/a/notebooks/analysis.ipynb"
    with_token = append_token_if_missing(url, "abc")
    assert with_token.endswith("analysis.ipynb?token=abc")


def test_notebook_url_from_log_file_appends_token(tmp_path: Path) -> None:
    path = tmp_path / "ask.log"
    path.write_text(
        "run_id=x notebook_edit_url=http://127.0.0.1:8888/lab/tree/reports/a/notebooks/analysis.ipynb",
        encoding="utf-8",
    )
    out = notebook_url_from_log_file(path, token="abc")
    assert out.endswith("analysis.ipynb?token=abc")
