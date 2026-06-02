# SysEngage Row 4 Mechanism: Requirement Derivation

**Implementation specification — physical / builder tier**

Filename: SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_2.md

Version: 0.2 (Supersedes v0.1. v0.1 was a row-agnostic physical spec, written before the Row 3 (logical) Requirement Derivation parent existed; it was implemented and produced the PMT Row 1 and NQPS Row 1 production runs. v0.2 re-frames the spec to its corrected place in the two-abstraction-level design: it now realises the Row 3 (logical) Requirement Derivation spec v0.1, aligns structurally to the Row 4 Domain Derivation sibling, fully authors §5.4 REQUIREMENT_ROW_GUIDANCE["1"] as a distinct dict from the domain ROW_GUIDANCE (decision B; closes the Row 1 portion of F81), adds CHK-3d-08 (decidable subject-vocabulary check, soft severity), and resolves OQ-3d-01..05 from the Row 3 spec. Rows 2–6 guidance remain short-phrase stubs pending their own validation cycles. See §12.4 for the v0.1→v0.2 change detail.)

Date: 02 June 2026

**Abstraction level:** Row 4 — Builder / Physical. This spec is the implementable realisation of the mechanism. Every design decision traces to the Row 3 (logical) Requirement Derivation spec; where this spec makes a physical choice the Row 3 spec deferred (an OQ), that resolution is recorded in §12.2.

**Purpose.** Implementation specification for the Requirement Derivation mechanism (Pass 3d). Derives Requirement entities from the CCIs grouped by Pass 3c Domains, with full CCI traceability and deterministic Domain attribution. Architectural pattern is the four-stage IM-primary / DM-envelope pattern shared with Domain Derivation; the logical authority is the Row 3 Requirement Derivation spec. This spec records the physical realisation: module structure, DDL, response schemas, literal prompt guidance, audit structure, fixtures, and VER→pytest mapping.

**Status:** Row 1 validated. §5.4 REQUIREMENT_ROW_GUIDANCE["1"] is fully authored; Rows 2–6 are short-phrase stubs. Supersedes the implemented v0.1; see §12.4 for the change detail.

---

## 1. Mechanism Identification

| Attribute | Value |
|---|---|
| **Mechanism name** | Requirement Derivation |
| **Mechanism ID** | MECH-3d |
| **Logical authority** | SysEngage_Row_3_Mechanism_Requirement_Derivation_v0.1.md — all sections. This physical spec realises that logical spec. Where silent on a shared pattern, the Row 4 Domain Derivation spec v0.24 governs as the structural sibling. |
| **Operational location** | Phase 3 Pass 3d. Executes after Pass 3c (Domain Derivation) completes for the row; before Phase 5 (Cell Quality) and Phase 6/8 (Coverage). Four stages: Stage 1 (pre-flight + CCI/Domain assembly + re-run detection, DM), Stage 2 (per-Domain AI derivation, IM), Stage 3 (structural validation + conditional repair, DM + IM conditional), Stage 4 (entity production + Domain-ref derivation + ledger commit, DM). |
| **Mechanism class** | AI-involving. IM-primary (Stage 2 per-Domain derivation; Stage 3 conditional Non-Loss repair). DM-envelope (Stage 1; Stage 3 structural checks; Stage 4 entity production, domain_refs derivation, ledger write). LPM throughout — CCI descriptions read as context, not rewritten verbatim into statements. |
| **Module location** | `mechanisms/requirement_derivation/`. See §3.1. |
| **Row applicability** | Row-sequential. Runs once per active row. Reads only the CCIs and Domains of the current row. The row's REQUIREMENT_ROW_GUIDANCE block (§5.4) governs statement subject and vocabulary. |
| **Mechanism Stakeholder** | None. SH001 covers structural review. SG-01 covers Practitioner quality review (§8.2). SG-03 carries execution attribution via AnalysisPass. |
| **Mode declaration** | Primary mode IM (Stage 2). DM sub-acts: pre-flight, structural validation, domain_refs derivation, entity production, RequirementRegister construction, AnalysisPass write. LPM throughout. |

---

## 2. Cross-References

| Source | Reference | What this provides |
|---|---|---|
| **Row 3 Requirement Derivation v0.1** | All sections | **Logical authority.** §4 stage logic, §4.1.1 REQUIREMENT_ROW_GUIDANCE (logical), §5 schema, §6 re-run semantics, §8 VER/PLB, §12.4 decision trace. This spec realises each. Section-level traces appear inline (e.g. "realises Row 3 §6"). |
| **Row 4 Domain Derivation v0.24** | All sections | **Structural sibling.** Shared four-stage pattern, mode-discipline decorator, `mechanism_data` audit convention, `execution_warnings` placement, fingerprint structure, fixture/AI-stub patterns, repair-prompt-as-IM-sub-act. This spec matches its conventions. |
| **Row 4 Applied v0.2** | All sections | Common architectural commitments: Python 3.12+, FastAPI, Neon PostgreSQL via SQLAlchemy + Alembic, Pydantic v2, Claude Sonnet via Anthropic API, pytest, transactional discipline, mode-discipline decorator. |
| **Canonical Ledger v2.12** | Requirement, RequirementRegister, AnalysisPass | Authoritative schemas. Eight required Requirement attributes, five optional. Normative rules transcribed in §5.1. |
| **Segmentation spec v9.2** | Statement formulation | Atomic, single-intent, normative, no inferred actors/behaviours. Realised in §5.4 guidance. |
| **sys_engage_specification_v2.md** | §Phase 3 Requirement Generation, §ADR | POC source for type-classification reasoning signals. Read as principle (D4), realised as §5.4 reasoning block — not a lookup table. |
| **Tracker v0.52** | F80, F81 | F80 (Open): consume Domains by domain_id (§4.4.2). F81 (Open): §5.4 REQUIREMENT_ROW_GUIDANCE + CHK-3d-08 are its closure path — authoring Row 1 here closes the Row 1 portion. |

---

## 3. Architectural Approach

### 3.1 Module structure

```
mechanisms/requirement_derivation/
  __init__.py                                  # Orchestration — Stages 1–4 in sequence
  stage1_preflight.py                          # DM: Pass 3c prerequisite; eligible CCI + active Domain
                                               #     assembly; two-part input hash; scenario detection; idempotent exit
  stage2_ai_derivation.py                      # IM: per-Domain derivation loop; schema validation at boundary;
                                               #     one retry on parse failure; IncrementalRerun branch
  stage3_structural_validation.py              # DM: CHK-3d-01..08; ADVC-3d-01; Non-Loss repair dispatch (IM conditional)
  stage4_entity_production.py                  # DM: requirement_id allocation; domain_refs DM-derivation;
                                               #     Requirement construction; FullRerun retirement; ledger
                                               #     transaction; RequirementRegister replace; AnalysisPass write
  prompts/
    requirement_derivation_prompt.py           # FirstRun / FullRerun per-Domain template; injects ROW_GUIDANCE[row]
    requirement_incremental_prompt.py          # IncrementalRerun template
    requirement_repair_prompt.py               # CHK-3d-05 Non-Loss repair template
    requirement_row_guidance.py                # REQUIREMENT_ROW_GUIDANCE dict (§5.4) — DISTINCT from domain ROW_GUIDANCE
  schemas/
    requirement_derivation_response_schema.py  # Pydantic: primary derivation response
    requirement_incremental_response_schema.py # Pydantic: IncrementalRerun response — DISTINCT class (§5.2)
    requirement_repair_response_schema.py      # Pydantic: repair response — DISTINCT class (§5.2)
```

