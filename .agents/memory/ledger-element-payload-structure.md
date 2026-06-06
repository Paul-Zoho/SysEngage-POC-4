---
name: Ledger element payload structure
description: All element fields live inside `payload`, not at the top-level element dict — verification checks must use el["payload"]["field"], not el["field"].
---

## Rule
When reading fields from exported ledger JSON elements (e.g. `row_target`, `refines_refs`, `confidence`), always navigate via `el.get("payload", {}).get("field")`. The top-level element dict has only three keys: `element_type`, `element_id`, `payload`.

**Why:** `json_builder.py` nests all field data inside `payload`. Checking `el.get("row_target")` always returns None, producing silent `0/0` counts in verification output.

**How to apply:** Any runner or test that verifies ledger content post-export — including row_target filtering and refines_refs counts — must go through `payload`. The pattern is:

```python
sum(
    1 for el in ledger["elements"]
    if el.get("element_type") == "Requirement"
    and str(el.get("payload", {}).get("row_target", "")) == str(ROW)
    and el.get("payload", {}).get("refines_refs")
)
```

Also: `refines_refs` was not originally emitted by `_build_requirement_element` in `mechanisms/ledger_export/json_builder.py`. It was added alongside migration 023 (project_id on matching log). Any future field added to `RequirementModel` must also be explicitly wired into `_build_requirement_element`.
