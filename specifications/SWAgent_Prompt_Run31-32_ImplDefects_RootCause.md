# SW-Agent Diagnostic Request — three implementation defects against the deployed spec (Runs 31–32)

**Runs reviewed:** `…Run31.json`, `…Run32.json`, ledger v2.17.
**Scope discipline:** the defects and required invariants are stated generally — they are properties of the mechanism, not of PMT. PMT strings appear only as *labelled evidence*. **Fix the mechanism, not the cited instance**; a fix that special-cases the example entities/attributes is not a fix.

**Note:** the resolver "`formed` includes unverified attribute paths" issue from the last review is now addressed **on the spec side** (Row 4 RD v0.38: `formed` is a per-segment verification; new `attribute_not_in_class_model` dangling reason). It is **not** in this list — implement to v0.38 when you take the resolver. The three items below are places where the **deployed build does not match a spec mandate that already exists**, plus one confirm-item.

## What is confirmed correct (do NOT regress)
- P1 (Row 1 no `class_model`), P2 (Row 2 profile clean), CHK-3d-13 exempt/repair, CHK-3d-09 atomicity, matching.
- The accreting `semantic_type` registry (reuse climbing, no spurious near-duplicates) — the open-accretion side of [G] is working.
- Bare-entity object_refs correctly dangle `malformed_path_min_2_segments`.

---

## 1. The [G] `attr_name`-non-empty hard gate is specified but not firing

**Spec mandate (already in force — Row 4 RD v0.37 §4.3 [G]):** a `class_model` attribute with an empty/absent `attr_name` MUST be rejected by CHK-3d-11 with `detail: attr_name_empty`. An attribute with no name is not a model element (it cannot be referenced by name) and may not be committed.

**Defect:** the gate is not rejecting null names — [G]'s soft side (the registry) is deployed, but the hard `attr_name` reject is not. Models composed entirely of unnamed attributes pass validation.

**Evidence (Runs 31–32, illustrative):** every surviving Row-2 model carries only `attr_name: null` attributes; `class_model_binding.invalid` contains no `attr_name_empty` (the only rejections are zero-attribute models under the older ≥1-attribute rule).

**Ask:** is the [G] `attr_name_empty` clause implemented in the class-model validator? If yes, why do all-null-name models pass? Make it reject. Also confirm the `semantic_type` shape (`^[a-z][a-z0-9_]*$`) and POS-tag gates exist as checks (not merely that this run's values happen to be clean).

---

## 2. The producer does not emit a real, referenceable `attr_name`

**Spec mandate (already in force — Row 4 RD v0.37 §5.4 Row 2):** every attribute the IM (or the CHK-3d-13 repair) emits carries `attr_name` = the attribute's actual, referenceable name (the noun a behavioural statement would use to reference it), alongside its `semantic_type`. Name and kind are distinct fields; emitting the kind without the name is incomplete.

**Defect:** the producer emits `semantic_type` but leaves `attr_name` null. This is the root that #1's gate exists to backstop — and the reason nothing resolves: there is no name for a behavioural path to bind to. The emitted name must be the *referenceable* one, or behavioural object_refs will dangle even against a correctly-validated model.

**Evidence (Runs 29–32, illustrative):** across four runs the producer has never populated `attr_name`; attributes carry only a `semantic_type`.

**Ask:** show the Row-2 `class_model` instruction and the emitted attribute JSON; fix the prompt/parse so the real attribute name is emitted (the noun the prose uses), not a placeholder or null.

---

## 3. CONFIRM — is the entity `entity_ref` binding reaching the strict path for *generic* terms?

**Spec position ([A], Row 4 RD §4.4.3a):** a `class_model`'s own entity name binds by **exact (normalised) canonical match, a registered synonym's `resolves_to`, or mint-new**, via `resolve_and_record(..., strict=True)` which skips the AI-judge step. The invariant we care about: a generic single-word entity name with no exact canonical should **mint its own**, not be absorbed into a semantically-near canonical.

**Observation:** a *distinctive* compound entity name mints its own canonical correctly, but a *generic* single-word entity name binds to a semantically-near existing canonical — i.e. the outcome is sensitive to how distinctive the term is, which the strict path is meant to remove.

**Evidence (illustrative):** in one run a compound earnings-type entity minted its own canonical while, in the same run, the bare single-word form bound to a different money-adjacent canonical; across runs the same bare term bound to two *different* near canonicals.

**This is a confirm-item, not yet a fix-item, because the spec permits one of the possible causes.** We need to know which is happening:
- **(a)** the bare term is binding through the **synonym `resolves_to`** path (a synonym registered earlier from a behavioural name-registration) — this is *within* the current spec, and the fix is a **spec decision** on whether an entity's own binding may use the synonym path at all (we will make that call); **or**
- **(b)** the bare term is reaching a **fuzzy / AI-judge** path despite `strict=True` — this is an **implementation bug** against [A].

**Ask:** for a generic single-word entity name that bound to a near canonical, show the binding decision — did it match an exact canonical, a synonym's `resolves_to`, or an ambiguous/judge path? That single fact tells us whether this is (a) a spec decision or (b) an [A] violation to fix.

---

## What we need back
1. The [G] `attr_name_empty` gate firing, and confirmation the `semantic_type` shape/POS gates exist as checks (#1).
2. The producer emitting real, referenceable `attr_name`s (#2).
3. The binding-decision trace for a generic single-word entity name (#3) — synonym path vs judge path.

(Resolver per-segment verification is spec'd in v0.38; implement it against that when you next touch `object_refs_resolver.py`. With #1/#2 landed and the resolver at v0.38, the next run's `formed` becomes trustworthy — the precondition for a Row 1–3 run to exercise CHK-3d-12.)
