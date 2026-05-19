#!/usr/bin/env python3
"""Regenerate the reviewed ibl-neuropixel signature sheet when the package is installed."""

from __future__ import annotations

from pathlib import Path

OUTPUT_PATH = Path("skills/ibl-neuropixel/references/neuropixel_function_signatures.md")


TEMPLATE = """# IBL Neuropixel Function Signatures

Reviewed callable sheet for the functions and classes explicitly surfaced by the upstream `int-brain-lab/ibl-neuropixel` repository README and related IBL docs.

## Usage policy
- Use `neuropixel_routing.md` first to choose the right workflow.
- Use this file second to copy exact call signatures or object entrypoints.
- Refresh this file against the upstream repo or installed package before expanding runtime coverage.

## `spikeglx`
- `Reader(file_bin)`
- `Reader.__getitem__(slice_or_index)`
- `Reader.compress_file(keep_original=True)`

Common reader attributes used in repo examples:
- `Reader.fs`
- `Reader.nc`
- `Reader.nsync`

## `ibldsp.voltage`
- `destripe(raw, fs=None, neuropixel_version=None, ...)`
- `decompress_destripe_cbin(sr_file, output_file=None, nprocesses=None, ...)`

## `ibldsp.plots`
- `voltageshow(raw, fs=None, title=None, ...)`

## `viewephys.gui`
- `viewephys(raw, fs=None, title=None, ...)`

## `brainbox.io.spikeglx`
- `extract_waveforms(ephys_file, ts, ch, t=2.0, sr=30000, n_ch_probe=385, car=True)`

## Notes
- This file starts from the stable public surface documented in the upstream README.
- Replace ellipses with exact optional parameters when the package is locally installed and validated.
"""


def main() -> None:
    OUTPUT_PATH.write_text(TEMPLATE, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
