---
name: Substitute mode ID remapping
description: When substituting R11 Row 2 reqs into other projects, source IDs collide with target Row 1 IDs; always remap to safe range R901+.
---

## Rule
In `_rm_attr_worker.py` substitute mode, ALWAYS remap source requirement IDs to R901, R902, … (one per source req in sorted order) before inserting into the target project. Never use the original R11 IDs directly.

## Why
R11 Row 2 IDs start at R018 (because R11 Row 1 ends at R017).
R12 Row 1 spans R001–R019, so R018 and R019 are already taken as Row 1 entries.
R13 Row 1 spans R001–R021, so R018–R021 all conflict.
Primary key is `(requirement_id, project_id)` — the DELETE only removes Row 2, leaving Row 1 intact, so any INSERT of a conflicting ID fails with UniqueViolation.

## How to apply
- `_substitute_row2_reqs` builds `id_map: {new_id: original_r11_id}` before opening a DB session.
- Inserts use `new_id` as the DB requirement_id.
- Returns `id_map` so `main()` can build `refines_refs_by_source_id` (keyed by original R11 IDs).
- Analysis reads `refines_refs_by_source_id`; falls back to `refines_refs` for rerun mode (where id_map is empty and DB IDs are already original R11 IDs).
