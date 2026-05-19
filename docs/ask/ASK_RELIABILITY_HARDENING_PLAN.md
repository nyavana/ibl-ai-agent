# Ask Runtime Reliability Hardening Plan

## Goal
Create a robust `ibl-ai-agent ask` experience that succeeds in fresh, restricted, sandboxed, and typical developer environments without the failure chain observed during interactive runs.

## Scope
This plan covers code changes, docs/instructions, install/bootstrap flow, runtime fallback behavior, and CI hardening.

## Codex End-to-End Execution Protocol
This section defines how Codex should execute this plan autonomously without stopping for manual guidance, except true hard blockers.

### Operating Mode
1. Execute phases in order: Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5 -> Phase 6 -> Phase 7 -> Phase 8.
2. Do not stop at planning. Implement code, tests, docs, and verification for each phase before moving on.
3. Only pause for user input on hard blockers:
   - missing/invalid credentials that cannot be generated locally
   - sandbox/escalation denial for required commands
   - external service outage preventing mandatory verification
4. If blocked, report:
   - exact blocker
   - commands attempted
   - next command to run once unblocked

### Command and Escalation Policy
1. Use repository-local cache/runtime defaults in all commands:
   - `UV_CACHE_DIR=.uv-cache`
   - `IPYTHONDIR=.ipython`
   - `MPLCONFIGDIR=.mplconfig`
   - `JUPYTER_RUNTIME_DIR=.jupyter_runtime`
2. Bootstrap command for fresh environments:
   - `UV_CACHE_DIR=.uv-cache uv sync --extra ibl --extra notebook`
3. If a required command fails due to sandbox/network restrictions, immediately retry with escalation.
4. Prefer deterministic non-interactive commands for validation:
   - `uv run ibl-ai-agent doctor`
   - `uv run ibl-ai-agent ask ... --plan-file ...`
   - `pytest -q tests/...`

### ONE/Alyx Auth Handling Policy
1. Default mode is strict live auth for free-form `ask`.
2. Preflight auth check must run before notebook rendering/execution.
3. If auth fails in strict mode:
   - fail hard
   - print setup and verification commands
   - do not consume fallback CSV scientific data
4. Allow fallback data only when explicitly enabled.

### Per-Phase Exit Criteria (Mandatory)
1. Phase 1 exit:
   - `doctor` implemented and tested
   - `ask` preflight blocks missing deps/auth with actionable fix commands
2. Phase 2 exit:
   - backend probe implemented
   - `auto` ordering is `cli-local -> local -> mcp`
   - manifest records backend probe + execution diagnostics
3. Phase 3 exit:
   - analysis compute fallback implemented for execution failures
   - strict-auth mode never substitutes fallback CSV silently
4. Phase 4 exit:
   - runtime env dirs forced repo-local and created automatically
5. Phase 5 exit:
   - standardized actionable errors with retry command
6. Phase 6 exit:
   - docs updated across `README.md`, `docs/ask/ASK_RUNTIME.md`, `AGENTS.md`
7. Phase 7 exit:
   - CI/tests cover all listed regressions
8. Phase 8 exit:
   - rollout checklist complete and validated

### Required Verification Commands
Run these after each relevant phase and before final completion:
1. Lint/type/unit subset (project-appropriate):
   - `pytest -q tests/test_ask.py tests/test_live_run.py`
2. New reliability tests:
   - `pytest -q tests/test_doctor.py tests/test_notebook_backend_probe.py tests/test_fallback_analysis_execution.py tests/test_auth_strict_mode.py`
3. Runtime smoke checks:
   - `UV_CACHE_DIR=.uv-cache uv run ibl-ai-agent doctor`
   - `UV_CACHE_DIR=.uv-cache uv run ibl-ai-agent ask \"Across PO, LP, and LGv, which region shows the shortest visual response latency and how does median firing rate differ between regions?\" --plan-file /tmp/plan_po_lp_lgv_latency_fr.yaml --execution-backend auto`

