# SysEngage Row 4 Understanding — §14 Addendum

**Filename:** SysEngage_Row_4_Understanding_v0_26.md (§14 addendum)

**Version:** 0.26 — §14 regenerated to index the Row 4 (physical) Requirement Derivation Mechanism Spec **v0.2**, which realises the Row 3 (logical) Requirement Derivation Mechanism Spec v0.1. Supersedes v0.25. v0.25 was provided to the build agent and produced the implemented v0.1 prototype (the PMT Row 1 / NQPS Row 1 runs); it indexed the earlier row-agnostic mechanism draft and named the Pass 3c Domain Derivation spec as authority. v0.26 corrects the authority chain (Row 3 logical → Row 4 physical v0.2), adds the `requirement_row_guidance.py` module and CHK-3d-08 index lines, and confirms the `mechanism_data` audit naming. §1–§12 (v0.5) and §13 (v0.24, Pass 3c) remain authoritative and unchanged; v0.26 supersedes v0.25 by §14 replacement only.

**Date:** 02 June 2026

**Purpose.** §14 carries structural guidance only for Pass 3d — module structure, ProjectProfile parameters, VER→pytest mapping, fixture→pytest mapping, and Agent handoff notes. All implementation detail (stages, DDL, Pydantic schemas, prompt text, REQUIREMENT_ROW_GUIDANCE content, edge cases, OQ resolutions) lives in the Row 4 Mechanism Spec v0.2 and is not duplicated here. This is the same structural/implementation firewall established for §13 (Pass 3c): the Understanding indexes the Mechanism Spec; it does not restate it.

**Scope note.** This document records §14 only.

**Authority chain.** Pass 3d is specified at two abstraction levels. The **logical authority** is SysEngage_Row_3_Mechanism_Requirement_Derivation_v0.1.md (what the mechanism must do and why). The **physical/implementation spec** is SysEngage_Row_4_Mechanism_Requirement_Derivation_v0.2.md (the buildable realisation), which §14 indexes. The Row 4 Domain Derivation Mechanism Spec v0.24 is the **structural sibling** (shared four-stage pattern and conventions). Where this artefact appears to differ from canonical ledger spec v2.12 or the Row 4 Mechanism Spec v0.2, the Mechanism Spec takes precedence.

---

## §14 Pass 3d — Requirement Derivation Implementation Framework

Structural framework for Pass 3d. Logical authority: Row 3 Requirement Derivation v0.1. Implementation spec: Row 4 Requirement Derivation v0.2 — all implementation detail lives there and is not duplicated here.

---

### §14.1 Module Structure

```
mechanisms/requirement_derivation/
  __init__.py                                  # Orchestration entry point — Stages 1–4
  stage1_preflight.py                          # Stage 1: Pass 3c prerequisite; CCI + Domain assembly; re-run detection
  stage2_ai_derivation.py                      # Stage 2: per-Domain AI derivation loop; response parsing
  stage3_structural_validation.py              # Stage 3: CHK-3d-01..08; ADVC-3d-01; Non-Loss repair (IM conditional)
  stage4_entity_production.py                  # Stage 4: requirement_id allocation; domain_refs DM-derivation;
                                               #          Requirement construction; ledger transaction
  prompts/
    requirement_derivation_prompt.py           # FirstRun / FullRerun per-Domain template; injects REQUIREMENT_ROW_GUIDANCE[row]
    requirement_incremental_prompt.py          # IncrementalRerun template
    requirement_repair_prompt.py               # CHK-3d-05 Non-Loss repair template
    requirement_row_guidance.py                # REQUIREMENT_ROW_GUIDANCE dict — DISTINCT from the domain ROW_GUIDANCE (decision B)
  schemas/
    requirement_derivation_response_schema.py  # Pydantic: primary derivation response (no requirement_id/row_target/
                                               #           domain_refs — those are DM-produced)
    requirement_incremental_response_schema.py # Pydantic: IncrementalRerun response — DISTINCT class; must not be shared
    requirement_repair_response_schema.py      # Pydantic: Non-Loss repair response — DISTINCT class; must not be shared
```

