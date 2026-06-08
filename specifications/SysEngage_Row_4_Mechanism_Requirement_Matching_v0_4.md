# SysEngage Row 4 Mechanism: Requirement Matching Service

**Implementation specification — physical / builder tier**

Version: 0.4
Date: 06 June 2026

**Abstraction level:** Row 4 — Builder / Physical. The implementable realisation of the Requirement Matching service. Every design decision traces to the Row 3 (logical) Requirement Matching Service spec; where this spec makes a physical choice the Row 3 spec deferred, that resolution is recorded in §3.2 / §6.

**Operational scope:** Cross-row standalone service (F93). Not a numbered pipeline pass (invocation sense); re-invocable incrementally. Records an AnalysisPass per execution as its provenance artefact (§5.3).

**Purpose.** Implementation specification for the Requirement Matching service (findings F85, F82, F90, F93): establishes the cross-row «refine» links by judging each row n requirement against the row n−1 set (three-way: refine-link / no-match / duplicate-merge), using the Data Dictionary as shared vocabulary. Records the physical realisation: module structure, the matching-judgement implementation, the confidence band, merge and gap propagation, the provenance AnalysisPass, fixtures, and VER→pytest mapping. Logical authority: the Row 3 Requirement Matching Service spec v0.2.

---

## Changelog

**v0.4 (06 June 2026) — Subject-class distinctness + empty-candidate-set correction.**
- **D-rm-5 (new) — subject-class is a duplicate pre-separator.** Two same-row requirements that share a DD entity but differ in **subject class** (actor / system / business per Row 2 Understanding §2.3.3) are **complementary, not duplicate** (boundary sides / column aspects of one concept). The duplicate judgement is pre-separated by subject class exactly as D-rm-2 pre-separates refine from duplicate by row: only **same-subject-class** siblings are duplicate candidates; a cross-subject-class same-entity pair is **never merged**. §4.1 sibling candidate set and §4.2 / §4.5 updated; new **VER-rm-11**. Fixes the observed false-merge of an actor statement with its system affordance (PMT R2: R031 "a parent can access reports" ↔ R022 "the system shall make reports available").
- **D-rm-6 (new) — an empty candidate set is NOT a no-match.** A row n>1 child that is DD-resolved but whose candidate set is **empty** (no row n−1 requirement shares its entity) is recorded as a distinct outcome **`no_candidates`**, separate from `no_match` (candidates considered, none fit). `no_candidates` emits a distinct gap-record kind (`unmatched_no_candidates`) signalling a possible pre-filter / cross-row-vocabulary gap — NOT a confident novel-orphan claim. Prevents an empty pre-filter from masquerading as assessed novelty and corrupting the gap signal (PMT R2 Run10: 12 requirements stamped `no_match` on 0 candidates). §4.3 / §4.6 / §5.2 enum + counts updated; new **VER-rm-12**.
- No change to the duplicate-merge survivor logic (v0.3), the provenance carrier (v0.2), refine-link judgement, or schema.

**v0.3 (06 June 2026) — Deterministic duplicate-merge survivor selection (Non-Loss fix).**

