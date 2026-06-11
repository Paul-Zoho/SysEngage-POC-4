---
name: Domain Derivation execution_status logic
description: PartialSuccess is only triggered by three specific conditions per spec v0.18 §4.4.6; all other advisory warnings are informational only.
---

# Domain Derivation `execution_status` decision rule

Per spec v0.18 §4.4.6, `PartialSuccess` fires **only** when one or more of:
- (a) Persistent orphaned CCIs remain after CHK-3c-04 repair: `stage3.status == "ok_with_warnings"`
- (b) `incremental_fallback_to_fullrerun` appears in `execution_warnings`
- (c) `mode_violations` is non-empty

Otherwise the status is `"Success"`.

**Why:** The original code used `bool(all_warnings)` which treated every advisory (domain_count_advisory, chk3c07_repair_failed, chk3c07_absorption_performed, large_cci_set_advisory, etc.) as status-changing. This was wrong and broke tests once CHK-3c-07 added advisory warnings to the common path.

**How to apply:** In `__init__.py`, the variable is `has_status_warnings` (NOT `has_warnings`). Advisory warnings are still stored in `pass_data["outputs"]["execution_warnings"]` but do not flip the status.

Note: before vocabulary unification, this used `"CompletedWithWarnings"` / `"Completed"`. After unification, it uses `"PartialSuccess"` / `"Success"`. The three triggering conditions are unchanged.
