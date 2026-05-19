# Firing-Rate Nonstationarity

## Core Phenomenon
Firing rates can change slowly or abruptly within a session. A trial-condition difference in baseline, pre-stimulus, or state-related firing can therefore reflect time-in-session structure as much as, or more than, the named condition.

## Why It Matters
Task variables and behavioral outcomes are often not uniformly distributed over session time. Early trials, late trials, easy trials, lapse/error trials, movement periods, and disengaged periods may differ in both neural state and recording stability. A firing-rate metric that is correct as code can still be misleading as biology if it is dominated by within-session nonstationarity.

## Ambiguous Interpretations
Within-session rate changes can be biological, technical, or mixed. Plausible interpretations include:

- arousal, engagement, fatigue, or task-set changes;
- slow behavioral-state transitions;
- probe settling or electrode drift;
- spike-detection or sorting instability;
- changing spike amplitude or unit isolation over time;
- region or layer localization uncertainty when drift changes which neurons dominate the signal;
- unit-selection artifacts when a set of units is treated as stable across the full session.

One session or one region is usually not enough to decide among these explanations.

## When To Keep This In Mind
This caveat is especially relevant for:

- baseline and pre-stimulus firing-rate metrics;
- correct/error, lapse, or trial-history comparisons;
- movement versus quiescence analyses;
- arousal or behavioral-state proxies based on neural activity;
- region-level firing-rate summaries;
- any analysis using trial-by-trial population rate as a state variable.

## Open Questions To Resolve Case By Case
When nonstationarity appears, useful scientific questions include:

- Is the change common across many units, or driven by a subset?
- Is it shared across regions on the same probe?
- Is it present on other probes in the same session?
- Does it align with spike amplitude, depth, or drift-related signals?
- Does it align with behavior, wheel, pupil/video, reaction time, or task engagement?
- Does the same pattern appear across sessions, subjects, labs, or only in one example?
- Would excluding, stratifying, or modeling session time change the scientific conclusion?

## Metric Risk Note Guidance
When this caveat is active, avoid prematurely labeling the effect as artifact or biology. A useful metric risk note should name:

- what the source-to-metric diagnostic supports;
- whether time-in-session structure could explain the condition effect;
- plausible biological and technical interpretations;
- what discriminating evidence would change the interpretation;
- whether scale-up should proceed as planned, add a time covariate/stratification, exclude unstable periods, or pause for more validation.
