---
name: CCI compute_execution_status signature
description: compute_execution_status now requires ccis_created and candidates_rejected_step3 params; zero-CCI produces PartialSuccess
---

`compute_execution_status` in `step6_analysis_pass.py` takes two additional keyword-only params added for the zero-CCI silent-swallow fix:

- `ccis_created: int` — total CCIs committed in Step 5
- `candidates_rejected_step3: int` — candidates rejected at _validate_item (Step 3b)

**Rule added:** if `batches_processed > 0 and ccis_created == 0` → emits `zero_ccis_from_content_bearing_input` warning → `PartialSuccess`.

**Why:** Run 25 showed Row 2 CCI reporting `execution_status: Success` with 0 CCIs from 9 signals. The spec requires loud failure over silent swallow. The zero-output-from-content-bearing-input case must be flagged.

**How to apply:** Every call site of `compute_execution_status` must pass both new params. Currently only one call site exists in `cci_construction/__init__.py` (lines ~279-288).
