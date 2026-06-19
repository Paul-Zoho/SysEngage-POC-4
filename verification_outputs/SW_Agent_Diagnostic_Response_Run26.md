# SW-Agent Diagnostic Response — Run 26: F105/F107 Audit Instrumentation + Class-model Analysis

**Responding to:** SW-Agent Diagnostic Request — Run 26: F105/F107 produce low-integrity class_models, and the audit instrumentation is missing  
**Run reviewed:** PMT_Ph03_3e_RequirementMatching_R2_Run26.json  
**Response prepared:** 2026-06-19  

---

## §1 — F105/F107 audit blocks: status and implementation

### 1a. Do CHK-3d-11 and CHK-3d-12 execute?

**CHK-3d-11** — YES, implemented and executing. Location: `stage3_structural_validation.py` lines 502–568. Hard violations exclude the proposal; results surface in `mechanism_data.validation_failures`. Soft violations surface in `execution_warnings`.

**CHK-3d-12** — YES, implemented and executing. Location: `stage4_entity_production.py` lines 1034–1066. Result is stored in `pass_data["mechanism_data_stage4"]["chk3d12"]`, and advisory warnings go into `pass_data["execution_warnings_stage4"]`. **However, `pass_data["mechanism_data_stage4"]` was never read back into the final `mechanism_data` dict in `__init__.py`** — the key existed but was never wired into the output. The CHK-3d-12 result was silently discarded from every run.

**Audit block assembly** — NOT previously implemented. CHK-3d-11 and CHK-3d-12 ran and produced data internally, but the structured `class_model_binding`, `object_refs_binding`, `model_coverage`, and `model_coverage_gaps` blocks per §4.4.3b/§7 were never assembled or surfaced in mechanism_data.

### 1b. Audit blocks — now implemented

The following changes have been made and syntax-verified:

**`stage3_structural_validation.py`** — `class_model_binding` collected across the CHK-3d-11 loop and stored in the new `Stage3Result.class_model_binding` field:
```json
{
  "structural_count": N,
  "with_class_model": N,
  "by_tier": {"1": N, "2": N, ...},
  "by_refinement_kind": {"introduce": N, "identity": N, ...},
  "invalid": [{"source_domain_id": "...", "entity": "...", "detail": "..."}]
}
```

**`stage4_entity_production.py`** — after the object_refs materialisation loop, `object_refs_binding` is assembled from the resolved paths and the `object_refs_dangling` warnings already in `pass_data`:
```json
{
  "formed": N,
  "dangling": [{"provenance_ref": "Rxx", "path": "Entity.attr", "reason": "..."}]
}
```
Stored in `pass_data["mechanism_data_stage4"]["object_refs_binding"]`.

Also in `stage4_entity_production.py`: removed `relationships_recorded: 0` and `values_recorded: 0` from the `dd_binding` audit dict.

**`__init__.py`** — all four new keys wired into `mechanism_data`:
- `class_model_binding`: from `stage3.class_model_binding`
- `object_refs_binding`: from `pass_data["mechanism_data_stage4"]["object_refs_binding"]`
- `model_coverage`: shaped from CHK-3d-12 result as `{parent_elements, covered, ratio}`
- `model_coverage_gaps[]`: from CHK-3d-12 `uncovered_entities` as `[{"entity": "..."}]`

Also removed `relationships_recorded: 0` and `values_recorded: 0` from the idempotent-pass dd_binding initialiser.

### 1c. Run 26 CHK-3d-11/12 evidence (retroactive from stored data)

**Row 1 pass (P1690) — CHK-3d-11:** 6 hard violations, all `tier must be in {2,3,4,5}, got 1`. The IM produced class_models with `tier: 1` which CHK-3d-11 correctly hard-rejected — 6 Structural proposals excluded. 0 soft violations.

