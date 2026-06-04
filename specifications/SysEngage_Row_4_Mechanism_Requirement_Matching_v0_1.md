# SysEngage Row 4 Mechanism: Requirement Matching Service

**Implementation specification — physical / builder tier**

Version: 0.1
Date: 03 June 2026

**Abstraction level:** Row 4 — Builder / Physical. The implementable realisation of the Requirement Matching service. Every design decision traces to the Row 3 (logical) Requirement Matching Service spec; where this spec makes a physical choice the Row 3 spec deferred, that resolution is recorded in §6.

**Operational scope:** Cross-row standalone service (F93). Not a numbered pass. Invoked over an assembled requirement set; re-invokable incrementally.

**Purpose.** Implementation specification for the Requirement Matching service (findings F85, F82, F90, F93): establishes the cross-row «refine» links by judging each row n requirement against the row n−1 set (three-way: refine-link / no-match / duplicate-merge), using the Data Dictionary as shared vocabulary. Records the physical realisation: module structure, the matching-judgement implementation, the confidence band, merge and gap propagation, audit, fixtures, and VER→pytest mapping. Logical authority: the Row 3 Requirement Matching Service spec.

---

## 1. Mechanism Identification

| Field | Value |
|---|---|
| **Mechanism name** | Requirement Matching Service (physical) |
| **Operational scope** | Cross-row; standalone service |
| **Logical authority** | SysEngage Row 3 Mechanism: Requirement Matching Service v0.1 |
| **Structural sibling** | Row 4 Data Dictionary Service v0.1 (shared conventions: service-not-pass, model-judged IM act, confidence-banded gating, service-log audit, fixed-constant band) |
| **Reads ledger** | `Requirement` (the set), `Requirement.refines_refs` (writes); Data Dictionary (vocabulary) |
| **Mode** | IM (matching judgement); DM (writing refines_refs, recording merges/gaps); LPM (statements never rewritten) |

## 2. Cross-References

| Source | Relevance |
|---|---|
| **Row 3 Requirement Matching Service v0.1** | All sections — logical authority: the three-way act, bidirectionality, gating, incrementality, edge cases |
| **Canonical Ledger v2.13** | `Requirement.refines_refs` schema and normative rule (parent at row_target − 1; empty permitted) |
| **Row 4 Data Dictionary Service v0.1** | The vocabulary dependency — read via `resolve_object` / `aliases_of` for the entity-level candidate pre-filter |
| **Row 4 Requirement Derivation v0.5 §5.5** | The caller-side interface: derivation emits `refines_refs=[]`; this service populates it |
| **Issues Tracker — F85/F82/F86/F84/F90/F91/F93** | Founding findings; gap-signal semantics; GQA hand-off; DD dependency; state-completeness kinship; service framing |

## 3. Architectural Approach

### 3.1 Module structure

```
requirement_matching/
  service.py        # public: match_requirement, match_row (batch over a row), match_set
  judge.py          # the IM matching judgement (§4.2) — child vs candidate parents
  candidates.py     # DD-based candidate pre-filter (§4.1)
  gating.py         # confidence-band gate (§4.4); fixed MATCH_CONFIDENCE_BAND constant
  merge.py          # duplicate-merge + reference repointing (§4.5)
  gaps.py           # no-match upward residue + parent-orphan downward gaps (§4.6)
  audit.py          # service-log audit records (§5.3)
```

Stateless per call over the persistent requirement set; no four-stage envelope. `match_row(n)` is the typical invocation (match all row n requirements against row n−1).

### 3.2 Major design decisions (Row 4 resolutions of Row 3 deferrals)

