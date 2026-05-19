#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf '[ask-open] %s\n' "$*"
}

err_report() {
  local exit_code="$1"
  local line_no="$2"
  log "FAILED (exit=${exit_code}) at line ${line_no}: ${BASH_COMMAND}"
  log "Tip: check /tmp/ibl_jupyter.log if failure happened while starting Jupyter."
}
trap 'err_report $? $LINENO' ERR

QUESTION_DEFAULT="Across PO, LP, and LGv, which region shows the shortest visual response latency and how does median firing rate differ between regions?"
QUESTION="${*:-$QUESTION_DEFAULT}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

UV_CACHE_DIR="${UV_CACHE_DIR:-.uv-cache}"
IPYTHONDIR="${IPYTHONDIR:-.ipython}"
MPLCONFIGDIR="${MPLCONFIGDIR:-.mplconfig}"
JUPYTER_RUNTIME_DIR="${JUPYTER_RUNTIME_DIR:-.jupyter_runtime}"
JUPYTER_BASE_URL="${IBL_AGENT_JUPYTER_BASE_URL:-http://127.0.0.1:8888}"
JUPYTER_ROOT="${IBL_AGENT_JUPYTER_ROOT:-$REPO_ROOT}"
ASK_PLANNER_MODE="${ASK_PLANNER_MODE:-codex_injected}"
ASK_EXECUTION_BACKEND="${ASK_EXECUTION_BACKEND:-auto}"
ASK_RUNTIME_MODE="${ASK_RUNTIME_MODE:-plan_only}"
ASK_RUNNER="${ASK_RUNNER:-codex}"
ASK_EXECUTE_NOTEBOOK="${ASK_EXECUTE_NOTEBOOK:-0}"
ASK_PLAN_FILE="${ASK_PLAN_FILE:-}"
CODEX_SANDBOX="${CODEX_SANDBOX:-danger-full-access}"
CODEX_APPROVAL="${CODEX_APPROVAL:-never}"
CODEX_OUTPUT_MODE="${CODEX_OUTPUT_MODE:-human}"
CODEX_COLOR="${CODEX_COLOR:-always}"
CODEX_USE_PTY="${CODEX_USE_PTY:-1}"
CODEX_NO_ALT_SCREEN="${CODEX_NO_ALT_SCREEN:-1}"

log "repo_root=$REPO_ROOT"
log "uv_cache_dir=$UV_CACHE_DIR"
log "ipythondir=$IPYTHONDIR"
log "mplconfigdir=$MPLCONFIGDIR"
log "jupyter_runtime_dir=$JUPYTER_RUNTIME_DIR"
log "jupyter_base_url=$JUPYTER_BASE_URL"
log "jupyter_root=$JUPYTER_ROOT"
log "runner=$ASK_RUNNER"
log "planner_mode=$ASK_PLANNER_MODE"
log "execution_backend=$ASK_EXECUTION_BACKEND"
log "runtime_mode=$ASK_RUNTIME_MODE"
log "execute_notebook=$ASK_EXECUTE_NOTEBOOK"
log "plan_file=${ASK_PLAN_FILE:-<none>}"
log "codex_sandbox=$CODEX_SANDBOX"
log "codex_approval=$CODEX_APPROVAL"
log "codex_output_mode=$CODEX_OUTPUT_MODE"
log "codex_color=$CODEX_COLOR"
log "codex_use_pty=$CODEX_USE_PTY"
log "codex_no_alt_screen=$CODEX_NO_ALT_SCREEN"
log "question=$QUESTION"

mkdir -p "$UV_CACHE_DIR" "$IPYTHONDIR" "$MPLCONFIGDIR" "$JUPYTER_RUNTIME_DIR"

