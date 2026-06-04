# SysEngage Row 4 Mechanism: Data Dictionary Service

**Implementation specification — physical / builder tier**

Version: 0.1
Date: 03 June 2026

**Abstraction level:** Row 4 — Builder / Physical. The implementable realisation of the Data Dictionary service. Every design decision traces to the Row 3 (logical) Data Dictionary Service spec; where this spec makes a physical choice the Row 3 spec deferred, that resolution is recorded in §6.

**Operational scope:** Cross-row standalone service (F93). Not a numbered pass. Invoked on demand by requirement mechanisms; the dictionary is populated incrementally and persists across rows and runs.

**Purpose.** Implementation specification for the Data Dictionary service (findings F90, F85, F93): builds and maintains the project-wide controlled vocabulary that behavioural requirements bind to, resolving each incoming term three-ways (canonical / synonym / flagged) under confidence-banded auto-resolve-with-register-review gating. Records the physical realisation: module structure, DDL, the resolution-judgement implementation, the confidence constant, rejection propagation, audit, fixtures, and VER→pytest mapping. Logical authority: the Row 3 Data Dictionary Service spec.

---

## 1. Mechanism Identification

| Field | Value |
|---|---|
| **Mechanism name** | Data Dictionary Service (physical) |
| **Operational scope** | Cross-row; project-wide; standalone service |
| **Logical authority** | SysEngage Data Dictionary Service (Row 3 logical) v0.1 |
| **Structural sibling** | Row 4 Domain Derivation v0.24 (shared conventions: SQLAlchemy/Pydantic, `mechanism_data` audit, mode-discipline) — adapted: service operations, not a four-stage pass |
| **Realises ledger** | v2.14 (`DataDictionaryEntry`, `DataDictionaryRegister`) |
| **Mode** | IM (resolution judgement); DM (entity production, commit); LPM (surface terms preserved as synonyms — vocabulary Non-Loss) |

## 2. Cross-References

| Source | Relevance |
|---|---|
| **Row 3 Data Dictionary Service v0.1** | All sections — logical authority: operations, three-way resolution, gating, inclusion rule, read operations, edge cases |
| **Canonical Ledger v2.14** | `DataDictionaryEntry` / `DataDictionaryRegister` schema; DDL §5.1 realises it |
| **Row 4 Requirement Derivation v0.5 §5.5** | The caller-side interface: Object-slot terms and Structural entities presented to `resolve_term`; refines_refs is the *Matching* service, distinct |
| **Issues Tracker — F90/F85/F93/F91** | Founding findings; representation decisions; service framing; state-model deferral |

## 3. Architectural Approach

### 3.1 Module structure

```
data_dictionary/
  service.py                  # public operations: resolve_term, record_relationship,
                              #   record_value, resolve_object, aliases_of, relationships_of
  resolution.py               # the IM resolution-judgement act (§4.2) — candidate vs canonical set
  models.py                   # SQLAlchemy + Pydantic for DataDictionaryEntry / Register
  gating.py                   # confidence-band gate (§4.3); the fixed RESOLUTION_CONFIDENCE_BAND constant
  rejection.py                # false-merge rejection propagation (§4.6)
  audit.py                    # service-log audit records (§5.3)
  ddl/                        # Alembic migration realising v2.14
```

The service is **stateless per call** over **persistent dictionary state** (the ledger). No four-stage pass envelope; operations are invoked individually.

### 3.2 Major design decisions (Row 4 resolutions of Row 3 deferrals)

- **D-dd-1 — resolution comparison method (the main deferred decision).** `resolve_term` judges a candidate term against existing canonical entries. Implementation: a two-tier comparison — (1) a cheap deterministic pre-filter (normalised exact / known-synonym lookup: if the surface term already exists as a synonym or matches a canonical name case-insensitively, resolve immediately, confidence = 1.0); (2) for the remainder, a model-judged semantic comparison: the candidate term *with its requirement context* is compared against the canonical entries' names + descriptions + existing synonyms, returning best-match canonical id(s) and a confidence. Embedding-similarity MAY pre-rank candidates to bound the comparison set, but the same/new/ambiguous judgement is model-made, not threshold-on-cosine (a cosine threshold would re-introduce the string-matching failure F90 identified — lexical proximity is not semantic identity). The literal model/prompt is authored here; the contract is fixed by Row 3 §4.1.
- **D-dd-2 — multi-candidate detection.** If the comparison returns two or more canonical entries within a small margin of the top score, the outcome is ambiguous (Row 3 outcome c) regardless of absolute confidence → flag, do not auto-record.
- **D-dd-3 — incremental, idempotent.** Every `resolve_term` checks the pre-filter first, so re-presenting an already-resolved term is a no-op (idempotency, Row 3 §6).
- **D-dd-4 — audit carrier.** A service log (`data_dictionary_resolution_log`), NOT a per-invocation AnalysisPass — resolutions are high-frequency and per-term; an AnalysisPass per term would flood the pass record. (Resolves the Row 3 §12 open item.)

