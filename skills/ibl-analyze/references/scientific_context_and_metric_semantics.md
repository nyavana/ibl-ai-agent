## Purpose
Canonical semantic checks for IBL scientific analyses.

## Sources
Verified against IBL behavior, data architecture, BWM, prior, reproducibility, and GLM-HMM paper pages on 2026-03-09.

## Core Rule
Do not map natural-language scientific terms directly onto convenient columns. First define the scientific quantity, event anchor, row grain, QC/population scope, and whether the chosen metric is direct, operationalized, or a proxy. Follow `interactive_scientific_analysis.md` so metric-validation diagnostics show the source signal-to-metric mapping before downstream analysis, unless the user explicitly skips validation.

Before choosing diagnostics or interpreting unexpected structure, consult applicable descriptive caveats in `scientific_caveats/`. Caveats are scientific background, not fixed diagnostic recipes; use them to name plausible biological and technical interpretations in the metric risk note.

## Shape-Before-Scalar Validation
When a metric reduces a structured source signal or distribution to one number, validate the source shape before treating the scalar as the scientific answer. This applies broadly to ambiguous quantities such as timescale, latency, response strength, selectivity, synchrony, variability, stability, and modulation.

Rules:
- Identify the source signal or distribution being compressed.
- Plot representative examples and failure cases before downstream analysis.
- Name distinct shape components that could drive the scalar.
- Add a complementary diagnostic metric when different shapes can yield the same scalar, or when one shape supports multiple scalar interpretations.
- Label metric status explicitly as candidate, provisional, validated, sensitivity, or rejected while the metric is evolving.
- Do not average or compare scalars across qualitatively different source-shape regimes without flagging, stratifying, or explaining the regime difference.

Unexpected diagnostic structure, such as oscillation, multimodality, heavy tails, unit dominance, nonmonotonicity, plateaus, or censored values, should become a diagnostic variable, caveat, exclusion candidate, or stratification candidate. Do not treat an exploratory exclusion rule as inferential merely because it improves a p-value.

## Semantic Match Gate
Classify each implemented metric:
- `direct`: exactly matches the question.
- `operationalized`: explicit defensible definition of an ambiguous quantity.
- `proxy`: related but not identical; Caveats must name the mismatch.

High-risk mismatches:
- movement-onset activity is not continuous movement-versus-quiescence state segmentation;
- peak latency is not response-onset latency;
- positive modulation is not all responsiveness; suppressed responses can count unless excitation-only is requested;
- unit rows are not insertion/session rows;
- Allen layer suffixes are labels, not validated physical depth without channel/depth checks;
- `probabilityLeft` is a block prior, not Bayes-optimal or subjective prior.

## Ambiguity Policy
Treat the question as underspecified when the answer depends materially on unstated metric definition, event window, QC/population, row grain, comparison statistic, dataset scope, or interpretation threshold.

For ambiguous metrics such as spike width, response latency, responsiveness, movement-related activity, strongest/best region, or all-versus-good-unit scope:
1. list plausible definitions and available/recomputable options;
2. label each option as stored, recomputed, proxy, unavailable locally, or a scope choice;
3. compute cheap local alternatives when feasible;
4. otherwise produce an ambiguity preflight with costs and a recommended default;
5. report conditionally if alternatives give different qualitative answers.

Do not average distinct definitions that answer different scientific quantities.

Preserve alternative metrics until their differences are understood. If a user challenges a metric definition or two plausible metrics diverge, state what each metric measures, what signal components it includes or excludes, and whether it remains primary, sensitivity, rejected, or provisional.

## Event Anchors
| Question shape | Default anchor |
| --- | --- |
| stimulus response | `stimOn_times` |
| movement onset | `firstMovement_times` |
| movement/quiescence state | wheel or behavior-state epochs |
| feedback response | `feedback_times` |

`goCue_times` is not a substitute for stimulus onset.

## Stored Versus Recomputed
| Quantity | Default status |
| --- | --- |
| session/probe metadata, region labels, QC labels, counts, firing-rate summaries | often stored/release-table |
| trial events and task variables | stored |
| wheel and behavioral state | partly stored, often derived |
| visual latency, movement modulation, passive responsiveness, waveform width, decoding, subjective prior | usually recomputed or model-derived |

Rules:
- Do not assume a paper-figure quantity exists as a release column.
- State whether a metric came from aggregates, trials, probe/session files, stored derived features, or recomputation from spikes/events.
- For stored derived features, report event/window/statistic/denominator fields when available.

## Domain Caveats
See `scientific_caveats/README.md` for reusable scientific caveats that should inform metric risk notes.

### Latency
- Name peak, onset, or BWM population-trajectory latency explicitly.
- For stored event-response latency features, report anchor, baseline, search window, sign convention, response threshold, and denominator.
- Flag right-edge/censored peak latencies.

### Region Effects
- Separate unit-level statistics from regional interpretation.
- Report eligible region thresholds and unit/insertion/session/subject/lab coverage when feasible.
- Treat single-insertion or single-session regional effects as exploratory.

### Statistical Unit
- Large spike, bin, unit, or trial counts do not create independent biological replication by themselves.
- Define the independent statistical unit before tests.
- For simultaneous superficial/deep or other within-recording population comparisons, prefer paired insertion/session-level deltas when feasible.
- Report paired `n`, paired deltas, and how exclusions change the paired denominator.

### Movement and Passive Responses
- Literal movement-versus-quiescence neural questions need state epochs or wheel thresholds.
- If using `firstMovement` features as a fallback, label them as movement-onset proxies.
- Passive responsiveness defaults to two-sided semantics unless the user asks for excitation only.
- Report passive-eligible and all-active-task denominators for overlap questions.

### Reproducibility and State
- Broad yield/rate features are more reproducible than every fine regional modulation.
- Fragile effects should be framed as analysis-dependent.
- Long-latency, lapse-like, or disengaged periods may reflect behavioral state switches, not only noise or fatigue.

## Planning Checklist
Before finalizing an analysis plan or presenting a metric proposal, answer:
1. What is the scientific quantity?
2. Is the metric direct, operationalized, or proxy?
3. What is the input and output row grain?
4. Is it stored, derived, or recomputed?
5. What event anchor/window/QC/filter applies?
6. What denominators and missing-modality exclusions matter?
7. What scientific caveats or paper/task caveats most affect interpretation?
8. Is ambiguity cheap to resolve now, or should a preflight ask the user to choose?
9. What metric-validation diagnostic and adversarial check will show the source signal, event/window, derived metric, and failure modes before downstream analysis?
10. What source-shape regimes or failure modes could make the scalar misleading?
11. What should the metric risk note say about supported interpretation, unresolved biological/technical ambiguity, and next discriminating evidence?
12. What is the independent unit of variability for statistical inference?
