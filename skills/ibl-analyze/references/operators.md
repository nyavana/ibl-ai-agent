## Purpose
Compact operator routing for common IBL scientific analyses.

## Sources
Verified against Brainbox docs and SciPy docs on 2026-03-03.

## Operator Map
| Question shape | Preferred operator/path |
| --- | --- |
| good units by lab/insertion/region | local `bwm_ephys` insertion/unit metadata, then `bwm_query` / `bwm_units` / aggregates |
| unit-feature association by region | pandas grouping plus SciPy correlation on aligned finite values |
| visual response latency | stored matching event-response feature, otherwise `visual_latency.md` recomputation |
| choice/stimulus/movement decoding | BWM decoding conventions plus `brainbox.population.decode` |
| event responsiveness or selectivity | `brainbox.task.closed_loop` after semantic match check |
| movement/quiescence | `bwm_behavior` state epochs or wheel-derived states plus spike counts |
| passive responsiveness | passive-response features or passive assets plus spikes |
| region aggregation | `BrainRegions` mapping via `../../ibl-load/references/brain_regions_qc.md` |
| pooled spike-time ACG / CCG-like timing | use `brainbox.singlecell.acorr` or related Brainbox spike-time operators when all-time spike timing is the intended quantity; use custom binned ACF only when state windows, rate traces, or custom detrending define the quantity |

## General Rules
- Match operator to scientific quantity before coding; do not force profile-specific metrics onto free-form questions.
- Prefer local BWM tables and shards when their schema covers the question.
- Use aggregate/release tables for release-wide metadata summaries; avoid session/probe loops unless a required field is absent.
- For paired statistics, align rows, drop/handle NaNs explicitly, verify nonzero variance where relevant, and report denominators.
- Fix random seeds before decoding or train/test splits and record split strategy.
- For ACG/CCG-style metrics, report bin size, window semantics, zero-lag handling, positive-lag range, normalization, and whether the scalar summarizes mass width, peak height, decay, or another shape component.
- For pooled population ACGs, inspect unit dominance, rhythmicity, and cross-unit synchrony risks before interpreting width as a timescale; see `scientific_caveats/pooled_population_acg.md`.

## BWM Loading Route
- Metadata/count questions: local `bwm_ephys` metadata, then `bwm_query`, `bwm_units`, or aggregate tables.
- Spike/event questions: local `bwm_ephys` units/events/spike shards, then `load_good_units` and `load_trials_and_mask` only as fallback.
- Wheel/movement questions: local `bwm_behavior` first; `SessionLoader.load_wheel()` only when local derived tables are insufficient.
- Missing-field fallbacks must preserve release filters and follow `../../ibl-load/references/bwm_fallback_preflight.md`.

## Output Contract
- Emit compact JSON-serializable summaries, not raw intermediate arrays.
- Include methods/provenance: data path/version, row grain, QC filters, operator, seed, denominators, exclusions.
- For region-level outputs, declare mapping (`Allen`, `Beryl`, `Cosmos`, or `-lr`) and count unknown labels.
- When computation is expensive or exclusion rules are exploratory, save reusable metric outputs before applying thresholds or inferential filters.