## 4. Operation-by-Operation Implementation

### 4.1 `resolve_term(surface_term, provenance_ref, context) → ResolutionResult`

Realises Row 3 §4.1/§4.2. Steps:
1. **Pre-filter (DM).** Normalise the surface term; if it equals an existing `synonym.surface_term` or a `canonical.name` (case-insensitive), return that canonical entry, confidence 1.0, outcome=`existing`. No new entry.
2. **Comparison (IM).** Otherwise invoke `resolution.judge(candidate, context, canonical_set)` → `{best: [canonical_id...], confidence, is_multi_candidate}`.
3. **Gate (DM, §4.3).** Apply the band:
   - confidence ≥ BAND and not multi-candidate, best matches one canonical → **outcome=synonym**: create `synonym` entry (`surface_term`, `resolves_to`=best, `provenance_ref`), auto-record, return.
   - confidence ≥ BAND and best matches nothing (the judge returns "no adequate match") → **outcome=canonical**: create `canonical` entry (name from term, description from context), auto-record, return.
   - confidence < BAND, or multi-candidate → **outcome=flagged**: write a flag record (candidate, competing canonical ids, confidence) to the resolution log; do NOT create an entry; signal the caller to block on this term pending Practitioner resolution.
4. **Audit (DM).** Append a resolution-log record either way (§5.3).

### 4.2 `resolution.judge` — the IM comparison (D-dd-1)

Input: candidate surface term, requirement context (the statement + row), the canonical entry set (optionally embedding-pre-ranked to the top-k). Output: best-match canonical id(s), a confidence in 0.0..1.0, and a multi-candidate flag. The judgement asks, in effect: *does this term denote an entity already in this set, and if so which one?* — a semantic same-entity judgement, not a lexical one. One retry on malformed model output; persistent failure → outcome=flagged (fail safe to human, never auto-merge on error).

### 4.3 `gating.py` — the confidence band

```python
# Fixed mechanism constant — provisional, NOT a ProjectProfile parameter at this version.
# Rationale: no run data yet on how resolution confidence distributes across real projects;
# a tunable knob would be false precision. Change here in one place when data arrives;
# promote to ProjectProfile only if observed distributions show projects need different bands.
RESOLUTION_CONFIDENCE_BAND = 0.85
MULTI_CANDIDATE_MARGIN = 0.05   # two canonicals within this of the top score → ambiguous (D-dd-2)
```
The literal `0.85` is a starting value, not a validated one; it is expected to be revisited against the first real resolution-confidence distributions. Recorded as provisional so it is not mistaken for a considered final value.

### 4.4 `record_relationship(from_term, to_term, cardinality, provenance_ref)`

Resolve both endpoints via `resolve_term` (each must resolve to a canonical entry; a flagged endpoint blocks the relationship). Create a directed `relationship` entry (`from_ref`, `to_ref`, `cardinality`). Reflexive (`from_ref == to_ref`) permitted with a logged advisory.

### 4.5 `record_value(canonical_term, attr_name, value, provenance_ref)`

Resolve `canonical_term`; ensure the named attribute exists on the canonical entry (add `{attr_name}` if absent — attribute *existence* is dictionary content); ensure `value` is present in that attribute's `value_set` (add if absent). No transition/state recording (F91 deferred). The value is now referenceable as `{name}.{attr_name}.{value}`.

### 4.6 `rejection.reject_synonym(dd_id)` — false-merge correction (Row 3 §6 requirement)

When a Practitioner rejects a `synonym` entry (a false merge): (1) create a new `canonical` entry from the synonym's `surface_term`; (2) delete/retire the `synonym` entry; (3) **re-resolution trigger** — find requirement Object bindings that resolved to the *wrongly-merged* canonical entry *via this surface term* (traceable through `provenance_ref`), and mark them for re-resolution against the corrected dictionary. The Row 3 spec required this propagation; this is its implementation. The dependent-binding re-resolution is queued, not silent.

