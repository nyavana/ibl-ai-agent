## Purpose
Compact ONE/Alyx session and insertion discovery policy.

## Sources
Verified against ONE docs and IBL notebooks on 2026-03-03.

## Core APIs
```python
eids = one.search(subject="SWC_001", limit=10)
eids, details = one.search(subject="SWC_001", details=True)
terms = one.search_terms(query_type="remote")
insertions = one.search_insertions(dataset="spikes.times.npy", exists=True)
eid, probe = one.pid2eid(pid)
```

## Search Policy
- Start with restrictive filters: subject, lab, project, task protocol, date range, or dataset requirement.
- Keep first-pass payload small: `details=False`, `limit=<small_int>`.
- Use `query_type="local"` for already-cached development and `query_type="remote"` for fresh discovery.
- Use `search_terms(query_type="remote")` before dynamic filter construction.
- Page large pulls with explicit `limit` and `offset`; sort deterministically when paging.

## Return and Failure Handling
- `search(..., details=True)` is usually `(eids, details)`; handle version differences defensively.
- Unknown filter: surface supported terms.
- Empty local result: retry remote before concluding absence.
- Empty true result: return structured empty output, not an uncaught exception.

## Alyx REST Fallback
Use `one.alyx.rest(...)` when `one.search(...)` cannot express a needed server-side filter, endpoint-specific field, or pagination contract.

Examples:
```python
rows = one.alyx.rest("sessions", "list", subject="SWC_001", limit=250, offset=0)
rows = one.alyx.rest("sessions", "list", django="start_time__date__gte,2022-01-01")
rows = one.alyx.rest("datasets", "list", dataset_type="camera.ROIMotionEnergy", limit=500)
```

For endpoints with weak server-side filtering, page and filter client-side.
