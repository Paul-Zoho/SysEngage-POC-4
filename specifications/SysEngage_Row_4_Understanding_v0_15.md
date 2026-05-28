# SysEngage Row 4 Understanding — §13 Addendum

**Filename:** SysEngage_Row_4_Understanding_v0_15.md (§13 addendum)

**Version:** 0.15 — §13.13 self-reference corrected (v0.13 → v0.15); §13.7 execution_warnings note updated (seven advisory types in table form matching Mechanism Spec v0.11 §7). Supersedes v0.14.

**Date:** 26 May 2026

**Purpose.** §13 carries structural guidance only. DDL lives in Mechanism Spec v0.11 §5.1. v0.15 replaces v0.14 in full; all §1–§12 content from v0.5 remains authoritative.

**Scope note.** This document records §13 only.

**Precedence rule.** Where this artefact appears to differ from canonical ledger spec v2.12 or Row 4 Mechanism Spec (Domain Derivation) v0.11, the Mechanism Spec takes precedence.

---

## §13 Pass 3c — Domain Derivation Implementation Framework

This section establishes the Row 4 implementation framework for Pass 3c. The architectural authority is **SysEngage_Row_3_Mechanism_Domain_Derivation_v0_1.md**. The implementation specification is **SysEngage_Row_4_Mechanism_Domain_Derivation_v0_11.md**. This section provides structural framework guidance — module structure, parameter tables, VER criteria mapping, fixture table, and Replit Agent handoff notes. Implementation detail (stage-by-stage behaviour, DDL, Pydantic schemas) lives in the Mechanism Spec §5.1 and is not duplicated here.

---

### §13.1 Mechanism Characteristics and Implementation Position

Pass 3c is the third pass in the Phase 3 classification and derivation sequence. Its position relative to the other mechanisms it coordinates with:

```
Phase 3 — Classification and Derivation (row-sequential)
  Pass 3a — Row-Lens Source Re-Analysis      [mechanisms/row_lens_source_reanalysis/]  COMPLETE
  Pass 3b — CellContentItem Construction     [mechanisms/cci_construction/]             COMPLETE
  Pass 3c — Domain Derivation                [mechanisms/domain_derivation/]            ← THIS SECTION
  Pass 3d — Requirement Derivation           [mechanisms/requirement_derivation/]       PENDING
```

**Key differences from Pass 3b that shape the implementation:**

Pass 3b is a *per-Signal, all-columns* derivation mechanism — each batch of Signals produces CCIs across the Zachman column axis. Pass 3c is a *whole-row, cross-column grouping* mechanism — the full CCI set is presented to the AI at once and the AI partitions it into Domains. This changes the implementation shape in three significant ways:

1. **No batching.** Pass 3b uses fixed-size Signal batches (ProjectProfile.cci_batch_size) because Signal counts can be large. Pass 3c takes all CCIs for the row in a single AI call. The CCI set is the already-distilled output of Pass 3b — it is substantially smaller than the Signal set. No batching loop is needed.

2. **Richer re-run logic.** Pass 3b's re-run behaviour is extend-on-rerun (new Signals produce new CCI candidates; deduplication handles overlap). Pass 3c has four distinct re-run scenarios (FirstRun / IdempotentRerun / IncrementalRerun / FullRerun) requiring different code paths. The re-run scenario is determined by comparing the current CCI set hash against the prior AnalysisPass record.

3. **Structural validation with repair loop.** Pass 3b's deduplication is a Stage 4 sub-act that handles near-identical candidates. Pass 3c's structural validation (Stage 3) enforces Non-Loss (every CCI must appear in at least one Domain) and can trigger a repair AI call if the primary grouping misses CCIs. This is a conditional second AI call, not part of the primary pipeline.

**Mode characterisation:**