ensure_jupyter() {
  local list_out
  log "Checking whether JupyterLab is already running on :8888 ..."
  list_out="$(UV_CACHE_DIR="$UV_CACHE_DIR" IPYTHONDIR="$IPYTHONDIR" MPLCONFIGDIR="$MPLCONFIGDIR" JUPYTER_RUNTIME_DIR="$JUPYTER_RUNTIME_DIR" uv run jupyter server list 2>/dev/null || true)"

  if printf '%s\n' "$list_out" | rg -q "127\.0\.0\.1:8888|localhost:8888"; then
    log "JupyterLab is already running."
    return 0
  fi

  log "Starting JupyterLab on 127.0.0.1:8888 ..."
  nohup bash -lc "cd '$REPO_ROOT' && UV_CACHE_DIR='$UV_CACHE_DIR' IPYTHONDIR='$IPYTHONDIR' MPLCONFIGDIR='$MPLCONFIGDIR' JUPYTER_RUNTIME_DIR='$JUPYTER_RUNTIME_DIR' uv run jupyter lab --no-browser --ip=127.0.0.1 --port=8888 --ServerApp.root_dir='$JUPYTER_ROOT'" >/tmp/ibl_jupyter.log 2>&1 &
  log "Jupyter start command launched in background; log file: /tmp/ibl_jupyter.log"

  for _ in $(seq 1 30); do
    sleep 1
    list_out="$(UV_CACHE_DIR="$UV_CACHE_DIR" IPYTHONDIR="$IPYTHONDIR" MPLCONFIGDIR="$MPLCONFIGDIR" JUPYTER_RUNTIME_DIR="$JUPYTER_RUNTIME_DIR" uv run jupyter server list 2>/dev/null || true)"
    if printf '%s\n' "$list_out" | rg -q "127\.0\.0\.1:8888|localhost:8888"; then
      log "JupyterLab is now running."
      return 0
    fi
  done

  log "JupyterLab did not start within 30s."
  log "Last 60 lines of /tmp/ibl_jupyter.log:"
  tail -n 60 /tmp/ibl_jupyter.log || true
  exit 1
}

get_jupyter_token() {
  local list_out line token
  list_out="$(UV_CACHE_DIR="$UV_CACHE_DIR" IPYTHONDIR="$IPYTHONDIR" MPLCONFIGDIR="$MPLCONFIGDIR" JUPYTER_RUNTIME_DIR="$JUPYTER_RUNTIME_DIR" uv run jupyter server list 2>/dev/null || true)"
  line="$(printf '%s\n' "$list_out" | rg "127\.0\.0\.1:8888|localhost:8888" | head -n1 || true)"
  token="$(printf '%s\n' "$line" | sed -n 's/.*token=\([^[:space:]]*\).*/\1/p')"
  printf '%s' "$token"
}

assert_draft_only_manifest() {
  local manifest_path runtime_mode execute_notebook
  manifest_path="$(rg -o 'manifest=[^ ]+' "$ASK_LOG" | tail -n1 | cut -d= -f2- || true)"

  if [[ -z "$manifest_path" || ! -f "$manifest_path" ]]; then
    log "Could not find manifest path in ask log; draft mode requires an ibl-ai-agent ask run with emitted manifest=... output."
    exit 1
  fi

  runtime_mode="$(rg '^runtime_mode:' "$manifest_path" | awk '{print $2}' | tail -n1 || true)"
  execute_notebook="$(rg '^execute_notebook:' "$manifest_path" | awk '{print $2}' | tail -n1 || true)"

  if [[ "$runtime_mode" != "plan_only" || "$execute_notebook" != "false" ]]; then
    log "Draft-mode guard failed. Expected runtime_mode=plan_only and execute_notebook=false."
    log "Observed in $manifest_path: runtime_mode=${runtime_mode:-<missing>}, execute_notebook=${execute_notebook:-<missing>}"
    exit 1
  fi
}

log "Running ask flow ..."
ASK_LOG="$(mktemp /tmp/ibl_ask_open_XXXX.log)"
log "ask log file: $ASK_LOG"

