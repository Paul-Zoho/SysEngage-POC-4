---
name: Ledger exporter v2.17 — cci_data key and row_target type
description: CCI passes use cci_data not mechanism_data; row_target is exported as string; v2.17 adds class_model + object_refs to Requirement
---

**CCI AnalysisPass output key is `cci_data`, not `mechanism_data`**

`finalise_cci_pass_completed` stores `outputs = {"cci_data": cci_data, "mode_violations": [...]}`. SourceCapture uses `outputs["mechanism_data"]`. This naming difference is intentional — do not confuse the two when inspecting exported JSON.

**`row_target` is a string in the export**

`Requirement.row_target` is a `VARCHAR` column in the DB, stored and exported as `"1"`, `"2"`, etc. — not integer. Python checks must use `== "2"` not `== 2`.

**Ledger v2.17 changes (vs v2.15)**

`_build_requirement_element` now exports:
- `object_refs` — always present (empty list `[]` if no resolved paths)
- `class_model` — present only for Structural requirements where the AI produced one (omitted if None)

`_build_data_dictionary_element` strips the `attributes` field from canonical DD payloads (was a pre-F107 artifact).

`SPEC_VERSION = "2.17"`, `SCHEMA_ID = "sysengage.ledger.instance.v2_17"`.

**Why:** Run 25 spec-agent review identified that class_model and object_refs were implemented in the DB (migration 026) but not exported in the ledger JSON. v2.17 closes this gap.