Pass 3c is **IM-primary, DM-envelope** — the AI grouping act is the core analytical work. This is a departure from the pass catalogue label ("DM + Robustness") documented in Row 2 v1.2 §3.9.3; that label is queued for correction per F-3c-01. The implementation must not be designed as DM-primary — the grouping judgment is inherently interpretive and cannot be reduced to a deterministic heuristic.

---

### §13.2 Module Structure

```
mechanisms/domain_derivation/
  __init__.py                              # Orchestration entry point — Stages 1–4
  stage1_preflight.py                      # DM: Pass 3b prerequisite check; CCI assembly; re-run scenario detection
  stage2_ai_grouping.py                    # IM: AI grouping call (primary); response parsing + Pydantic validation
  stage3_structural_validation.py          # DM: CHK-3c-01..06 checks; repair prompt dispatch (IM conditional)
  stage4_entity_production.py              # DM: domain_id allocation; Domain entity construction (six canonical
                                           #     attributes only); FullRerun retirement; ledger transaction; DomainRegister
  prompts/
    domain_grouping_prompt.py              # Template: FirstRun / FullRerun — full CCI set grouping
                                           #           (ROW_ABSTRACTION_PHRASES inline dict defined here — see §5.4)
    domain_incremental_prompt.py           # Template: IncrementalRerun — new CCIs against existing Domain summaries
    domain_repair_prompt.py                # Template: CHK-3c-04 repair — orphaned CCIs to be assigned
  schemas/
    domain_grouping_response_schema.py     # Pydantic: AI grouping response (name, description, classification_type, cci_refs)
    domain_incremental_response_schema.py  # Pydantic: IncrementalRerun response (action: assign|new)
    domain_repair_response_schema.py       # Pydantic: repair prompt response (action-based: assign|new;
                                           #           DISTINCT from incremental schema — uses domain_name
                                           #           not domain_id; must not be shared across files)
```

**Module naming convention** follows the Stage nomenclature from the Row 3 Mechanism Spec §4 rather than the Step nomenclature used by Pass 3b. This reflects the different internal structure of Pass 3c (four Stages vs six Steps). The convention is not a problem — the orchestration entry point in `__init__.py` sequences them correctly regardless of naming.

---

### §13.3 Re-run Scenario Detection

Stage 1 determines which of four re-run scenarios applies before any AI call is made. The four scenarios are **FirstRun**, **IdempotentRerun**, **IncrementalRerun**, and **FullRerun**. Detection uses a SHA-256 hash of the sorted eligible ci_id list compared against the prior AnalysisPass record.

Key implementation constraints (detail in Mechanism Spec §4.1):
- The prior-pass query (`query_most_recent_completed_domain_derivation_pass`) excludes Failed runs — a Failed run committed no Domains and must be treated as if no prior run exists. IdempotentRerun produces execution_status=Completed; the query correctly returns it as a prior run for hash comparison.
- The CCI delta calculation for IncrementalRerun uses `query_committed_cci_ids_for_row(row_ref, project_id)` — a live DB query on `domain_cci_membership`, not a stored field in `mechanism_data`.
- Zero-division guard: if `prior_cci_count == 0`, treat as FirstRun.
- IdempotentRerun exits Stage 1 immediately — no AI call, no entity production.

---

### §13.4 AI Grouping Call Pattern

The primary AI call (Stage 2) differs structurally from Pass 3b's per-batch derivation call:

- **No loop.** A single `call_domain_grouping_ai()` function wraps the Stage 2 IM act. There is no batch iteration.
- **One retry on parse failure.** If the Pydantic response schema validation fails, one retry is issued with the identical prompt. Second failure → `execution_status = Failed`.
- **Three prompt templates** (not one): `domain_grouping_prompt.py` (FirstRun/FullRerun), `domain_incremental_prompt.py` (IncrementalRerun), `domain_repair_prompt.py` (CHK-3c-04 repair). Each has its own Pydantic response schema. See Row 3 Mechanism Spec §4.1 for all three prompt structures.

**Prompt parameterisation contract for `domain_grouping_prompt.py`:**

