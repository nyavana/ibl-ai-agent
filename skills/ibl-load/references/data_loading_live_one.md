## Purpose
Supplemental live-server ONE/Alyx examples.

Use only for explicit server-backed discovery, remote dataset access, or live ONE examples. Default reviewed analysis should prefer configured local datasets, cached files, and `data_loading.md`.

## Core ONE Calls
```python
from one.api import ONE

one = ONE(base_url="https://openalyx.internationalbrainlab.org", silent=True)
eids = one.search(subject="SWC_043", limit=5)
trials = one.load_object(eid, "trials", attribute=["stimOn_times", "choice"])
spikes = one.load_object(eid, "spikes", collection="alf/probe00")
files = one.load_dataset(eid, "trials.table.pqt", revision="2024-05-06")
datasets = one.list_datasets(eid)
collections = one.list_collections(eid)
```

## Selective Loading
- Use `attribute=[...]` to restrict object fields.
- Use `collection=...` for probe/camera-scoped datasets.
- Use `download_only=True` when staging files for later parsing.
- State revisions when reproducibility depends on them.

## Alyx REST
Use REST for endpoint-specific fields, Django predicates, explicit pagination, or stale-cache recovery:
```python
rows = one.alyx.rest("sessions", "list", subject="SWC_001", limit=250, offset=0)
fresh = one.alyx.rest("sessions", "list", subject="SWC_001", no_cache=True)
```

For camera/video discovery, query dataset records directly when high-level search misses coverage:
```python
recs = one.alyx.rest("datasets", "list", dataset_type="camera.ROIMotionEnergy", limit=500)
```

## BWM Guardrail
Do not use Alyx aggregate-tag discovery as a BWM default. For BWM paper helpers, use `bwm_paper_repo.md`; for local fallback snippets, use `data_loading_fallback_examples.md`.
