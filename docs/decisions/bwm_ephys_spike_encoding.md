# BWM Ephys spike encoding decision

Date: 2026-04-11
Status: accepted for `bwm_ephys` v1 defaults

## Decision

Use the following default spike storage settings for `bwm_ephys`:

- encoding: `delta_int_ticks`
- quantization: `100 us`
- compression: `shuffle_zstd`

In short:

```text
delta_int_ticks + 100 us + shuffle_zstd
```

## Why this was chosen

This setting is the preferred tradeoff between:

- compact storage size
- acceptable read/query performance
- strong compression on sorted spike trains
- low enough quantization error for reviewed and general BWM analyses

## Rationale

### Why `delta_int_ticks`

Spike times are sorted, so explicit delta encoding produces small integer differences with much lower entropy than absolute timestamps.

### Why `100 us`

`100 us` was judged to be a good compromise:

- clearly better fidelity than `250 us`
- meaningfully smaller than higher-precision alternatives
- appropriate for most planned reviewed and analysis-ready use cases

### Why `shuffle_zstd`

The shuffle filter rearranges bytes by significance before Zstandard compression. This helps integer and delta-encoded arrays compress more effectively, especially when many high-order bytes repeat.

## Alternatives considered

- `delta_int_ticks + 50 us + shuffle_zstd`
  - more conservative / higher fidelity
  - somewhat larger
- `int_ticks + 100 us + shuffle_zstd`
  - simpler to decode conceptually
  - larger than delta encoding
- `float32_seconds`
  - simple but less compact and less precise than the chosen integer representation
- `float64_seconds`
  - exact baseline, but much larger

## Evidence

See profile outputs under:

- `reports/profiles/bwm_ephys_spike_encoding/`

The profile suite compares:

- `float64_seconds`
- `float32_seconds`
- `int_ticks`
- `delta_int_ticks`

across:

- `25 us`
- `50 us`
- `100 us`
- `250 us`

with:

- `zstd`
- `shuffle_zstd`

## Implementation targets

This decision should be reflected in:

- `docs/bwm/ephys.md`
- `ibl_ai_agent/datasets/bwm_ephys.py`
- dataset provenance/build metadata written by the builder