| Parameter | Source | Notes |
|---|---|---|
| `row_ref` | current_row | Integer 1–6 |
| `abstraction_level_phrase` | `ROW_ABSTRACTION_PHRASES[str(row_ref)]` inline dict | e.g., "business conceptual level — business processes, entities, roles, events, and rules" |
| `cci_set` | eligible_ccis | List of {ci_id, column, classification_type, description} dicts |
| `cci_count` | len(eligible_ccis) | Injected as context for the AI |

`ROW_ABSTRACTION_PHRASES` is a simple inline dict constant defined in the prompt template file (Mechanism Spec §5.4). The `row_abstraction_vocabulary.py` module has been withdrawn — `domain_qualifier_label` entries have been removed along with `domain_qualifier`.

---

### §13.5 Structural Validation

Stage 3 runs six named checks (CHK-3c-01 through CHK-3c-06) in sequence against the AI proposal — all in-memory, no DB calls. CHK-3c-04 (Non-Loss) is the only check that may trigger a second AI call (the repair prompt, a conditional IM sub-act of Stage 3). See Mechanism Spec §4.3 for the full check sequence and failure actions.

Key constraints:
- Stage 3 has **no DB calls** — all operations are in-memory on the parsed Pydantic object.
- IncrementalRerun `action="assign"` outputs resolved during Stage 2 into `assign_membership_inserts` are **not written here** — they are written inside the Stage 4 transaction (Mechanism Spec §4.4.4 step 3b).
- The repair prompt uses `domain_name: str` to reference existing Domains (not `domain_id`). See Mechanism Spec §5.2 and the IMPORTANT distinct-class warning there.

---

### §13.6 Entity Production

Stage 4 is fully DM. Key implementation decisions (detail in Mechanism Spec §4.4):

- **domain_id allocation** is global per-project — `query_max_domain_id(project_id)` queries across all rows including retired Domains. Retired ids are never reused.
- **Domain entities carry the six canonical attributes only** (domain_id, name, description, classification_type, row_target, cell_content_item_refs). No domain_qualifier or upstream_domain_ref — both withdrawn. Cross-row Domain tracing uses the canonical path: `Domain → cell_content_item_refs → CCI → signal_refs → Requirement (row n-1) → domain_refs → Domain (row n-1)`.
- **FullRerun retirement timing:** `prior_active_domains` must be captured *before* the transaction opens — `retirement_mapping` is computed from the pre-retirement list, not after the UPDATE.
- **Transaction (Mechanism Spec §4.4.3):** Single atomic transaction containing: FullRerun retirement UPDATE; new Domain entity INSERTs (six canonical attributes); new Domain membership INSERTs (step 3a); IncrementalRerun `assign_membership_inserts` INSERTs (step 3b); project-wide DomainRegister UPDATE (no `row_target` filter).
- **DomainRegister update** uses `query_all_active_domain_ids(project_id)` — applies to **all paths including the zero-CCI early exit in §4.1** — never hardcode `member_ids = []`.

---

### §13.7 AnalysisPass Population

The `mechanism_data` sub-structure in `AnalysisPass.outputs` is defined in Mechanism Spec v0.11 §7. The implementation must populate ALL fields; zero-value arrays MUST be `[]` not null. The AnalysisPass is written outside the main ledger transaction (same discipline as Pass 3b Step 6).

**`mechanism_data` field population responsibilities by Stage:**

