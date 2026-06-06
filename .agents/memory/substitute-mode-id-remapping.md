---
name: Substitute mode ID remapping
description: When substituting R11 Row 2 reqs into other projects, source IDs can collide with target Row 1 IDs; use next available ID from global table max.
---

## Rule
In `_rm_attr_worker.py` substitute mode, remap source requirement IDs to the next available IDs globally across the entire `requirement` table (not per-project). After the DELETE of Row 2, query `MAX(CAST(SUBSTRING(requirement_id FROM 2) AS INTEGER))` where `requirement_id ~ '^R[0-9]+$'`, then assign R{max+1}, R{max+2}, etc.

## Why
R11 Row 2 IDs start at R018 (R11 Row 1 ends at R017). R12 Row 1 spans R001–R019, so R018/R019 are already taken as Row 1. R13 Row 1 spans R001–R021, so R018–R021 all conflict. The DELETE only removes Row 2, leaving Row 1 intact, so any INSERT of a conflicting ID fails with UniqueViolation. Gaps within a project are intentional and inconsequential.

## How to apply
- Query is done inside the session AFTER the DELETE+flush, so the max reflects the post-delete state.
- Build `id_map: {new_db_id: original_r11_id}` from the result.
- Insert using `new_db_id`; return `id_map` so `main()` can build `refines_refs_by_source_id` keyed by original R11 IDs for cross-baseline comparison.
- Analysis reads `refines_refs_by_source_id`; falls back to `refines_refs` for rerun mode (id_map empty, DB IDs are already original R11 IDs).
