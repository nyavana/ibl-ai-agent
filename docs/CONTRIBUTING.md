# Contributing

## Setup

```bash
UV_CACHE_DIR=.uv-cache uv sync --extra ibl --extra notebook
```

## Quality gates

```bash
UV_CACHE_DIR=.uv-cache uv run ruff check .
UV_CACHE_DIR=.uv-cache uv run pytest -q
```

## Refactor rules

- Keep `ibl_ai_agent/ask` layered (`domain`, `app`, `infra`).
- Add/adjust architecture guard tests when moving responsibilities.
- Prefer typed contracts over untyped dict plumbing in runtime internals.
- Keep CLI commands thin; shared behavior should live in `commands/common.py` or `commands/kernel.py`.

## Docs policy

Authoritative docs are:

- `docs/ARCHITECTURE.md`
- `docs/ask/ASK_RUNTIME.md`
- `docs/CONTRIBUTING.md`

If behavior changes, update docs in the same PR.