### Artifact Contract (What Codex Must Leave Behind)
1. Code and tests implementing all accepted changes.
2. Updated docs listed in this plan.
3. At least one successful strict-auth smoke run artifact set under `reports/ask_runs/<run_id>/` OR a hard-fail artifact proving strict-auth enforcement with actionable instructions.
4. Final implementation summary including:
   - files changed
   - tests run and results
   - known residual risks

## Observed Failure Modes To Eliminate
1. Dependencies missing on first run (`ModuleNotFoundError: one`).
2. `uv run` attempts implicit network/install and fails in offline/restricted environments.
3. `auto` notebook backend attempts incompatible MCP invocation (`execute-notebook` command mismatch).
4. Local notebook execution fails with permissions (`Operation not permitted`).
5. Result extraction fails when notebook execution fails (`analysis_result.json` missing).
6. Runtime warnings for unwritable user dirs (`~/.ipython`) in constrained environments.
7. Final answer becomes non-informative when result JSON is absent.
8. In-process notebook execution path may be less portable than a subprocess CLI path in some environments.
9. Live ONE/Alyx auth failures can be silently masked by fallback CSV data in normal ask flows.

## New Policy: Fail Hard on ONE/Alyx Auth Failure
1. Default behavior for free-form `ibl-ai-agent ask` runs must require live ONE/Alyx access.
2. If ONE/Alyx authentication fails, stop execution immediately with a clear actionable setup error.
3. Do not silently use fallback clusters/decoding data in normal ask mode.
4. Allow fallback data only in explicit modes:
   - explicit validation flows
   - explicit `--allow-fallback-data` flag (default `false`)
5. Manifest/report must include:
   - `live_one_required`
   - `live_one_ok`
   - `auth_mode` (`public` or `private`)
   - `fallback_data_used`
   - `failure_reason`

## Phase 0: Define Success Criteria
1. Define green-run contract: `ibl-ai-agent ask` returns scientific answer and writes notebook/html/plan/manifest/result JSON.
2. Define degraded-mode contract: if notebook execution fails, answer still includes computed result from fallback execution path.
3. Define environment contract: fresh clone + documented bootstrap commands work on macOS/Linux without manual debugging.
4. Add criteria to `docs/ask/ASK_RUNTIME.md`.

## Phase 1: Bootstrap and Preflight Reliability
1. Add `ibl-ai-agent doctor` CLI command under `ibl_ai_agent/commands`.
2. Add checks for imports (`one`, `brainbox`, `iblatlas`, `nbclient`), kernel availability, writable runtime dirs, backend capability, and manifest existence.
3. Add `doctor` output schema: `ok`, `checks[]`, `fatal[]`, `warnings[]`, `fix_commands[]`.
4. Make `ibl-ai-agent ask` run preflight and fail fast with one actionable error block if fatal checks fail.
5. Add explicit first-run bootstrap command to docs: `UV_CACHE_DIR=.uv-cache uv sync --extra ibl --extra notebook`.
6. Update `README.md` quickstart to require extras before `uv run ibl-ai-agent ask`.
7. Add explicit preflight auth check against configured Alyx endpoint before notebook render/execute.
8. If auth is missing/invalid, fail fast with concrete setup instructions (interactive and non-interactive paths).

### Phase 1 Acceptance Tests
1. Fresh env without extras: `doctor` fails with clear fix command.
2. After sync: `doctor` passes.
3. Missing/invalid Alyx auth: preflight fails before notebook execution.

## Phase 2: Notebook Backend Selection Fix
1. Refactor backend selection in `ibl_ai_agent/ask/app/notebook_execution.py`: `auto` must probe capabilities, not just binary presence.
2. Implement MCP capability probe to verify actual notebook execution support.
3. If MCP incompatible, skip MCP and continue to local backend without failing early.
4. Record probe results in manifest (`backend_probe`, `reason`).
5. Add a new CLI notebook backend (`cli-local`) using `jupyter nbconvert --to notebook --execute --inplace {notebook}`.
6. Add backend order policy for `auto`: `cli-local` -> `local` (in-process `nbclient`) -> `mcp`.
7. Expose configurable command via env var (for example `IBL_AGENT_NOTEBOOK_EXEC_CMD`) and capture command/exit code/stderr tail in manifest for diagnostics.

