---
name: RD audit block wiring — pass_data["mechanism_data_stage4"] was silent
description: CHK-3d-12 and object_refs_binding data was stored in pass_data but never wired into mechanism_data output; fixed by reading mechanism_data_stage4 in __init__.py
---

## The bug

`stage4_entity_production.py` stored CHK-3d-12 results in `pass_data["mechanism_data_stage4"]["chk3d12"]` and object_refs_binding in `pass_data["mechanism_data_stage4"]["object_refs_binding"]`.

`__init__.py` never read `pass_data["mechanism_data_stage4"]` when assembling the final mechanism_data dict. The entire sub-dict was silently discarded on every run.

Only `pass_data["execution_warnings_stage4"]` was read (merged into `all_warnings`).

## Fix applied

`__init__.py` now reads `pass_data.get("mechanism_data_stage4", {})` to extract:
- `object_refs_binding`: forwarded directly
- `chk3d12`: reshaped into `model_coverage` (parent_elements, covered, ratio) and `model_coverage_gaps[]`

`stage3_structural_validation.py`: new `Stage3Result.class_model_binding` field populated in the CHK-3d-11 loop; wired into mechanism_data as `class_model_binding`.

## Row 1 class_model cascade

Row 1 IM produces class_models with `tier: 1`. CHK-3d-11 hard-rejects any `tier not in {2,3,4,5}` — so ALL Row 1 Structural proposals with class_models are excluded. No class_models committed for Row 1 in the DB. Consequence: CHK-3d-12 at Row 2 calls `_get_class_models_for_row(session, pid, row_ref=1)` → empty → early return, no coverage computed.

**Why:** The CHK-3d-11 rule `tier MUST equal row_ref` is correct — Row 1 does not have a class_model tier (the valid enum starts at 2). The IM produces tier=1 because the prompt says "tier MUST equal the current row number" but doesn't explicitly say "Row 1 class_models are not authored — only rows 2–5 have class_models." Row 1 is a known no-class_model row; the IM needs explicit suppression.

**How to apply:** If a future run shows 0 class_model_binding entries for Row 1 and CHK-3d-12 shows no-op at Row 2, this is expected behavior (Row 1 has no class_model tier). Only check CHK-3d-12 at rows ≥ 3.
