## Purpose
Paper-grounded scope note for the 2025 Brain Wide Map release and how it should shape loading plans.

## Status
Supplemental reference.
Use when the question depends on BWM release scale, inclusion subsets, or release-level caveats.

## Verified
- Verified against public paper pages on 2026-03-09.
- Primary sources:
  - https://www.nature.com/articles/s41586-025-09235-0
  - https://www.nature.com/articles/s41586-025-09226-1
  - https://www.internationalbrainlab.com/publications/
  - https://github.com/int-brain-lab/paper-brain-wide-map/blob/main/brainwidemap/meta/region_info.csv

## Canonical scope summary
The main 2025 Brain Wide Map paper reports:
- 621,733 recorded neurons,
- 699 Neuropixels probes,
- 139 mice,
- 12 laboratories,
- coverage of 279 brain areas,
- a decision-making task with sensory, motor, and cognitive components.

The paper also emphasizes a stricter analysis subset:
- 75,708 well-isolated neurons after stringent QC,
- a canonical dataset of 201 regions for some main analyses,
- additional analysis subsets depending on inclusion criteria.

## Loading consequences
1. BWM is fundamentally a release-scale dataset, not a session-by-session toy dataset.
2. Many broad questions should start from the release roster and aggregate/unit tables.
3. Session-by-session raw loading is often scientifically unnecessary and computationally wasteful for release-wide summaries.
4. Different analyses in the papers use different inclusion subsets; do not assume one universal region/session mask for every metric.

## Canonical task variables highlighted in the papers
The main BWM paper emphasizes four key task variables for initial analyses:
- visual stimulus,
- choice,
- feedback,
- wheel movement

It also explicitly references alignment to:
- stimulus onset,
- first wheel movement,
- feedback

The prior paper adds:
- true block prior,
- Bayes-optimal prior,
- subjective prior inferred from behavior

## Stored-versus-recomputed guidance
The BWM papers support this operational split:

- Usually available as stored/release-level information:
  - release roster and session/probe metadata
  - trial events and task variables
  - QC-filtered unit tables and region metadata
  - broad inclusion information

- Usually requires recomputation or paper-specific code:
  - event-aligned neural response timing metrics
  - decoder outputs
  - subjective-prior estimates
  - fine-grained waveform metrics
  - region-by-region task-variable encoding metrics unless explicitly shipped in a release table

Rule:
- Do not assume that because a quantity appears in a BWM paper figure it is already stored in a downloadable aggregate table.

## Interpretation caveats from the papers
- Task modulation is widespread, but absence of a detected signal in one region is not evidence of absence.
- The main paper used relatively simple robust analysis variants for the initial appraisal.
- Large-scale summaries are valuable, but finer analyses may need subregions, layers, or cell-type proxies.

## Agent rules
1. Start from the newest semantically sufficient configured local `bwm_ephys` and/or `bwm_behavior` dataset when the schemas cover the BWM question; use `brainwidemap` release helpers only as the upstream fallback layer.
2. Treat release-scale aggregate paths as default for broad cross-region questions.
3. State the analysis subset explicitly when the paper uses region/session inclusion criteria.
4. If the desired metric is not obviously present in release tables, say so and plan the narrow recomputation path.
5. Distinguish task prior variables in the data from subjective-prior variables inferred in the paper.