### 3.2 Major design decisions

These realise the Row 3 logical decisions (Row 3 §12.4). Rationale is in the Row 3 spec; this section records only the physical realisation.

**MD-1 — Per-Domain Stage 2 (realises Row 3 §4 Stage 2 / D1a).** One AI call per active Domain; the Domain's `cell_content_item_refs` is the derivation scope. A Requirement references CCIs from exactly one Domain. Forward-compatible with whole-row (D1b): the Stage 4 `domain_refs` intersection (MD-2) is general, so a later switch changes only the Stage 2 loop boundary.

**MD-2 — `domain_refs` DM-derived (realises Row 3 §4 Stage 4 / D2).** The AI never proposes `domain_refs`. Stage 4 computes, per Requirement, the set of active Domains whose membership intersects the Requirement's `cci_refs`. Guarantees the ledger's resolution and row-consistency rules by construction. Under MD-1 the intersection yields one Domain; written generally regardless. Empty result → fail closed (§4.4.2).

**MD-3 — Two-part input hash (realises Row 3 §6 / D3, resolves OQ-3d-01).** `requirement_input_hash = SHA-256("CCI:" + "|".join(sorted(ci_ids)) + "||DOM:" + "|".join(sorted(active_domain_ids)))`. The sorted active Domain-id list is also stored separately in `mechanism_data.domain_id_set` for the Domain-set-change comparison. A Pass 3c FullRerun (fresh domain_ids) changes the DOM portion → detected as change. A Domain-set change forces FullRerun (§4.1).

**MD-4 — Four re-run scenarios (realises Row 3 §6).** FirstRun / IdempotentRerun / IncrementalRerun / FullRerun, selected by hash comparison refined by the Domain-set rule. Same detection skeleton as the sibling §4.1.

**MD-5 — Type classification principle-based (realises Row 3 §4.1.1(d) / D4).** Enum enforced at the Pydantic parse boundary; value choice is IM, informed by the §5.4 reasoning block. No lookup table.

**MD-6 — Global `R###` allocation (realises Row 3 §5.4).** Single per-project sequence, never row-scoped, never reused (includes retired). See §5.3.

### 3.3 Large CCI set advisory threshold

Per-Domain derivation keeps per-call CCI counts small, so the sibling's whole-row large-set risk is largely mitigated. A `large_cci_set_advisory` fires if the **row's** total `cci_count_input > requirement_large_cci_set_advisory_threshold` (default 80) — a Practitioner density signal, not a chunking trigger (no chunking at v0.1). Per-Domain processing proceeds regardless.

---

## 4. Stage-by-Stage Implementation

### 4.1 Stage 1 — Pre-flight, CCI/Domain Assembly, Re-run Detection (DM)

Realises Row 3 §4 Stage 1 and §6.

**Precondition (hard stop):** Query AnalysisPass for `mechanism="DomainDerivation"`, `row_ref=current_row`, `project_id`. If absent or `execution_status="Failed"`: Pass 3d `execution_status="Failed"`, `failure_reason="Pass 3c prerequisite not met"`. An IdempotentRerun (Skipped) Pass 3c satisfies the gate if a prior Completed Pass 3c exists.

**CCI assembly:** `cell_content_item JOIN zachman_cell WHERE zachman_cell.row_target = str(current_row) AND project_id = :pid`. Record `cci_count_input`.

**Domain assembly:** `SELECT domain_id, name, description, cell_content_item_refs FROM domain WHERE project_id=:pid AND row_target=str(current_row) AND retired_at IS NULL`. Record `domain_count_input`.

**Zero-CCI early exit (realises Row 3 §3.1):** if `cci_count_input==0`: AnalysisPass `execution_status="CompletedWithWarnings"`, `execution_warnings += no_cci_input`. RequirementRegister `member_ids = query_all_active_requirement_ids(project_id)` — project-wide, all rows, `retired_at IS NULL`. **Do NOT empty the register.** Exit. (NQPS Row 4.)

**Pass 3c invariant guard (realises Row 3 §3.1):** if `cci_count_input>0 AND domain_count_input==0`: `execution_status="Failed"`, `failure_reason="Pass 3c invariant violated — CCIs exist but no active Domains cover them"`. Unreachable given VER-3c-05; asserted not silently patched.

**Large-set advisory:** if `cci_count_input > threshold`: `mechanism_data.large_cci_set_advisory=true`.

**Re-run detection (MD-3):** compute `current_hash`. Query most recent non-Failed Pass 3d AnalysisPass for this row/project.
- None → `FirstRun`.
- `current_hash == prior.mechanism_data.requirement_input_hash` → `IdempotentRerun`.
- Else:
  - If `sorted(active_domain_ids) != prior.mechanism_data.domain_id_set` → **`FullRerun`** (Domain-set change; per-Domain scoping invalidated).
  - Else (Domain set unchanged, CCI delta only):
    - `prior_cci_count = prior.mechanism_data.cci_count_input`. If `prior_cci_count==0` → treat as `FirstRun`.
    - `covered = query_covered_cci_ids_for_row(row, project_id)` — live query: `SELECT DISTINCT jsonb_array_elements_text(cci_refs) FROM requirement WHERE project_id=:pid AND row_target=:row AND retired_at IS NULL`.
    - `new_cci_count = len(eligible_ci_ids - covered)`.
    - If `new_cci_count / prior_cci_count >= requirement_rerun_threshold` → `FullRerun`; else `IncrementalRerun`.

**IdempotentRerun exit:** AnalysisPass `execution_status="Skipped"`, `mechanism_data.run_scenario="IdempotentRerun"`, `idempotent=true`, `requirement_input_hash=current_hash`, `ai_model_fingerprints=[]`. Existing Requirements and register unchanged. Exit.

**Error cases:** DB failure during assembly → `Failed`. CCI referencing a non-existent ZachmanCell → `execution_warnings += cci_referential_integrity_violation`; exclude; continue.

### 4.2 Stage 2 — Per-Domain AI Derivation Act (IM)

Realises Row 3 §4 Stage 2 and §4.1.2/§4.1.3.

