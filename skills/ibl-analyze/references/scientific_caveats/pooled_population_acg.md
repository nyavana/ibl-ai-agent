## Pooled Population ACG

## Use When
A metric pools spike times across units in a region, layer, insertion, or population and computes an autocorrelogram or related spike-time timing summary.

## Core Risk
A pooled population ACG is not a pure intrinsic neuronal timescale. It mixes:
- individual-unit autocorrelation and refractory/burst structure;
- cross-unit synchrony;
- firing-rate heterogeneity and unit dominance;
- rhythmicity;
- task, stimulus, movement, and state modulation across the recording.

## Validation Checks
- Report bin size, window semantics, zero-lag handling, positive-lag range, and normalization.
- Plot source ACG shapes before reducing them to scalar widths or peaks.
- Check top-unit spike fraction or another unit-composition measure.
- When oscillation is visible, add a rhythmicity or spectral diagnostic and consider unit-wise ACG averages or circular-shift controls.
- Report complementary shape summaries when the visual difference includes both early peak height and sustained tail.

## Interpretation
Treat pooled ACG scalar widths as operational summaries of aggregate spike-train timing. If the scientific question asks about intrinsic single-neuron dynamics, state that pooled ACG is a proxy or use single-unit metrics. If the question asks about state-specific population dynamics, consider state-epoch or binned population-rate metrics instead.
