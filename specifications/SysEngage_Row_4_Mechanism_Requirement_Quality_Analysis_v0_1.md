# SysEngage Row 4 Mechanism: Requirement Quality Analysis (Phase 4)

**Implementation specification — physical / builder tier**

Version: 0.1
Date: 03 June 2026

**Abstraction level:** Row 4 — Builder / Physical. The implementable realisation of Phase 4 Requirement Quality Analysis. Every design decision traces to the Row 3 (logical) Requirement Quality Analysis spec; physical choices the Row 3 spec deferred are resolved in §6.

**Operational scope:** Per-requirement, all rows; a phase mechanism over the assembled, matched requirement set. Read-and-score — does not modify requirements.

**Purpose.** Implementation specification for Phase 4 Requirement Quality Analysis (findings F88, F89, F90): scores each requirement against the type-specific rules, producing a per-requirement quality score and violation list. Records the physical realisation: module structure, the decidable-check implementations, the IM-judged-check prompt contract, the scoring engine, the result carrier, audit, fixtures, and VER→pytest mapping. Logical authority: the Row 3 Requirement Quality Analysis spec.

---

## 1. Mechanism Identification

| Field | Value |
|---|---|
| **Mechanism name** | Requirement Quality Analysis (Phase 4, physical) |
| **Logical authority** | SysEngage Row 3 Mechanism: Requirement Quality Analysis (Phase 4) v0.1 |
| **Structural sibling** | Row 4 Requirement Derivation v0.6 (shared: type triad, slot canon, DM/IM split, service-log audit) |
| **Reads ledger** | `Requirement` (statement, requirement_type, verification_method, fit_criteria, refines_refs); Data Dictionary (Object/entity resolution) |
| **Writes** | A per-requirement quality result (§5.2 carrier). Does NOT modify requirements. |
| **Mode** | DM (decidable checks + score arithmetic); IM (ambiguity / implied-design / subjective-term / type-confirmation judgements) |

## 2. Cross-References

| Source | Relevance |
|---|---|
| **Row 3 Requirement Quality Analysis v0.1** | All sections — logical authority: the scoring framework, the type-reconciled rules (§5.2–5.4), the steps, edge cases |
| **`requirements_document_v6.docx`** | The source framework — severity model, per-type rules, worked examples (the fixtures §7 use them) |
| **Row 4 Requirement Derivation v0.6** | CHK-3d-09 (hard atomicity) and the slot-detector code Phase 4 reuses for decidable structural checks |
| **Row 4 Data Dictionary v0.1** | `resolve_object` for the Object/entity-resolution check |
| **Canonical Ledger v2.13** | requirement_type / verification_method / fit_criteria fields |
| **Issues Tracker — F88/F89/F90** | Framework identity; type triad; DD binding |

## 3. Architectural Approach

### 3.1 Module structure
```
requirement_quality/
  service.py            # score_requirement, score_set, aggregate
  classify.py           # type confirmation (§4.1) — IM, against the triad classification table
  rules/
    functional.py       # §5.2 — decidable slot checks + IM judgements
    constraint.py       # §5.3 — merged DC/Env/Perf rules; verification_method selects which bite
    structural.py       # §5.4 — candidate rules (F88/F90)
  slots.py              # shared typed-slot detector (reused from derivation CHK-3d-09)
  judge.py              # IM-judged checks (ambiguous verb, implied design, subjective terms)
  scoring.py            # arithmetic: 100 − Σ penalties, floor 0; bands
  result.py             # quality-result carrier (§5.2)
  audit.py              # service-log
```

### 3.2 Major design decisions (Row 4 resolutions)
- **D-q-1 — decidable vs IM split.** Decidable (regex/parse/lookup, reproducible): compound condition/object (conjunction detection), missing required slot (the shared `slots.py` detector reused from CHK-3d-09), multiple lifecycle phases, missing-criteria-when-Measurement, Object-resolves-to-DD (lookup via `resolve_object`). IM-judged (model call): ambiguous verb, implied design, subjective/unquantified terms, behaviour-present-misclassification, and type confirmation. Each requirement gets at most one IM call (batch its IM-judged checks) to bound cost.
- **D-q-2 — slot detector reuse.** The typed-slot detector built for CHK-3d-09 (derivation) is the same code Phase 4 uses for missing-slot and compound checks — one implementation of the F88 slot canon, used at creation (hard reject) and at scoring (graded penalty). Guarantees the two mechanisms judge slots identically.
- **D-q-3 — read-and-score, no write-back.** Phase 4 writes only the quality result; a reclassification (§4.1) is recorded as a finding in the result, NOT written back to the requirement (that requires Practitioner action / re-derivation). Enforced.
- **D-q-4 — result carrier.** A `requirement_quality_result` side table keyed by requirement_id (not a field on the requirement, and not a canonical ledger element at this version — quality results are analysis output, re-derivable, and would bloat the requirement row). Promotable to a canonical CoverageItem/quality element later if cross-phase coverage needs it.
- **D-q-5 — scoring constants.** Severity penalties (30/15/5), 100 start, 0 floor are framework constants in `scoring.py`, not ProjectProfile.