- **D-rm-1 — the matching judgement (main deferred decision).** `judge(child, candidate_parents)` decides refine / duplicate / none + confidence. Implementation mirrors the DD's two-tier approach: (1) candidate pre-filter via the DD — parents whose Object resolves to the same/related canonical entry as the child (this is the cheap entity-level bound; F90's whole point is that the DD makes this an entity lookup, not free text); (2) a model-judged abstraction-level comparison over the pre-filtered candidates: is the child the *same obligation as a parent, more concrete* (refine), the *same obligation as a sibling at the same row* (duplicate), or *neither* (no-match)? Embedding similarity MAY pre-rank within the candidate set but does not decide the outcome (a cosine threshold would mistake topical overlap for refinement — the judgement is abstraction-level, not lexical).
- **D-rm-2 — refinement vs duplication discrimination.** A refine-link is across rows (child row n, parent row n−1); a duplicate is within a row (same row_target). The row dimension is decidable and pre-separates the two: cross-row candidates can only be refine/none; same-row candidates can only be duplicate/none. The model judges *within* each decidable bucket.
- **D-rm-3 — no-match is never auto-corrected.** A no-match writes a gap record (F86) and leaves `refines_refs` empty; it does NOT invent a parent (that is GQA, F84). Fail-safe: a judge error → treat as flagged-for-review, never as a false refine-link.
- **D-rm-4 — audit carrier.** A service log (`requirement_matching_log`), not a per-invocation AnalysisPass — consistent with the DD service decision (per-requirement frequency).

## 4. Operation-by-Operation Implementation

### 4.1 `candidates(child)` — DD-based pre-filter

Resolve the child requirement's Object/entity to its canonical DD entry (via `resolve_object`). Candidate parents = row n−1 requirements whose Object resolves to the same canonical entry, or to an entry related to it (via a DD `relationship`). If the child's Object is DD-unresolved (DD flagged it, §5.2 of Row 3), the child is marked not-yet-matchable and skipped until its DD resolution completes. This pre-filter is what makes matching tractable — it replaces a free-text all-pairs comparison with an entity-anchored candidate set.

### 4.2 `judge(child, candidate_parents, candidate_siblings)` — the IM act (D-rm-1, D-rm-2)

- Against **cross-row candidate_parents** (row n−1): judge refine vs none. Output: matched parent id(s) (many-to-many allowed) + confidence + multi-parent-ambiguous flag.
- Against **same-row candidate_siblings**: judge duplicate vs none. Output: duplicate-of id + confidence.
The judgement is abstraction-level reasoning ("is this the same obligation, one level more concrete?"), anchored on the shared DD entity. One retry on malformed output; persistent failure → flagged (D-rm-3 fail-safe).

### 4.3 `match_requirement(child) → MatchResult`

1. `candidates(child)` (§4.1); if not-yet-matchable, return deferred.
2. `judge(...)` (§4.2).
3. Gate (§4.4) and act:
   - **refine-link**, confidence ≥ BAND, not multi-parent-ambiguous → write `child.refines_refs += [parent_id...]` (each verified at row_target − 1); auto-record; log.
   - **duplicate**, confidence ≥ BAND → merge (§4.5).
   - **no-match** → leave `refines_refs` empty; write a gap record (§4.6, F86); log. (Row 1 child: no gap record — empty is correct, §4.6.)
   - confidence < BAND, or multi-parent-ambiguous → flag for Practitioner; do not commit; log.

### 4.4 `gating.py` — the confidence band

```python
# Fixed mechanism constant — provisional, NOT a ProjectProfile parameter at this version.
# Same rationale as the DD service: no run data yet on match-confidence distribution.
MATCH_CONFIDENCE_BAND = 0.85
MULTI_PARENT_MARGIN   = 0.05   # parents within this of the top score → ambiguous → flag
```
`0.85` is a provisional starting value, expected to be revisited against real match-confidence data; promotable to a ProjectProfile parameter if distributions show projects differ. Until validated, the band may be set conservatively high to favour Practitioner review over auto-linking.

### 4.5 `merge.py` — duplicate-merge and reference repointing (D-rm-1)

