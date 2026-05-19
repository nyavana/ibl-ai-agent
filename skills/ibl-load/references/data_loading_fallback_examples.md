## Purpose
Supplemental local-cache and loader fallback examples.

Use this when the default local BWM path or a narrow ONE object is insufficient and you need a concrete fallback pattern.

## Guardrail
- These are exception paths, not the default answer path.
- Prefer the smallest narrow dataset that answers the question before using heavyweight loaders.

## Narrow local-cache fallback example
Use this only when a required field is absent from `bwm_ephys` and direct local cache reads are justified.

```python
from pathlib import Path

import numpy as np
import pandas as pd

SPIKE_SORTING_REVISION = "2024-05-06"

probe_meta = bwm_query(freeze="2023_12_bwm_release")[
    ["pid", "probe_name", "lab", "subject", "date", "session_number"]
].drop_duplicates()

def session_cache_path(one, row):
    return (
        Path(one.cache_dir)
        / row["lab"]
        / "Subjects"
        / row["subject"]
        / str(row["date"])
        / f"{int(row['session_number']):03d}"
    )

rows = []
for probe in probe_meta.itertuples(index=False):
    peak_to_trough_path = (
        session_cache_path(one, probe._asdict())
        / "alf"
        / probe.probe_name
        / "pykilosort"
        / f"#{SPIKE_SORTING_REVISION}#"
        / "clusters.peakToTrough.npy"
    )
    peak_to_trough = np.load(peak_to_trough_path, mmap_mode="r")
    rows.append(
        pd.DataFrame(
            {
                "pid": probe.pid,
                "cluster_id": np.arange(len(peak_to_trough), dtype=int),
                "peak_to_trough": peak_to_trough,
            }
        )
    )

spike_widths = pd.concat(rows, ignore_index=True)
```

## Loader fallback patterns
```python
from brainbox.io.one import SessionLoader, SpikeSortingLoader

sl = SessionLoader(one=one, eid=eid)
sl.load_trials()
trials = sl.trials

ssl = SpikeSortingLoader(one=one, eid=eid, pname="probe00")
spikes, clusters, channels = ssl.load_spike_sorting()
clusters = ssl.merge_clusters(spikes, clusters, channels)
```

```python
ssl = SpikeSortingLoader(one=one, eid=eid, pname="probe00")
spikes, clusters, channels = ssl.load_spike_sorting(good_units=True)
clusters = ssl.merge_clusters(spikes, clusters, channels)
```

## Notes
- Prefer `bwm_ephys_spike_example.md` for the standard local spike-loading path.
- Use `data_loading_live_one.md` only when the task genuinely needs server-backed discovery or remote loading.
