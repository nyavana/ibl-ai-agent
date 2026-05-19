---
name: ibl-access
description: Use this skill when a task needs IBL data access setup, ONE/Alyx authentication, or selecting between public and private data modes.
---

# IBL Access

## Use this skill when
- You need to connect to IBL data via ONE.
- You need to switch between `public` and `private` access modes.
- You need session/insertion queries constrained by releases/tags.

## Local references (read before browsing)
- `../SOURCES.md`: provenance index for this skill and its references.
- `references/one_auth.md`: ONE instantiation, online/offline modes, auth patterns.
- `references/session_search.md`: `search`, `search_terms`, `search_insertions`, and Alyx REST patterns.

Default policy: use these local references first. Browse official docs only when behavior differs from references or an API call fails unexpectedly.

## Workflow
1. Determine mode (`public` or `private`) and record it in run metadata.
2. Configure ONE base URL:
- Public: `https://openalyx.internationalbrainlab.org`
- Private: `https://alyx.internationalbrainlab.org`
3. Validate auth state:
- interactive login path,
- non-interactive env path.
4. Build query strategy with performance defaults:
- narrow filters first,
- `limit`/`offset` paging for large pulls,
- `details=True` only when needed,
- `query_type="local"` vs `"remote"` selected explicitly.
5. Return connection status and provenance fields required by profile reports.

## Outputs
- Resolved endpoint.
- Auth mode used.
- Query constraints (release/tag/session filters).
- Provenance block for reports.