## 4. Step-by-Step Implementation

### 4.1 `classify.confirm(requirement)` — type confirmation (IM)
Confirm the carried `requirement_type` against the §5.1 triad classification table. If the content indicates a different type, record `type_reclassification {from, to}` in the result and score against the corrected type (D-q-3: recorded, not written back). One model call; batched with the IM-judged checks (D-q-1) where possible.

### 4.2 `score_requirement(requirement) → QualityResult`
1. `classify.confirm` → effective type.
2. Run the effective type's rule module (`rules/functional|constraint|structural.py`): decidable checks first (slots, conjunctions, lifecycle, criteria-when-Measurement, DD-resolution), then the batched IM-judged checks.
3. `scoring.score(violations)` → 100 − Σ penalties, floor 0.
4. Build `QualityResult {requirement_id, effective_type, score, violations:[{rule, severity, penalty}], reclassification?}`.

### 4.3 Decidable check implementations (DM)
- **Missing slot / compound condition / compound object:** `slots.py` (shared with CHK-3d-09) parses the statement to the type's slot pattern; absence of a required slot or a conjunction in condition/object fires the rule.
- **Multiple lifecycle phases (Constraint):** detect operate/store/transport co-occurrence.
- **Missing measurable Criteria when `verification_method == 'Measurement'`:** if Measurement and `fit_criteria` empty/absent → High (§5.3). NOT fired for Inspection-verified Constraints.
- **Object/entity resolves to DD:** `resolve_object(object_term)`; no resolution and no clear concrete noun → Medium.

### 4.4 IM-judged check implementations (IM)
One batched model call per requirement returns judgements for: ambiguous verb (handle/manage/support/process), implied design, subjective/unquantified terms (robust/sufficient/easy/quickly), behaviour-present (misclassification). The prompt presents the statement, its type, and asks for each judgement with a boolean + brief reason. One retry on malformed output; persistent failure → those IM checks recorded as `not_assessed` (the decidable score still stands; the requirement is flagged for manual quality review — fail-safe, never silently pass).

### 4.5 `aggregate(result_set)`
Mean score; violation frequency by rule / type / row; the score-band distribution (§5.5 of Row 3). Drives iteration targeting (which requirements/rows need revision). Advisory output, not a gate.

## 5. Schema and Validation

### 5.1 Classification table — see Row 3 §5.1 (the F89 triad).

### 5.2 Quality-result carrier (DDL)
```sql
CREATE TABLE requirement_quality_result (
  result_id        BIGSERIAL PRIMARY KEY,
  requirement_id   VARCHAR(8) NOT NULL,
  effective_type   VARCHAR(16) NOT NULL CHECK (effective_type IN ('Functional','Constraint','Structural')),
  reclassified_from VARCHAR(16),                  -- set when classify.confirm changed the type
  score            INTEGER NOT NULL CHECK (score >= 0 AND score <= 100),
  violations       JSONB NOT NULL DEFAULT '[]',   -- [{rule, severity, penalty}]
  scored_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
```
Keyed by `requirement_id`; latest result per requirement supersedes on re-score. Not a ledger element (D-q-4).

### 5.3 Rule modules realise Row 3 §5.2–§5.4
`functional.py` = §5.2; `constraint.py` = §5.3 (with the `verification_method` selector for the Criteria rule); `structural.py` = §5.4 (candidate). Severity/penalty per the Row 3 tables.

## 6. Verification Criteria (→ pytest)