**FirstRun / FullRerun (per-Domain loop — MD-1):** for each active Domain `d`:
- Expand `d.cell_content_item_refs`; assemble `domain_cci_set` = `[{ci_id, column, classification_type, description}]` joined from eligible CCIs.
- Invoke `requirement_derivation_prompt.py` with `row_ref`, `REQUIREMENT_ROW_GUIDANCE[str(row_ref)]` (§5.4), `domain={domain_id,name,description}`, `domain_cci_set`.
- Claude Sonnet (model per Row 4 Applied §4.5). Parse against `requirement_derivation_response_schema.py`. Parse failure → one retry, identical prompt. Second failure → log `domain_derivation_parse_failure` in `validation_failures`; skip Domain (its CCIs become orphans for CHK-3d-05). **All** Domains fail → `execution_status="Failed"`, `failure_reason="AI derivation parse failure for all Domains after retry"`.
- Tag each proposal with in-memory `source_domain_id` (not a Requirement attribute).

**IncrementalRerun:** reachable only when Domain set unchanged. For each Domain owning ≥1 new CCI: assemble existing Requirement summaries `{requirement_id, statement, requirement_type}` for that Domain and `new_domain_ccis` (the Domain's not-yet-covered CCIs). Invoke `requirement_incremental_prompt.py`. Parse against the incremental schema. One retry. Persistent failure → `execution_warnings += incremental_fallback_to_fullrerun`; re-invoke Stage 2 FullRerun path for the whole row.

**Fingerprinting:** one `ai_model_fingerprints` entry per call: `{stage:"stage2_domain_<domain_id>", model, input_tokens, output_tokens}`. Repair fingerprinted separately (`stage3_repair`).

**LPM:** prompt instructs the AI not to copy CCI description text verbatim into the statement. Automated verbatim detection not implemented at v0.1 (PLB-3d-04).

### 4.3 Stage 3 — Structural Validation (DM, with conditional IM repair)

Realises Row 3 §4 Stage 3. All in-memory except the repair prompt.

**CHK-3d-01 — No empty statement.** Empty/whitespace → reject; log in `validation_failures`.

**CHK-3d-02 — No empty cci_refs.** `len(cci_refs)==0` → reject; log.

**CHK-3d-03 — cci_refs ⊆ source Domain membership.** Strip refs not in the source Domain's membership; log stripped. If emptied → reject (as CHK-3d-02). Enforces MD-1.

**CHK-3d-04 — fit_criteria integrity.** Present-but-empty → strip, log `fit_criteria_empty_stripped`. `requirement_type=="Performance"` and fit_criteria absent → log `performance_missing_fit_criteria` (informational; PLB-3d-05).

**CHK-3d-05 — Non-Loss.** `orphaned = eligible_ci_ids - {ref for p in proposals for ref in p.cci_refs}`. If non-empty: invoke repair (IM sub-act). For each orphan resolve owning Domain(s) (non-empty by Pass 3c Non-Loss). Assemble `requirement_repair_prompt.py` with `orphaned_ccis=[{ci_id,column,classification_type,description,owning_domain_id,owning_domain_name}]` + REQUIREMENT_ROW_GUIDANCE. Parse against repair schema; one attempt (no retry). Tag repair proposals `source_domain_id=owning_domain_id`. Merge; recompute `orphaned`. Persistent orphan → record in `mechanism_data.orphaned_ccis`; `execution_status="CompletedWithWarnings"`; raise Concern (CN-NNN). `execution_warnings += chk3d05_repair_performed` / `chk3d05_repair_failed` as applicable.

**CHK-3d-06 — Failure path.** Proposal set empty after CHK-3d-01..03 **and** repair produced nothing → `execution_status="Failed"`, `failure_reason="No valid Requirement proposals survived validation"`.

**CHK-3d-07 — Exact-duplicate collapse.** Two proposals with identical `statement` (case-insensitive) **and** identical `cci_refs` set → collapse to first; log `duplicate_requirement_collapsed`. (No name-uniqueness analogue — Requirements have no unique name. Near-duplicates → PLB-3d-01.)

**CHK-3d-08 — Row-appropriate statement subject (decidable; realises Row 3 §4 Stage 3 / closes F81 detection).** For each surviving Requirement, test the statement's grammatical subject against the row's required subject (§5.4(a)). At Row 1 the subject must be the enterprise; a statement opening "The system shall…" (or otherwise system/component-subjected) at Row 1 is a mismatch. **Severity (resolves Row 3 OQ-3d-03): soft at v0.1** — a mismatch logs `subject_vocabulary_mismatch` in `mechanism_data.subject_vocabulary_flags` (`[{requirement_id_placeholder, row, detected_subject}]`) and surfaces via PLB-3d-02; it does NOT reject the Requirement or block production. Rationale: until §5.4 Row 1 guidance has run-time evidence of how often it holds, hard rejection risks discarding otherwise-valid Requirements over a fixable surface form. Revisit severity when Row 1 production data accrues. The check is implemented as a decidable detector (subject extraction is a closed test), consistent with classifying it CHK not PLB.

**ADVC-3d-01 — Requirement-per-Domain soft bounds.** Per source Domain, count surviving Requirements; `m = len(domain.cell_content_item_refs)`. Zero Requirements → manifests as orphans (CHK-3d-05). `> m` Requirements → log `requirement_count_advisory {domain_id, requirement_count, cci_count}` (PLB-3d-06). Informational; production proceeds.

### 4.4 Stage 4 — Entity Production and Ledger Commit (DM)

Realises Row 3 §4 Stage 4.

**4.4.1 requirement_id allocation.** `query_max_requirement_id(project_id)` including retired rows. Allocate forward from next `R###`. §5.3.

**4.4.2 domain_refs DM-derivation (MD-2).** Per surviving proposal: `domain_refs = sorted({d.domain_id for d in active_domains if set(proposal.cci_refs) & set(d.cell_content_item_refs)})`. Assert `len(domain_refs) >= 1` (guaranteed under MD-1 post-CHK-3d-03) and every referenced Domain `row_target == str(current_row)`. Empty result → fail closed: reject proposal, log `{check_id:"MD-2", detail:"domain_refs derivation empty"}` in `validation_failures`; re-run CHK-3d-05 on the reduced set.

**4.4.3 Requirement construction.** Build each Requirement: allocated `requirement_id`; `statement`; `requirement_type`; `row_target=str(current_row)`; `confidence`; `cci_refs`; derived `domain_refs`; optional `rationale`/`fit_criteria`/`verification_method`/`priority` where present; `answer_refs=[]`.

**4.4.4 FullRerun retirement (resolves Row 3 OQ-3d-04).** On FullRerun: set `retired_at=now()` on all active Requirements for the row before inserting the new set (soft-retire, not delete — preserves referential integrity for any downstream refs, consistent with the sibling OQ-3c-03 soft-delete). `query_max_requirement_id` includes retired; new ids continue forward. Build `retirement_mapping` (one per retired Requirement; `inferred_successor_requirement_id` populated if statement similarity ≥ 0.50 against a new Requirement).

**4.4.5 downstream_rerun_required.** If Phase 5/6/8 AnalysisPasses exist for this row and this run committed a non-trivial change (FullRerun, or Incremental that added/retired): `mechanism_data.downstream_rerun_required=true`. Orchestrator surfaces advisory; downstream NOT auto-triggered.

**4.4.6 Transaction.** Single transaction: insert (and on FullRerun retire) Requirements; replace `RequirementRegister.member_ids` with `query_all_active_requirement_ids(project_id)` (project-wide, all rows, active); write the AnalysisPass. On rollback: `execution_status="Failed"`; pre-run state preserved.

**4.4.7 execution_status.** `Completed` unless: persistent orphan (CHK-3d-05) → `CompletedWithWarnings`; `incremental_fallback_to_fullrerun` logged → `CompletedWithWarnings`; an earlier Failed condition fired → `Failed`; IdempotentRerun → `Skipped`. Informational advisories alone (including `subject_vocabulary_mismatch`) do not change status.

---

## 5. Schema and Validation

### 5.1 SQLAlchemy / Pydantic models and Database DDL

**`requirement` table:**

| Column | Type | Constraint |
|---|---|---|
| `requirement_id` | VARCHAR(8) | PK component; `^R\d{3}$` |
| `project_id` | VARCHAR/UUID | FK → project; PK component |
| `statement` | TEXT | NOT NULL; CHECK length > 0 |
| `requirement_type` | VARCHAR(16) | NOT NULL; CHECK IN ('Functional','Constraint','Performance','Suitability','Non-Functional') |
| `row_target` | VARCHAR(1) | NOT NULL; CHECK IN ('1','2','3','4','5','6') |
| `rationale` | TEXT | NULL |
| `cci_refs` | JSONB | NOT NULL; CHECK jsonb_array_length >= 1 |
| `domain_refs` | JSONB | NOT NULL; CHECK jsonb_array_length >= 1 |
| `fit_criteria` | TEXT | NULL; CHECK (fit_criteria IS NULL OR length(fit_criteria) > 0) |
| `verification_method` | VARCHAR(16) | NULL; CHECK IN ('Test','Analysis','Inspection','Demonstration') |
| `priority` | VARCHAR(8) | NULL; CHECK IN ('High','Medium','Low') |
| `answer_refs` | JSONB | NOT NULL DEFAULT '[]' |
| `confidence` | DOUBLE PRECISION | NOT NULL; CHECK 0.0 <= confidence <= 1.0 |
| `retired_at` | TIMESTAMPTZ | NULL (soft-delete for FullRerun) |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() |

`cci_refs`/`domain_refs`/`answer_refs` are JSONB arrays on the row (same JSONB-array-on-row convention as the sibling `cell_content_item_refs`; no join table). `retired_at` mirrors the `domain` table.

**`requirement_register`:** one seeded row per project (migration seeds it): `register_id` PK, `project_id`, `register_type='Requirement'`, `member_ids` JSONB, `completeness_rule` TEXT, `confidence` DOUBLE PRECISION.

**Ledger normative rules (transcribed v2.12, all enforced):** `requirement_id` unique and `^R\d{3}$`; `statement` non-empty; `cci_refs` non-empty; `domain_refs` ≥1 referencing existing Domain; if `fit_criteria` present, non-empty; `requirement_type` in enum; Performance SHOULD carry `fit_criteria`; `row_target` in "1".."6"; `row_target` equals row of every referenced CCI and Domain; `confidence` 0.0..1.0. Exactly one RequirementRegister; `member_ids` contains all `requirement_id`.

### 5.2 AI response schemas (Pydantic)

**`requirement_derivation_response_schema.py` — primary (FirstRun / FullRerun):**

```
Response root: List[RequirementProposal]
RequirementProposal:
  statement:            str                 (minLength=1)
  requirement_type:     Literal["Functional","Constraint","Performance","Suitability","Non-Functional"]
  cci_refs:             List[str]           (minItems=1)
  rationale:            Optional[str]
  fit_criteria:         Optional[str]
  verification_method:  Optional[Literal["Test","Analysis","Inspection","Demonstration"]]
  priority:             Optional[Literal["High","Medium","Low"]]
  confidence:           float               (0.0..1.0)
```
The AI does NOT return `requirement_id`, `row_target`, `domain_refs`, or `answer_refs` (Stage 4 / deferred). Enum enforced at parse (MD-5).

**`requirement_incremental_response_schema.py` — IncrementalRerun:** **IMPORTANT — DISTINCT CLASS** `IncrementalRequirementProposal`. Same field shape; do NOT alias the primary class. Covers only `new_domain_ccis`; refs outside the new-CCI set logged `incremental_ref_outside_new_set`.

**`requirement_repair_response_schema.py` — repair:** **IMPORTANT — DISTINCT CLASS** `RepairRequirementProposal`. Same field shape; every proposal covers ≥1 orphaned ci_id, scoped to one owning Domain. The three classes handle different operations and MUST be separate (same discipline as the sibling §5.2 distinct-schema warning).

### 5.3 Identifier conventions

- Requirement `R###` — global per-project sequence, zero-padded 3 digits, allocated Stage 4.4.1, never reused (includes retired). **Scale ceiling (resolves Row 3 OQ-3d-05):** 999 ids per project including retired. If a project exceeds 800 allocated ids, raise a tracker finding for a 4-digit format (R####). Same caveat as `domain_id`.
- RequirementRegister: one per project; `register_id` seeded by migration.
- AnalysisPass: `P###` via the common writer utility.

### 5.4 REQUIREMENT_ROW_GUIDANCE — prompt constants

Realises Row 3 §4.1.1. **DISTINCT from the domain ROW_GUIDANCE** (decision B): that governs domain naming/grouping; this governs requirement-statement formulation. Held in `prompts/requirement_row_guidance.py`, injected by `REQUIREMENT_ROW_GUIDANCE[str(row_ref)]` into the derivation, incremental, and repair prompts. Principle-based, not pattern-based.

**Row 1 is fully authored (validated against PMT Row 1 / NQPS Row 1). Rows 2–6 are short-phrase stubs pending their own validation cycles** — the same staged approach taken for the domain ROW_GUIDANCE (Row 1, then Row 2, then Rows 3–5 across three iterations).

```
REQUIREMENT_ROW_GUIDANCE = {
    "1": """
## Row 1 — Planner / Scope Layer — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the enterprise scope level — the view of
a senior executive or board member. Each requirement expresses something the enterprise
commits to, is accountable for, or is constrained by — without reference to how any
system works.

### Statement subject (REQUIRED)
Every Row 1 requirement statement takes THE ENTERPRISE as its subject:
  "The enterprise shall ..."
Do NOT write "The system shall ..." at Row 1 — that is Row 2+ vocabulary and describes
a system, not an enterprise commitment.

This holds for COMPLIANCE, LEGISLATIVE, and REGULATORY obligations, which otherwise tend
to attract conventional system-requirements phrasing. Write:
  "The enterprise shall comply with applicable legislative obligations."
NEVER:
  "The system shall comply with applicable legislative obligations."
If the source content is a regulatory or compliance constraint, the enterprise is still
the accountable subject — not a system.

### Normative form and atomicity
- Use the normative "shall". One obligation per statement.
- If a statement would join two distinct obligations with "and" / "," apply the two-step
  test: (1) is there a single obligation that subsumes both? Use it. (2) If not, split
  into two requirements. (Requirement-level analogue of the domain "and" test.)
  Example: "shall determine and present aggregate earnings" is two acts (determine;
  present) — prefer one obligation, or split.

### Statement vocabulary
Row 1 statements use enterprise-commitment verbs:
  Appropriate: recognise, establish, maintain, provide, govern, ensure, comply, commit,
               be accountable for, be entitled to, enable (at enterprise scope)
  Avoid: calculate, display, track, store, retrieve, retain, generate, manage, process
         (these describe system functions — they belong at Row 2 or below). "retain" in
         particular is storage vocabulary — say "maintain records" / "be accountable for"
         at Row 1.

### requirement_type reasoning (principle-based — choose, do not pattern-match)
Weigh the source CCIs' Zachman columns and content against the row's abstraction level:
- Why-column / motivation / rule / policy / commitment content → lean Constraint.
- How / What / When / capability / function content → lean Functional.
- Content expressing a measurable threshold, rate, latency, or capacity → Performance
  (and the statement SHOULD carry fit_criteria).
- Content expressing a quality attribute (usability, maintainability, portability) →
  Suitability or Non-Functional per the attribute.
These are reasoning signals, not a lookup table. A genuinely ambiguous obligation may
read as either Constraint or Functional — choose the dominant force; do not force a
distribution.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: include only when the content gives a measurable acceptance basis.
- verification_method (Test/Analysis/Inspection/Demonstration): include only when a
  natural method exists. An abstract enterprise constraint (e.g. "support charitable
  responsibility obligations") may have NO natural verification method at Row 1 — OMIT
  the field rather than guessing. Omission is correct, not a defect.
- priority (High/Medium/Low): include only when the source content supports a relative
  priority judgement. Do NOT default every requirement to High. If the content gives no
  basis, omit.

### What NOT to do
- Do NOT introduce actors, behaviours, or constraints not present in the source CCIs.
- Do NOT reproduce CCI description text verbatim as the statement — derive a normative
  statement from it.
- Do NOT produce one thin requirement per CCI mechanically; consolidate where CCIs
  express one obligation, split where one CCI carries two.
""",

    # Rows 2–6: short-phrase stubs pending per-row requirement-derivation validation cycles.
    # Each will be expanded to a full block (subject / atomicity / vocabulary / type-reasoning /
    # optional-field policy) after that row has run-time evidence — same staged approach as the
    # domain ROW_GUIDANCE. The prompt template handles both the full block and the short phrase.
    "2": "Business conceptual level — statements subjected to the enterprise/business or a named "
         "business actor; business-process and rule vocabulary; no implementation verbs. "
         "[Full block pending Row 2 requirement-derivation validation.]",
    "3": "Logical design level — statements expressed as logical system capability; logical-design "
         "vocabulary (logical structure, behaviour, state, interaction); technology-agnostic, no "
         "physical/implementation vocabulary. [Full block pending Row 3 requirement-derivation validation.]",
    "4": "Physical builder level — statements subjected to the system or a named component; specific "
         "technology and component vocabulary appropriate. [Full block pending Row 4 requirement-derivation validation.]",
    "5": "Detailed design level — statements at algorithm/format/configuration detail. "
         "[Full block pending Row 5 requirement-derivation validation.]",
    "6": "Operational level — statements covering runtime procedures and user/operator interactions. "
         "[Short phrase — operational content is rare in source documents.]",
}
```

The prompt template accesses `REQUIREMENT_ROW_GUIDANCE[str(row_ref)]` and injects the full block (Row 1) or short phrase (Rows 2–6) as a prompt section, exactly as the domain ROW_GUIDANCE template does.

---

## 6. Mode Discipline Realisation

Mode-discipline decorator pattern (Row 4 Applied §4.7), identical structure to the sibling §6.

| Stage / Sub-act | Declared mode | Constraint | AnalysisPass record |
|---|---|---|---|
| Stage 1 — Pre-flight | DM | No AI calls | `mode_active:["DM"]` |
| Stage 2 — Per-Domain derivation | IM | AI call per Domain; LPM on CCI text | `mode_active:["IM"]`; one fingerprint per Domain |
| Stage 2 — Retry | IM | Second AI call; same constraint | Retry fingerprint appended |
| Stage 3 — Structural checks (CHK-3d-01..04,06,07,08; ADVC-3d-01) | DM | No AI calls (except repair) | `mode_active:["DM"]` |
| Stage 3 — Non-Loss repair (conditional) | IM | AI call; `repair_prompt_issued=true` | `stage3_repair` fingerprint |
| Stage 4 — Entity production | DM | No AI calls; domain_refs derivation + ledger write | `mode_active:["DM"]` |

`declared_transformation_modes=["IM","DM"]`; primary `mode_active="IM"`. **Do NOT record `mode_active:"LPM"`** — LPM is a preservation constraint, not a transformation mode (carry forward the sibling's PMT build correction). Mode violations → `mechanism_data.mode_violations`; `execution_status="CompletedWithWarnings"`.

---

## 7. Audit Trail Population

AnalysisPass `outputs` for `mechanism="RequirementDerivation"`. All fields required; zero-value arrays `[]`. **`mechanism_data` naming (resolves Row 3 OQ-3d-02): this spec adopts the sibling's `mechanism_data` convention** — not `requirement_data` — for consistency with the Domain Derivation spec and with the existing production run files, which already emit `mechanism_data`. `execution_warnings` is a **standard top-level AnalysisPass field**, not nested in `mechanism_data` (same as the sibling §7).

`execution_warnings` types: `no_cci_input` (§4.1 → CompletedWithWarnings); `cci_referential_integrity_violation` (info); `incremental_fallback_to_fullrerun` (→ CompletedWithWarnings); `fit_criteria_empty_stripped`, `performance_missing_fit_criteria`, `duplicate_requirement_collapsed`, `requirement_count_advisory`, `incremental_ref_outside_new_set`, `chk3d05_repair_performed`, `chk3d05_repair_failed`, `subject_vocabulary_mismatch` (info).

```jsonc
{
  "mechanism_data": {
    // --- Stage 1 ---
    "run_scenario":              "FirstRun",        // one of four scenario names
    "requirement_input_hash":    "<sha256-hex>",    // two-part hash (CCI-ids + active Domain-ids), MD-3
    "domain_id_set":             ["D001","D002"],   // sorted active Domain-ids at run time (Domain-set comparison)
    "cci_count_input":           7,                 // 0 on zero-CCI exit
    "domain_count_input":        3,
    "large_cci_set_advisory":    false,
    "idempotent":                false,             // true on IdempotentRerun only

    // --- Stage 3 ---
    "repair_prompt_issued":      false,
    "orphaned_ccis":             [],                // persistent orphans after repair
    "validation_failures":       [],                // [{check_id, source_domain_id, detail}]
    "duplicate_requirements_collapsed": [],         // [{kept_statement, collapsed_count}]
    "subject_vocabulary_flags":  [],                // [{requirement_id, row, detected_subject}] — CHK-3d-08

    // --- Stage 4 ---
    "requirement_count_produced": 5,
    "requirement_count_retired":  0,                // non-zero on FullRerun only
    "requirement_type_distribution": {
      "Functional": 3, "Constraint": 2, "Performance": 0, "Suitability": 0, "Non-Functional": 0
    },
    "requirements_produced": [
      { "requirement_id": "R001", "requirement_type": "Functional",
        "cci_ref_count": 2, "domain_refs": ["D001"] }
    ],
    "downstream_rerun_required": false,
    "retirement_mapping":        [],                // [{old_requirement_id, inferred_successor_requirement_id}]

    // --- Mode discipline ---
    "mode_violations":           [],

    // --- AI fingerprints (all IM calls this run) ---
    "ai_model_fingerprints": [
      { "stage": "stage2_domain_D001", "model": "claude-sonnet-4-20250514",
        "input_tokens": 0, "output_tokens": 0 }
    ]
  }
}
```

`ai_model_fingerprints` accumulates every IM call: each Stage 2 per-Domain call, any retry, the Stage 3 repair. On IdempotentRerun: `[]` and `idempotent=true`. `row_ref` is set both top-level on the AnalysisPass and inside `mechanism_data` (sibling convention). VER-3d-08 checks `mechanism_data` completeness; `execution_warnings` is verified by the common AnalysisPass schema validator.

---

## 8. Verification Criteria

### 8.1 Decidable criteria (automated — pytest)

In `tests/test_requirement_derivation.py`, Neon test DB with transaction-rollback isolation (same pattern as `tests/test_domain_derivation.py`). Realises Row 3 §8.1.

| ID | Criterion | pytest assertion |
|---|---|---|
| **VER-3d-01** | All `requirement_id` match `^R\d{3}$` | `re.fullmatch` all in project |
| **VER-3d-02** | All `requirement_id` unique (active + retired) | `len(set(ids))==len(ids)` |
| **VER-3d-03** | Non-empty `statement`; ≥1 `cci_refs` | `len(statement)>0` and `jsonb_array_length(cci_refs)>=1` |
| **VER-3d-04** | `cci_refs` resolve to CCIs with matching `row_target` | expand; JOIN `cell_content_item → zachman_cell`; assert row match |
| **VER-3d-05** | Non-Loss: every eligible CCI in ≥1 Requirement | union of `cci_refs` ⊇ eligible set for the row |
| **VER-3d-06** | RequirementRegister `member_ids` == active set (all rows) | set equality, `retired_at IS NULL`, no row filter; ≥2 rows in integration test |
| **VER-3d-07** | AnalysisPass `mechanism="RequirementDerivation"`, `row_ref` exists | presence query |
| **VER-3d-08** | `mechanism_data` present; required fields non-null | schema validation against §7 |
| **VER-3d-09** | All `requirement_type` in enum | membership check |
| **VER-3d-10** | `domain_refs` ≥1; resolve to existing Domains with matching `row_target` | expand; JOIN `domain`; assert exists + row match |
| **VER-3d-11** | IdempotentRerun: set unchanged; `idempotent==true`; status=Skipped | before/after + flag |
| **VER-3d-12** | FullRerun: `requirement_count_retired` == prior active count | query prior; assert equality |
| **VER-3d-13** | `requirement_count_produced >= 1` when `cci_count_input > 0` | conditional |
| **VER-3d-14** | No `fit_criteria` present-but-empty | `fit_criteria IS NULL OR length>0` |

(CHK-3d-08 subject mismatch is recorded in `subject_vocabulary_flags` and reviewed via PLB-3d-02; it is not a VER gate at v0.1 per its soft severity.)

### 8.2 Plausibility checklist for Practitioner review

Realises Row 3 §8.2.

1. **PLB-3d-01 — Statement atomicity.** One obligation per statement; compound "and" split. Near-duplicates (not collapsed by CHK-3d-07) flagged.
2. **PLB-3d-02 — Row-appropriate abstraction.** Subject and vocabulary match the row. Review `subject_vocabulary_flags` (CHK-3d-08) — any Row 1 statement subjected to "the system" is an abstraction failure to correct. Implementation verbs (calculate, store, retain) at Row 1/2 are PLB failures.
3. **PLB-3d-03 — requirement_type plausibility.** Type matches source CCI columns. Review `requirement_type_distribution` for anomalies. Boundary-case type variance across runs is accepted (Tracker F81 related item).
4. **PLB-3d-04 — No inferred content (LPM).** No actor/behaviour/constraint absent from source CCIs; no verbatim CCI text.
5. **PLB-3d-05 — Performance fit_criteria.** Every Performance Requirement carries meaningful `fit_criteria`; complete where `performance_missing_fit_criteria` fired.
6. **PLB-3d-06 — Requirement-per-Domain balance.** Where `requirement_count_advisory` fired, review for over-decomposition (thin near-passthrough requirements) or genuine fan-out.

---

## 9. Test Fixtures

Seven fixtures in `tests/test_requirement_derivation.py`; AI stubs via monkeypatch (sibling §9 pattern). Realises Row 3 §9. Worked examples use the rows with production evidence (**PMT Row 1, NQPS Row 1**).

### 9.1 Fixture 1 — PMT Row 1: FirstRun happy path
**Test:** `test_pmt_row1_firstrun`. Setup: PMT Row 1 with Pass 3c Domains D001–D004 and their CCIs (18 CCIs). AI stub returns RequirementProposals per Domain.
**Assertions:** VER-3d-05 (all 18 CCIs covered); VER-3d-09; VER-3d-10 (each Requirement's `domain_refs` == source Domain); RequirementRegister populated.

### 9.2 Fixture 2 — NQPS Row 1: FirstRun constraint-heavy (and zero-CCI companion)
**Test:** `test_nqps_row1_firstrun`. Setup: NQPS Row 1 Domains D001–D006 + CCIs (34 CCIs, constraint-heavy).
**Assertions:** VER-3d-05; VER-3d-09 with Constraint present where warranted (type distribution not forced all-Functional); CHK-3d-08 clean (no "the system shall" at Row 1, including on the compliance Domain — the D005 case); optional fields omitted where content gives no natural value without that being a failure (the D005 verification_method/priority case). **Companion** (`test_nqps_row4_zero_cci`): NQPS Row 4 (zero CCIs) → `no_cci_input`, `CompletedWithWarnings`, RequirementRegister preserves other-row members, Stage 2 not invoked.

### 9.3 Fixture 3 — PMT Row 1: IdempotentRerun
**Test:** `test_pmt_row1_idempotent_rerun`. Re-invoke Fixture 1 with identical CCI and Domain sets.
**Assertions:** VER-3d-11; `run_scenario=="IdempotentRerun"`; Stage 2 stub `assert_not_called()`; `requirement_input_hash` matches prior.

### 9.4 Fixture 4 — PMT Row 1: IncrementalRerun (one new CCI)
**Test:** `test_pmt_row1_incremental_rerun`. Run Fixture 1; add one CCI to an existing Domain (Domain set unchanged → Incremental reachable). Incremental stub returns one proposal.
**Assertions:** `run_scenario=="IncrementalRerun"`; VER-3d-05 after delta; existing `requirement_id`s preserved; prior AnalysisPass unchanged.

### 9.5 Fixture 5 — Non-Loss repair: orphaned CCI recovered
**Test:** `test_noloss_repair_prompt_recovery`. PMT Row 1 FirstRun; primary stub omits one CCI. CHK-3d-05 detects 1 orphan; repair stub covers it.
**Assertions:** `repair_prompt_issued==true`; `orphaned_ccis==[]`; VER-3d-05 passes; `execution_status=="Completed"`; fingerprints include per-Domain entries plus `stage3_repair`.

### 9.6 Fixture 6 — Persistent orphan after repair failure
**Test:** `test_noloss_repair_persistent_orphan`. Primary stub omits one CCI; repair stub returns `[]`.
**Assertions:** `repair_prompt_issued==true`; `orphaned_ccis==[<ci_id>]`; `execution_status=="CompletedWithWarnings"`; VER-3d-05 asserted to FAIL here (the orphan is recorded); Concern CN-NNN exists.

### 9.7 Fixture 7 — FullRerun forced by Domain-set change
**Test:** `test_pmt_row1_fullrerun`. Run Fixture 1; simulate a Pass 3c FullRerun retiring D001–D004 and committing D005–D008 over the same CCIs (Domain-id set changed → MD-3 forces FullRerun). Invoke Pass 3d.
**Assertions:** `run_scenario=="FullRerun"`; prior Requirements `retired_at IS NOT NULL`; new ids from next `R###` (no reuse); VER-3d-12; VER-3d-05 on new set; `domain_refs` reference new Domain-ids; `downstream_rerun_required` reflects Phase 5/6 presence.

---

## 10. Edge Cases

Physical handling; logical disposition in Row 3 §10.

| Edge case | Handling |
|---|---|
| **Zero CCIs for the row** | Stage 1 early exit: `CompletedWithWarnings`, `no_cci_input`; RequirementRegister = project-wide active set (not emptied). Stage 2 not invoked. (NQPS Row 4.) |
| **CCIs exist but zero active Domains** | §4.1 invariant guard → `Failed`. Unreachable given VER-3c-05; asserted. |
| **Single CCI in a Domain** | One-CCI Domain → AI returns ≥1 Requirement covering it. |
| **Domain yields zero Requirements** | CCIs become orphans → CHK-3d-05 repair. Repair fails → persistent orphan, Concern raised. |
| **cci_refs outside source Domain** | Stripped by CHK-3d-03; emptied proposal rejected; orphans → CHK-3d-05. |
| **Row 1 statement subjected to "the system"** | CHK-3d-08 logs `subject_vocabulary_mismatch` (soft); PLB-3d-02 review. Prevention is §5.4 Row 1 subject discipline. |
| **Performance without fit_criteria** | `performance_missing_fit_criteria` (info); PLB-3d-05. |
| **fit_criteria present but empty** | Stripped (CHK-3d-04); `fit_criteria_empty_stripped`. |
| **Optional verification_method/priority omitted for abstract constraints** | Correct per §5.4(optional-field policy); not a failure. (NQPS D005.) |
| **Parse failure one Domain (others ok)** | Domain skipped; logged; its CCIs → CHK-3d-05. |
| **Parse failure all Domains after retry** | `Failed`. |
| **IncrementalRerun parse failure** | `incremental_fallback_to_fullrerun`; FullRerun path. If that also fails → `Failed`. |
| **Domain-id set changed since prior run** | FullRerun forced (MD-3) even if CCI set unchanged. |
| **FullRerun with Phase 5/6/8 complete** | `downstream_rerun_required=true`; not auto-triggered. |
| **Repair empty list** | Persistent orphan; `CompletedWithWarnings`; Concern; surviving Requirements committed. |
| **FullRerun retirement rollback** | Single transaction → no partial retirement; pre-run state; `Failed`. |
| **RequirementRegister seed missing** | `Failed`, `failure_reason="RequirementRegister not found — migration may not have run"`. |
| **Large CCI set (>80 for row)** | `large_cci_set_advisory`; per-Domain processing proceeds; no chunking at v0.1. |

---

## 11. Cross-Mechanism Interactions

### 11.1 Upstream

| Mechanism | What this mechanism receives | Dependency type |
|---|---|---|
| **Pass 3c — Domain Derivation** | Domain entities (with `cell_content_item_refs`) — per-Domain derivation scope and basis for DM-derived `domain_refs`. | Hard — orchestrator checks Pass 3c `execution_status ∈ {Completed, CompletedWithWarnings}` (Skipped Idempotent satisfies if a prior Completed exists). |
| **Pass 3b — CCI Construction** | CellContentItem rows — source content. | Transitive via Pass 3c; CCIs read directly for descriptions. |
| **Phase 2 — Mechanism Activation** | ProjectProfile — the two Pass 3d parameters. | Soft. |

### 11.2 Downstream

| Mechanism | What this mechanism produces | Dependency type |
|---|---|---|
| **Phase 5 — Cell Quality** | Requirement rows for quality assessment. | Analytical. |
| **Phase 6 / Phase 8 — Coverage** | Requirement rows (with `cci_refs`, `domain_refs`) as coverage inventory. | Analytical. |
| **Phase 10 — Gap/Question/Answer** | Populates `answer_refs`; may create Requirements via Answer resolution. | Writes `answer_refs`; not a Pass 3d concern at v0.1. |

### 11.3 Ledger coordination

Mechanisms coordinate via ledger reads, not direct calls (Row 4 Applied §4.11). Pass 3d reads CCIs and Domains; writes Requirements, RequirementRegister, AnalysisPass in one transaction. The orchestrator enforces sequencing by querying AnalysisPass records before invoking each mechanism. No mechanism imports another.

---

## 12. Build Notes

### 12.1 Tracker findings relevant to this build

| Finding | Status | Relevance |
|---|---|---|
| **F80** | Open | Consume Domains by `domain_id`, not name (MD-2). Derivation unaffected by cross-row name duplication. Presentation concern remains for review tooling. Stays Open. |
| **F81** | Open → Row 1 portion addressed | §5.4 REQUIREMENT_ROW_GUIDANCE["1"] (full) + CHK-3d-08 (soft) realise the Row 1 closure path. F81 stays Open until Rows 2–6 guidance is authored in their validation cycles; recommend annotating F81 "Row 1 closed; Rows 2–6 pending" at the next tracker increment. |

### 12.2 OQ resolutions committed at this spec

Resolving the open questions deferred by the Row 3 logical spec (Row 3 §12.2):

| OQ | Resolution |
|---|---|
| **OQ-3d-01** (re-run mechanics) | Two-part SHA-256 hash over sorted CCI-ids and sorted active Domain-ids; `domain_id_set` stored separately for Domain-set comparison; Domain-set change forces FullRerun (§4.1, MD-3). |
| **OQ-3d-02** (audit naming) | Adopt the sibling's `mechanism_data` convention (not `requirement_data`), matching Domain Derivation and the existing production run files (§7). |
| **OQ-3d-03** (CHK-3d-08 severity) | Soft at v0.1: log `subject_vocabulary_mismatch`, surface via PLB-3d-02, do not reject (§4.3 CHK-3d-08). Revisit when Row 1 production data accrues. |
| **OQ-3d-04** (retirement persistence) | Soft-retire via `retired_at` timestamp (not delete), consistent with sibling OQ-3c-03 (§4.4.4). |
| **OQ-3d-05** (id scale ceiling) | 999 ids per project incl. retired; raise a tracker finding for `R####` if a project exceeds 800 allocated (§5.3). |

### 12.4 v0.1 → v0.2 change detail

v0.1 was implemented and is the version behind the PMT Row 1 and NQPS Row 1 production runs reviewed during this design cycle. v0.2 does not change the implemented mechanism's runtime behaviour for the cases v0.1 already handled correctly; it re-frames the specification and adds the requirement-statement guidance and subject check that v0.1 lacked. Changes:

- **Re-framing (no behavioural change):** v0.1 was a standalone, row-agnostic physical spec naming the Pass 3c Domain Derivation spec as its authority. v0.2 establishes the Row 3 (logical) Requirement Derivation spec as the logical authority and the Row 4 Domain Derivation spec as the structural sibling, with section-level traces throughout. The four-stage flow, DDL, response schemas, and re-run mechanics are unchanged.
- **§5.4 REQUIREMENT_ROW_GUIDANCE (new):** v0.1 had a thin sketch of statement/type guidance. v0.2 introduces the full per-row guidance dict, distinct from the domain ROW_GUIDANCE (decision B), with Row 1 fully authored — carrying the statement-subject discipline ("The enterprise shall…", robust to compliance phrasing) that addresses the observed Row 1 subject leak (Tracker F81; NQPS Row 1 D005). This is the substantive behavioural addition: prompts built from v0.2 §5.4 will anchor the Row 1 subject where v0.1 did not.
- **CHK-3d-08 (new):** decidable row-subject check added to Stage 3, soft severity (records `subject_vocabulary_mismatch`, does not reject). No analogue in v0.1.
- **Optional-field policy (clarified):** §5.4 now states explicitly that `verification_method` and `priority` are populated when warranted and omitted otherwise — making the v0.1-observed ragged emission (NQPS D005) principled rather than accidental.
- **OQ resolutions (new):** §12.2 resolves OQ-3d-01..05 raised by the Row 3 logical spec — including adopting the `mechanism_data` audit naming (§7) that v0.1's implementation already emitted, now formally reconciled against the sibling convention.
- **Fixtures:** worked examples moved from PMT Row 2 / NQPS Row 3 (v0.1, illustrative) to PMT Row 1 / NQPS Row 1 (v0.2, the rows with production evidence), with Fixture 2 now explicitly exercising the D005 cases.

**Re-implementation impact:** the Row 1 statement-guidance and CHK-3d-08 are the parts requiring a code change from the v0.1 implementation. The rest is documentation re-framing. Re-running PMT Row 1 / NQPS Row 1 under v0.2 guidance is the validation step for the F81 Row 1 closure.

### 12.5 Replit Agent task structure

**Primary inputs:**
- This spec (Row 4 Requirement Derivation v0.2) — implementation authority (DDL §5.1, schemas §5.2, guidance §5.4)
- Row 3 Requirement Derivation v0.1 — logical authority (stage logic, VER/PLB intent)
- Row 4 Domain Derivation v0.24 — structural sibling (four-stage pattern, audit/fingerprint conventions)
- Row 4 Understanding §14 — framework (module structure, ProjectProfile params, VER→pytest, fixtures)

**Reference:** Row 4 Applied v0.2; Canonical Ledger v2.12; Segmentation spec v9.2.

**Build sequence:**
1. Alembic migration `add_requirement_tables` — `requirement` table + RequirementRegister seed (DDL §5.1).
2. Alembic migration `add_requirement_profile_params` — two ProjectProfile columns (Understanding §14.2).
3. `prompts/requirement_row_guidance.py` — REQUIREMENT_ROW_GUIDANCE (§5.4): Row 1 full, Rows 2–6 stubs.
4. `schemas/` — three DISTINCT response schemas (§5.2).
5. `prompts/` — three prompt templates injecting `REQUIREMENT_ROW_GUIDANCE[row]`.
6. `stage1_preflight.py` → `stage4_entity_production.py` and `__init__.py`.
7. `tests/test_requirement_derivation.py` — Fixtures 1–7 (§9); AI stubs via monkeypatch.
8. Migrations; pytest; verify VER-3d-01..14 on Fixtures 1, 2, 3, 4, 7; Fixtures 5/6 against their specific assertions.

**Deviations from the Domain Derivation sibling to watch:**
- Stage 2 is a **per-Domain loop**, not a single whole-row call.
- `domain_refs` is **DM-derived in Stage 4**, never AI-proposed — response schema omits it.
- Re-run hash is **two-part**; a Domain-set change forces FullRerun.
- **CHK-3d-08** (subject vocabulary) has no sibling analogue — soft severity at v0.1.
- **REQUIREMENT_ROW_GUIDANCE** is a separate dict from the domain ROW_GUIDANCE (decision B) — do not merge them.
- No name-uniqueness merge (no CHK-3c-03 analogue); CHK-3d-07 collapses only exact statement+cci_refs duplicates.
- Non-Loss repair derives a **covering Requirement** (not a Domain), scoped to the orphan's owning Domain.

---

## Document End

End of SysEngage Row 4 Mechanism: Requirement Derivation v0.2.

Physical realisation of the Row 3 (logical) Requirement Derivation spec. Aligned to the Row 4 Domain Derivation v0.24 structure. Row 1 REQUIREMENT_ROW_GUIDANCE fully authored and validated against PMT Row 1 / NQPS Row 1; Rows 2–6 stubbed pending their own validation cycles. OQ-3d-01..05 resolved (§12.2). F80 Open (domain_id consumption); F81 Row 1 portion addressed, Rows 2–6 pending.

Companion artefacts:
- SysEngage_Row_3_Mechanism_Requirement_Derivation_v0_1.md — logical authority
- SysEngage_Row_4_Domain_Derivation_v0_24.md — structural sibling
- SysEngage_Row_4_Understanding_v0_26.md §14 — implementation framework (structural index to this spec)
- SysEngage_Issues_Tracker_v0_52.md — F80, F81 disposition
- sysengage_minimal_ledger_spec_v2_12.md — canonical Requirement / RequirementRegister schema authority
