# BWM dataset layering decision

Date: 2026-04-25
Status: proposed

Updated: 2026-05-19

## Decision

Keep the existing repo-local Brain Wide Map dataset layering simple:

- `bwm_ephys` remains the main metadata + spike-shard + compact ephys-summary dataset
- `bwm_behavior` remains the main behavior + wheel + pose + behavior-state dataset
- add a separate `bwm_events` dataset for event-locked binned spike-count payloads
- add a smaller query-facing neurobehavior feature atlas, tentatively
  `bwm_neurobehavior`, for precomputed unit-by-feature summaries and
  neural-behavior correlations

Do not create a separate `bwm_states` dataset at this stage.

## Why

The three products have different semantics and row grains:

- `bwm_ephys`
  - units, insertions, spike shards, compact neural summaries
- `bwm_behavior`
  - behavior-first tables, wheel/pose summaries, continuous behavior-defined states
- `bwm_events`
  - event-locked time-resolved neural activity
- `bwm_neurobehavior`
  - compact per-unit PETH, behavior-correlation, QC, location, and ephys-atlas
    feature vectors for broad "where in the brain is this information?"
    questions

This keeps the architecture general rather than reviewed-question-specific.
Reviewed questions are examples; the dataset surfaces should instead reflect the
main scientific abstractions users will reuse.

The full `bwm_ephys` and `bwm_behavior` datasets are intentionally
source-like derived surfaces, but together they are still more than `8G` in the
current local build. Many broad brain-map questions do not need local spike
shards or trace-level behavior stores. They need a smaller set of reusable
neuro-behavioral correlations and response summaries. A compact atlas layer
should serve those questions without forcing users to download or scan the full
source-like datasets.

## Product boundaries

### `bwm_ephys`

Recommended future `1.2.0` additions:
- canonical cortical layer labels in `units` or `unit_features`
- more compact unit/session summary features
- keep event summaries compact; do not add large event tensors here

### `bwm_behavior`

Recommended future `1.2.0` additions:
- `movement_state_epochs`
- `quiescence_state_epochs`
- optional `wheel_bouts`
- session-level behavior-state summaries

These state products should be derived from existing IBL wheel logic rather
than a new custom detector. The release should keep wheel storage compact and
store the derived epochs directly instead of storing a dense `1000 Hz`
resampled wheel trace.

### `bwm_events`

Recommended initial `1.0.0` scope:
- event-locked integer spike counts in fixed bins
- stable trial/unit lookup tables
- shared time axes
- explicit payload registry

Recommended storage shape:
- one sparse payload per `(pid, event)`
- CSR matrix with shape `(n_trials * n_units, n_bins)`
- values are integer spike counts per bin

### `bwm_neurobehavior`

Recommended initial scope:
- one row per unit for stable metadata, location, QC, and ephys-atlas-style
  features
- compact PETH summaries for task trial types and events
- compact cross-correlations between neural activity and named behavior signals
- auxiliary counts and coverage fields so users can judge whether a feature is
  based on enough trials or samples
- optional low-rank factors over standardized feature blocks for fast search
  and further compression

Recommended signal families:
- task PETHs by event and condition, including choice side, correctness, and
  probability-left block
- wheel velocity and speed
- named Lightning Pose traces rather than one opaque camera magnitude
- Lightning Action state transitions when available
- whisker motion energy and body-camera motion energy when available
- ephys-atlas features such as template shape, autocorrelation, population
  firing-rate correlation, and LFP correlation when source data permit
- unit location and QC metrics, including amplitude/firing-rate stability,
  presence ratio, and refractory-period violations

Storage guidance:
- keep interpretable scalar or short-vector feature blocks as the primary
  product
- use SVD/PCA factors as a secondary acceleration and compression layer rather
  than the only representation
- preserve feature provenance, source windows, lags, bin sizes, smoothing, and
  trial/sample counts

## What not to do yet

- do not create `bwm_states` as a separate dataset unless the state layer later
  becomes large and operationally distinct
- do not make new datasets mirror one reviewed question each
- do not put large event-aligned tensors inside `bwm_ephys`
- do not replace interpretable neurobehavior features with only latent SVD
  coordinates

## Rationale

This layering supports a broad range of scientific questions:

- event-locked neural analyses use `bwm_events`
- behavior-defined state analyses use `bwm_behavior`
- spikes, units, anatomy, and compact neural summaries stay in `bwm_ephys`
- broad unit-level "where is X represented?" analyses use `bwm_neurobehavior`

It preserves clear dataset roles while allowing each dataset to evolve without
becoming an unstructured grab-bag.