When two requirements at the same row duplicate: collapse to one survivor (preserve the union of cci_refs / domain_refs / provenance). **Repoint references** to the retired requirement — any `refines_refs` (in the row below) that pointed at the merged-away id is repointed to the survivor; the retired id is marked retired, not deleted (id not reused). This is the matching analogue of the DD's false-merge rejection propagation. High-confidence merges auto-record (reviewable); low-confidence flag for Practitioner.

### 4.6 `gaps.py` — upward residue and downward gaps (F86, §4.2 of Row 3)

- **Child-orphan (no-match):** a row n>1 requirement with empty `refines_refs` after matching → write an upward-gap record (novel requirement with no parent) for GQA (F84) to consider. **Row 1 exception:** a row 1 requirement's empty `refines_refs` is correct (top) → no gap record. The row check is decidable.
- **Parent-orphan (downward gap):** after matching a row, any row n−1 requirement that no row n requirement refines → write a downward-gap record (an obligation nothing elaborates). This is the bidirectional half (Row 3 §4.2) and the requirement-level sibling of the deferred F91 state-completeness check.

Both are records for gap analysis; neither is auto-fixed here.

## 5. Schema and Validation

### 5.1 What the service writes

Only `Requirement.refines_refs` (ledger v2.13: array of `R###`, each parent at row_target − 1, empty permitted), retirement flags on merged-away requirements, and gap/merge/log records. No statement/type/other-field changes.

### 5.2 DDL (records, not new ledger element types)

```sql
CREATE TABLE requirement_matching_log (
  log_id          BIGSERIAL PRIMARY KEY,
  requirement_id  VARCHAR(8) NOT NULL,
  outcome         VARCHAR(16) NOT NULL,   -- refine | duplicate | no_match | flagged | deferred
  parent_ids      JSONB,                  -- on refine
  duplicate_of    VARCHAR(8),             -- on duplicate
  confidence      DOUBLE PRECISION,
  auto_recorded   BOOLEAN NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE requirement_gap_record (
  gap_id          BIGSERIAL PRIMARY KEY,
  direction       VARCHAR(8) NOT NULL,    -- upward (child-orphan) | downward (parent-orphan)
  requirement_id  VARCHAR(8) NOT NULL,
  row_target      VARCHAR(1) NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```
`refines_refs` itself is the existing JSONB column on `requirement` (added in Row 4 Requirement Derivation v0.5, ledger v2.13). This service writes it; it does not add ledger element types. (Gap records may later promote to canonical `Gap` elements — the existing ledger Gap type — when GQA consumes them; that integration is a GQA-mechanism concern, noted not built here.)

### 5.3 Audit

`requirement_matching_log` row per `match_requirement`. `refines_refs` is itself the durable audit surface for links (as the synonym register is for the DD); the log carries flags, merges, and no-matches.

## 6. Verification Criteria (→ pytest)

| ID | Criterion | Test |
|---|---|---|
| VER-rm-01 | every populated `refines_refs` entry references an existing Requirement at row_target − 1 | `test_refines_refs_parent_row` |
| VER-rm-02 | no row 1 requirement has non-empty `refines_refs` | `test_row1_top` |
| VER-rm-03 | duplicate-merge → one survivor; retired id flagged, not dangling; references repointed | `test_merge_repoint` |
| VER-rm-04 | confidence ≥ BAND ⇒ auto-recorded; < BAND or multi-parent ⇒ flagged | `test_gating` |
| VER-rm-05 | every row n>1 no-match → an upward gap record; no gap record for row 1 empties | `test_no_match_gap` |
| VER-rm-06 | every parent-orphan → a downward gap record | `test_parent_orphan_gap` |
| VER-rm-07 | DD-unresolved Object ⇒ deferred (not-yet-matchable), not forced | `test_dd_unresolved_deferred` |
| VER-rm-08 | idempotency: re-matching an unchanged set adds no new links/records | `test_idempotent` |

## 7. Test Fixtures