if [[ "$ASK_EXECUTE_NOTEBOOK" != "1" && "$ASK_RUNTIME_MODE" != "plan_only" ]]; then
  log "Generate-only mode requires ASK_RUNTIME_MODE=plan_only."
  exit 1
fi

if [[ "$ASK_RUNNER" == "codex" ]]; then
  if [[ "$ASK_EXECUTE_NOTEBOOK" != "1" ]]; then
    log "Generate-only mode requested; still running via Codex with question-only prompt."
  fi
  PROMPT="$QUESTION"
  CODEX_JSON_FLAG=()
  CODEX_TOPLEVEL_FLAG=()
  if [[ "$CODEX_OUTPUT_MODE" == "json" ]]; then
    CODEX_JSON_FLAG=(--json --color never)
    log "Executing Codex command (JSON event stream):"
  else
    CODEX_JSON_FLAG=(--color "$CODEX_COLOR")
    if [[ "$CODEX_NO_ALT_SCREEN" == "1" ]]; then
      CODEX_TOPLEVEL_FLAG=(--no-alt-screen)
    fi
    log "Executing Codex command (human-readable live output):"
  fi
  printf 'IBL_AGENT_JUPYTER_BASE_URL=%q IBL_AGENT_JUPYTER_ROOT=%q UV_CACHE_DIR=%q codex -a %q -s %q %s exec --cd %q --ephemeral %s %q\n' \
    "$JUPYTER_BASE_URL" "$JUPYTER_ROOT" "$UV_CACHE_DIR" "$CODEX_APPROVAL" "$CODEX_SANDBOX" "${CODEX_TOPLEVEL_FLAG[*]}" "$REPO_ROOT" "${CODEX_JSON_FLAG[*]}" "$PROMPT"
  set +e
  if [[ "$CODEX_USE_PTY" == "1" ]] && command -v script >/dev/null 2>&1; then
    CODEX_CMD=(
      env
      "IBL_AGENT_JUPYTER_BASE_URL=$JUPYTER_BASE_URL"
      "IBL_AGENT_JUPYTER_ROOT=$JUPYTER_ROOT"
      "UV_CACHE_DIR=$UV_CACHE_DIR"
      "IPYTHONDIR=$IPYTHONDIR"
      "MPLCONFIGDIR=$MPLCONFIGDIR"
      "JUPYTER_RUNTIME_DIR=$JUPYTER_RUNTIME_DIR"
      "ASK_EXECUTE_NOTEBOOK=$ASK_EXECUTE_NOTEBOOK"
      "ASK_PLANNER_MODE=$ASK_PLANNER_MODE"
      "ASK_EXECUTION_BACKEND=$ASK_EXECUTION_BACKEND"
      codex -a "$CODEX_APPROVAL" -s "$CODEX_SANDBOX" "${CODEX_TOPLEVEL_FLAG[@]}" exec --cd "$REPO_ROOT" --ephemeral
      "${CODEX_JSON_FLAG[@]}" "$PROMPT"
    )
    CODEX_CMD_STR="$(printf '%q ' "${CODEX_CMD[@]}")"
    script -qefc "$CODEX_CMD_STR" /dev/null 2>&1 | tee "$ASK_LOG"
    ASK_STATUS=${PIPESTATUS[0]}
  else
    IBL_AGENT_JUPYTER_BASE_URL="$JUPYTER_BASE_URL" \
    IBL_AGENT_JUPYTER_ROOT="$JUPYTER_ROOT" \
    UV_CACHE_DIR="$UV_CACHE_DIR" \
    IPYTHONDIR="$IPYTHONDIR" \
    MPLCONFIGDIR="$MPLCONFIGDIR" \
    JUPYTER_RUNTIME_DIR="$JUPYTER_RUNTIME_DIR" \
    ASK_EXECUTE_NOTEBOOK="$ASK_EXECUTE_NOTEBOOK" \
    ASK_PLANNER_MODE="$ASK_PLANNER_MODE" \
    ASK_EXECUTION_BACKEND="$ASK_EXECUTION_BACKEND" \
    codex -a "$CODEX_APPROVAL" -s "$CODEX_SANDBOX" "${CODEX_TOPLEVEL_FLAG[@]}" exec --cd "$REPO_ROOT" --ephemeral "${CODEX_JSON_FLAG[@]}" "$PROMPT" \
      2>&1 | tee "$ASK_LOG"
    ASK_STATUS=${PIPESTATUS[0]}
  fi
  set -e
