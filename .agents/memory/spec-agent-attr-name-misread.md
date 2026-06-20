---
name: Spec agent ledger misread — attr_name label vs JSON key
description: Spec agent writes "attr_name: null" meaning the CHK-3d-11 detail-label field, NOT a JSON dict key; always verify against the actual ledger JSON file before acting on null-attr claims.
---

## Rule

When the spec agent reports something like:

```
R026 Task  (attr_name=null, money), (attr_name=null, lifecycle_state)
```

…the phrase `attr_name=null` refers to the CHK-3d-11 **detail label** `attr_name_empty` — it is the spec agent's shorthand display for "this attribute's name slot", not a JSON key named `attr_name`. The actual ledger JSON stores the field as `"name"`.

**Why:** The Run 31 diagnostic claimed all Row 2 model attributes had `attr_name: null`. Inspection of the actual ledger file showed attributes were correctly named (`name='availability_status'`, `name='monetary_value'`, etc.). `formed=4` was legitimate. Acting on the claim without verification would have introduced spurious code changes.

**How to apply:** Before accepting any spec agent assertion about null/missing fields in a stored class_model, run:

```python
python3 -c "
import json
with open('verification_outputs/<run_file>.json') as f:
    data = json.load(f)
for e in data['elements']:
    if e['element_type'] == 'Requirement':
        cm = e['payload'].get('class_model')
        if cm:
            print(e['payload']['requirement_id'], [(a.get('name'), a.get('semantic_type')) for a in cm.get('attributes',[])])
"
```
