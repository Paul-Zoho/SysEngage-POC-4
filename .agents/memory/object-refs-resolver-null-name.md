---
name: object_refs_resolver null-name crash
description: dict.get("name","") returns None (not "") when key exists with null value — crashes on .strip(); fixed with str(... or "").strip()
---

## Rule

In `core/object_refs_resolver.py` attribute-segment lookup, always use:

```python
str(a.get("name") or "").strip().lower()
```

NOT:

```python
a.get("name", "").strip().lower()
```

**Why:** `dict.get(key, default)` only uses the default when the key is absent. When the key exists with value `None` (null in JSONB), `a.get("name", "")` returns `None`, not `""`. Calling `None.strip()` raises `AttributeError`. Stage 4 catches the exception and appends `[]` to `proposal_object_refs` — so `formed` silently becomes 0 instead of producing a clean `attribute_not_in_class_model` dangle.

**How to apply:** Any code that reads attribute `.name` from a class_model dict loaded from JSONB must use the `str(... or "").strip()` pattern. The same pattern is already used in `class_model_validity.py` CHK-3d-11 for the same reason.
