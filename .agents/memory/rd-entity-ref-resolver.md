---
name: RD entity_ref resolver — fuzzy-synonym bug
description: resolve_and_record uses AI judge for semantic similarity; entity names with high-confidence-but-wrong matches are fuzzy-bound to existing canonicals instead of minting new ones
---

## Algorithm (deployed)

`resolve_and_record(term, context, provenance_ref)` → `resolve_term(...)` in `data_dictionary/service.py`:

1. **Step 1 — Pre-filter (DM):** `_lookup_existing(session, surface_term)` — case-insensitive exact match on `canonical.name` OR `synonym.surface_term`. Returns immediately if found (`outcome: existing`).

2. **Step 2 — IM comparison:** `_judge(surface_term, context, canonical_entries)` — AI call presenting ALL existing canonicals + the surface term + statement context. IM returns `confidence` (float), `best_canonical_ids` (list), `is_multi_candidate` (bool).

3. **Step 3 — Gate (DM):**
   - `confidence < RESOLUTION_CONFIDENCE_BAND` OR `is_multi_candidate` → `flagged`
   - `confidence ≥ band` AND `best_ids` non-empty → `synonym` (binds to existing canonical — the fuzzy path)
   - `confidence ≥ band` AND `best_ids` empty → `canonical` (mint new)

## The bug

Entity names that are semantically related to an existing canonical but structurally distinct are fuzzy-bound to the wrong canonical. Example from Run 26:
- "ChildEarnings" → IM judges high confidence match to DD003 "monetary value" → `entity_ref = DD003` (wrong)
- "TaskCompletionAssignment" → IM judges match to DD006 "task completion" → `entity_ref = DD006` (wrong)
- Two distinct requirements share `entity_ref: DD003` (ChildEarnings R057, R064) and two share DD006 (R056, R063)

## Spec intent (§6 — pending)

The spec will require: **exact-match-or-mint-new; never fuzzy-bind an entity name.** This eliminates the synonym path for entity_ref resolution — any name that doesn't exact-match should mint a new canonical. No code change to make until the spec is issued.

**How to apply:** When diagnosing entity_ref binding errors, look at the DD service resolution_log for `outcome: synonym` entries on class_model entity names. Each synonym entity_ref is a candidate wrong binding.