### Phase 2 Acceptance Tests
1. MCP installed but incompatible CLI shape: run succeeds via local.
2. MCP unavailable: no hard fail, local attempted.
3. `jupyter nbconvert` available: `auto` selects `cli-local` and succeeds.
4. `cli-local` fails: runtime falls through to `local`, then `mcp` only if explicitly enabled and supported.

## Phase 3: Execution Fallback That Still Produces Results
1. Add fallback pipeline step in `ibl_ai_agent/ask/app/pipeline.py`: if notebook execution fails, execute analysis code in controlled Python runner and write `analysis_result.json`.
2. Ensure fallback runner receives same runtime variables: `QUESTION`, `QUESTION_FILTERS`, `clusters_df`, `trials_df`, `decoding_df`, `FIGURE_PATH`, `RESULT_JSON_PATH`.
3. Keep notebook artifact generation even when execution fails.
4. Update answer generation logic so missing notebook execution does not imply missing scientific answer.
5. Manifest must capture both notebook execution failure and fallback execution success.
6. Clarify fallback scope: fallback execution is for compute path only, not for substituting scientific input data when live auth is required.
7. If live data loading fails due to auth in strict mode, raise hard failure with setup guidance; do not produce fallback-data scientific outputs.

### Phase 3 Acceptance Tests
1. Force notebook execution failure: answer still contains computed metrics.
2. Verify `analysis_result.json` exists after fallback.
3. Auth failure in strict mode: run fails hard and does not consume fallback CSV data.

## Phase 4: Environment Hardening for Restricted Sandboxes
1. In wrapper scripts (especially `scripts/ask_and_open_notebook.sh`), export:
   - `UV_CACHE_DIR=.uv-cache`
   - `IPYTHONDIR=.ipython`
   - `MPLCONFIGDIR=.mplconfig`
   - `JUPYTER_RUNTIME_DIR=.jupyter_runtime`
2. Ensure directories are created under repo-local writable paths.
3. Add documented non-interactive mode: `--no-execute-notebook` with guaranteed artifact creation + editable notebook URL.
4. Add fallback behavior when execution is blocked by OS policy: continue with non-notebook fallback analysis execution.

### Phase 4 Acceptance Tests
1. Environment with non-writable home dir: no fatal warnings, run succeeds.
2. Environment with notebook kernel restrictions: fallback still produces answer.

## Phase 5: Error Messaging and UX
1. Replace generic `result JSON missing` message with root-cause summary + next actions.
2. Standardize actionable error blocks: `What failed`, `Why`, `How to fix`, `Retry command`.
3. Update final answer template to include `execution mode`, `fallback used`, `result source`.
4. Ensure answer states whether values came from notebook execution or fallback runner.
5. Add a standard ONE/Alyx auth failure block:
   - What failed: ONE/Alyx authentication.
   - Why: invalid or missing credentials/session for selected endpoint.
   - How to fix: provide exact setup command(s) and endpoint.
   - Retry command: echo the original `ibl-ai-agent ask ...` command.

### Phase 5 Acceptance Tests
1. Simulate each failure class and verify user-facing fix command is included.
2. Ensure no dead-end messages remain.

## Phase 6: Documentation and Instruction Updates
1. Update `README.md` with quickstart bootstrap, `doctor`, and troubleshooting matrix.
2. Update `docs/ask/ASK_RUNTIME.md` with execution decision tree and fallback behavior.
3. Update `AGENTS.md` to require bootstrap/preflight for fresh environments.
4. Add offline/restricted environment section: wheelhouse strategy and no-network bootstrap.
5. Add troubleshooting table keyed by exact error signatures:
   - `ModuleNotFoundError: one`
   - MCP command mismatch
   - permission denied
   - missing result JSON
