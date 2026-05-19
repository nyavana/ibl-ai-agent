## Purpose
QC, statistical hygiene, and interpretation rules for IBL scientific analyses.

## Verified
- Verified against public paper pages on 2026-03-09.
- Primary sources:
  - https://elifesciences.org/articles/100840
  - https://www.nature.com/articles/s41586-025-09235-0

## Canonical reproducibility summary
The reproducibility paper defines reproducibility as a lack of systematic across-lab differences such that within-lab variation is comparable to across-lab variation. Under standardized procedures and RIGOR QC, the paper reports that features such as neuronal yield, firing rate, and LFP power were reproducible across laboratories. Some finer single-variable modulation effects were less consistently reproducible in some regions, while richer response-profile analyses were more robust.

## Scientific implications for analysis
1. Standardized QC matters materially.
2. Broad electrophysiology features are more robust than every specific regional modulation test.
3. Full response-profile approaches can be more reliable than isolated single-number summaries.
4. A non-replicated effect in one region may reflect instability of the test, not necessarily failure of the whole dataset.

## QC-related agent rules
- State the QC filter used for neurons, sessions, and trials.
- Prefer canonical release QC when available over improvised local thresholds.
- When comparing labs or regions, avoid overclaiming from a fragile single metric.
- When feasible, report unit/session counts alongside the main estimate.

## General statistical hygiene
- Align paired samples before computing any paired statistic.
- Drop or impute missing values explicitly; report excluded counts when they affect denominators.
- Check that each statistic's inputs meet minimal assumptions, such as numeric dtype, adequate sample size, and nonzero variance where relevant.
- Use deterministic seeds for stochastic steps.
- Record sample size, excluded counts, seed, and any fallback behavior in the report or provenance.

## Stored-versus-recomputed consequences
- QC labels and some quality summaries may be stored.
- Reproducibility judgments are not stored fields; they depend on explicit cross-lab analysis design.
- Many response-modulation metrics require recomputation and are more sensitive to analysis choices than core yield/rate metrics.

## Interpretation warnings
### Robust
- neuronal yield
- firing rate
- LFP power

### More fragile
- proportion of cells modulated by a specific task variable in a specific region
- precise effect size for single decision variables

## Agent behavior
1. Prefer robust summaries when the user asks a broad exploratory question.
2. When using a fragile metric, state that it is more analysis-dependent.
3. Distinguish reproducible preprocessing/QC pipelines from reproducibility of every downstream biological contrast.
4. Include sample sizes and exclusions in reports whenever possible.