| Field | Populated by | Notes |
|---|---|---|
| `run_scenario` | Stage 1 | String: one of the four scenario names |
| `cci_set_hash` | Stage 1 | SHA-256 of sorted ci_id list |
| `cci_count_input` | Stage 1 | `len(eligible_ccis)` |
| `idempotent` | Stage 1 | Boolean; true on IdempotentRerun only |
| `large_cci_set_advisory` | Stage 1 | Boolean; true if CCI count exceeded advisory threshold |
| `orphaned_ccis` | Stage 3 | ci_ids of persistent orphans after repair attempt |
| `repair_prompt_issued` | Stage 3 | Boolean; true if CHK-3c-04 triggered the repair prompt |
| `cross_cutting_advisories` | Stage 3 | List of {ci_id, domain_count} for CCIs exceeding advisory threshold |
| `validation_failures` | Stage 3 | Array of {check_id, domain_name, detail} |
| `domain_count_produced` | Stage 4 | `len(domain_entities)`; 0 on IdempotentRerun |
| `domain_count_retired` | Stage 4 | Count of Domains retired on FullRerun; 0 otherwise |
| `domains_produced` | Stage 4 | Per-domain summary (domain_id, name, cci_ref_count, cross_cutting_cci_count) |
| `downstream_rerun_required` | Stage 4 | Boolean; true if FullRerun and Pass 3d has previously completed |
| `retirement_mapping` | Stage 4 | Array of {old_domain_id, inferred_successor_domain_id\|null}; empty on non-FullRerun |
| `mode_violations` | All stages | Mode discipline decorator; empty array if no violations |
| `ai_model_fingerprints` | Stage 2 + Stage 3 (repair) | List of {stage, model, input_tokens, output_tokens}; one entry per IM call; `[]` on IdempotentRerun |

**`execution_warnings` — placement note:** `execution_warnings` is a **standard top-level AnalysisPass field** outside `mechanism_data` — consistent with all other mechanisms. Entries in `execution_warnings` do **not** change `execution_status` (see Mechanism Spec §4.4.6 for the precise CompletedWithWarnings trigger conditions). Pass 3c writes to `execution_warnings` in seven cases:

| Advisory type | Source section | When |
|---|---|---|
| `no_cci_input` | §4.1 | Zero-CCI early exit |
| `cci_referential_integrity_violation` | §4.1 | CCI references non-existent ZachmanCell |
| `incremental_fallback_to_fullrerun` | §4.2 | IncrementalRerun AI parse failure; fell back to FullRerun |
| `duplicate_domain_name_merged` | §4.3 CHK-3c-03 | Duplicate proposal names merged |
| `domain_count_advisory` | §4.3 ADVC-3c-01 | Domain count outside soft bounds |
| `repair_assign_name_not_found` | §4.3 repair | Repair assign domain_name unmatched; treated as new |
| `incremental_assign_invalid_domain_id` | §5.2 | IncrementalRerun assign domain_id invalid; treated as new |

See Mechanism Spec v0.11 §7 for the authoritative enumeration.

---

### §13.8 Database Schema

Pass 3c requires the `domain` and `domain_cci_membership` tables and a DomainRegister seed row. The authoritative CREATE TABLE DDL is in **Mechanism Spec v0.11 §5.1**. The DDL is not duplicated here.

Key schema decisions:
- `cell_content_item_refs` is a join table (`domain_cci_membership`), not a JSONB array.
- `retired_at` is the soft-delete column — `NULL` = active; non-null = retired.
- Composite PK `(domain_id, project_id)` on both tables.
- Domain table has **no** `domain_qualifier` or `upstream_domain_ref` columns — both withdrawn.
- Migration file: `migrations/XXXX_add_domain_tables.py`.

---

### §13.9 ProjectProfile Parameters for Pass 3c

Three ProjectProfile parameters are introduced by Pass 3c. These must be added to the `project_profile` table alongside the existing Pass 3b parameters:

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `domain_rerun_threshold` | float 0.0–1.0 | 0.20 | Fraction of new CCIs above which FullRerun is triggered instead of IncrementalRerun |
| `domain_cross_cutting_advisory_threshold` | integer | 3 | Number of Domains a single CCI may appear in before advisory is recorded |
| `domain_large_cci_set_advisory_threshold` | integer | 80 | CCI count above which a large-set advisory is recorded before the grouping call |

