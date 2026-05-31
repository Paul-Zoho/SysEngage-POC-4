# SysEngage Row 4 Understanding — §13 Addendum

**Filename:** SysEngage_Row_4_Understanding_v0_24.md (§13 addendum)

**Version:** 0.24 — CHK-3c-08 added: §13.1 two new files; §13.3 VER-3c-14 added; §13.5 key decisions updated. Supersedes v0.23.

**Date:** 26 May 2026

**Purpose.** §13 carries structural guidance only. DDL lives in Mechanism Spec v0.22 §5.1. v0.24 replaces v0.23 in full; all §1–§12 content from v0.5 remains authoritative.

**Scope note.** This document records §13 only.

**Precedence rule.** Where this artefact appears to differ from canonical ledger spec v2.12 or Row 4 Mechanism Spec (Domain Derivation) v0.22, the Mechanism Spec takes precedence.

---

## §13 Pass 3c — Domain Derivation Implementation Framework

This section provides the structural framework for Pass 3c. The architectural authority is **SysEngage_Row_3_Mechanism_Domain_Derivation_v0_1.md**. The implementation specification is **SysEngage_Row_4_Mechanism_Domain_Derivation_v0_22.md** — all implementation detail (stages, transaction steps, DDL, Pydantic schemas, edge cases, OQ resolutions) lives there and is not duplicated here.

---

### §13.1 Module Structure

```
mechanisms/domain_derivation/
  __init__.py                              # Orchestration entry point — Stages 1–4
  stage1_preflight.py                      # Stage 1: Pass 3b prerequisite; CCI assembly; re-run detection
  stage2_ai_grouping.py                    # Stage 2: AI grouping call; response parsing
  stage3_structural_validation.py          # Stage 3: CHK-3c-01..06; ADVC-3c-01; repair prompt (IM conditional)
  stage4_entity_production.py              # Stage 4: domain_id allocation; Domain construction; ledger transaction
  prompts/
    domain_grouping_prompt.py              # FirstRun / FullRerun grouping template; ROW_GUIDANCE dict (see §5.4)
    domain_incremental_prompt.py           # IncrementalRerun template
    domain_repair_prompt.py                # CHK-3c-04 repair template
  schemas/
    domain_grouping_response_schema.py     # Pydantic: primary grouping response
    domain_incremental_response_schema.py  # Pydantic: IncrementalRerun response (action: assign|new; uses domain_id)
    domain_repair_response_schema.py       # Pydantic: repair response (action: assign|new; uses domain_name —
                                           #           DISTINCT class from incremental schema; must not be shared)
```

---

### §13.2 ProjectProfile Parameters

Three parameters introduced by Pass 3c. Add to `project_profile` table with defaults as nullable columns.

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `domain_rerun_threshold` | float 0–1 | 0.20 | New-CCI fraction above which IncrementalRerun escalates to FullRerun |
| `domain_cross_cutting_advisory_threshold` | integer | 3 | Max Domains a single CCI may appear in before advisory fires |
| `domain_large_cci_set_advisory_threshold` | integer | 80 | CCI count above which large-set advisory fires before AI call |

See Mechanism Spec §4.1 (Stage 1 pre-flight), §4.3 (ADVC-3c-01), §12.2 (OQ resolutions) for how these parameters are applied. Mechanism Spec §5.1 has the Alembic migration DDL.

---

### §13.3 VER Criteria → pytest Mapping

| VER ID | Assertion | pytest location |
|---|---|---|
| VER-3c-01 | All `domain_id` values match `^D\d{3}$` | `tests/test_domain_derivation.py` |
| VER-3c-02 | All `domain_id` values unique within project (active + retired) | `tests/test_domain_derivation.py` |
| VER-3c-03 | Every Domain has `jsonb_array_length(cell_content_item_refs) >= 1` | `tests/test_domain_derivation.py` |
| VER-3c-04 | All ci_ids in `cell_content_item_refs` resolve via `cell_content_item.cell_id → zachman_cell.row_target == domain.row_target` | `tests/test_domain_derivation.py` |
| VER-3c-05 | Every eligible CCI ci_id appears in at least one Domain's `cell_content_item_refs` | `tests/test_domain_derivation.py` |
| VER-3c-06 | `domain_register.member_ids` == active `domain.domain_id` set for project (all rows, no `row_target` filter) | `tests/test_domain_derivation.py` |
| VER-3c-07 | AnalysisPass with `mechanism="DomainDerivation"` and `row_ref=current_row` exists | `tests/test_domain_derivation.py` |
| VER-3c-08 | `mechanism_data` present with all required fields non-null | `tests/test_domain_derivation.py` |
| VER-3c-09 | `domain_qualifier` and `upstream_domain_ref` columns absent from `domain` table | `tests/test_domain_derivation.py` |
| VER-3c-10 | IdempotentRerun: domain set unchanged; `mechanism_data.idempotent == true`; execution_status=Completed | `tests/test_domain_derivation.py` |
| VER-3c-11 | FullRerun: `domain_count_retired` == prior active Domain count for this row | `tests/test_domain_derivation.py` |
| VER-3c-12 | `domain_count_produced >= 1` when `cci_count_input > 0` | `tests/test_domain_derivation.py` |
| VER-3c-13 | No active Domain has `jsonb_array_length(cell_content_item_refs) == 1`, unless `cci_count_input == 1`. If `chk3c07_repair_failed` in execution_warnings, residual single-CCI domains must be documented there. | `tests/test_domain_derivation.py` |
| VER-3c-14 | No active Domain has `jsonb_array_length(cell_content_item_refs) > floor(cci_count_input/2)`, unless `cci_count_input <= 4` (sparse), all domains exceed threshold (circular), or `chk3c08_repair_failed` in execution_warnings. | `tests/test_domain_derivation.py` |