**Row 2 pass (P1694) — CHK-3d-11:** 0 validation_failures, 0 soft violations. All Row 2 class_models passed the structural validity checks (tier=2 valid, ≥1 attribute present, ≥1 attribute with semantic_type). The profile over-population (§4) is NOT caught by CHK-3d-11 — see §4a below.

**Row 1 — CHK-3d-12:** No-op: `check_concept_coverage` returns immediately for `row_ref < 3`.

**Row 2 — CHK-3d-12:** Ran, but produced no coverage result. Because all Row 1 Structural class_models had `tier: 1` and were hard-rejected by CHK-3d-11, no class_models were committed to the DB for Row 1. `_get_class_models_for_row(session, project_id, row_ref - 1)` returned empty → early return with no coverage data. So CHK-3d-12 is functioning correctly — Row 1 simply has no prior class_models to check coverage against.

**Consequence of §1c finding:** The Row 1 IM is producing class_models with `tier: 1`, which CHK-3d-11 correctly rejects as hard-invalid (`tier must be in {2,3,4,5}`). This means Row 1 produces 0 committed class_models, which cascades: CHK-3d-12 at Row 2 has nothing to compute coverage against. This is a separate issue from the audit instrumentation gap — the Row 1 derivation prompt constrains `tier MUST equal the current row number` but the IM is producing `tier: 1` which falls outside the valid enum `{2,3,4,5}`.

---

## §2 — entity_ref resolver: match algorithm and mint behaviour

### 2a. How does the resolver match an entity name to a canonical?

The resolver (`resolve_and_record` → `resolve_term` in `data_dictionary/service.py`) runs three steps:

**Step 1 — Pre-filter (DM):** `_lookup_existing(session, surface_term)` performs a **case-insensitive exact match** against all existing canonical names and synonym surface_terms. If found → `outcome: existing`, returns immediately with that dd_id. No AI involved.

**Step 2 — IM comparison:** If Step 1 misses, `_judge(surface_term, context, canonical_entries)` makes an **AI call** presenting ALL existing canonical entries alongside the surface term and its statement context. The IM returns `confidence` (float), `best_canonical_ids` (list), `is_multi_candidate` (bool). This is the fuzzy/semantic step — the IM uses its language model to assess similarity across all canonicals.

**Step 3 — Gate (DM):** 
- `confidence < RESOLUTION_CONFIDENCE_BAND` OR `is_multi_candidate` → `flagged` (new entity, unresolved)
- `confidence ≥ band` AND `best_ids` non-empty → **synonym** (binds to existing canonical, wrong or right)
- `confidence ≥ band` AND `best_ids` empty → **mint new canonical**

**ChildEarnings → DD003 trace:**
1. `_lookup_existing` — "ChildEarnings" not found as canonical name or synonym surface_term. Step 2 triggered.
2. `_judge` called with "ChildEarnings" + statement context (earnings-related Structural requirement) + ALL existing canonicals including DD003 ("monetary value"). At Row 2, the entity is described abstractly; the IM judges "ChildEarnings" to be a form of "monetary value" with high confidence (≥ threshold) and returns `best_canonical_ids: ["DD003"]`.
3. Gate: confidence ≥ band, best_ids non-empty → `outcome: synonym` → `entity_ref = DD003`.

The binding is semantically plausible at the concept level but entity-structurally wrong: ChildEarnings is a distinct entity (an aggregate record) that happens to hold a monetary amount, not an instance of the "monetary value" concept.

### 2b. Does the resolver mint when there's no exact match?

Only if the IM judge returns `best_ids: []` (no similar canonical) at high confidence. If the IM finds any existing canonical with high confidence → synonym path. The resolver WILL fuzzy-bind when the IM judges sufficient similarity, as observed with ChildEarnings and TaskCompletionAssignment. The "mint-new when no exact match" behaviour is the correct spec intent per §6 — the current code violates it for entity_ref purposes.

### 2c. Uniqueness enforcement on entity_ref↔entity?

