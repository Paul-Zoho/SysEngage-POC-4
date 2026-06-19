---
name: RD entity_ref resolver — strict binding (v0.36 fix)
description: class_model entity_ref binding uses strict=True (exact-match-or-mint only); behavioural term resolution still uses AI judge. These are two separate paths.
---

## Two resolution paths

`resolve_and_record()` in `data_dictionary/service.py` now accepts `strict: bool = False`.

### Default path (strict=False) — behavioural terms
`resolve_term(term, provenance_ref, context)`:
1. Pre-filter (DM): exact case-insensitive match on `canonical.name` or `synonym.surface_term` → `outcome: existing`
2. IM comparison: `_judge(surface_term, context, canonical_entries)` — AI call presenting ALL canonicals + the surface term. Returns `confidence`, `best_canonical_ids`, `is_multi_candidate`.
3. Gate (DM): low confidence or multi → `flagged`; high confidence + match → `synonym`; high confidence + no match → `canonical` (mint new).

### Strict path (strict=True) — class_model entity_ref binding [A] v0.36
`_resolve_strict(term, provenance_ref)`:
1. Pre-filter (DM) only: exact match → `outcome: existing`
2. No match → mint new canonical immediately (**no AI judge step**)

## Why the strict path exists

Entity names that are semantically related to an existing canonical but structurally distinct were fuzzy-bound to the wrong canonical via the AI judge. Example from Run 26:
- "ChildEarnings" → IM judged high-confidence match to DD003 "monetary value" → `entity_ref = DD003` (wrong)
- Two distinct requirements shared `entity_ref: DD003` → entity coverage collapsed

Entity identity is exact-match-or-mint; it must never go through the synonym fuzzy path.

## Call sites

- Stage 4 class_model entity binding: `resolve_and_record(entity, proposal.statement, req_id, strict=True)`
- All other (behavioural) callers: `resolve_and_record(term, context, provenance_ref)` (strict=False default)

**How to apply:** When diagnosing entity_ref binding errors, check whether the call site passes `strict=True`. A `strict=False` call on a class_model entity name is a bug.
