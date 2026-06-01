# SysEngage Row 4 Understanding — §14 Addendum

**Filename:** SysEngage_Row_4_Understanding_v0_25.md (§14 addendum)

**Version:** 0.25 — §14 added: Pass 3d Requirement Derivation implementation framework. §1–§12 (v0.5) and §13 (v0.24, Pass 3c) remain authoritative and unchanged. Supersedes v0.24 by addition only.

**Date:** 01 June 2026

**Purpose.** §14 carries structural guidance only for Pass 3d. All implementation detail (stages, DDL, Pydantic schemas, edge cases, OQ resolutions) lives in the Row 4 Mechanism Spec (Requirement Derivation) v0.1 and is not duplicated here. This is the same structural/implementation firewall established for §13 (Pass 3c) and §11–§12 (Pass 3b): the Understanding indexes the Mechanism Spec; it does not restate it.

**Scope note.** This document records §14 only.

**Precedence rule.** Where this artefact appears to differ from canonical ledger spec v2.12 or Row 4 Mechanism Spec (Requirement Derivation) v0.1, the Mechanism Spec takes precedence.

---

## §14 Pass 3d — Requirement Derivation Implementation Framework

This section provides the structural framework for Pass 3d. The architectural authority is **SysEngage_Row_4_Mechanism_Domain_Derivation_v0_24.md** (the four-stage pattern Pass 3d inherits). The implementation specification is **SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_1.md** — all implementation detail (stages, transaction steps, DDL, Pydantic schemas, edge cases, OQ resolutions) lives there and is not duplicated here.

---

### §14.1 Module Structure

```
mechanisms/requirement_derivation/
  __init__.py                                  # Orchestration entry point — Stages 1–4
  stage1_preflight.py                          # Stage 1: Pass 3c prerequisite; CCI + Domain assembly; re-run detection
  stage2_ai_derivation.py                      # Stage 2: per-Domain AI derivation loop; response parsing
  stage3_structural_validation.py              # Stage 3: CHK-3d-01..07; ADVC-3d-01; Non-Loss repair (IM conditional)
  stage4_entity_production.py                  # Stage 4: requirement_id allocation; domain_refs DM-derivation;
                                               #          Requirement construction; ledger transaction
  prompts/
    requirement_derivation_prompt.py           # FirstRun / FullRerun per-Domain template; §5.4 guidance inline
    requirement_incremental_prompt.py          # IncrementalRerun template
    requirement_repair_prompt.py               # CHK-3d-05 Non-Loss repair template
  schemas/
    requirement_derivation_response_schema.py  # Pydantic: primary derivation response (no requirement_id/row_target/
                                               #           domain_refs — those are DM-produced)
    requirement_incremental_response_schema.py # Pydantic: IncrementalRerun response — DISTINCT class; must not be shared
    requirement_repair_response_schema.py      # Pydantic: Non-Loss repair response — DISTINCT class; must not be shared
```

---

### §14.2 ProjectProfile Parameters

Two parameters introduced by Pass 3d. Add to `project_profile` table with defaults as nullable columns.

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `requirement_rerun_threshold` | float 0–1 | 0.20 | New-CCI fraction above which IncrementalRerun escalates to FullRerun (applies only when the Domain-id set is unchanged; a Domain-set change forces FullRerun regardless) |
| `requirement_large_cci_set_advisory_threshold` | integer | 80 | Row CCI count above which the large-set advisory fires (signal only — per-Domain processing proceeds; no chunking at v0.1) |

See Mechanism Spec §4.1 (Stage 1 re-run detection), §3.3 (large-set advisory), §12.2 (OQ resolutions). Mechanism Spec §5.1 has the Alembic migration DDL.

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
| VER-3d-11 | IdempotentRerun: requirement set unchanged; `mechanism_data.idempotent == true`; execution_status=Completed | `tests/test_requirement_derivation.py` |
| VER-3d-12 | FullRerun: `requirement_count_retired` == prior active Requirement count for this row | `tests/test_requirement_derivation.py` |
| VER-3d-13 | `requirement_count_produced >= 1` when `cci_count_input > 0` | `tests/test_requirement_derivation.py` |
| VER-3d-14 | No active Requirement has `fit_criteria` present-but-empty (`fit_criteria IS NULL OR length > 0`) | `tests/test_requirement_derivation.py` |

---

### §14.4 Test Fixtures → pytest Mapping

All seven fixtures implemented in `tests/fixtures/requirement_derivation/`.

