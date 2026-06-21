---
name: RD entity_ref strict binding — [A] synonym path is intentional
description: _resolve_strict uses exact-canonical OR synonym→resolves_to OR mint-new; AI judge bypassed. Synonym path in strict binding is [A]-correct per spec decision.
---

## Two resolution paths

`resolve_and_record()` in `data_dictionary/service.py` accepts `strict: bool = False`.

### Default path (strict=False) — behavioural terms
`resolve_term(term, provenance_ref, context)`:
1. Pre-filter (DM): exact case-insensitive match on `canonical.name` or `synonym.surface_term` → `outcome: existing`
2. IM comparison: `_judge(surface_term, context, canonical_entries)` — AI call presenting ALL canonicals + the surface term. Returns `confidence`, `best_canonical_ids`, `is_multi_candidate`.
3. Gate (DM): low confidence or multi → `flagged`; high confidence + match → `synonym`; high confidence + no match → `canonical` (mint new).

### Strict path (strict=True) — class_model entity_ref binding [A] v0.36
`_resolve_strict(term, provenance_ref)` via `_lookup_existing`:
1. Exact canonical name match (case-insensitive) → `outcome: existing`
2. Synonym `resolves_to` match → `outcome: existing`
3. No match → mint new canonical immediately (**no AI judge step**)

## Why the strict path exists

Entity names that are semantically related to an existing canonical but structurally distinct were fuzzy-bound to the wrong canonical via the AI judge. Example from Run 26:
- "ChildEarnings" → IM judged high-confidence match to DD003 "monetary value" → `entity_ref = DD003` (wrong)
- Two distinct requirements shared `entity_ref: DD003` → entity coverage collapsed

## Why the synonym branch stays in _resolve_strict

**Spec decision (confirmed):** The synonym `resolves_to` path is `[A]`-correct and must not be removed. Removing it would cause entity fragmentation: a surface name previously registered as a synonym of an existing canonical would mint a duplicate canonical instead of binding correctly. `[B]` (CHK-3d-11 uniqueness) cannot catch this — two different surface names produce two different `entity_ref`s with no collision. The only detection path would be PLB-3d-07 practitioner review.

The `[A]` bug (Run 26) was the **AI-judge fuzzy similarity** path — not the synonym path. These are distinct:
- AI judge: confidence-scored similarity; can bind unrelated entities
- Synonym `resolves_to`: explicitly recorded surface-term variant of a canonical

If bad synonyms are being created, the fix is a guard at **synonym creation time** in the DD service, not at the binding layer.

## Call sites

- Stage 4 class_model entity binding: `resolve_and_record(entity, proposal.statement, req_id, strict=True)`
- All other (behavioural) callers: `resolve_and_record(term, context, provenance_ref)` (strict=False default)

**How to apply:** When diagnosing entity_ref binding errors, check whether the call site passes `strict=True`. A `strict=False` call on a class_model entity name is a bug. Never remove the synonym check from `_resolve_strict`.