Realises Row 3 §7 on real PMT requirements:
- **F-rm-1** row 2 req refines one row 1 parent (DD makes "work opportunity"≈"task") → refine-link (`test_refine_single`).
- **F-rm-2** cross-cutting row 2 req → two parents (`test_refine_many`).
- **F-rm-3** novel row 2 req → no-match → upward gap (`test_no_match`).
- **F-rm-4** duplicate row 2 reqs → merge + repoint (`test_duplicate_merge`).
- **F-rm-5** row 1 parent with no row 2 child → downward gap (`test_parent_orphan`).
- **F-rm-6** low-confidence / multi-parent → flagged (`test_flagged`).
- **F-rm-7** row 1 reqs → no upward matching, empty refines_refs, no gap (`test_row1`).
- **F-rm-8** GQA generates a parent + re-descends → re-match links the child (`test_incremental_relink`).

## 8. Edge Cases

Per Row 3 §8: row 1 (no parents; empty correct, not a gap); row n−1 not yet derived (defer, not fail); DD-unresolved Object (defer); self/same-row refine forbidden decidably (row_target − 1 rule); many-to-many fan-out uncapped. Judge failure → flagged, never auto-link (D-rm-3).

## 9. Cross-Mechanism Interactions

- **Requirement Derivation (upstream):** emits `refines_refs=[]` (§5.5 interface); this service populates it.
- **Data Dictionary service (dependency):** read for the entity pre-filter; DD-before-Matching ordering enforced (DD-unresolved → defer).
- **GQA / gap analysis (downstream, F84/F86):** consumes upward and downward gap records; re-triggers matching after re-descent. The gap records here are the hand-off; promotion to canonical `Gap` elements is a GQA concern.
- **Phase 4 (downstream, F82 motivation):** reads `refines_refs` to score higher-level requirements as satisfied by their linked refinements.
- **Back-refinement / state-completeness (F91):** the parent-orphan check (§4.6) is the requirement-level sibling; the general state-completeness mechanism remains deferred.

## 10. Build Notes

- Row 4 resolutions of Row 3 deferrals: D-rm-1 (two-tier: DD candidate pre-filter + model-judged abstraction-level comparison, embedding only to pre-rank), D-rm-2 (row dimension pre-separates refine from duplicate decidably), D-rm-3 (no-match never auto-corrected; fail-safe to flagged), D-rm-4 (service log not AnalysisPass).
- `MATCH_CONFIDENCE_BAND` / `MULTI_PARENT_MARGIN` fixed constants pending data; promotable to ProjectProfile.
- The model-judged matching (D-rm-1) is the IM heart and the main thing to validate on real data; until validated, set BAND high to favour review.
- Gap-record → canonical `Gap` element promotion is a GQA-mechanism integration, noted not built here.

## Document End

End of SysEngage Row 4 Mechanism: Requirement Matching Service v0.1.

Physical realisation of the Row 3 logical Requirement Matching Service spec, against ledger v2.13 (`refines_refs`). Two-tier matching (DD candidate pre-filter + model-judged abstraction-level comparison); row dimension pre-separates refine (cross-row) from duplicate (same-row); confidence-banded auto-link/merge-with-review (fixed constant BAND=0.85, provisional); duplicate-merge with reference repointing; no-match → upward gap (F86, never auto-corrected); parent-orphan → downward gap (bidirectional, F91 kinship); service-log audit. Completes the Requirement Matching mechanism pair (Row 3 logical + Row 4 physical).

Companion artefacts:
- SysEngage_Row_3_Mechanism_Requirement_Matching_v0_1.md — logical authority
- sysengage_minimal_ledger_spec_v2_13.md — `Requirement.refines_refs` schema authority
- SysEngage_Row_4_Mechanism_Data_Dictionary_v0_1.md — the vocabulary dependency
- SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_5.md §5.5 — the caller-side interface this service realises
- SysEngage_Issues_Tracker_v0_63.md — F85, F82, F86, F84, F90, F93 disposition