---

### §14.2 ProjectProfile Parameters

Two parameters introduced by Pass 3d. Add to `project_profile` as nullable columns with defaults.

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `requirement_rerun_threshold` | float 0–1 | 0.20 | New-CCI fraction above which IncrementalRerun escalates to FullRerun (applies only when the active Domain-id set is unchanged; a Domain-set change forces FullRerun regardless) |
| `requirement_large_cci_set_advisory_threshold` | integer | 80 | Row CCI count above which the large-set advisory fires (signal only — per-Domain processing proceeds; no chunking at v0.2) |

See Mechanism Spec §4.1 (Stage 1 re-run detection), §3.3 (large-set advisory), §5.1 (Alembic migration DDL).

---

### §14.3 VER Criteria → pytest Mapping

| VER ID | Assertion | pytest location |
|---|---|---|
| VER-3d-01 | All `requirement_id` match `^R\d{3}$` | `tests/test_requirement_derivation.py` |
| VER-3d-02 | All `requirement_id` unique within project (active + retired) | `tests/test_requirement_derivation.py` |
| VER-3d-03 | Every Requirement has non-empty `statement` and `jsonb_array_length(cci_refs) >= 1` | `tests/test_requirement_derivation.py` |
| VER-3d-04 | All `cci_refs` resolve via `cell_content_item.cell_id → zachman_cell.row_target == requirement.row_target` | `tests/test_requirement_derivation.py` |
| VER-3d-05 | Non-Loss: every eligible CCI ci_id appears in ≥1 Requirement's `cci_refs` | `tests/test_requirement_derivation.py` |
| VER-3d-06 | `requirement_register.member_ids` == active `requirement.requirement_id` set for project (all rows, no `row_target` filter) | `tests/test_requirement_derivation.py` |
| VER-3d-07 | AnalysisPass with `mechanism="RequirementDerivation"` and `row_ref=current_row` exists | `tests/test_requirement_derivation.py` |
| VER-3d-08 | `mechanism_data` present with all required fields non-null | `tests/test_requirement_derivation.py` |
| VER-3d-09 | All `requirement_type` values in `{Functional,Constraint,Performance,Suitability,Non-Functional}` | `tests/test_requirement_derivation.py` |
| VER-3d-10 | Every Requirement has `jsonb_array_length(domain_refs) >= 1`; all `domain_refs` resolve to existing Domains with matching `row_target` | `tests/test_requirement_derivation.py` |
| VER-3d-11 | IdempotentRerun: requirement set unchanged; `mechanism_data.idempotent == true`; execution_status=Skipped | `tests/test_requirement_derivation.py` |
| VER-3d-12 | FullRerun: `requirement_count_retired` == prior active Requirement count for this row | `tests/test_requirement_derivation.py` |
| VER-3d-13 | `requirement_count_produced >= 1` when `cci_count_input > 0` | `tests/test_requirement_derivation.py` |
| VER-3d-14 | No active Requirement has `fit_criteria` present-but-empty (`fit_criteria IS NULL OR length > 0`) | `tests/test_requirement_derivation.py` |

**CHK-3d-08 (row-subject vocabulary)** is a Stage 3 decidable check, soft severity at v0.2 — it records `mechanism_data.subject_vocabulary_flags` and is reviewed via PLB-3d-02. It is NOT a VER gate (Mechanism Spec §4.3, §8.1, OQ-3d-03). Listed here so the Agent does not mistake its absence from the VER table for an omission.

---

### §14.4 Test Fixtures → pytest Mapping

Seven fixtures in `tests/test_requirement_derivation.py`; AI stubs via monkeypatch. Worked examples use the rows with production evidence (PMT Row 1, NQPS Row 1).

