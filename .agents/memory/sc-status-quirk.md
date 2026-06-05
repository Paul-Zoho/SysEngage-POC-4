---
name: Source Capture execution_status quirk
description: SourceCapture writes "Success" to analysis_pass; all other mechanisms write "Completed"/"CompletedWithWarnings". Idempotency guards must include "Success".
---

## Rule (FIXED — no longer applies)
`audit_trail.finalise_pass_success` previously wrote `execution_status = "Success"` and
`finalise_pass_partial_success` wrote `"PartialSuccess"`.

These were normalised to `"Completed"` and `"CompletedWithWarnings"` respectively to match
all other mechanisms. The SC internal idempotency check was updated at the same time to use
the new values.

**Why:** Source Capture predated the standardised status vocabulary; its strings were
inconsistent with Phase 3 mechanisms, causing idempotency guards that checked only
`"Completed"/"CompletedWithWarnings"` to miss SC passes and re-run SC on every invocation.

**How to apply:** All mechanisms now use only `"Completed"`, `"CompletedWithWarnings"`,
or `"Failed"`. Any idempotency guard checking `analysis_pass.execution_status` need only
include those three values.