**None.** The sub-pass 1 loop in `_run_dd_binding` processes each `cm_struct_proposal` independently with no cross-proposal uniqueness check. Two proposals resolving to the same dd_id is not detected or flagged. This produces the observed DD006 collision (TaskCompletionAssignment and TaskCompletion → same canonical) and DD003 collision (two ChildEarnings → same canonical). No guard exists; behaviour is current.

---

## §3 — Duplicate-collapse key and per-(entity,row) guard

### 3a. What is the duplicate-collapse key?

CHK-3d-07 (`stage3_structural_validation.py` lines 596–615) uses:

```python
key = (p.statement.lower().strip(), frozenset(p.cci_refs))
```

**Both statement text AND cci_refs set must match** for collapse. Entity name, class_model content, and requirement_type are NOT part of the key. R057 and R064 survive as separate requirements because they have different statements (different attribute lists — `weekly_period`/`earnings_total` vs `weekly_period_id`/`total_earnings`) and may have different cci_refs sets. The collapse key treats them as distinct even though they model the same entity.

### 3b. Is there a "one class_model per (entity, row_target)" guard?

**No.** Stage 3 has no such guard. Each proposal is processed independently; entity names across proposals are never compared. Multiple Structural proposals for the same (entity, row) pass through and are committed as separate Requirement rows, producing divergent class_models for the same entity. Behaviour is current.

---

## §4 — Profile over-population: Row 2 class_models carrying Row 4 physical detail

### 4a. Is the §4.4.3c profile-conformance check implemented?

**No.** `class_model_validity.py` (CHK-3d-11) enforces:
- `tier not in {2,3,4,5}` → hard reject
- `tier != row_ref` → hard reject (so Row 2 class_models with tier=2 pass this check)
- `len(attributes) == 0` → hard reject
- `Row 2: no attribute with semantic_type` → hard reject
- FK without target_ref → soft

It does **NOT** check whether attributes at Row 2 carry only `semantic_type` (and not `physical_type`, `domain` values beyond concept-level, `key: PK/FK`). A Row 2 class_model with `task_id [PK] Integer domain=[available, unavailable]` passes CHK-3d-11 because `tier==2`, `≥1 attribute`, `semantic_type present`. No profile advisory is computed or surfaced because this check does not exist.

This is confirmed in Run 26 — P1694 shows 0 CHK-3d-11 failures despite the over-populated attributes.

### 4b. What is the deployed Row-2 class_model derivation guidance?

The `_CLASS_MODEL_GUIDANCE` block in `requirement_derivation_prompt.py` (lines 79–130) presents the **same full attribute schema at all rows 2–5** with no row-gating on which fields to populate. Specifically it instructs:

```json
"attributes": [
  {
    "name": "attr_name",
    "type": "String|Integer|DateTime|Boolean|Decimal|Enum|Reference|JSON",
    "key": "PK|FK|null",
    "semantic_type": "identifier|lifecycle_state|quantity|...",
    "origin": "refines|realises|introduced",
    "domain": ["allowed_value_1", "allowed_value_2"],
    "target_ref": "ForeignEntityName"
  }
]
```

CHK-3d-11 constraints listed in the prompt mention only: `tier MUST equal current row`, `refinement_kind MUST be one of five`, `≥1 attribute required`, `at Row 2 ≥1 attribute must have semantic_type`, `FK must have target_ref`. There is **no instruction to omit `type`, `key: PK/FK`, or `domain` at Row 2**. The IM fills whatever schema fields it finds plausible from the entity description, producing physical-tier content at Row 2 because nothing stops it.

**Root cause:** The IM is given the full physical schema with a single semantic_type carve-out; it naturally populates all visible fields. Without explicit "at Row 2, populate only: name, semantic_type, origin; omit type, key, domain" guidance, over-population is the expected IM behaviour.

---

## §5 — Prose Structurals duplicating class_model content

### 5a. Why does the IM emit prose Structurals for pure attribute assertions?

