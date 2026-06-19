# RD v0.15 — Spec Review

**Against:** `SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_15.md`  
**Implementation baseline:** checkpoint `ef596466` (v0.14 gaps closed)  
**Date:** 2026-06-09  
**Reviewer:** Replit Agent

---

## Summary

| Category | Count |
|---|---|
| Spec internal inconsistencies | 4 |
| Spec gaps (undocumented implementation behaviour) | 1 |
| Spec/implementation divergences | 1 |
| Cosmetic docstring debt (code) | 2 |
| **Code action required** | **0** |
| **Spec doc update required** | **6** |

No code changes needed. All findings are spec-side. Ordered by severity.

---

## SPEC-A — §12.2 OQ-3d-01 still says "two-part hash" *(HIGH — direct contradiction)*

**Location:** §12.2 OQ-3d-01 resolution (line ~977)

**Current text:**
> Two-part SHA-256 hash over sorted CCI-ids and sorted active Domain-ids; `domain_id_set` stored separately for Domain-set comparison; Domain-set change forces FullRerun (§4.1, MD-3).

**Problem:** The BUG-3 fix (SPEC-1 from v0.14) correctly updated MD-3 (§3.2) to document the three-part hash, but the OQ-3d-01 resolution block was not updated. OQ-3d-01 now contradicts MD-3 directly — a reader checking the OQ resolution against the main spec will see two different answers.

**Required update:**
```
OQ-3d-01 (re-run mechanics) | Three-part SHA-256 hash for rows ≥ 2;
two-part for Row 1 (no seeds above). Hash =
  SHA-256("CCI:<ids>||DOM:<ids>||SEEDS:<sorted row n-1 ids>")
for rows ≥ 2; SHA-256("CCI:<ids>||DOM:<ids>") for Row 1.
`domain_id_set` stored separately for the Domain-set-change comparison.
Domain-set change → FullRerun; SEEDS-segment change (upstream row
committed new requirements) → FullRerun. See MD-3 (§3.2).
```

---

## SPEC-B — §12.5 "Deviations" bullet still says "two-part" *(HIGH — direct contradiction)*

**Location:** §12.5 "Deviations from the Domain Derivation sibling to watch:" (line ~1019)

**Current text:**
> Re-run hash is **two-part**; a Domain-set change forces FullRerun.

**Problem:** Same residual error as SPEC-A — this deviation note was not updated when MD-3 was corrected in v0.15.

**Required update:**
```
Re-run hash is three-part for rows ≥ 2 (CCI|DOM|SEEDS) and
two-part for Row 1 (CCI|DOM — no row above). A Domain-set change
OR a change in surviving row n-1 requirement ids forces FullRerun.
See MD-3 (§3.2).
```

---

## SPEC-C — §4.4.3 `refines_refs=[]` clause contradicts §4.2 Path R *(MEDIUM — internal inconsistency)*

**Location:** §4.4.3 Requirement construction (line ~215)

**Current text:**
> `refines_refs=[]` (F82 — populated later by the Requirement Matching service, NOT by Pass 3d; §5.5 / F93)

**Problem:** This statement was correct before v0.13 (Path R). Under v0.13+ Path R, proposals produced by seed interrogative-elaboration carry `refines_refs=[seed_id]` **set at derivation** (§4.2: "each tagged `refines_refs=[seed_id]` set AT DERIVATION, by construction"). The §4.4.3 text is a pre-Path-R carry-over that now contradicts §4.2.

The implementation correctly commits Path R proposals with their `refines_refs` intact (stage4_entity_production.py line 754: `"refines_refs": json.dumps(sorted(proposal.refines_refs))`).

**Required update:**
```
refines_refs = proposal.refines_refs as set at derivation (Path R proposals
carry [seed_id] by construction — §4.2); [] for Path N proposals
(populated later by the Requirement Matching service — §5.5 / F93).
```

---

## SPEC-D — Filename header wrong *(LOW — cosmetic)*

**Location:** Line 5

**Current text:**
```
Filename: SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_5.md
```

**Required update:** `v0_5.md` → `v0_15.md`

---

## SPEC-E — §4.4.2 MD-2 undocumented Path R fallback *(MEDIUM — spec gap)*

**Location:** §4.4.2 domain_refs DM-derivation

**Current spec text:**
> `domain_refs = sorted({d.domain_id for d in active_domains if set(proposal.cci_refs) & set(d.cell_content_item_refs)})`
> Assert `len(domain_refs) >= 1` (guaranteed under MD-1 post-CHK-3d-03)