**Migration:** Add three columns to the `project_profile` table with the default values above. All three are nullable — `NULL` means "use default". The mechanism reads the value, substitutes the default if NULL.

Note: `domain_upstream_match_threshold` was defined in earlier spec versions but is withdrawn — `upstream_domain_ref` is not produced by this mechanism.

---

### §13.10 Mode Discipline Realisation

Pass 3c uses the mode discipline decorator pattern established at Row 4 Applied §4.7 and carried through Pass 3b. The decorator is applied per Stage:

| Stage / Sub-act | Declared mode | Decorator behaviour |
|---|---|---|
| Stage 1 — Pre-flight | DM | Verifies no AI calls made; records DM on AnalysisPass |
| Stage 2 — AI grouping (primary) | IM | Records AI invocation fingerprint (model, temperature, tokens); LPM constraint on CCI text |
| Stage 2 — AI grouping (retry, if parse failure) | IM | Second fingerprint recorded; retry reason logged |
| Stage 3 — Structural validation | DM | Verifies no AI calls made (except the repair sub-act) |
| Stage 3 — Repair prompt (conditional) | IM | Records AI invocation fingerprint; flagged as `repair_prompt_issued=true` |
| Stage 4 — Entity production | DM | Verifies no AI calls; records ledger write |

**Mode violations** are recorded in `AnalysisPass.outputs.mechanism_data.mode_violations` and set `execution_status = CompletedWithWarnings`.

---

### §13.11 Verification Criteria for Pass 3c (extending Row 3 Mechanism Spec §8)

The decidable criteria (VER-3c-01 through VER-3c-12) from the Row 3 Mechanism Spec are the authoritative automated verification targets. The Row 4 implementation maps them to pytest tests:

| Row 3 VER ID | pytest implementation | Test module |
|---|---|---|
| VER-3c-01 | Assert all `domain_id` values match `^D\d{3}$` | `tests/test_domain_derivation.py` |
| VER-3c-02 | Assert uniqueness of `domain_id` across all rows in project | `tests/test_domain_derivation.py` |
| VER-3c-03 | Assert `domain_cci_membership` has ≥1 row per domain_id | `tests/test_domain_derivation.py` |
| VER-3c-04 | Assert all ci_ids in `domain_cci_membership` resolve to `cell_content_item` with matching row_target | `tests/test_domain_derivation.py` |
| VER-3c-05 | Assert every eligible CCI ci_id appears in at least one `domain_cci_membership` row | `tests/test_domain_derivation.py` |
| VER-3c-06 | Assert `domain_register.member_ids` == set of active `domain.domain_id` for this **project** (all rows, `retired_at IS NULL`, no `row_target` filter) | `tests/test_domain_derivation.py` — **cross-row test care:** single-row fixtures pass this trivially; integration tests exercising Row 2 then Row 3 in the same project must query across both rows. Scoping the assertion to `row_target = current_row` is incorrect. |
| VER-3c-07 | Assert AnalysisPass with `mechanism="DomainDerivation"` and `row_ref=current_row` exists | `tests/test_domain_derivation.py` |
| VER-3c-08 | Assert `mechanism_data` structure present with all required fields non-null | `tests/test_domain_derivation.py` |
| VER-3c-09 | Assert `domain_qualifier` and `upstream_domain_ref` columns absent from `domain` table schema | `tests/test_domain_derivation.py` |
| VER-3c-10 | Assert IdempotentRerun leaves domain set unchanged; `mechanism_data.idempotent == true`; execution_status=Completed | `tests/test_domain_derivation.py` |
| VER-3c-11 | Assert FullRerun `domain_count_retired` = count of prior committed Domains | `tests/test_domain_derivation.py` |
| VER-3c-12 | Assert domain_count_produced ≥ 1 when cci_count_input > 0 | `tests/test_domain_derivation.py` |

