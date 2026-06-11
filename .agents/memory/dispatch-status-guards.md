---
name: run_dispatch execution_status guards
description: Return-dict guards use ("Success","PartialSuccess") only; ALL DB read guards that query execution_status must include all 4 values for pre-migration rows.
---

## Rule

After the vocabulary unification, two categories of guard exist:

**Return-dict guards** (mechanism call → return value):
```python
if r["execution_status"] not in ("Success", "PartialSuccess"):
    all_ok = False
```
Return dicts are always produced live by the mechanism, so they will always carry the new vocabulary after the migration. Two values only.

**DB read guards** (idempotency / prerequisite checks that query `analysis_pass`):
```python
AnalysisPassModel.execution_status.in_(
    ["Completed", "CompletedWithWarnings", "Success", "PartialSuccess"]
)
```
Existing rows in the DB were written before the migration and carry the old vocabulary. All 4 values must be listed until the DB is explicitly migrated.

**Why:** The old and new vocabularies coexisted: old mechanisms wrote `"Completed"/"CompletedWithWarnings"` (spec vocabulary); Requirement Matching and later mechanisms used `"Success"/"PartialSuccess"` (build vocabulary). Unification retired the old write paths, but old DB rows remain.

**How to apply:**
- New mechanism added to `run_dispatch.py`: return-dict guard uses 2 values only.
- New idempotency/prerequisite query anywhere in the codebase: list all 4 values until DB migration is done. This includes inline SQL strings, not just SQLAlchemy ORM expressions — e.g. `_check_downstream_rerun_required` in `stage4_entity_production.py` uses a raw SQL `IN (...)` clause that also needs all 4 values.
- Pass 3e (RM) has no return-dict status guard in run_dispatch — it only catches exceptions.