| ID | Criterion | Test |
|---|---|---|
| VER-q-01 | effective_type ∈ triad before scoring | `test_type_confirmed` |
| VER-q-02 | score == 100 − Σ penalties, floored 0 | `test_score_arithmetic` |
| VER-q-03 | decidable rules reproducible on same input | `test_decidable_reproducible` |
| VER-q-04 | Criteria rule fires only when verification_method == 'Measurement' | `test_criteria_only_measurement` |
| VER-q-05 | no requirement statement/type/field modified by Phase 4 | `test_read_only` |
| VER-q-06 | slot detector shared with CHK-3d-09 yields identical slot judgements | `test_slot_detector_parity` |
| VER-q-07 | IM-judge failure → not_assessed + manual-review flag, never silent pass | `test_im_failsafe` |

## 7. Test Fixtures
Realises Row 3 §7 using the framework's worked examples + real PMT:
- **F-q-1** alarm example → 100 (`test_high_quality_functional`).
- **F-q-2** "handle the alarm appropriately" with compound condition + missing criteria → 25 (`test_poor_functional`).
- **F-q-3** Measurement-Constraint missing criteria → −30; USB-C Inspection-Constraint not penalised for criteria (`test_constraint_verification_selector`).
- **F-q-4** behaviour misclassified as Constraint → −15 (`test_misclassification`).
- **F-q-5** Functional Object unresolved in DD → −15 (`test_object_dd_resolution`).
- **F-q-6** Structural: clean composition → 100; with implementation detail → −5 (`test_structural_candidate`).
- **F-q-7** real PMT R004 pre-split scored: compound object −15 (`test_pmt_r004`).
- **F-q-8** IM-judge failure path → not_assessed, manual-review flag (`test_im_failsafe`).

## 8. Edge Cases
Per Row 3 §8: not-a-requirement → flagged, not type-scored; abstract Row 1 requirement with no natural verification method → no penalty for missing verification_method (consistent with derivation optional-field policy); Structural rules candidate/provisional; reclassified requirement scored against corrected type, reclassification recorded not written back.

## 9. Cross-Mechanism Interactions
- **Requirement Derivation (upstream):** shares `slots.py` (D-q-2) — identical slot canon at creation and scoring; CHK-3d-09 pre-prevents High structural defects so derived requirements should score higher than raw input.
- **Requirement Matching (upstream):** Phase 4 runs on the matched set; MAY use `refines_refs` as a traceability signal (noted, not a scored rule).
- **Data Dictionary (read):** `resolve_object` for §4.3.
- **Iteration (downstream):** low scores surface requirements for revision → re-derive/re-match → Phase 4 re-scores. Phase 4 is the iteration-loop quality gate.

## 10. Build Notes
- Row 4 decisions: D-q-1 (decidable vs IM split; one batched IM call/requirement), D-q-2 (reuse the CHK-3d-09 slot detector — single F88 slot implementation), D-q-3 (read-and-score, reclassification recorded not written back), D-q-4 (side-table result carrier, not a ledger element; promotable), D-q-5 (framework constants).
- The IM-judged checks (§4.4) are the main validation target; the decidable checks are reproducible by construction. Structural rules (§5.4) are candidate — validate once Structural requirements exist.
- The slot-detector parity test (VER-q-06) is important: it guarantees derivation and Phase 4 cannot drift apart on what a "missing Object" or "compound object" is.

## Document End

End of SysEngage Row 4 Mechanism: Requirement Quality Analysis (Phase 4) v0.1.

Physical realisation of the Row 3 logical Phase 4 spec — the INCOSE/ISO-29148 quality framework reconciled to the F89 triad. Decidable checks (shared slot detector with CHK-3d-09) + batched IM-judged checks per requirement; verification_method selects which Constraint rules bite; Structural rules candidate; side-table quality-result carrier; read-and-score (no write-back); IM-failure fail-safe to manual review. Completes the Requirement Quality Analysis mechanism pair (Row 3 logical + Row 4 physical) and the requirements build.

Companion artefacts:
- SysEngage_Row_3_Mechanism_Requirement_Quality_Analysis_v0_1.md — logical authority
- requirements_document_v6.docx — source quality framework (F88)
- SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_6.md — shared slot detector (CHK-3d-09)
- SysEngage_Row_4_Mechanism_Data_Dictionary_v0_1.md — Object/entity resolution
- sysengage_minimal_ledger_spec_v2_13.md — requirement field authority
- SysEngage_Issues_Tracker_v0_63.md — F88, F89, F90 disposition