**Test fixtures** (from Row 4 Mechanism Spec §9) are implemented as data fixtures in `tests/fixtures/domain_derivation/`. All seven fixtures map to pytest test cases:

| Fixture | Test case name | Key assertion |
|---|---|---|
| Fixture 1 — PMT Row 2 happy path | `test_pmt_row2_firstrun` | VER-3c-05 (Non-Loss), VER-3c-09 (no qualifier columns), ≥2 Domains |
| Fixture 2 — NQPS Row 3 narrow | `test_nqps_row3_firstrun` | VER-3c-05, VER-3c-09, PLB-3c-05 (logical-design vocabulary spot check) |
| Fixture 3 — IdempotentRerun | `test_pmt_row2_idempotent_rerun` | VER-3c-10, execution_status=Completed, mechanism_data.idempotent=true, Stage 2 AI stub not called |
| Fixture 4 — IncrementalRerun | `test_pmt_row2_incremental_rerun` | VER-3c-05 passes after delta; existing domain_ids preserved; no downstream_rerun_required |
| Fixture 5 — Non-Loss repair (orphan recovered) | `test_noloss_repair_prompt_recovery` | `repair_prompt_issued=true`; VER-3c-05 passes after repair; execution_status=Completed |
| Fixture 6 — Persistent orphan after repair failure | `test_noloss_repair_persistent_orphan` | `orphaned_ccis` non-empty; execution_status=CompletedWithWarnings; Concern entity raised; VER-3c-05 asserted to **fail** (expected) |
| Fixture 7 — FullRerun: retirement + fresh allocation | `test_pmt_row2_fullrerun` | VER-3c-11 (domain_count_retired == prior active count); retired_at IS NOT NULL on old Domains; new domain_ids from D004+; VER-3c-05 passes on new set |

**AI stub pattern for tests:** Tests that involve the AI grouping call (Fixtures 1, 2, 4, 5) use an AI stub — a hardcoded `DomainProposal` response injected via dependency injection or monkeypatching. The stub for Fixture 5 deliberately omits one CCI from all proposed Domains to trigger the repair path. This is the same stub pattern used by the Pass 3b test suite (see `tests/test_cci_construction.py` for the pattern reference).

---

### §13.12 Pass 3c → Pass 3d Sequencing Constraint

Pass 3d (Requirement Derivation) takes CCIs and Domains as its joint input. The sequencing constraint is hard:

> Pass 3d CANNOT begin until Pass 3c has completed with `execution_status ∈ {Completed, CompletedWithWarnings}`.

The orchestrator (`core/orchestrator.py`) must enforce this. The check is: query AnalysisPass for `mechanism="DomainDerivation"` and `row_ref=current_row`; assert `execution_status ∈ {Completed, CompletedWithWarnings}`. IdempotentRerun produces `execution_status = Completed` with `mechanism_data.idempotent = true` — this satisfies the gate. `Failed` blocks Pass 3d.

**FullRerun and Pass 3d dependency:** When Stage 4 sets `downstream_rerun_required=true` in the AnalysisPass, the orchestrator should surface this as an advisory to the Practitioner before Pass 3d is invoked. The orchestrator does NOT automatically trigger Pass 3d re-run — this is a Practitioner decision. The advisory should clearly state that existing Requirements referencing retired domain_ids may be dangling.

---

### §13.13 Replit Agent Handoff Notes

The implementation handoff to the Replit Agent for Pass 3c should include:

- Row 4 Mechanism Spec (Domain Derivation) v0.11 — primary implementation reference (all detail including DDL)
- This section (Row 4 Understanding §13 v0.15) — structural framework
- Row 4 Applied v0.2 — common architectural commitments (stack, transactional discipline, mode decorator)
- Row 4 Understanding §12 (v0.5) — reference implementation patterns from Pass 3b
- Canonical Ledger v2.12 — Domain and DomainRegister entity schemas (six Domain attributes only)
- Existing `mechanisms/cci_construction/` implementation — reference for AI invocation pattern, Pydantic response schema, AnalysisPass write, transactional discipline

