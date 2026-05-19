## Purpose
Paper-grounded description of the IBL decision-making task for loading and interpretation decisions.

## Status
Supplemental reference.
Use when the question needs extra task-specific detail beyond the shared semantic core.

## Verified
- Verified against public paper abstracts/pages on 2026-03-09.
- Primary sources:
  - https://elifesciences.org/articles/63711
  - https://www.nature.com/articles/s41592-022-01742-6
  - https://www.nature.com/articles/s41593-021-01007-z
  - https://www.internationalbrainlab.com/publications/

## Canonical task summary
The core IBL task is a head-fixed visual decision-making task in which mice detect a grating presented on the left or right and report the perceived side by turning a steering wheel. Task difficulty is controlled by stimulus contrast. Correct choices are rewarded. In the full task, the probability of stimulus appearance on the left versus right changes across blocks, so mice can combine sensory evidence with prior expectations inferred from recent trial history.

This means the task is not just a sensory discrimination assay. It explicitly mixes:
- sensory evidence,
- action selection,
- reward outcome,
- block prior / expectation,
- internal state and engagement.

## Skill-relevant scientific consequences
1. `stimOn_times` is a canonical sensory alignment event.
2. Wheel movement is part of the task response, not an incidental side measurement.
3. `probabilityLeft` is a task variable with real scientific meaning, not just metadata.
4. Behavioral analyses should distinguish the equal-probability basic task from the biased-block full task.
5. Low-contrast or zero-contrast trials are where prior-related effects are most interpretable.

## Trial-field interpretation guide
Use these as the default semantics unless a release-specific paper or dataset note overrides them.

| Field or concept | Interpretation |
| --- | --- |
| `contrastLeft`, `contrastRight` | Sensory evidence magnitude on the left and right visual fields. |
| `stimOn_times` | Stimulus onset; default event for visual response latency or visual PSTHs. |
| `goCue_times` | Cue allowing/encouraging response; do not confuse with stimulus onset. |
| `firstMovement_times` | Movement initiation; default event for movement-aligned analyses. |
| `choice` | Behavioral report of perceived side / selected action. |
| `feedback_times` | Reward or error feedback timing; default event for feedback-aligned analyses. |
| `probabilityLeft` | Block prior for stimulus side probability; essential for prior/bias analyses. |
| wheel traces | Continuous motor output; needed when the question is about movement itself, suppression during movement, or quiescence segmentation. |

## Loading consequences
- Start from aggregate tables for broad release-wide questions.
- Escalate to session-level trial objects when the analysis depends on event timing, block structure, or wheel traces.
- Escalate to spikes plus trials when the analysis depends on neural responses aligned to task events.

## Stored versus recomputed metrics
This distinction must be explicit in scripts and skills.

- Some quantities are typically stored directly:
  - trial events such as `stimOn_times`, `firstMovement_times`, `feedback_times`
  - task variables such as contrasts, choices, and `probabilityLeft`
  - aggregate unit metadata such as region, QC labels, and often firing-rate-like summaries
- Some quantities are often not stored as canonical release-wide fields and instead require recomputation:
  - visual response latency from spike trains aligned to `stimOn_times`
  - movement modulation from spikes and movement/quiescence segmentation
  - waveform features not present in aggregates, such as template-based spike width
  - passive-response metrics when they require passive-period session assets

Rule:
- Before computing a metric, state whether it is expected to exist in aggregates, in per-session trial objects, in per-probe spike-sorting outputs, or only as a derived quantity.

## Behavior-state caveat
The GLM-HMM paper indicates that mice can switch between discrete behavioral strategies within sessions. Therefore:
- average session-level behavioral summaries can hide state switches,
- long-latency or biased periods may reflect internal-state changes rather than stable sensory performance,
- analyses of "stops responding", disengagement, or lapse-like periods should not assume stationarity.

## Operational rules for the agent
1. If a question says "after stimulus onset", prefer `stimOn_times`.
2. If a question says "around movement onset" or "during movement", prefer `firstMovement_times` and wheel-derived epochs.
3. If a question concerns priors, expectation, or bias blocks, inspect `probabilityLeft`.
4. If a question concerns engagement, lapses, or satiation-like slowing, do not assume a single stationary behavioral regime.
5. If the wording says "peak response", do not silently substitute an onset-latency threshold rule; state the definition explicitly.
