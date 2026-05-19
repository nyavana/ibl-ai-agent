## Purpose
Minimal real-world example for loading good-unit spikes from the local `bwm_ephys` dataset.

## When to use
- You want a straightforward starting point for spike-based BWM analysis.
- You already know which insertion or region you want to analyze.
- You want decoded spike times plus unit metadata without going through remote loaders.

## Example
```python
import numpy as np
import pandas as pd

from ibl_ai_agent.data_locations import resolve_dataset_dir
from ibl_ai_agent.datasets.bwm_ephys import load_spike_shard

DATASET_DIR = resolve_dataset_dir("bwm_ephys")

# Load local metadata tables.
units = pd.read_parquet(DATASET_DIR / "metadata" / "units.parquet")
trials = pd.read_parquet(DATASET_DIR / "metadata" / "trials.parquet")

# Pick one insertion and keep its good units.
pid = str(units["pid"].iloc[0])
units_pid = units.loc[units["pid"] == pid].copy()

# Load the local spike shard for that insertion.
shard = load_spike_shard(DATASET_DIR / "spikes" / pid)
spike_times = np.asarray(shard["spike_times_seconds"], dtype=float)
spike_clusters_dense = np.asarray(shard["spike_clusters"], dtype=int)
cluster_ids = np.asarray(shard["cluster_ids"], dtype=int)

# Map dense local spike-cluster indices back to the real cluster ids in units.parquet.
spike_cluster_ids = cluster_ids[spike_clusters_dense]

# Example: restrict spikes to one unit.
cluster_id = int(units_pid["cluster_id"].iloc[0])
unit_spike_times = spike_times[spike_cluster_ids == cluster_id]

# Example: get trial-aligned spikes for that unit around stimulus onset.
eid = units_pid["eid"].iloc[0]
stim_on = trials.loc[trials["eid"] == eid, "stimOn_times"].dropna().to_numpy()

window = (-0.2, 0.5)
aligned = [
    unit_spike_times[
        (unit_spike_times >= t + window[0]) & (unit_spike_times <= t + window[1])
    ] - t
    for t in stim_on
]

print(f"pid={pid}")
print(f"n_units={len(units_pid)}")
print(f"n_spikes={len(spike_times)}")
print(f"cluster_id={cluster_id}")
print(f"n_spikes_for_unit={len(unit_spike_times)}")
print(f"n_trials={len(stim_on)}")
```

## What this gives you
- `units_pid`: good-unit metadata for one insertion
- `spike_times`: decoded spike times in seconds
- `spike_cluster_ids`: per-spike cluster ids matching `units_pid["cluster_id"]`
- `aligned`: one list entry per trial, each containing spike times relative to `stimOn_times`

## Notes
- `DATASET_DIR` is resolved from `data_locations.local.yaml` or `IBL_AGENT_DATA_LOCATIONS`; do not assume BWM data live under this repository.
- `units.parquet` already contains good units only for the dataset build.
- `cluster_ids` gives the real cluster ids for the insertion.
- `spike_clusters` is stored as dense local indices, so map it through `cluster_ids` before joining to unit metadata.
- This is the preferred local path for new BWM spike analyses in this repo.