| Fixture | Test function | Key assertion |
|---|---|---|
| Fixture 1 — PMT Row 1 FirstRun | `test_pmt_row1_firstrun` | VER-3d-05, VER-3d-10, RequirementRegister populated |
| Fixture 2 — NQPS Row 1 FirstRun (constraint-heavy) + Row 4 zero-CCI companion | `test_nqps_row1_firstrun` / `test_nqps_row4_zero_cci` | VER-3d-05, VER-3d-09 (Constraint present where warranted); CHK-3d-08 clean on compliance content (D005 case); optional fields omitted where unwarranted without failure; zero-CCI: `no_cci_input`, register preserved, Stage 2 not called |
| Fixture 3 — IdempotentRerun | `test_pmt_row1_idempotent_rerun` | VER-3d-11; Stage 2 AI stub not called |
| Fixture 4 — IncrementalRerun | `test_pmt_row1_incremental_rerun` | VER-3d-05 after delta; existing `requirement_id`s preserved; Domain set unchanged |
| Fixture 5 — Non-Loss repair (orphan recovered) | `test_noloss_repair_prompt_recovery` | `repair_prompt_issued=true`; VER-3d-05 passes; execution_status=Completed |
| Fixture 6 — Persistent orphan | `test_noloss_repair_persistent_orphan` | `orphaned_ccis` non-empty; execution_status=CompletedWithWarnings; Concern raised |
| Fixture 7 — FullRerun (Domain-set change) | `test_pmt_row1_fullrerun` | VER-3d-12; `retired_at` set on old Requirements; VER-3d-05 on new set; new `domain_refs` |

For fixture data content, AI-stub implementation pattern, and assertion detail: see Mechanism Spec §9.

---

### §14.5 Replit Agent Handoff Notes

**Documents to hand to the Agent:**
- Row 4 Mechanism Spec (Requirement Derivation) **v0.2** — primary implementation reference (all detail including DDL §5.1, schemas §5.2, REQUIREMENT_ROW_GUIDANCE §5.4)
- This section (Row 4 Understanding §14 v0.26) — structural framework
- Row 3 Mechanism Spec (Requirement Derivation) v0.1 — logical authority (stage logic, VER/PLB intent)
- Row 4 Mechanism Spec (Domain Derivation) v0.24 — structural sibling (four-stage pattern, audit/fingerprint conventions)
- Row 4 Applied v0.2 — common architectural commitments
- Canonical Ledger v2.12 — Requirement and RequirementRegister entity schemas
- Segmentation spec v9.2 — requirement statement formulation discipline

**This is a re-implementation against v0.2, not a fresh build.** v0.1 is already implemented (it produced the PMT Row 1 / NQPS Row 1 runs). Per Mechanism Spec §12.4, only two parts require a code change from the v0.1 implementation:
1. **§5.4 REQUIREMENT_ROW_GUIDANCE** — author `requirement_row_guidance.py` with the Row 1 block (full) and Rows 2–6 (short-phrase stubs), and inject it into the three prompt templates. This is the part that anchors the Row 1 statement subject ("The enterprise shall…", robust to compliance phrasing) that v0.1 lacked — the F81 Row 1 closure.
2. **CHK-3d-08** — add the decidable row-subject check to Stage 3 (soft severity: record `subject_vocabulary_flags`, do not reject).
The rest (four-stage flow, DDL, response schemas, re-run mechanics, `mechanism_data` audit) is unchanged from the v0.1 implementation.

**Key adaptations from the Domain Derivation sibling (`mechanisms/domain_derivation/`):**
- Stage 2 is a **per-Domain loop** — one AI call per active Domain, not a single whole-row call
- Inputs are **both** CCIs and active Domains (Domain Derivation took CCIs only)
- `domain_refs` is **DM-derived in Stage 4** by intersecting `cci_refs` with Domain membership — never AI-proposed; the response schema omits it
- Re-run hash is **two-part** (sorted CCI-ids + sorted active Domain-ids); a Domain-id-set change forces FullRerun
- **REQUIREMENT_ROW_GUIDANCE is a separate dict** from the domain ROW_GUIDANCE (decision B) — do not merge them
- **CHK-3d-08** (row-subject vocabulary) has no Domain Derivation analogue — soft severity at v0.2
- Non-Loss repair derives a **covering Requirement** for orphaned CCIs (not a Domain), scoped to the orphan's owning Domain
- No name-uniqueness merge (no CHK-3c-03 analogue) — CHK-3d-07 collapses only exact statement+cci_refs duplicates
- `requirement_type` enum enforced at the parse boundary; value choice is principle-based (no lookup table)