| Fixture | Test function | Key assertion |
|---|---|---|
| Fixture 1 — PMT Row 2 FirstRun | `test_pmt_row2_firstrun` | VER-3d-05, VER-3d-10, `requirement_count_produced >= domain_count_input` |
| Fixture 2 — NQPS Row 3 FirstRun (+ Row 4 zero-CCI companion) | `test_nqps_row3_firstrun` / `test_nqps_row4_zero_cci` | VER-3d-05, VER-3d-09; zero-CCI: `no_cci_input`, register preserved, Stage 2 not called |
| Fixture 3 — IdempotentRerun | `test_pmt_row2_idempotent_rerun` | VER-3d-11; Stage 2 AI stub not called |
| Fixture 4 — IncrementalRerun | `test_pmt_row2_incremental_rerun` | VER-3d-05 after delta; existing `requirement_id`s preserved; Domain set unchanged |
| Fixture 5 — Non-Loss repair (orphan recovered) | `test_noloss_repair_prompt_recovery` | `repair_prompt_issued=true`; VER-3d-05 passes; execution_status=Completed |
| Fixture 6 — Persistent orphan | `test_noloss_repair_persistent_orphan` | `orphaned_ccis` non-empty; execution_status=CompletedWithWarnings; Concern raised |
| Fixture 7 — FullRerun (Domain-set change) | `test_pmt_row2_fullrerun` | VER-3d-12; `retired_at` set on old Requirements; VER-3d-05 on new set; new `domain_refs` |

For fixture data content, AI-stub implementation pattern, and assertion detail: see Mechanism Spec §9.

---

### §14.5 Replit Agent Handoff Notes

**Documents to hand to the Agent:**
- Row 4 Mechanism Spec (Requirement Derivation) v0.1 — primary implementation reference (all detail including DDL)
- This section (Row 4 Understanding §14 v0.25) — structural framework
- Pass 3c Mechanism Spec (Domain Derivation) v0.24 — architectural authority for the four-stage pattern
- Row 4 Applied v0.2 — common architectural commitments
- Canonical Ledger v2.12 — Requirement and RequirementRegister entity schemas
- Segmentation spec v9.2 — requirement statement formulation discipline

**Key adaptations from Pass 3c (`mechanisms/domain_derivation/`) to Pass 3d:**
- Stage 2 is a **per-Domain loop** — one AI call per active Domain, not a single whole-row call
- Inputs are **both** CCIs and active Domains (Pass 3c took CCIs only)
- `domain_refs` is **DM-derived in Stage 4** by intersecting `cci_refs` with Domain membership — never AI-proposed; the response schema omits it
- Re-run hash is **two-part** (sorted CCI-ids + sorted active Domain-ids); a Domain-id-set change forces FullRerun
- Non-Loss repair derives a **covering Requirement** for orphaned CCIs (not a Domain), scoped to the orphan's owning Domain
- No name-uniqueness merge (no Pass 3c CHK-3c-03 analogue) — CHK-3d-07 collapses only exact statement+cci_refs duplicates
- `requirement_type` enum enforced at the parse boundary; value choice is principle-based (no lookup table)

**Key design decisions the Agent must not re-derive (all resolved in Mechanism Spec):**
- Per-Domain Stage 2 (D1a) — forward-compatible with whole-row (D1b) via the general `domain_refs` intersection; do not hard-code the single-Domain assumption into Stage 4 (MD-1, MD-2)
- `domain_refs` DM-derivation guarantees the ledger row_target/resolution rules by construction (MD-2); a proposal yielding empty `domain_refs` fails closed
- Two-part re-run hash and the Domain-set-change → FullRerun rule (MD-3, §4.1)
- IncrementalRerun is reachable **only** when the Domain-id set is unchanged (MD-3)
- Persistent orphan after failed repair → `CompletedWithWarnings` + Concern raised; not a hard failure
- `row_ref` is a top-level AnalysisPass field AND appears inside `mechanism_data` — both must be set
- `mode_active` is `"IM"` / `declared_transformation_modes` is `["IM","DM"]` — NOT `"LPM"` (carry forward the Pass 3c build correction)

**Migrations required:**
- `XXXX_add_requirement_tables.py` — `requirement` table (with `cci_refs`/`domain_refs`/`answer_refs` JSONB and `retired_at`); RequirementRegister seed (DDL: Mechanism Spec §5.1)
- `XXXX_add_requirement_profile_params.py` — two ProjectProfile columns (§14.2 above)

**F80 disposition (D5):** Pass 3d consumes Domains by `domain_id`, never by `name`, so cross-row Domain name duplication is harmless to derivation. F80 remains **Open** — the residual Practitioner-presentation concern is deferred to review tooling, not resolved by Pass 3d. Log this disposition against F80; do not close Wont-Fix.

---

## Document End

End of SysEngage Row 4 Understanding v0.25 — §14 addendum.

**Changes in v0.25:**
- §14 added — Pass 3d Requirement Derivation implementation framework (module structure, two ProjectProfile parameters, VER-3d-01..14 → pytest mapping, seven-fixture mapping, Agent handoff notes)
- No change to §1–§12 (v0.5) or §13 (v0.24); v0.25 supersedes v0.24 by addition only

Companion artefacts:
- SysEngage_Row_4_Mechanism_Domain_Derivation_v0_24.md — architectural authority for the four-stage pattern
- SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_1.md — implementation spec for Pass 3d
- SysEngage_Issues_Tracker_v0_51.md — finding disposition (F80, F66)
- sysengage_minimal_ledger_spec_v2_12.md — canonical Requirement / RequirementRegister schema authority