**Problem:** The formula only works for Path N proposals (non-empty `cci_refs`). Path R proposals produced without any `cci_refs` (pure seed elaboration) yield an empty intersection, which would fail the MD-2 assert and reject the proposal. The guarantee "guaranteed under MD-1 post-CHK-3d-03" does not hold for Path R proposals.

The implementation handles this correctly with a fallback (stage4_entity_production.py lines 619–624):
```python
if proposal.refines_refs and proposal.source_domain_id:
    active_domain_ids = {d.domain_id for d in active_domains}
    if proposal.source_domain_id in active_domain_ids:
        return [proposal.source_domain_id]
    if active_domains:
        return [active_domains[0].domain_id]
```

The spec does not document this fallback, making the "guaranteed" assertion misleading.

**Required update — append to §4.4.2:**
```
Path R exception: a Path R proposal with empty cci_refs (pure seed
elaboration with no row-n CCI references) cannot resolve domain_refs
by set intersection. Fall back to [source_domain_id] — the Domain
that batched the seed for elaboration — if that domain_id is active;
otherwise the first active Domain. The MD-2 assert is still satisfiable
for any Path R proposal (its source_domain_id is always set at derivation).
The "guaranteed under MD-1 post-CHK-3d-03" note applies to Path N only.
```

---

## SPEC-F — §4.2 Path R batching — spec says per-Domain; implementation uses one batch *(LOW — spec/impl divergence)*

**Location:** §4.2 Path R description (line ~154)

**Current spec text:**
> Batch seeds by Domain lineage; per batch invoke `requirement_refinement_prompt.py`

**Implementation:** `_run_path_r()` is called once with all seeds in a single batch (stage2_ai_derivation.py line 379), regardless of Domain lineage. The per-Domain batching described in the spec is not implemented.

**Impact:** Low in practice — one combined call is simpler and works correctly. But for large rows (many seeds across many Domains) this produces a single large AI call rather than smaller per-Domain calls. As seed volumes grow the token ceiling risk increases.

**Options:**
1. Update spec to match implementation ("one batch for all seeds").
2. Implement per-Domain batching as specified (more complex; no evidence of failure yet).

**Recommendation:** Update spec to match the implemented one-batch strategy at v0.15; add a note that per-Domain batching is deferred to a later version when token ceiling pressure is observed in practice.

---

## Code Docstring Debt (cosmetic; no functional gap)

These do not affect runtime behaviour but should be updated to reduce reader confusion.

| File | Current | Required |
|---|---|---|
| `stage1_preflight.py` line 12 | `"two-part SHA-256 hash (CCI-ids + active Domain-ids)"` | `"three-part SHA-256 hash for rows ≥ 2 (CCI-ids + Domain-ids + SEEDS); two-part for Row 1"` |
| `stage2_ai_derivation.py` line 4 | `"Per Requirement Derivation Mechanism Spec v0.13 §4.2"` | `"Per Requirement Derivation Mechanism Spec v0.15 §4.2"` |

---

## Implementation Conformance Snapshot

All v0.14 build gaps confirmed closed against v0.15:

| Item | Spec reference | Status |
|---|---|---|
| Three-part hash (`\|\|SEEDS:`) for rows ≥ 2 | MD-3 (§3.2) | ✅ Implemented — stage1_preflight.py |
| `seed_set_surviving_count` field | §4.2 | ✅ Implemented — Stage2Result |
| `_count_surviving_requirements()` independent query | VER-3d-21 | ✅ Implemented — stage2_ai_derivation.py |
| `empty_seed_set_upstream_gap` warning | §4.2 | ✅ Implemented — run_stage2 |
| VER-3d-21 provenance guard in Stage 3 | §8.1 VER-3d-21 | ✅ Implemented — stage3_structural_validation.py |
| `chk3d10_seed_extinct` persistent-gap warning | §4.3 CHK-3d-10 | ✅ Implemented — stage3_structural_validation.py |
| VER-3d-03 corrected (`cci_refs OR refines_refs`) | §8.1 VER-3d-03 | ✅ In spec; aligns with migration 025 |
| §3.1 lists `requirement_refinement_prompt.py` | §3.1 | ✅ In spec; both files listed |
| `refines_refs` committed for Path R proposals | §4.4.3 / stage4 | ✅ Implemented (contradicts §4.4.3 text — SPEC-C) |
| MD-2 Path R fallback (`source_domain_id`) | Not in spec — SPEC-E | ✅ Implemented; spec gap only |