else
  if [[ -z "$ASK_PLAN_FILE" ]]; then
    log "ASK_PLAN_FILE is required for non-codex runner (execution-only ask runtime)."
    exit 1
  fi
  if [[ "$ASK_EXECUTE_NOTEBOOK" == "1" ]] && [[ "$ASK_RUNTIME_MODE" == "plan_only" ]]; then
    ASK_RUNTIME_MODE="full"
  fi
  ASK_NOTEBOOK_FLAG=(--execute-notebook)
  if [[ "$ASK_EXECUTE_NOTEBOOK" != "1" ]]; then
    ASK_NOTEBOOK_FLAG=(--no-execute-notebook)
    log "Generate-only mode requested; executing ibl-ai-agent ask without notebook execution."
  fi
  log "Executing ibl-ai-agent ask command:"
  printf 'IBL_AGENT_JUPYTER_BASE_URL=%q IBL_AGENT_JUPYTER_ROOT=%q UV_CACHE_DIR=%q uv run ibl-ai-agent ask %q --plan-file %q --runtime-mode %q %s --execution-backend %q\n' \
    "$JUPYTER_BASE_URL" "$JUPYTER_ROOT" "$UV_CACHE_DIR" "$QUESTION" "$ASK_PLAN_FILE" "$ASK_RUNTIME_MODE" "${ASK_NOTEBOOK_FLAG[*]}" "$ASK_EXECUTION_BACKEND"
  set +e
  IBL_AGENT_JUPYTER_BASE_URL="$JUPYTER_BASE_URL" \
  IBL_AGENT_JUPYTER_ROOT="$JUPYTER_ROOT" \
  UV_CACHE_DIR="$UV_CACHE_DIR" \
  IPYTHONDIR="$IPYTHONDIR" \
  MPLCONFIGDIR="$MPLCONFIGDIR" \
  JUPYTER_RUNTIME_DIR="$JUPYTER_RUNTIME_DIR" \
  uv run ibl-ai-agent ask "$QUESTION" --plan-file "$ASK_PLAN_FILE" --runtime-mode "$ASK_RUNTIME_MODE" "${ASK_NOTEBOOK_FLAG[@]}" --execution-backend "$ASK_EXECUTION_BACKEND" \
    2>&1 | tee "$ASK_LOG"
  ASK_STATUS=${PIPESTATUS[0]}
  set -e
fi

if [[ "$ASK_STATUS" -ne 0 ]]; then
  log "ask command failed with exit code $ASK_STATUS"
  exit "$ASK_STATUS"
fi

if [[ "$ASK_EXECUTE_NOTEBOOK" != "1" ]]; then
  assert_draft_only_manifest
fi

ensure_jupyter

TOKEN="$(get_jupyter_token)"
NOTEBOOK_URL="$(UV_CACHE_DIR="$UV_CACHE_DIR" IPYTHONDIR="$IPYTHONDIR" MPLCONFIGDIR="$MPLCONFIGDIR" JUPYTER_RUNTIME_DIR="$JUPYTER_RUNTIME_DIR" uv run ibl-ai-agent open-notebook-url --ask-log "$ASK_LOG" --token "${TOKEN:-}" 2>/dev/null || true)"
if [[ -z "$NOTEBOOK_URL" ]]; then
  log "Could not extract notebook_edit_url from ask output."
  exit 1
fi

log "Opening notebook: $NOTEBOOK_URL"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$NOTEBOOK_URL" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
  open "$NOTEBOOK_URL" >/dev/null 2>&1 || true
fi

log "Done."