The routing condition is **"SHOULD"** (not "MUST"). The prompt says: *"When `requirement_type` is `Structural`, you SHOULD provide a `class_model` dict"*. The IM can emit `requirement_type: Structural` with no `class_model` — a prose Structural — and the system accepts it. CHK-3d-11 explicitly skips proposals without class_model:

```python
if p.requirement_type != "Structural" or not p.class_model:
    surviving_11.append(p)
    continue
```

There is no DM-layer routing that forces attribute assertions into class_model form.

The observed R023, R069, R072 pattern ("a task shall have an associated monetary value") appears when the IM produces a Structural statement about an attribute-holding relationship without recognising it as entity-modelling. Specifically: the object-recursion guidance in the interrogative preamble ("for every named Object entity, recurse — does it carry a structural obligation? If so, derive a dedicated Structural requirement") triggers the prose form rather than a class_model because the IM does not always recognise that the attribute observation belongs inside the existing Task class_model's attribute list.

### 5b. Are prose Structurals expected to be merged downstream?

No merging mechanism exists — there is no downstream step that reconciles prose Structurals against class_model content. They propagate as separate Requirement rows. Per F105 intent, pure attribute assertions should be folded into the entity's class_model, not produced as separate prose Structurals. Whether this is enforced in code or prompt is a spec decision; the current code does not enforce it at either layer.

---

## §6 — Observed behaviours that are spec gaps (no code change made)

Reporting current behaviour only per the request:

**CHK-3d-11 correctness + uniqueness:** Deployed check tests `tier`, `refinement_kind`, attribute count, semantic_type presence (Row 2), FK target_ref. Does NOT test: (a) whether entity_ref resolves to the *correct* canonical (only that it resolves), (b) uniqueness of entity_ref per (entity, row). Both are unimplemented at the DM layer.

**entity_ref minting rule:** Current behaviour: exact-name match → `existing`; AI judge high-confidence match → `synonym` (fuzzy bind); AI judge no match → `canonical` (mint new). The fuzzy-synonym path operates on entity names presented as class_model.entity strings; context is the requirement statement. No minimum edit-distance or name-equality gate exists before the synonym path — high semantic confidence alone is sufficient to bind to an existing canonical.

**object_ref path arity rule (C2):** The resolver in `core/object_refs_resolver.py` rejects any path with fewer than 2 segments as `malformed_path_min_2_segments`. Bare `<Entity>` references (1 segment) are rejected unconditionally. The ≥2-segment rule is the currently deployed rule; there is no edge-case handling (e.g., empty string is also rejected). This is confirmed by the Run 26 dangling entry: `{"path": "TaskCompletionAssignment", "reason": "malformed_path_min_2_segments"}`.

---

## Summary table

| Question | Status |
|---|---|
| CHK-3d-11 implemented and executing | Yes — hard rejects in validation_failures, soft in execution_warnings |
| CHK-3d-12 implemented and executing | Yes — but result was silently discarded from mechanism_data output (now fixed) |
| Profile-conformance check (§4a) | Not implemented |
| class_model_binding block | Now implemented — will appear in next run |
| object_refs_binding block | Now implemented — will appear in next run |
| model_coverage / model_coverage_gaps | Now implemented (from CHK-3d-12 result) — will appear in next run |
| dd_binding: relationships_recorded / values_recorded | Removed |
| entity_ref match algorithm | DM exact-match → IM AI judge → synonym-or-mint |
| entity_ref minting when no exact match | Only when AI judge returns no best_ids; fuzzy-bind otherwise (bug) |
| Uniqueness enforcement on entity_ref↔entity | None |
| CHK-3d-07 collapse key | (statement.lower().strip(), frozenset(cci_refs)) — no entity guard |
| Per-(entity, row) class_model guard | None |
| Row 2 class_model prompt field restriction | None — full physical schema shown at all rows 2–5 |
| Structural→class_model routing | "SHOULD" not "MUST"; no DM enforcement |
| Prose Structurals: merge mechanism | None |