### 4.7 Read operations

`resolve_object(term)` → canonical entry or unresolved-signal; `aliases_of(canonical_id)` → query `synonym WHERE resolves_to = canonical_id`; `relationships_of(canonical_id)` → query `relationship WHERE from_ref = id OR to_ref = id`. All are direct queries (the synonym-as-single-source decision makes aliases a query, not a field read).

## 5. Schema and Validation

### 5.1 Database DDL (realises ledger v2.14)

```sql
CREATE TABLE data_dictionary_entry (
  dd_id           VARCHAR(8)  PRIMARY KEY,           -- ^DD\d{3}$
  entry_kind      VARCHAR(16) NOT NULL CHECK (entry_kind IN ('canonical','synonym','relationship')),
  name            TEXT,                              -- canonical: NOT NULL (enforced in app/CHK)
  description     TEXT,
  attributes      JSONB       NOT NULL DEFAULT '[]', -- [{attr_name, attr_description?, value_set?:[...]}]
  surface_term    TEXT,                              -- synonym
  resolves_to     VARCHAR(8)  REFERENCES data_dictionary_entry(dd_id),  -- synonym → canonical
  from_ref        VARCHAR(8)  REFERENCES data_dictionary_entry(dd_id),  -- relationship
  to_ref          VARCHAR(8)  REFERENCES data_dictionary_entry(dd_id),  -- relationship
  cardinality     VARCHAR(16),                       -- relationship
  provenance_ref  TEXT,
  confidence      DOUBLE PRECISION NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
  -- NO row_target column: the DD is project-wide (v2.14)
  CONSTRAINT canonical_has_name      CHECK (entry_kind <> 'canonical' OR (name IS NOT NULL AND description IS NOT NULL)),
  CONSTRAINT synonym_has_target      CHECK (entry_kind <> 'synonym'   OR (surface_term IS NOT NULL AND resolves_to IS NOT NULL)),
  CONSTRAINT relationship_has_ends   CHECK (entry_kind <> 'relationship' OR (from_ref IS NOT NULL AND to_ref IS NOT NULL AND cardinality IS NOT NULL))
);

CREATE TABLE data_dictionary_resolution_log (   -- audit carrier (D-dd-4)
  log_id          BIGSERIAL PRIMARY KEY,
  surface_term    TEXT NOT NULL,
  provenance_ref  TEXT,
  outcome         VARCHAR(16) NOT NULL,            -- existing | synonym | canonical | flagged
  confidence      DOUBLE PRECISION,
  competing_refs  JSONB,                           -- canonical ids when flagged multi-candidate
  auto_recorded   BOOLEAN NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```
A trigger or app-level guard enforces "exactly one synonym/canonical referential integrity" beyond the FK (e.g. `resolves_to` must point at an entry whose `entry_kind='canonical'` — enforced in app, as a CHECK cannot subquery). The `data_dictionary_register` is the standard register table/row (`register_type='DataDictionaryEntry'`, `member_ids` = all `dd_id`).

### 5.2 Pydantic model

A discriminated model on `entry_kind` (canonical / synonym / relationship variants), mirroring the v2.14 conditional requireds: canonical requires name+description; synonym requires surface_term+resolves_to; relationship requires from_ref+to_ref+cardinality. `attributes` is a list of `{attr_name, attr_description?, value_set?}`. Distinct variant classes (same discipline as the Requirement Derivation distinct-schema warning).

### 5.3 Audit (`data_dictionary_resolution_log`)

Every `resolve_term` appends one log row: surface_term, provenance_ref, outcome, confidence, competing_refs (if flagged), auto_recorded. The synonym entries themselves are the durable canonicalisation-decision register (Row 3 §4.2); the log is the per-attempt trail including flags and rejections.

## 6. Verification Criteria (→ pytest)

