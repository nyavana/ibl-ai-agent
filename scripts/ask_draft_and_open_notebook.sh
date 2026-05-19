#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

export ASK_RUNNER="${ASK_RUNNER:-codex}"
export ASK_EXECUTE_NOTEBOOK=0
export ASK_PLANNER_MODE="${ASK_PLANNER_MODE:-auto}"
export ASK_EXECUTION_BACKEND="${ASK_EXECUTION_BACKEND:-auto}"
export ASK_RUNTIME_MODE="${ASK_RUNTIME_MODE:-plan_only}"

exec ./scripts/ask_and_open_notebook.sh "$@"