**The Agent should implement `mechanisms/domain_derivation/` following the established pattern of `mechanisms/cci_construction/` with the following adaptations:**

- No batching loop (single AI call per run)
- Four re-run scenarios instead of extend-on-rerun
- Three prompt templates instead of two
- `domain_cci_membership` join table instead of a `cell_content_item_refs` JSONB array
- Conditional repair prompt as IM sub-act within Stage 3
- `downstream_rerun_required` flag detection and AnalysisPass population
- No `domain_qualifier` assignment, no `upstream_domain_ref` heuristic, no `row_abstraction_vocabulary.py` module

**Build task — new migrations required:**
- `migrations/XXXX_add_domain_tables.py` — creates `domain` and `domain_cci_membership` tables and seeds DomainRegister row (use DDL from Mechanism Spec v0.11 §5.1)
- `migrations/XXXX_add_domain_profile_params.py` — adds **three** new ProjectProfile columns (not four)

**Build task — ProjectProfile model update:**
- `schemas/project_profile.py` (or equivalent Pydantic model) — add three new optional fields with defaults

---

### §13.14 Open Questions Deferred from Row 3 Mechanism Spec §12.2

Three open questions from the Row 3 Mechanism Spec are deferred to Row 4 implementation:

| OQ ID | Question | Row 4 decision |
|---|---|---|
| **OQ-3c-01** | Domain count calibration: no formula or hard bounds specified | Soft advisory bounds implemented in Stage 3: advisory if `domain_count < 1 + ceil(cci_count / 15)` or `domain_count > cci_count / 2`. AnalysisPass advisory only, not a failure. Calibrate against PMT and NQPS production runs. |
| **OQ-3c-02** | upstream_domain_ref threshold: deferred to Row 4 | **Withdrawn** — upstream_domain_ref is not produced by this mechanism. Cross-row Domain tracing uses the canonical CCI → Requirement → Domain path. No ProjectProfile parameter needed. |
| **OQ-3c-03** | FullRerun retirement: soft-delete flag vs archive table | **Resolved** — soft-delete (`retired_at TIMESTAMPTZ`, nullable; null = active). Simpler than an archive table; preserves referential integrity; `query_max_domain_id` includes retired Domains to prevent id reuse. |

---

## Document End

End of SysEngage Row 4 Understanding v0.15 — §13 addendum.

**Changes from v0.14:**
- §13.1: mechanism spec reference updated v0.10 → v0.11
- §13.7: execution_warnings note rewritten — seven advisory types in table form (two §4.1 types added: `no_cci_input`, `cci_referential_integrity_violation`); explicit statement that execution_warnings entries do not change execution_status; cross-ref to Mechanism Spec §4.4.6
- §13.8: DDL pointer updated to Mechanism Spec v0.11 §5.1
- §13.13: self-reference "v0.13" corrected to "v0.15"; Mechanism Spec reference updated to v0.11

§13 content from v0.14 is superseded by v0.15. All §1–§12 content from v0.5 unchanged.

**This is the designated handoff version.** Further Understanding iteration after v0.15 is driven by implementation evidence only.

Companion artefacts:
- SysEngage_Row_3_Mechanism_Domain_Derivation_v0_1.md — architectural authority for Pass 3c
- SysEngage_Row_4_Mechanism_Domain_Derivation_v0_11.md — implementation spec (handoff version)
- SysEngage_Issues_Tracker_v0_37.md — finding disposition

§13 content from v0.14 is superseded by v0.15. All §1–§12 content from v0.5 unchanged.

Companion artefacts:
- SysEngage_Row_3_Mechanism_Domain_Derivation_v0_1.md — architectural authority for Pass 3c
- SysEngage_Row_4_Mechanism_Domain_Derivation_v0_11.md — implementation spec
- SysEngage_Issues_Tracker_v0_37.md — finding disposition
