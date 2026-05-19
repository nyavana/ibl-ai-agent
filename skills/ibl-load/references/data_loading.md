## Purpose
Short default loading policy for IBL and Brain Wide Map questions.

## Policy
- Default to aggregate-first loading for general IBL data questions.
- For Brain Wide Map questions, follow `bwm_runtime_policy.md` first.
- Use `brainwidemap` as the upstream BWM fallback layer, not as the mandatory opening move.
- Treat session-level ONE objects and `brainbox` loaders as fallback paths.
- Keep generated scripts lean: no CLI flags, no config plumbing, no speculative fallback branches.
- Large reusable datasets are user-local, not repo state. Resolve configured roots with `data_locations.local.yaml` / `ibl_ai_agent.data_locations`; do not assume `reports/datasets`.

## Non-BWM default decision path
Use the smallest loading surface that matches the question.

1. Session discovery or dataset availability:
   - start with `ONE.search(...)`, `one.list_datasets(...)`, or `one.list_collections(...)`
2. Behavioral trial questions for one or a few sessions:
   - prefer `one.load_object(eid, "trials", attribute=[...])`
3. Session-level neural questions for one or a few probes:
   - prefer probe-scoped ALF objects or `SpikeSortingLoader`
4. Region mapping, acronym conversion, or hierarchy questions:
   - use `BrainRegions` plus `brain_regions_qc.md`
5. Cross-session Brain Wide Map questions:
   - switch to the BWM path below rather than session-by-session loading

Rules:
- Discover first, then load.
- Restrict to needed fields and collections.
- Do not default to live Alyx or remote ONE queries unless the task explicitly needs server-backed discovery or downloads.
- If a question is answerable from a configured local dataset or already-cached files, prefer that path over remote-first examples.
- If a local dataset path is needed but not configured, stop with a setup note pointing to `docs/data_locations.md`.

## High-impact loading defaults
1. Discover first, load second.
2. Load the smallest object that answers the question.
3. Restrict object fields with `attribute=[...]` when possible.
4. Restrict dataset paths with `collection=...` for probe-scoped data.
5. Use `download_only=True` when staging files for later parsing.

## BWM default loading order
Use `bwm_runtime_policy.md` as the canonical BWM loading order. It owns:
- local `bwm_ephys` / `bwm_behavior` schema discovery;
- row-grain table selection;
- upstream helper fallback order;
- rules against invented aggregate tags and speculative fallback branches.

Use `bwm_ephys_spike_example.md` for concrete local spike-shard code, and `bwm_fallback_preflight.md` when a needed field is absent from local BWM or aggregate/unit tables.

## When To Open Extra References
- Use `bwm_paper_repo.md` only when the task specifically depends on upstream paper-helper behavior.
- Use `bwm_fallback_preflight.md` when a required field is absent from `bwm_ephys`, `bwm_units`, or `clusters.pqt`.
- Use `data_loading_live_one.md` for live ONE, Alyx, remote camera access, or server-backed discovery examples.
- Use `data_loading_fallback_examples.md` for local-cache fallback snippets or session-loader fallback examples.
