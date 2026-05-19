## Purpose
Operational recipe for visual response latency when no matching stored latency feature exists.

## Inputs
Prefer local BWM surfaces:
- `bwm_ephys` units/trials/events tables;
- `features/event_response_features.parquet` when its event/window/sign definition matches the question;
- local `spikes/<pid>/...` shards via `load_spike_shard(...)` when recomputing.

Fallback: `SpikeSortingLoader` or `brainwidemap.load_good_units(...)` plus trial events only when local fields are insufficient.

## Output
- per-unit latency in ms, NaN when unavailable;
- per-region median latency;
- metadata: event, window, bin size, smoothing, threshold rule, valid unit/trial counts.

## Default Onset Method
Use only when the question asks for onset latency or accepts this operational definition.

1. Select finite `stimOn_times`; optionally restrict to nonzero contrast.
2. Compute unit PETHs with `brainbox.singlecell.calculate_peths`.
3. Suggested defaults: `pre_time=0.2`, `post_time=0.3`, `bin_size=0.005`, `smoothing=0.02`.
4. Baseline: `[-0.2, 0.0)` s. Search window: `[0.0, 0.2]` s.
5. Onset: first response-window bin with firing rate at least `baseline_mean + 3 * baseline_std` for at least two consecutive bins.
6. Aggregate valid unit latencies by declared region mapping, usually median by Beryl region.

## Caveats
- This is not peak latency, BWM population-trajectory latency, or waveform timing.
- Results depend on trial selection, smoothing, bin size, and threshold rule.
- Flag right-edge/censored values if using a finite peak-search window.
- Report omitted regions and denominators; do not present positive-only latency summaries as all responses.