**Key design decisions the Agent must not re-derive (all resolved in the Mechanism Spec, traced to the Row 3 logical spec):**
- Per-Domain Stage 2 (D1a) — forward-compatible with whole-row (D1b) via the general `domain_refs` intersection; do not hard-code the single-Domain assumption into Stage 4 (MD-1, MD-2)
- `domain_refs` DM-derivation guarantees the ledger row_target/resolution rules by construction (MD-2); a proposal yielding empty `domain_refs` fails closed
- Two-part re-run hash and the Domain-set-change → FullRerun rule (MD-3; OQ-3d-01)
- IncrementalRerun reachable **only** when the Domain-id set is unchanged (MD-3)
- Persistent orphan after failed repair → `CompletedWithWarnings` + Concern raised; not a hard failure
- Soft-retire via `retired_at` on FullRerun, not delete (OQ-3d-04)
- `row_ref` is a top-level AnalysisPass field AND appears inside `mechanism_data` — both must be set
- Audit object is `mechanism_data` (not `requirement_data`), matching the sibling convention and the existing run files (OQ-3d-02)
- `mode_active` is `"IM"` / `declared_transformation_modes` is `["IM","DM"]` — NOT `"LPM"` (carry forward the Domain Derivation build correction)
- CHK-3d-08 severity is soft at v0.2 (OQ-3d-03)

**Migrations required:**
- `XXXX_add_requirement_tables.py` — `requirement` table (with `cci_refs`/`domain_refs`/`answer_refs` JSONB and `retired_at`); RequirementRegister seed (DDL: Mechanism Spec §5.1)
- `XXXX_add_requirement_profile_params.py` — two ProjectProfile columns (§14.2 above)

**Tracker dispositions (v0.52):**
- **F80** (Open): Pass 3d consumes Domains by `domain_id`, never by `name` — cross-row Domain name duplication is harmless to derivation. Stays Open (presentation-layer concern, review tooling).
- **F81** (Open → Row 1 portion addressed): §5.4 REQUIREMENT_ROW_GUIDANCE["1"] + CHK-3d-08 are the Row 1 closure path. F81 stays Open until Rows 2–6 guidance is authored in their own validation cycles. Re-running PMT Row 1 / NQPS Row 1 under v0.2 guidance is the F81 Row 1 validation step.

---

## Document End

End of SysEngage Row 4 Understanding v0.26 — §14 addendum.

**Changes in v0.26:**
- §14 regenerated to index the Row 4 Mechanism Spec **v0.2** (realising the Row 3 logical spec v0.1), correcting the authority chain that v0.25 had pointed at the row-agnostic mechanism draft / Pass 3c Domain Derivation
- Added `requirement_row_guidance.py` to the module structure and the CHK-3d-08 note to §14.3; confirmed `mechanism_data` audit naming
- Fixtures re-pointed to Row 1 production evidence (PMT Row 1 / NQPS Row 1)
- v0.25 (provided to the build agent; behind the implemented v0.1 prototype) is superseded by §14 replacement; §1–§12 (v0.5) and §13 (v0.24) unchanged

Companion artefacts:
- SysEngage_Row_3_Mechanism_Requirement_Derivation_v0_1.md — logical authority
- SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_2.md — physical implementation spec for Pass 3d
- SysEngage_Row_4_Mechanism_Domain_Derivation_v0_24.md — structural sibling (four-stage pattern)
- SysEngage_Issues_Tracker_v0_52.md — F80, F81 disposition
- sysengage_minimal_ledger_spec_v2_12.md — canonical Requirement / RequirementRegister schema authority
