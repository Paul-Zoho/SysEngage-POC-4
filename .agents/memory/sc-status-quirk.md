---
name: execution_status vocabulary — unified to build vocabulary
description: All mechanisms now write "Success"/"PartialSuccess"/"Failed". The old spec vocabulary ("Completed"/"CompletedWithWarnings") was retired. DB read guards keep both for backward compatibility with pre-migration rows.
---

## Rule

All mechanisms write `"Success"`, `"PartialSuccess"`, or `"Failed"` to
`analysis_pass.execution_status`. The spec vocabulary (`"Completed"`,
`"CompletedWithWarnings"`) was retired from all write paths.

**Single source of truth:** `sysengage/core/audit_trail.py`
— `finalise_pass_success` → `"Success"`
— `finalise_pass_partial_success` → `"PartialSuccess"`

**Why:** Two vocabularies coexisted in the DB: Phase 3a–3d mechanisms
wrote `"Completed"/"CompletedWithWarnings"` (spec vocabulary); Requirement
Matching wrote `"Success"/"PartialSuccess"` (build vocabulary). The ledger
export normalised both via `json_builder._EXECUTION_STATUS_MAP`. After
unification, the export normalisation layer is a no-op safety net; dispatch
guards enumerate only two acceptance values; idempotency guards still include
all four to match pre-migration rows in the DB.

**How to apply:**
- New mechanism writes: use `"Success"` / `"PartialSuccess"` / `"Failed"` only.
- DB read guards (idempotency / prerequisite checks): include all four values
  (`["Completed", "CompletedWithWarnings", "Success", "PartialSuccess"]`) to
  match rows written before the migration.
- Return-dict dispatch guards: `("Success", "PartialSuccess")` is sufficient
  (return dicts are produced live, always use the new vocabulary after migration).
- The `_EXECUTION_STATUS_MAP` in `json_builder.py` retains both sets as a safety
  net; it requires no update.
