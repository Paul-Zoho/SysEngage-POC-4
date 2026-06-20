---
name: CHK-3d-11 [G] attribute well-formedness
description: v0.37 [G] adds three HARD checks to CHK-3d-11; POS check order and None-safe name lookup.
---

## Rule

v0.37 [G] adds three HARD checks to `core/class_model_validity.py`:

1. **`attr_name_empty`** — attribute name null/empty. Use `str(attr.get("name") or "").strip()` (not `.get("name","").strip()`) because `.get(key, default)` returns the stored `None` value when the key is present — the default only fires when the key is absent.

2. **`semantic_type_pos_tag`** — runs BEFORE the shape check; case-insensitive match against `_POS_TAG_SET`. This means `"Noun"` → `semantic_type_pos_tag` (not `semantic_type_malformed`), even though `"Noun"` would fail the lowercase shape check. The spec test fixture `semantic_type='Noun' → semantic_type_pos_tag` confirms this ordering.

3. **`semantic_type_malformed`** — `^[a-z][a-z0-9_]*$` shape check, runs AFTER POS gate. Only fires when value is present and not a POS tag.

Novel domain terms (e.g. `systolic_pressure`, `identifier`) pass both checks.

## Why

Spec §12.18 [G] standardises attribute well-formedness as part of CHK-3d-11 Stage-3 HARD gating.

## How to apply

- Check order: POS (case-insensitive) → shape regex. Do not swap.
- The POS closed set: `{noun, verb, qualifier, adjective, adverb, pronoun, preposition, conjunction, determiner, interjection, article, particle}`.
- `semantic_type=None` or absent → no [G] violations (field is optional except for Row 2 which has a separate "≥1 attr with semantic_type" aggregate check).
- `SemanticTypeRegistry` (session-scoped, in-memory) is wired in `stage4_entity_production.py` §4.4.3c; summary in `mechanism_data.semantic_type_registry`.
