---
name: branch_manager _build_conn_uri_for_branch is fragile
description: The existing-branch path in branch_manager reconstructs the connection URI via regex substitution on DATABASE_URL_MAIN, which fails silently and returns a malformed string. Use delete+recreate instead.
---

## Rule
When an orchestrator needs a Neon connection string for a test branch, always **delete and recreate** the branch so `_create_branch` returns `connection_uris[0]["connection_uri"]` directly from the Neon API response.

Never rely on `_build_conn_uri_for_branch` for the connection string — it uses `re.sub(r"@[^/]+/", f"@{host}/", DATABASE_URL_MAIN)` to reconstruct the URI, which silently returns only the query-string suffix (e.g. `sslmode=require&channel_binding=require`) when the substitution fails.

**Why:** `_create_branch` receives the connection URI from the Neon branch-creation response. `_build_conn_uri_for_branch` has to reconstruct it by substituting the endpoint host into `DATABASE_URL_MAIN`, and that regex substitution breaks when the source URL format doesn't match the expected pattern.

**How to apply:** In orchestrator scripts that call branch_manager, always:
```python
existing = bm._find_branch_by_name(neon_project, TEST_BRANCH_NAME)
if existing:
    bm._delete_branch(neon_project, existing["id"])
branch_id, conn_str = bm._create_branch(neon_project, TEST_BRANCH_NAME, snap_branch["id"])
```
This also guarantees a clean snapshot state for every test run.
