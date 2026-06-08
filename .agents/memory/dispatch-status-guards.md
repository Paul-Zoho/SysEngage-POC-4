---
name: run_dispatch execution_status guards
description: All 5 mechanism status guards in run_dispatch.py must accept both old and new v2.15 enum values to avoid false all_ok=False exits.
---

## Rule
`run_dispatch.py` checks each mechanism's `execution_status` return value to decide whether to set `all_ok = False`. The guard must accept **both** the old and new enum values:

```python
if r["execution_status"] not in (
    "Completed", "CompletedWithWarnings",   # old values (CCI, DD, RD, RLSRA)
    "Success", "PartialSuccess"             # v2.15 values (SC, RM, future mechanisms)
):
    all_ok = False
```

**Why:** SC has always written `"Success"` (not `"Completed"`). RM provenance was updated to write `"Success"` / `"PartialSuccess"` per ledger spec v2.15. Any guard that only lists the old values will trigger a false failure whenever SC or RM runs.

**How to apply:**
- Any new mechanism added to run_dispatch.py should get this same four-value guard.
- If a mechanism is updated to use new enum values, the guard already covers it — no change needed.
- The 5 guards are for: SC (line ~230), RLSRA (line ~253), CCI (line ~274), DD (line ~293), RD (line ~312). Pass 3e (RM) has no status guard — it only catches exceptions.

## Symptom of the bug
- Pipeline exits with code 1 even though all AnalysisPasses show success in the ledger.
- Run takes expected time for idempotent passes (fast) then exits with code 1.
- Caused by SC returning `"Success"` while the guard only allowed `"Completed"`.
