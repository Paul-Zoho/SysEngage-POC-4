---
name: Source Capture execution_status quirk
description: SourceCapture writes "Success" to analysis_pass; all other mechanisms write "Completed"/"CompletedWithWarnings". Idempotency guards must include "Success".
---

## Rule
`SourceCapture` writes `execution_status = "Success"` to `analysis_pass`.
Every other mechanism (RLSRA, CCI, DD, RD) writes `"Completed"` or `"CompletedWithWarnings"`.

**Why:** Source Capture predates the standardised terminal-status vocabulary introduced for the Phase 3 mechanisms. Its status string was not normalised.

**How to apply:** Any idempotency guard that queries `analysis_pass.execution_status` to decide whether to skip a pass must include `"Success"` in the IN clause:

```python
"execution_status IN ('Completed','CompletedWithWarnings','Success')"
```

Omitting `"Success"` means Source Capture re-runs on every invocation, duplicating `source` rows in the DB. This was observed during the PMT Row 1 regression run (30 sources accumulated instead of 10 across three re-runs).
