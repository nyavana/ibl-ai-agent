## Purpose
Paper-grounded guide to prior-related quantities in the IBL task so the agent does not conflate stored block variables with inferred latent priors.

## Status
Supplemental reference.
Use when the question specifically concerns prior, bias blocks, or subjective prior.

## Verified
- Verified against public paper pages on 2026-03-09.
- Primary sources:
  - https://www.nature.com/articles/s41586-025-09226-1
  - https://elifesciences.org/articles/63711

## Core distinction
There are at least three different "prior" quantities in the IBL task/papers:

1. True block prior
- Experimental variable set by the task design.
- In the biased task, the stimulus-side probability switches between block values such as 0.2 and 0.8, after an initial 0.5 block.
- This is the closest thing to a directly stored task prior.

2. Bayes-optimal prior
- A model-derived estimate of the block prior given full knowledge of the task structure and trial history.
- Not a raw stored trial column by default.

3. Subjective prior
- The animal's inferred internal estimate of the prior.
- Not directly stored.
- Must be inferred behaviorally or decoded neurally under an explicit model.

## Why this matters
It is easy to ask for "prior" and accidentally answer with the wrong object.

Examples of incorrect substitutions:
- using `probabilityLeft` when the paper question is about subjective prior
- treating Bayes-optimal prior as if it were a stored trial variable
- interpreting prior effects as generic motor bias without checking contrast dependence

## Default mapping for analysis
| Requested concept | Default data/analysis interpretation |
| --- | --- |
| block prior | `probabilityLeft` or equivalent task block variable |
| true prior | task-defined block prior |
| Bayes-optimal prior | recomputed model quantity from task structure and history |
| subjective prior | inferred latent variable, not a stored field |
| prior effect on choice | often strongest on zero-contrast or low-contrast trials |

## Stored-versus-recomputed guidance
- Usually stored:
  - block identity or side-probability variables such as `probabilityLeft`
  - trial history needed to infer priors
- Usually recomputed:
  - Bayes-optimal prior
  - subjective prior
  - neural prior-decoding metrics

Rule:
- Do not claim to analyze "prior" without naming which prior.

## Scientific interpretation rules
1. If the signal differs most strongly on zero-contrast trials, a prior-based explanation is plausible.
2. If a shift is uniform across contrasts, consider an action or perseveration bias rather than prior use.
3. The prior paper indicates that mice use prior information nearly optimally, but not perfectly.
4. The paper argues that the subjective prior is closer to the Bayes-optimal prior than to the raw true block prior.

## Agent rules
1. If a user asks about priors, explicitly choose one of:
   - true block prior,
   - Bayes-optimal prior,
   - subjective prior.
2. If the user does not specify, default to the stored task prior only for simple descriptive analyses.
3. For BWM questions about neural representation of prior, do not substitute `probabilityLeft` for subjective prior without warning.
4. If the analysis needs subjective prior, mark it as a latent inferred quantity requiring explicit modeling.
