---
name: ibl-neuropixel
description: Use this skill for raw Neuropixels binary access, destriping, compression, waveform extraction, and probe-level preprocessing based on the `int-brain-lab/ibl-neuropixel` repository.
---

# IBL Neuropixel

## Use this skill when
- The task involves raw SpikeGLX `.bin` or `.cbin` files.
- The user asks about destriping, compression, chunked binary reads, or probe-level preprocessing before ALF/ONE analysis.
- The user asks how to use tooling from the `int-brain-lab/ibl-neuropixel` repository.

## Do not use this skill when
- The question is already about analysis-ready spikes, clusters, trials, or ONE-loaded objects.
- The task is primarily a scientific comparison, statistical contrast, or report-writing problem.

## Local references
- `references/neuropixel_routing.md`
- `references/neuropixel_function_signatures.md`
- `../SOURCES.md`

## Default policy
1. Decide whether the user needs raw-ephys preprocessing or analysis-ready loading.
2. If raw binary access is needed, prefer repo-native `spikeglx` and `ibldsp` helpers before custom NumPy I/O.
3. If the task is destriping, compression, or chunked reading, follow the patterns documented in the upstream repo README.
4. Keep raw preprocessing separate from downstream scientific metrics.
5. Hand off to `ibl-load` or `ibl-analyze` once the data are in an analysis-ready form.

## Boundary with other skills
- `ibl-neuropixel`: raw file mechanics, destriping, compression, waveform extraction, probe preprocessing.
- `ibl-load`: session-level loading through ONE/ALF or Brain Wide Map helpers.
- `ibl-analyze`: scientific metrics, PSTHs, decoding, statistics, and interpretation.