---

### §13.4 Test Fixtures → pytest Mapping

All seven fixtures implemented in `tests/fixtures/domain_derivation/`.

| Fixture | Test function | Key assertion |
|---|---|---|
| Fixture 1 — PMT Row 2 FirstRun | `test_pmt_row2_firstrun` | VER-3c-05, VER-3c-09, ≥2 Domains |
| Fixture 2 — NQPS Row 3 FirstRun | `test_nqps_row3_firstrun` | VER-3c-05, VER-3c-09, PLB-3c-05 |
| Fixture 3 — IdempotentRerun | `test_pmt_row2_idempotent_rerun` | VER-3c-10; Stage 2 AI stub not called |
| Fixture 4 — IncrementalRerun | `test_pmt_row2_incremental_rerun` | VER-3c-05 after delta; existing domain_ids preserved |
| Fixture 5 — Non-Loss repair (orphan recovered) | `test_noloss_repair_prompt_recovery` | `repair_prompt_issued=true`; VER-3c-05 passes; execution_status=Completed |
| Fixture 6 — Persistent orphan | `test_noloss_repair_persistent_orphan` | `orphaned_ccis` non-empty; execution_status=CompletedWithWarnings |
| Fixture 7 — FullRerun retirement | `test_pmt_row2_fullrerun` | VER-3c-11; retired_at set on old Domains; VER-3c-05 passes on new set |

For fixture data content, AI stub implementation pattern, and assertion details: see Mechanism Spec §9.

---

### §13.5 Replit Agent Handoff Notes

**Documents to hand to the Agent:**
- Row 4 Mechanism Spec (Domain Derivation) v0.22 — primary implementation reference (all detail including DDL)
- This section (Row 4 Understanding §13 v0.24) — structural framework
- Row 4 Applied v0.2 — common architectural commitments
- Row 4 Understanding §12 (v0.5) — Pass 3b reference implementation patterns
- Canonical Ledger v2.12 — Domain and DomainRegister entity schemas (six Domain attributes only)

**Key adaptations from Pass 3b (`mechanisms/cci_construction/`) to Pass 3c:**
- No batching loop — single AI call per run
- Four re-run scenarios (FirstRun / IdempotentRerun / IncrementalRerun / FullRerun) — see Mechanism Spec §4.1
- Three prompt templates, not two
- `cell_content_item_refs` stored as JSONB array on `domain` row — no join table
- Conditional repair prompt as IM sub-act within Stage 3
- `downstream_rerun_required` flag — see Mechanism Spec §4.4.5
- No `domain_qualifier`, no `upstream_domain_ref`, no `row_abstraction_vocabulary.py` module

**Key design decisions the Agent must not re-derive (all resolved in Mechanism Spec):**
- `cell_content_item_refs` is a JSONB array on the `domain` row — not a join table (see MD-4)
- CHK-3c-07 single-CCI absorption fires only when `cci_count_input > 1` AND `len(proposals) > 1` AND not all proposals are single-CCI
- CHK-3c-07 uses `assign` actions only — no new Domain creation; every isolated ci_id must appear in exactly one assignment
- `chk3c07_absorption_performed` in execution_warnings is informational only — does not change `execution_status`
- CHK-3c-04 Non-Loss re-check runs after CHK-3c-07 merge — safety check, not a full re-validation
- `row_ref` is a top-level AnalysisPass field AND appears inside `mechanism_data` — both must be set

**Migrations required:**
- `XXXX_add_domain_tables.py` — `domain` table with `cell_content_item_refs JSONB`; DomainRegister seed (DDL: Mechanism Spec §5.1)
- `XXXX_add_domain_profile_params.py` — three ProjectProfile columns (§13.2 above)

---

## Document End

End of SysEngage Row 4 Understanding v0.24 — §13 addendum.

**Changes in v0.24:**
- §13.1: two CHK-3c-08 files added (`domain_split_repair_prompt.py`, `domain_split_repair_response_schema.py`)
- §13.3: VER-3c-14 added — no active Domain has more CCI refs than `floor(cci_count_input/2)` (with sparse-row and circular-split exceptions)
- §13.5: CHK-3c-08 key decisions added (threshold formula, chaining with CHK-3c-07, exceptions)
- All Mechanism Spec references updated v0.21 → v0.22; tracker → v0.48

§13 content from v0.23 is superseded by v0.24. All §1–§12 content from v0.5 unchanged.

Companion artefacts:
- SysEngage_Row_3_Mechanism_Domain_Derivation_v0_1.md — architectural authority for Pass 3c
- SysEngage_Row_4_Mechanism_Domain_Derivation_v0_22.md — implementation spec
- SysEngage_Issues_Tracker_v0_48.md — finding disposition

§13 content from v0.23 is superseded by v0.24. All §1–§12 content from v0.5 unchanged.

Companion artefacts:
- SysEngage_Row_3_Mechanism_Domain_Derivation_v0_1.md — architectural authority for Pass 3c
- SysEngage_Row_4_Mechanism_Domain_Derivation_v0_22.md — implementation spec
- SysEngage_Issues_Tracker_v0_48.md — finding disposition
