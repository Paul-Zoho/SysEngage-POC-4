---
name: Neon snapshot promotion — rename vs create+delete
description: Why test-branch-to-snapshot promotion must use PATCH rename, not branch creation followed by deletion.
---

**Rule:** When promoting a test branch to a snapshot, rename it in-place using `PATCH /projects/{id}/branches/{branch_id}` with `{"branch": {"name": snap_name}}`. Do NOT create a new child branch from it and then delete the test branch.

**Why:** Creating a child from the test branch makes the test branch the *parent* of the new snapshot. Neon's API returns HTTP 422 "cannot delete branch that has children" when you then try to delete it. The test branch is stuck as an orphaned parent, wasting storage and cluttering Neon's branch list.

**How to apply:** In any snapshot promotion script (e.g. `run_create_3b_snapshots.py`), after the CCI run completes successfully:
1. Call `_neon_request("PATCH", f"/projects/{neon_project}/branches/{branch_id}", body={"branch": {"name": target_snap}})` to rename.
2. Register `branch_id` (unchanged) in `snapshot_registry.json`.
3. No deletion step needed — the renamed branch IS the snapshot.

The `_neon_request` helper from `scripts/branch_manager.py` handles auth and error handling; import it directly.
