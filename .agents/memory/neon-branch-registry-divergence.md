---
name: Neon branch vs registry divergence
description: Registry entries survive after Neon branch deletion — always confirm live state with _find_branch_by_name, not the registry.
---

## Rule
The snapshot registry (`sysengage/test_infrastructure/snapshot_registry.json`) is a historical record, NOT a source of truth about what currently exists in Neon. A registry entry with a `neon_branch_id` can be stale if the branch was deleted from Neon.

**Why:** Branches can be deleted via the Neon console, API, or branch_manager without the registry being updated. The registry has no auto-sync mechanism.

**How to apply:**
- Always verify existence with `bm._find_branch_by_name(neon_project, name)` before using a snapshot. Return value of `None` = branch gone.
- When a branch is confirmed deleted, add `"neon_status": "deleted"` and `"neon_status_note": "..."` to the registry entry to make the stale state explicit for future agents/operators.
- Scripts that clone from a named snapshot should print rebuild instructions on failure, not just "not found".

## Confirmed deleted on 2026-06-08
All three PMT-specific 3x snapshots were gone:
- `snap_PMT_ph03_3d_R1_3x_20260606` (br-spring-water-ab1j4l83)
- `snap_PMT_ph03_3d_R2_3x_20260606` (br-solitary-heart-abegqepe)
- `snap_PMT_ph03_3e_R2_3x_20260606` (br-ancient-grass-ab6zyv6i)

Surviving snapshots: `snap_ph03_3a_AllProjects`, `snap_ph03_3b_AllProjects`, `snap_ph03_3c_AllProjects`.

## Rebuild chain for PMT 3x snapshots
Starting point: `snap_ph03_3c_AllProjects` (alive, has CCI+DD for PMT/NQPS all rows).
1. Clone → run RD for PMT_E2E_R11/R12/R13 rows 1+2 → promote to `snap_PMT_ph03_3d_R2_3x_YYYYMMDD`
2. Update `SOURCE_SNAP` in `run_pmt_rm_r2_3x.py`
3. Run `run_pmt_rm_r2_3x.py` → promotes to `snap_PMT_ph03_3e_R2_3x_YYYYMMDD`
4. Update `SOURCE_SNAP` in `run_pmt_det_check.py`
5. Re-run `run_pmt_task37.py`