6. Document notebook backend preference and override examples (`--execution-backend`, `IBL_AGENT_NOTEBOOK_EXEC_CMD`).
7. Add a dedicated ONE/Alyx authentication setup section:
   - public endpoint (`https://openalyx.internationalbrainlab.org`)
   - private endpoint (`https://alyx.internationalbrainlab.org`)
   - interactive vs non-interactive auth
   - verification command before ask runs
8. Explicitly document that strict mode returns no fallback-data scientific answer when live auth is unavailable.

## Phase 7: CI and Regression Coverage
1. Add clean-environment CI job: fresh env, bootstrap extras, run one real ask smoke test.
2. Add test where MCP binary exists but command is incompatible.
3. Add test where notebook execution is denied; verify fallback still writes result JSON.
4. Add test for missing dependencies and assert clear preflight error.
5. Add test for writable-dir constraints with forced unwritable home.
6. Add test coverage for `cli-local` success/failure and backend fallback ordering.
7. Add test that ONE/Alyx auth failure causes hard failure in normal ask mode.
8. Add test that fallback CSV data is never consumed unless explicit override is enabled.

### Target Test Files
1. `tests/test_ask.py`
2. `tests/test_live_run.py`
3. New: `tests/test_doctor.py`
4. New: `tests/test_notebook_backend_probe.py`
5. New: `tests/test_fallback_analysis_execution.py`
6. New: `tests/test_auth_strict_mode.py`

## Phase 8: Rollout Plan
1. Ship in three PRs:
   - PR1: preflight + docs
   - PR2: backend probe + fallback execution
   - PR3: CI + regression hardening
2. After PR1 merge, deprecate old quickstart path.
3. After PR2 merge, enforce fallback requirement in runtime contract.
4. After PR3 merge, require clean-room smoke test before release.

## Detailed Implementation Checklist

### PR1: Bootstrap + Doctor + Docs
1. Add `doctor` command and status model.
2. Add preflight call in `ask` command path.
3. Add repo-local runtime dir exports in scripts.
4. Update README/runtime docs.
5. Add tests for dependency and writable-dir checks.
6. Add strict auth preflight and explicit `--allow-fallback-data` escape hatch (default off).

### PR2: Backend Probe + Fallback Execution
1. Implement backend probe model and auto-selection logic.
2. Add fallback analysis execution path in pipeline.
3. Update answer renderer to consume fallback results.
4. Add manifest fields for fallback provenance.
5. Add `cli-local` backend and tests for fallback order (`cli-local` -> `local` -> `mcp`).
6. Add tests for MCP mismatch and notebook permission errors.
7. Enforce no fallback-data substitution during strict-auth scientific runs.

### PR3: CI Hardening
1. Add clean-room smoke pipeline.
2. Add restricted-mode simulation tests.
3. Add failure-message snapshot tests.
4. Update contributor docs with robust local validation workflow.

## Proposed Document Changes

### `README.md`
1. Mandatory first-run bootstrap.
2. Run doctor before first ask.
3. Fallback behavior when notebook execution fails.
4. Offline/restricted setup.
5. ONE/Alyx auth setup and verification before ask runs.

### `docs/ask/ASK_RUNTIME.md`
1. Runtime state machine including fallback path.
2. Backend capability probe behavior.
3. Result-source semantics (notebook vs fallback).
4. Strict auth policy and explicit fallback-data override semantics.

### `AGENTS.md`
1. Preflight-first policy.
2. Required env vars for reliable execution.
3. Requirement for non-empty scientific answer when data loading succeeds.
4. Requirement to fail hard on live auth failure unless fallback mode is explicitly requested.

## Definition of Done
1. Fresh-environment user can run documented bootstrap and get successful ask result.
2. Ask does not fail silently on backend mismatch.
3. Notebook execution failure still yields valid result JSON and scientific answer.
4. Error messages are actionable and specific.
5. CI protects all previously observed failure classes.
6. In normal ask mode, auth failure never silently produces fallback-data scientific answers.

## Suggested Execution Order
1. Implement PR1.
2. Implement PR2.
3. Implement PR3.
4. Run validation in both fresh and restricted environments.
5. Freeze release checklist and link docs in final merge.