| ID | Criterion | Test |
|---|---|---|
| VER-dd-01 | `dd_id` matches `^DD\d{3}$`, unique | `test_dd_ids` |
| VER-dd-02 | every `synonym.resolves_to` references an existing `canonical` | `test_synonym_target_canonical` |
| VER-dd-03 | every `relationship` from/to reference existing `canonical` | `test_relationship_ends` |
| VER-dd-04 | no `canonical` row stores an alias array (aliases only as synonym rows) | `test_no_alias_array` |
| VER-dd-05 | no entry has a row_target | `test_no_row_target` |
| VER-dd-06 | exactly one register; `member_ids` == all `dd_id` | `test_register_complete` |
| VER-dd-07 | every entry has a resolving `provenance_ref` | `test_provenance` |
| VER-dd-08 | confidence ≥ BAND ⇒ auto_recorded; < BAND or multi-candidate ⇒ flagged, not recorded | `test_gating` |
| VER-dd-09 | pre-filter idempotency: re-presented term creates no new entry | `test_idempotent_resolve` |
| VER-dd-10 | reject_synonym creates a canonical, retires the synonym, queues dependent re-resolution | `test_reject_synonym_propagation` |

## 7. Test Fixtures

Realises Row 3 §9 on real PMT vocabulary:
- **F-dd-1** empty dictionary, first term "Task" → canonical (`test_first_term_canonical`).
- **F-dd-2** "compensated work opportunity" then "chore" → both synonyms of Task (`test_aliases_resolve` — the F90 language-inconsistency case).
- **F-dd-3** a term plausibly matching two canonicals → flagged (`test_multi_candidate_flagged`).
- **F-dd-4** a weak match below BAND → flagged (`test_low_confidence_flagged`).
- **F-dd-5** Inventory 1:* Task directed relationship (`test_relationship`).
- **F-dd-6** Task.status.available added to value_set, no transition recorded (`test_value_set`).
- **F-dd-7** re-present "Task" → idempotent (`test_idempotent`).
- **F-dd-8** reject "chore"→Task synonym → "chore" becomes its own canonical + dependent bindings queued (`test_reject_propagation`).

## 8. Edge Cases

Per Row 3 §10: empty dictionary (all-canonical); term == canonical name (resolve, no synonym); reflexive relationship (allowed + advisory); value before attribute exists (create attribute then value); a row-requirement-not-vocabulary term (inclusion rule rejects — the caller should not have presented it; logged). Model-judge failure → fail-safe to flagged (never auto-merge on error, D-dd-1 retry then flag).

## 9. Cross-Mechanism Interactions

- **Requirement Derivation (caller, v0.5 §5.5):** presents Object-slot terms / Structural entities to `resolve_term`; binds to returned canonical entries. A flagged term blocks that binding pending resolution.
- **Requirement Matching service (reader, F85):** uses `resolve_object` / `aliases_of` so lexically-different requirements about the same entity match against shared vocabulary.
- **Phase 4 (reader):** checks Object slots resolve to dictionary entries.
- **State-model capability (deferred, F91):** value-naming (§4.5) already supports later transitions-as-relationships; not built.

## 10. Build Notes

- The Row 4 decisions resolving Row 3 deferrals: D-dd-1 (two-tier resolution: deterministic pre-filter + model-judged semantic comparison, embedding only to pre-rank), D-dd-4 (service log not AnalysisPass), §4.3 (literal BAND = 0.85 provisional), §4.6 (rejection propagation as a queued re-resolution).
- `RESOLUTION_CONFIDENCE_BAND` and `MULTI_CANDIDATE_MARGIN` are fixed constants pending data; candidates for promotion to ProjectProfile parameters.
- The model-judged comparison (D-dd-1) is the IM heart and the main thing to validate on real data before trusting auto-resolution; until validated, the BAND can be set conservatively high (more flagging, fewer auto-merges) to favour Practitioner review.

## Document End

End of SysEngage Mechanism: Data Dictionary Service (Row 4 — Physical) v0.1.

Physical realisation of the Row 3 logical Data Dictionary Service spec, against ledger v2.14. Two-tier resolution (deterministic pre-filter + model-judged semantic comparison); confidence-banded auto-resolve-with-register-review (fixed constant BAND=0.85, provisional); directed relationships; named-addressable value-sets (state-model deferred); false-merge rejection with dependent-binding re-resolution; service-log audit. Completes the Data Dictionary mechanism pair (Row 3 logical + Row 4 physical).

Companion artefacts:
- SysEngage_Row_3_Mechanism_Data_Dictionary_v0_1.md — logical authority
- sysengage_minimal_ledger_spec_v2_14.md — DataDictionaryEntry / DataDictionaryRegister schema authority
- SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_5.md §5.5 — caller-side Object-slot interface
- SysEngage_Issues_Tracker_v0_63.md — F90, F85, F93, F91 disposition