**v0.3 (06 June 2026) — Deterministic duplicate-merge survivor selection (Non-Loss fix).**
- §4.5 `merge.py` rewritten: duplicate claims are resolved into **duplicate equivalence classes** (union-find / connected components over the judge's `duplicate_of` edges, so reciprocal A↔B and chained A↔B↔C form one class). Each class collapses to **one survivor = lowest `requirement_id`**; the rest are retired and repointed; the survivor takes the union of the class's refs; **one `merge_record` per class** (`survivor_id`, `retired_ids[]`). **Hard Non-Loss assertion:** every class has exactly one active survivor — retiring all members is a fail-closed error.
- VER-rm-03 strengthened; new **VER-rm-10** (`test_circular_merge_survivor`) — reciprocal/chained claims → one survivor, never both-retired.
- `merge_records` schema gains `retired_ids` (array) replacing the single `retired_id`.
- Realises Row 3 Requirement Matching v0.3 §4.1.3. Motivated by PMT R2 T&E (reciprocal pair R026↔R035 had both members retired).

**v0.2 (06 June 2026)** — Provenance carrier reversed from service-log to AnalysisPass; see below.

**v0.2 (06 June 2026) — Provenance carrier reversed from service-log to AnalysisPass.**
- **D-rm-4 reversed.** The audit carrier is now a **self-recorded AnalysisPass per matching execution** (one pass per `match_row` / `match_set` invocation), replacing the v0.1 `requirement_matching_log` DDL service-log. Rationale below.
- The v0.1 "per-requirement frequency" objection is resolved by **granularity**: the pass is written **per execution (per row matched), not per requirement** — the per-requirement detail lives in `AnalysisPass.outputs.mechanism_data` (the same way Domain Derivation records its per-domain decisions in one pass). At per-execution granularity the frequency objection does not apply.
- §5.2 replaced: the DDL service-log tables (`requirement_matching_log`, `requirement_gap_record`) are removed; the match records and gap records are now structured sub-fields of `outputs.mechanism_data` (§5.2, §5.3). Single store, in the ledger, visible to the same review path as every other mechanism's provenance.
- §1.1 structural-sibling line qualified: Matching diverges from the DD on the audit carrier (records a pass; the DD does not) — deliberate, because Matching is an active per-row IM judgement (sibling to Domain Derivation), not a passive accumulating store. Other shared conventions (model-judged IM act, confidence-banded gating, fixed-constant band) retained.
- Added **VER-rm-09** (provenance AnalysisPass recorded and complete). Existing VER-rm-05/06 retained; "gap record" now denotes a `mechanism_data` gap-record entry.
- No ledger-spec change required: `mechanism` is a free string, `pass_type` accepts "Per-row", `outputs` is a free-form object whose mechanism-specific sub-structure is the mechanism's responsibility (ledger v2.15 §AnalysisPass).
- Version references advanced (ledger v2.15; RD v0.6; Issues Tracker v0.65; Row 3 Matching v0.2).

**v0.1 (03 June 2026)** — Initial physical specification.

---

## 1. Mechanism Identification

| Field | Value |
|---|---|
| **Mechanism name** | Requirement Matching Service (physical) |
| **`AnalysisPass.mechanism`** | `"RequirementMatching"` |
| **Operational scope** | Cross-row; standalone service (not a numbered pipeline pass) |
| **Logical authority** | SysEngage Row 3 Mechanism: Requirement Matching Service v0.3 |
| **Structural sibling** | Row 4 Data Dictionary Service v0.1 (shared: model-judged IM act, confidence-banded gating, fixed-constant band). **Divergence:** Matching records a provenance AnalysisPass per execution; the DD uses a service-log. The divergence is deliberate — Matching is an active per-row IM judgement (provenance sibling to Domain Derivation), not a passive accumulating store. |
| **Reads ledger** | `Requirement` (the set), `Requirement.refines_refs` (writes); Data Dictionary (vocabulary) |
| **Writes ledger** | `Requirement.refines_refs`; retirement flags on merged-away requirements; one `AnalysisPass` per execution (provenance, §5.3) |
| **Mode** | IM (matching judgement); DM (writing refines_refs, recording merges/gaps, writing the provenance pass); LPM (statements never rewritten) |

## 2. Cross-References

| Source | Relevance |
|---|---|
| **Row 3 Requirement Matching Service v0.3** | All sections — logical authority: the three-way act, bidirectionality, gating, incrementality, decision-provenance requirement (§4.5), edge cases |
| **Canonical Ledger v2.15** | `Requirement.refines_refs` schema and normative rule (parent at row_target − 1; empty permitted), introduced v2.13; `AnalysisPass` schema (mechanism / execution_status / mode_active / declared_transformation_modes / outputs / timestamps — F25) as the provenance carrier |
| **Row 4 Data Dictionary Service v0.1** | The vocabulary dependency — read via `resolve_object` / `aliases_of` for the entity-level candidate pre-filter |
| **Row 4 Requirement Derivation v0.6 §5.5** | The caller-side interface: derivation emits `refines_refs=[]`; this service populates it |
| **Row 4 Domain Derivation (provenance pattern)** | The model for a cross-cutting analytical mechanism that records per-item decisions in a single pass's `outputs.mechanism_data` (splits/absorptions) — the pattern this service now follows for match records |
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
  provenance.py     # assemble + write the per-execution AnalysisPass (§5.3) [v0.2: was audit.py/service-log]
```

Stateless per call over the persistent requirement set; no four-stage envelope. `match_row(n)` is the typical invocation (match all row n requirements against row n−1) and is the unit that produces one AnalysisPass.

### 3.2 Major design decisions (Row 4 resolutions of Row 3 deferrals)

- **D-rm-1 — the matching judgement (main deferred decision).** `judge(child, candidate_parents)` decides refine / duplicate / none + confidence. Implementation mirrors the DD's two-tier approach: (1) candidate pre-filter via the DD — parents whose Object resolves to the same/related canonical entry as the child (this is the cheap entity-level bound; F90's whole point is that the DD makes this an entity lookup, not free text); (2) a model-judged abstraction-level comparison over the pre-filtered candidates: is the child the *same obligation as a parent, more concrete* (refine), the *same obligation as a sibling at the same row* (duplicate), or *neither* (no-match)? Embedding similarity MAY pre-rank within the candidate set but does not decide the outcome (a cosine threshold would mistake topical overlap for refinement — the judgement is abstraction-level, not lexical).
- **D-rm-2 — refinement vs duplication discrimination.** A refine-link is across rows (child row n, parent row n−1); a duplicate is within a row (same row_target). The row dimension is decidable and pre-separates the two: cross-row candidates can only be refine/none; same-row candidates can only be duplicate/none. The model judges *within* each decidable bucket.
- **D-rm-3 — no-match is never auto-corrected.** A no-match writes a gap record (F86) and leaves `refines_refs` empty; it does NOT invent a parent (that is GQA, F84). Fail-safe: a judge error → treat as flagged-for-review, never as a false refine-link.
- **D-rm-4 (v0.2 — REVERSED) — audit carrier is a per-execution AnalysisPass.** The service records **one `AnalysisPass` per matching execution** (`match_row` / `match_set`), mechanism = `"RequirementMatching"`, with the per-requirement decision detail in `outputs.mechanism_data` (§5.3). This replaces the v0.1 decision (a `requirement_matching_log` DDL service-log, "not a per-invocation AnalysisPass"). Two reasons drove the reversal: (a) the v0.1 carrier put the decision provenance *outside the ledger*, so it was invisible to the review path that inspects every other mechanism's provenance, and a no-match could not be distinguished from a missed parent by ledger inspection (Row 3 §4.5/PLB-rm-03); (b) the stated v0.1 objection — "per-requirement frequency" — does not apply once the pass is written **per execution, not per requirement**, with per-match rows carried in `mechanism_data` exactly as Domain Derivation carries its per-domain decisions. The DD analogy that justified v0.1 is the wrong sibling: Matching's provenance sibling is Domain Derivation (active per-row judgement), not the DD (passive store).
- **D-rm-5 (v0.4) — subject-class pre-separates duplicates.** Same-entity is necessary but NOT sufficient for a duplicate. Two same-row requirements that resolve to the same DD entity but carry **different subject classes** (actor / system / business — Row 2 Understanding §2.3.3) are **complementary, not duplicate**: they are different boundary sides / Zachman-column aspects of one concept (the actor reaching in; the system affordance; the business responsibility), each a distinct obligation. The subject class is therefore a hard pre-separator on the *duplicate* branch, the way the row dimension (D-rm-2) is a hard pre-separator between refine and duplicate: **only same-subject-class siblings are eligible to be judged duplicate; a cross-subject-class same-entity pair is excluded from the duplicate candidate set and never merged.** (Such a pair MAY be a complementary relationship — the system affordance enables the actor action — but matching does not create that link here; it is a relationship concern, not a merge.) Subject class is determined from `Requirement.subject` by the same closed classification CHK-3d-08 uses (leading "the system" → system; actor-noun + can/may/shall-be-able → actor; "the business" / named role → business); an explicit `subject_class` field is read if present. This is decidable — it narrows the candidate set before the IM duplicate judgement, it does not ask the model to weigh subject class.
- **D-rm-6 (v0.4) — empty candidate set ≠ no-match.** The three-way outcome assumed candidates were offered. When the §4.1 pre-filter returns an **empty** candidate set for a DD-resolved row n>1 child (no row n−1 requirement shares its entity), there is nothing to judge — the child was *not assessed against any parent*, which is categorically different from *assessed against parents and found novel*. Recording it as `no_match` overstates the gap signal as confident novelty when it may be a cross-row vocabulary / pre-filter miss (the very failure mode the entity-vocabulary fixes target). v0.4 records this as a distinct outcome **`no_candidates`** with its own gap-record kind (`unmatched_no_candidates`): a *possible* novelty or a *possible* recall gap, flagged for review, not asserted as a novel orphan. `no_match` is reserved for "candidates_considered ≥ 1, none judged a parent." (DD-unresolved children remain `deferred`, D-rm-1/VER-rm-07 — a third, distinct state.)

## 4. Operation-by-Operation Implementation

### 4.1 `candidates(child)` — DD-based pre-filter

Resolve the child requirement's Object/entity to its canonical DD entry (via `resolve_object`). Candidate parents = row n−1 requirements whose Object resolves to the same canonical entry, or to an entry related to it (via a DD `relationship`). If the child's Object is DD-unresolved (DD flagged it, §5.2 of Row 3), the child is marked not-yet-matchable and skipped until its DD resolution completes. This pre-filter is what makes matching tractable — it replaces a free-text all-pairs comparison with an entity-anchored candidate set. **The candidate set returned here is retained for the provenance record** (§5.3) so the rejected candidates of a no-match are auditable. **Sibling set (D-rm-5):** the same-row sibling candidates are additionally filtered to the child's own subject class (actor / system / business); same-entity siblings of a different subject class are dropped from the duplicate candidates (they are complementary, not duplicate). **Empty-set signal (D-rm-6):** if the child is DD-resolved but the candidate-parent set is empty, that emptiness is carried through as `no_candidates` (§4.3), distinct from a judged no-match.

### 4.2 `judge(child, candidate_parents, candidate_siblings)` — the IM act (D-rm-1, D-rm-2)

- Against **cross-row candidate_parents** (row n−1): judge refine vs none. Output: matched parent id(s) (many-to-many allowed) + confidence + multi-parent-ambiguous flag.
- Against **same-row candidate_siblings**: judge duplicate vs none. Output: duplicate-of id + confidence. **Subject-class pre-separation (D-rm-5):** the candidate_siblings set passed here contains only siblings of the **same subject class** as the child (actor / system / business, from `Requirement.subject`); same-entity siblings of a *different* subject class are excluded upstream (§4.1) and are never judged duplicate — they are complementary boundary/column aspects, not repeats.
The judgement is abstraction-level reasoning ("is this the same obligation, one level more concrete?"), anchored on the shared DD entity. One retry on malformed output; persistent failure → flagged (D-rm-3 fail-safe). The AI-model fingerprint of each judgement call is captured for the provenance record (§5.3).

### 4.3 `match_requirement(child) → MatchResult`

1. `candidates(child)` (§4.1); if not-yet-matchable (DD-unresolved Object), return `deferred`. **If the child is DD-resolved but the candidate-parent set is empty (row n>1), return `no_candidates` (D-rm-6): leave `refines_refs` empty; emit an `unmatched_no_candidates` gap record (§4.6) and a match record (with `candidates_considered: []`). Do NOT judge and do NOT record `no_match`. (Row 1 child: empty is correct — no gap record.)**
2. `judge(...)` (§4.2) — reached only when ≥1 candidate exists.
3. Gate (§4.4) and act:
   - **refine-link**, confidence ≥ BAND, not multi-parent-ambiguous → write `child.refines_refs += [parent_id...]` (each verified at row_target − 1); auto-record; emit a match record into the execution provenance.
   - **duplicate**, confidence ≥ BAND → merge (§4.5); emit a match record.
   - **no-match** (candidates were considered, none judged a parent) → leave `refines_refs` empty; emit a gap record (§4.6, F86) and a match record carrying the rejected candidate set. (Row 1 child: no gap record — empty is correct, §4.6.)
   - confidence < BAND, or multi-parent-ambiguous → flag for Practitioner; do not commit; emit a `flagged` match record.

Every branch emits exactly one match record into the per-execution provenance accumulator (§5.3); no requirement processed is unaccounted for.

### 4.4 `gating.py` — the confidence band

```python
# Fixed mechanism constant — provisional, NOT a ProjectProfile parameter at this version.
# Same rationale as the DD service: no run data yet on match-confidence distribution.
MATCH_CONFIDENCE_BAND = 0.85
MULTI_PARENT_MARGIN   = 0.05   # parents within this of the top score → ambiguous → flag
```
`0.85` is a provisional starting value, expected to be revisited against real match-confidence data; promotable to a ProjectProfile parameter if distributions show projects differ. Until validated, the band may be set conservatively high to favour Practitioner review over auto-linking. **The recorded provenance (§5.3) is the data source for this calibration** — per-match confidences across runs are what a future F-series calibration of BAND will be argued from.

### 4.5 `merge.py` — duplicate-merge, deterministic survivor, reference repointing (D-rm-1)

Duplicate claims from the judge (§4.2) are pairwise and may be reciprocal (A `duplicate_of` B *and* B `duplicate_of` A) or chained (A≡B, B≡C). `merge.py` first resolves them into **duplicate equivalence classes** — connected components (union-find) over the `duplicate_of` edges — so one underlying duplicate relationship is handled once, not once per emitted claim.

Per class:
- **Survivor = the member with the lowest `requirement_id`** (deterministic, order-independent — a reciprocal pair always resolves to the same survivor). 
- **Retire the other members** (soft-retire, `retired_at` set, id not reused); the survivor takes the **union** of the class's `cci_refs` / `domain_refs` / provenance.
- **Repoint references:** any `refines_refs` (in the row below) pointing at a retired member is repointed to the survivor.
- **One `merge_record` per class:** `{ survivor_id, retired_ids:[…], confidence }`.
- **Hard Non-Loss assertion (fail-closed):** each class has exactly one **active** survivor after the merge; `assert survivor not in retired_ids and len(class) - len(retired_ids) == 1`. Retiring all members of a class is a fail-closed error (the merge is rejected and the requirements left intact, flagged for review) — it is never silently allowed. This is the explicit guard against the both-members-retired failure observed in T&E.

High-confidence merges auto-record (reviewable); low-confidence flag for Practitioner. The merge and its repointing are recorded in the execution provenance (§5.2 `merge_records`).

### 4.6 `gaps.py` — upward residue and downward gaps (F86, §4.2 of Row 3)

- **Child-orphan (no-match):** a row n>1 requirement with empty `refines_refs` after matching, **where candidates were considered (≥1) and none judged a parent**, → emit an upward gap record (novel requirement with no parent) for GQA (F84) to consider. **Row 1 exception:** a row 1 requirement's empty `refines_refs` is correct (top) → no gap record. The row check is decidable.
- **No-candidates (D-rm-6):** a row n>1 requirement that was DD-resolved but for which the pre-filter offered **zero** candidates → emit a distinct `unmatched_no_candidates` gap record. This is NOT a confident novel-orphan: it flags either a genuine top-of-thread novelty OR a cross-row vocabulary / pre-filter miss (no parent shared the entity), to be triaged by review / GQA. Keeping it distinct from `no_match` stops an empty pre-filter from inflating the apparent novel-requirement count (T&E: PMT R2 Run10).
- **Parent-orphan (downward gap):** after matching a row, any row n−1 requirement that no row n requirement refines → emit a downward gap record (an obligation nothing elaborates). This is the bidirectional half (Row 3 §4.2) and the requirement-level sibling of the deferred F91 state-completeness check.

Both are records for gap analysis; neither is auto-fixed here. In v0.2 these records are entries in `outputs.mechanism_data.gap_records` (§5.2). Promotion to canonical `Gap` (`G###`) ledger elements — including resolving how a `Gap` references an orphan Requirement rather than a CoverageItem — is a **GQA-mechanism concern**, noted not built here; matching's obligation (VER-rm-05/06) is discharged by emitting the gap-record entries in its provenance.

## 5. Schema and Validation

### 5.1 What the service writes

- `Requirement.refines_refs` (ledger v2.13/v2.15: array of `R###`, each parent at row_target − 1, empty permitted) — the committed link surface.
- Retirement flags on merged-away requirements.
- **One `AnalysisPass` per matching execution** carrying the decision provenance (§5.2/§5.3).

No statement/type/other-field changes. No new ledger element types.

### 5.2 The provenance AnalysisPass (`outputs.mechanism_data` structure)

The service writes one `AnalysisPass` per `match_row` / `match_set` execution. The standard F25 attributes are populated as:

| Attribute | Value |
|---|---|
| `mechanism` | `"RequirementMatching"` |
| `pass_type` | `"Per-row"` (one execution = one row matched against row−1) |
| `execution_status` | `"Success"` \| `"PartialSuccess"` (judge failures flagged but execution completed) \| `"Failed"` (ledger enum; v2.15) |
| `mode_active` | `"IM"` (the judgement dominates; DM for the writes) |
| `declared_transformation_modes` | `["IM", "DM", "LPM"]` |
| `evaluated_scope` | the row matched (n) and its parent row (n−1) |
| `confidence` | execution-level summary confidence (e.g., mean committed-link confidence) |
| `pass_started_at` / `pass_completed_at` | timestamps |

`outputs.mechanism_data` carries the decision provenance required by Row 3 §4.5:

```jsonc
{
  "row_ref": 2,                      // the row matched
  "parent_row_ref": 1,
  "dd_version_ref": "...",           // DD state used for the entity pre-filter
  "ai_model_fingerprints": [ ... ],  // the judge() calls
  "counts": {
    "processed": 16, "refine_link": 8, "no_match": 4, "no_candidates": 2,
    "duplicate_merge": 1, "flagged": 1, "deferred": 0
  },
  "match_records": [                 // ONE per requirement processed — no requirement unaccounted
    {
      "requirement_id": "R015",
      "outcome": "refine_link",      // refine_link | no_match | no_candidates | duplicate_merge | flagged | deferred
      "confidence": 0.91,
      "candidates_considered": ["R006","R010","R011"],   // DD pre-filter output
      "parent_ids": ["R011"],        // present on refine_link
      "duplicate_of": null,          // present on duplicate_merge
      "auto_recorded": true,
      "multi_parent_ambiguous": false
    }
    // ... one entry for every processed requirement, including every no_match
    // (with its rejected candidates_considered) and every flagged/deferred
  ],
  "gap_records": [                   // VER-rm-05 / VER-rm-06
    { "direction": "upward",   "requirement_id": "R017", "row_target": "2" },
    { "direction": "downward", "requirement_id": "R009", "row_target": "1" }
  ],
  "merge_records": [
    { "survivor_id": "R012", "retired_ids": ["R031"], "confidence": 0.88, "repointed_refs": ["R044"] }
  ],
  "mode_violations": []
}
```

The `match_records` array is the diagnostic surface: because it carries an entry for **every** processed requirement (including the candidate set rejected by each no-match), a no-match (genuine novelty) is distinguishable from a missed parent (recall failure) by inspection — which the v0.1 service-log, being outside the ledger, was not used to provide and which the bare `refines_refs` link cannot provide.

### 5.3 Provenance assembly and the link/decision split

`provenance.py` accumulates a match record per `match_requirement` call within an execution and writes a single `AnalysisPass` on completion of `match_row` / `match_set`. The two surfaces are distinct and complementary:

- **`Requirement.refines_refs`** — the durable *link* surface (committed parents only; queried directly by Phase 4 and by re-matching idempotency).
- **`AnalysisPass.outputs.mechanism_data`** — the durable *decision* surface (every outcome, its confidence, the candidates considered, the gaps and merges, the model fingerprints).

This split is the v0.2 correction of the v0.1 statement that "`refines_refs` is itself the durable audit surface": `refines_refs` remains the link surface, but it is not sufficient provenance for the *judgements*, so the AnalysisPass carries those.

## 6. Verification Criteria (→ pytest)

| ID | Criterion | Test |
|---|---|---|
| VER-rm-01 | every populated `refines_refs` entry references an existing Requirement at row_target − 1 | `test_refines_refs_parent_row` |
| VER-rm-02 | no row 1 requirement has non-empty `refines_refs` | `test_row1_top` |
| VER-rm-03 | each duplicate equivalence class → one active survivor (lowest id); all other members retired (not dangling) and repointed; survivor carries union of refs | `test_merge_repoint` |
| VER-rm-10 | reciprocal (A↔B) / chained (A≡B≡C) duplicate claims → one merge_record, one active survivor per class; no class has all members retired (Non-Loss, fail-closed) | `test_circular_merge_survivor` |
| VER-rm-04 | confidence ≥ BAND ⇒ auto-recorded; < BAND or multi-parent ⇒ flagged | `test_gating` |
| VER-rm-05 | every row n>1 no-match → an upward gap record (in `mechanism_data.gap_records`); no gap record for row 1 empties | `test_no_match_gap` |
| VER-rm-06 | every parent-orphan → a downward gap record | `test_parent_orphan_gap` |
| VER-rm-07 | DD-unresolved Object ⇒ deferred (not-yet-matchable), not forced; recorded as `deferred` | `test_dd_unresolved_deferred` |
| VER-rm-08 | idempotency: re-matching an unchanged set adds no new links/records | `test_idempotent` |
| VER-rm-09 | every execution writes exactly one `AnalysisPass` (mechanism="RequirementMatching") whose `mechanism_data.match_records` has one entry per processed requirement (outcome + confidence + candidates_considered), with execution-level `counts` and `ai_model_fingerprints` | `test_matching_pass_provenance` |
| VER-rm-11 | two same-row requirements that share a DD entity but differ in subject class (actor/system/business) are NOT merged as duplicates (cross-subject-class pairs excluded from the duplicate candidate set) | `test_subject_class_not_merged` |
| VER-rm-12 | a DD-resolved row n>1 child with an empty candidate set is recorded `no_candidates` (not `no_match`) and emits an `unmatched_no_candidates` gap record; `no_match` requires candidates_considered ≥ 1 | `test_empty_candidates_not_no_match` |

## 7. Test Fixtures

Realises Row 3 §7 on real PMT requirements:
- **F-rm-1** row 2 req refines one row 1 parent (DD makes "work opportunity"≈"task") → refine-link (`test_refine_single`).
- **F-rm-2** cross-cutting row 2 req → two parents (`test_refine_many`).
- **F-rm-3** novel row 2 req → no-match → upward gap; provenance record carries the rejected candidates (`test_no_match`).
- **F-rm-4** duplicate row 2 reqs → merge + repoint (`test_duplicate_merge`).
- **F-rm-5** row 1 parent with no row 2 child → downward gap (`test_parent_orphan`).
- **F-rm-6** low-confidence / multi-parent → flagged (`test_flagged`).
- **F-rm-7** row 1 reqs → no upward matching, empty refines_refs, no gap (`test_row1`).
- **F-rm-8** GQA generates a parent + re-descends → re-match links the child (`test_incremental_relink`).
- **F-rm-9** a `match_row` execution writes one provenance AnalysisPass accounting for every processed requirement (`test_matching_pass_provenance`).

## 8. Edge Cases

Per Row 3 §8: row 1 (no parents; empty correct, not a gap — but the execution pass still records the row 1 run); row n−1 not yet derived (defer, not fail); DD-unresolved Object (defer, recorded as `deferred`); self/same-row refine forbidden decidably (row_target − 1 rule); many-to-many fan-out uncapped. Judge failure → flagged, never auto-link (D-rm-3); a `match_row` containing flagged/deferred requirements completes with `execution_status = PartialSuccess`.

## 9. Cross-Mechanism Interactions

- **Requirement Derivation (upstream):** emits `refines_refs=[]` (§5.5 interface); this service populates it.
- **Data Dictionary service (dependency):** read for the entity pre-filter; DD-before-Matching ordering enforced (DD-unresolved → defer).
- **GQA / gap analysis (downstream, F84/F86):** consumes the upward and downward gap records from `mechanism_data.gap_records`; re-triggers matching after re-descent. Promotion of gap-record entries to canonical `Gap` elements is a GQA concern.
- **Phase 4 (downstream, F82 motivation):** reads `refines_refs` to score higher-level requirements as satisfied by their linked refinements.
- **Back-refinement / state-completeness (F91):** the parent-orphan check (§4.6) is the requirement-level sibling; the general state-completeness mechanism remains deferred.

## 10. Build Notes

- Row 4 resolutions of Row 3 deferrals: D-rm-1 (two-tier: DD candidate pre-filter + model-judged abstraction-level comparison, embedding only to pre-rank), D-rm-2 (row dimension pre-separates refine from duplicate decidably), D-rm-3 (no-match never auto-corrected; fail-safe to flagged), **D-rm-4 (v0.2: per-execution AnalysisPass, not a service-log)**.
- The AnalysisPass is **per execution, not per requirement** — this is what resolves the v0.1 frequency objection; match detail goes in `mechanism_data.match_records`, mirroring Domain Derivation's per-domain decision records in one pass.
- No ledger-spec change: `mechanism` is a free string, `pass_type="Per-row"` is valid, `outputs` sub-structure is the mechanism's responsibility (ledger v2.15). The DDL service-log of v0.1 is removed (single store, in the ledger).
- `MATCH_CONFIDENCE_BAND` / `MULTI_PARENT_MARGIN` fixed constants pending data; promotable to ProjectProfile. The recorded per-match confidences (§5.2) are the calibration data source.
- The model-judged matching (D-rm-1) is the IM heart and the main thing to validate on real data; until validated, set BAND high to favour review. The false-novel rate (no-matches that should have linked) is now measurable from `match_records` — that is the recall metric to watch.
- Gap-record → canonical `Gap` element promotion (and the orphan-Requirement reference question) is a GQA-mechanism integration, noted not built here.

## Document End

End of SysEngage Row 4 Mechanism: Requirement Matching Service v0.4.

Physical realisation of the Row 3 logical Requirement Matching Service spec v0.3, against ledger v2.15 (`refines_refs`, `AnalysisPass`). Two-tier matching (DD candidate pre-filter + model-judged abstraction-level comparison); row dimension pre-separates refine (cross-row) from duplicate (same-row); confidence-banded auto-link/merge-with-review (fixed constant BAND=0.85, provisional); duplicate-merge resolves duplicate equivalence classes to one deterministic survivor (lowest id), one merge record per class, with a hard fail-closed Non-Loss guard against retiring all members (v0.3), and reference repointing; no-match → upward gap (F86, never auto-corrected); parent-orphan → downward gap (bidirectional, F91 kinship). **Decision provenance recorded as one AnalysisPass per execution (D-rm-4 reversed in v0.2), replacing the v0.1 service-log** — per-requirement match records in `outputs.mechanism_data`, in the ledger, on the same review path as every other mechanism. Completes the Requirement Matching mechanism pair (Row 3 logical v0.3 + Row 4 physical v0.3).

Companion artefacts:
- SysEngage_Row_3_Mechanism_Requirement_Matching_v0_3.md — logical authority
- sysengage_minimal_ledger_spec_v2_15.md — `Requirement.refines_refs` and `AnalysisPass` schema authority
- SysEngage_Row_4_Mechanism_Data_Dictionary_v0_1.md — the vocabulary dependency
- SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_8.md §5.5 — the caller-side interface this service realises
- SysEngage_Issues_Tracker_v0_65.md — F85, F82, F86, F84, F90, F93 disposition
