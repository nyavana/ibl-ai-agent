set shell := ["bash", "-euo", "pipefail", "-c"]
uv_cache_dir := ".uv-cache"

check:
    UV_CACHE_DIR={{uv_cache_dir}} uv run ruff check .
    UV_CACHE_DIR={{uv_cache_dir}} uv run pytest -q

ask question:
    UV_CACHE_DIR={{uv_cache_dir}} uv run ibl-ai-agent ask "{{question}}"

jupyter:
    UV_CACHE_DIR={{uv_cache_dir}} uv run jupyter lab --no-browser --ip=127.0.0.1 --port=8888 --ServerApp.root_dir="$(pwd)"

ask-open *question:
    ./scripts/ask_and_open_notebook.sh {{question}}

ask-draft-open *question:
    ./scripts/ask_draft_and_open_notebook.sh {{question}}

clean-runs *args:
    UV_CACHE_DIR={{uv_cache_dir}} uv run ibl-ai-agent clean-runs {{args}}
