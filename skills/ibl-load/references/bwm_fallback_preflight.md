## Purpose
Checklist for Brain Wide Map analyses that combine aggregate/unit tables with probe- or session-level fallback fields.

Use this when at least one required analysis field is not present in `bwm_units(...)` or `clusters.pqt`.

## When to use
- The analysis is anchored on `bwm_units(...)` or `clusters.pqt`.
- A required field is missing from the aggregate/unit table AND from `clusters.pqt` in bwm_ephys ≥ 1.2.0.
- You need to merge a fallback dataset back onto aggregate-filtered rows.

Note: waveform metrics (spike width, peak-to-trough, slopes, ACG) are now available in `clusters.pqt` and companion `.npy` files at the dataset root within `bwm_ephys ≥ 1.2.0`. Check those before falling back to session-level loaders.

## Mandatory preflight
1. Schema preflight
   - List the required analysis fields.
   - Mark each field as `present_in_aggregate`, `requires_fallback`, or `unknown`.
   - Do not proceed until every field has an identified source.
2. Fallback source selection
   - Enumerate candidate narrow datasets before considering heavyweight loaders.
   - Prefer revisioned cluster-level datasets when available.
   - Do not assume the default unrevisioned ALF path matches the aggregate source.
3. Alignment preflight
   - Sample 3 to 10 probes or sessions.
   - Compare aggregate keys against fallback coverage using row counts, id ranges, or sampled joins.
   - Require the sampled alignment check to pass before generating the full fallback loop.
4. Integrity gate
   - After the full merge, assert that missing fallback values are zero or below a tiny, explained threshold.
   - Treat larger failures as source misalignment, not ordinary missing data.
5. Cost gate
   - If the fallback path would trigger heavyweight loads such as full spike arrays, state that cost explicitly.
   - Keep searching for a narrower source before committing to the heavyweight path.

## Source-alignment rules
- When `bwm_units(...)` or `clusters.pqt` drives the analysis, fallback files must come from the matching sorter collection or revision.
- Use `bwm_query(...)` to recover `probe_name` or probe/session metadata needed to locate the fallback source.
- When files are already present in the local ONE cache and the cache layout is standard, prefer constructing the session path from `one.cache_dir` plus `bwm_query(...)` metadata (`lab`, `subject`, `date`, `session_number`) over repeated `one.load_dataset(...)` resolution inside a large probe loop.
- Prefer loading a single narrow field and merging it back by stable keys such as `pid` + `cluster_id`.
- If a revisioned dataset exists and the aggregate source is revision-sensitive, prefer the revisioned dataset.

## Heavyweight-loader policy
- Prefer narrow datasets like `clusters.metrics.pqt` or `clusters.peakToTrough.npy` over `SpikeSortingLoader` when both can answer the question.
- Use `SpikeSortingLoader` only when the needed field truly cannot be recovered from a narrow dataset.
- If `SpikeSortingLoader` is required, state that it may download large spike arrays and that this is an exception path.

## High-fanout local-cache policy
- Known bottleneck: a per-probe `one.load_dataset(..., download_only=True)` loop can remain very slow even when every target file is already on disk.
- The bottleneck is often ONE dataset resolution and revision/index bookkeeping, not the actual `.npy` or parquet read.
- If the question is explicitly local-cache based and the file path is deterministic, read the narrow file directly from the cache path and document the cache-layout assumption.
- Good fit: revisioned narrow files such as `alf/<probe_name>/pykilosort/#<revision>#/clusters.peakToTrough.npy`.
- Pair this with a persistent merged cache (for example a local parquet keyed by `pid` + `cluster_id`) when the join result will be reused across runs.

## Anti-patterns
- Do not generate a full fallback loading loop from a guessed probe dataset path.
- Do not treat large post-merge missing counts as normal missing data until alignment is verified.
- Do not add concurrency to the fallback path unless the underlying loader/cache path is known safe.
- Do not escalate immediately to full spike-sorting loads when a narrow revisioned cluster dataset is available.
- Do not assume that local file presence makes `one.load_dataset(...)` cheap inside a large loop.

## Question-to-operator contract
Before generating the full script, identify:
- the grouping field source,
- the primary metric source,
- the fallback metric source for each missing field,
- the join keys,
- the collection or revision alignment evidence,
- the expected post-merge integrity condition.

Do not generate the full fallback loop until each item above is verified or an explicit blocker is surfaced.
