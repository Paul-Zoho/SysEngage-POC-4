# SysEngage Row 4 Mechanism: Requirement Derivation

**Implementation specification — depth tier (i)+**

Filename: SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_1.md

Version: 0.1 (Initial Pass 3d specification. Establishes Requirement Derivation as the fourth Phase 3 mechanism, consuming Pass 3c Domains and Pass 3b CCIs. Per-Domain Stage 2 derivation (D1a); deterministically derived `domain_refs` (D2); two-part re-run input hash over CCI-ids and active Domain-ids (D3); principle-based `requirement_type` guidance (D4); F80 logged, left open (D5).)

Date: 01 June 2026

**Purpose.** Implementation specification for the Requirement Derivation mechanism (Pass 3d). Derives canonical `Requirement` entities from the CellContentItems grouped by Pass 3c Domains, with full CCI traceability and deterministic Domain attribution. Architectural pattern is inherited wholesale from the Pass 3c Domain Derivation mechanism (four-stage, IM-primary, DM-envelope, LPM, four re-run scenarios, conditional repair prompt); this spec records only the Pass 3d-specific realisation of that pattern.

**Excludes.** Per Row 4 Understanding §14 (§8.1 discipline): NO pseudo-code, NO function signatures, NO code-level interface definitions in the Understanding. All implementation detail (stages, DDL, schemas, edge cases, OQ resolutions) lives in this spec and is not duplicated in the Understanding.

---

## 1. Mechanism Identification

| Attribute | Value |
|---|---|
| **Mechanism name** | Requirement Derivation |
| **Architectural authority reference** | SysEngage_Row_4_Mechanism_Domain_Derivation_v0_24.md — all sections. Pass 3d reuses the Pass 3c four-stage architecture, re-run scenario detection, repair-prompt-as-IM-sub-act pattern, soft-delete retirement, mode discipline, and audit-trail conventions. Where this spec is silent on a shared pattern, the Pass 3c spec governs. |
| **Operational location** | Phase 3 Pass 3d. Executes after Pass 3c (Domain Derivation) completes for the row; before Phase 5 (Cell Quality) and Phase 6/8 (Coverage Analysis). Four stages: Stage 1 (pre-flight + CCI/Domain assembly + re-run scenario detection, DM), Stage 2 (per-Domain AI derivation act, IM), Stage 3 (structural validation + conditional repair, DM + IM conditional), Stage 4 (entity production + ledger commit, DM). |
| **Mechanism class** | AI-involving. IM-primary (Stage 2 per-Domain requirement derivation; Stage 3 conditional Non-Loss repair prompt). DM-envelope (Stage 1 pre-flight; Stage 3 structural checks; Stage 4 entity production, `domain_refs` derivation, ledger write). LPM preservation constraint throughout — CCI descriptions are read as context, not rewritten verbatim into requirement statements. |
| **Module location** | `mechanisms/requirement_derivation/` directory. See §3.1 for file structure. |
| **Row applicability** | Row-sequential. Runs once per active row. Reads only the CCIs and Domains of the current row. |
| **Mechanism Stakeholder** | None. SH001 covers structural review. SG-01 covers Practitioner quality review (plausibility checklist §8.2). SG-03 carries execution attribution via AnalysisPass. |

---

## 2. Cross-References

| Source | Reference | What this provides |
|---|---|---|
| **Pass 3c Mechanism Spec v0.24** | All sections | Architectural authority: four-stage pass structure, re-run scenario detection (§4.1), repair prompt pattern (§4.3), soft-delete retirement (§4.4, §12.2 OQ-3c-03), mode discipline (§6), audit-trail conventions (§7), fixture and AI-stub patterns (§9), `query_committed_*` live-query convention. Pass 3d substitutes "Requirement" for "Domain" throughout and adds the Pass 3d-specific differences recorded in §3.2 below. |
| **Row 4 Understanding v0.25** | §14 | Pass 3d implementation framework: module structure, ProjectProfile parameters (two), VER criteria → pytest mapping, fixture table, Replit Agent handoff. Structural index only — no implementation detail. |
| **Row 4 Applied v0.2** | All sections | Common architectural commitments: Python 3.12+, FastAPI, Neon PostgreSQL via SQLAlchemy + Alembic, Pydantic v2, Claude Sonnet via Anthropic API, pytest, transactional discipline, mode discipline decorator. |
| **Canonical Ledger v2.12** | Requirement, RequirementRegister, AnalysisPass element types | Authoritative schemas. Requirement has eight required attributes (`requirement_id`, `statement`, `requirement_type`, `row_target`, `confidence`, `cci_refs`, `domain_refs`) and five optional (`rationale`, `fit_criteria`, `verification_method`, `priority`, `answer_refs`). Normative rules transcribed verbatim in §5.1. |
| **Segmentation spec v9.2** | Requirement statement formulation | Statement discipline applied at the prompt level: atomic, single intent, normative phrasing, no inferred actors or behaviours beyond the source CCIs. See §5.4. |
| **sys_engage_specification_v2.md** | §Phase 3 Requirement Generation, §ADR sections | POC source for `requirement_type` classification reasoning signals and Zachman-column→type mapping. Read as principle, not pattern (D4) — extracted into §5.4 as reasoning guidance, not as a lookup table. POC fields conflicting with ledger v2.12 are superseded by the ledger schema. |
| **Tracker v0.51** | F80, F66 | F80 (Open): cross-row Domain name duplication — Pass 3d consumes Domains by `domain_id`, not name (§3.2 MD-2). Logged, left open per D5; see §12.1. F66: status-summary bookkeeping reconcile noted; no implementation impact (§12.1). |

---

## 3. Architectural Approach

### 3.1 Module structure

```
mechanisms/requirement_derivation/
  __init__.py                                  # Orchestration entry point — Stages 1–4 in sequence
  stage1_preflight.py                          # DM: Pass 3c prerequisite check; eligible CCI + active Domain
                                               #     assembly; two-part re-run hash; scenario detection; idempotent exit
  stage2_ai_derivation.py                      # IM: per-Domain requirement derivation loop; Pydantic validation at
                                               #     boundary; one retry on parse failure; IncrementalRerun branch
  stage3_structural_validation.py              # DM: CHK-3d-01..07; ADVC-3d-01 requirement-per-domain advisory;
                                               #     Non-Loss repair prompt dispatch (IM conditional)
  stage4_entity_production.py                  # DM: requirement_id allocation; Requirement construction;
                                               #     domain_refs DM-derivation; FullRerun retirement; ledger
                                               #     transaction; RequirementRegister replace; AnalysisPass write
  prompts/
    requirement_derivation_prompt.py           # Template: FirstRun / FullRerun — per-Domain CCI set → requirements
    requirement_incremental_prompt.py          # Template: IncrementalRerun — new CCIs vs existing Domain requirements
    requirement_repair_prompt.py               # Template: CHK-3d-05 Non-Loss repair — orphaned CCIs to be covered
  schemas/
    requirement_derivation_response_schema.py  # Pydantic: primary derivation response (statement, requirement_type,
                                               #           cci_refs, rationale?, fit_criteria?, verification_method?,
                                               #           priority?, confidence)
    requirement_incremental_response_schema.py # Pydantic: IncrementalRerun response. DISTINCT class — must NOT be
                                               #           shared with the primary schema. See §5.2 IMPORTANT warning.
    requirement_repair_response_schema.py      # Pydantic: CHK-3d-05 repair response (proposals covering orphaned
                                               #           ci_ids). DISTINCT class — see §5.2 IMPORTANT warning.
```

### 3.2 Major design decisions

**MD-1 — Per-Domain Stage 2 (D1a).** The AI derivation act is scoped to one Domain at a time. Each active Domain's `cell_content_item_refs` set is passed to a single AI call, which proposes the Requirements derived from that Domain's CCIs. This gives the AI a bounded, coherent concern and keeps prompts small. A Requirement derived in this mode references CCIs from exactly one Domain; cross-Domain Requirements are not produced at v0.1. The architecture is forward-compatible with whole-row derivation (D1b): Stage 4 `domain_refs` derivation (MD-2) is a general intersection lookup that produces correct results under either mode, so switching to D1b later requires changing only Stage 2's loop boundary, not Stage 4.

**MD-2 — `domain_refs` is DM-derived, not AI-proposed (D2).** The AI never proposes `domain_refs`. Stage 4 computes, for each Requirement, the set of active Domain `domain_id`s whose `cell_content_item_refs` intersect that Requirement's `cci_refs`. This guarantees by construction the ledger's normative rules — `domain_refs` resolves to existing Domains and `row_target` matches every referenced Domain — and eliminates the AI error surface of proposing dangling or mismatched Domain references. It also directly satisfies F80: Pass 3d consumes Domains by `domain_id`, never by `name`. Under MD-1 the intersection yields exactly one Domain per Requirement; the lookup is written generally regardless.

**MD-3 — Two-part re-run input hash (D3).** Pass 3c keys re-run detection on the sorted CCI-id set alone. Pass 3d Requirements depend on **both** CCIs and Domains, so the input hash covers both: `requirement_input_hash = SHA-256("CCI:" + "|".join(sorted(ci_ids)) + "||DOM:" + "|".join(sorted(active_domain_ids)))`. A Pass 3c FullRerun that retires Domains and allocates fresh `domain_id`s changes the DOM portion even when the CCI set is unchanged, so it is correctly detected as a change rather than read as Idempotent. Scenario classification adds one rule beyond the Pass 3c logic: **a change to the active Domain-id set forces FullRerun** (a Domain reshuffle invalidates per-Domain scoping; partial re-derivation is unsafe). IncrementalRerun is reachable only when the Domain-id set is unchanged and the CCI delta is below threshold. See §4.1. This decision affects Pass 3d only — Pass 3c writes its `retired_at` soft-delete state regardless, and Pass 3d reads it; no Pass 3c change is required.

**MD-4 — Four re-run scenarios.** FirstRun / IdempotentRerun / IncrementalRerun / FullRerun, selected by `requirement_input_hash` comparison against the prior Pass 3d AnalysisPass, refined by the Domain-set rule of MD-3. Same detection skeleton as Pass 3c §4.1.

**MD-5 — `requirement_type` classification is principle-based (D4).** The five-value enum (`Functional | Constraint | Performance | Suitability | Non-Functional`) is assigned by the AI using reasoning guidance about Zachman column semantics and abstraction level, not a transcribed POC lookup table. The enum membership is enforced deterministically at the Pydantic parse boundary; the *choice* of value is an IM responsibility informed by §5.4 guidance.

**MD-6 — Global `R###` allocation.** `requirement_id` is allocated from a single per-project sequence (R001, R002, …), not scoped by row — identical to the `domain_id` (D###) convention. Retired ids are not reused. See §5.3.

### 3.3 Large CCI set advisory threshold

Per-Domain derivation makes the per-call CCI count small (a Domain's membership), so the Pass 3c whole-row large-set risk is largely mitigated. A `large_cci_set_advisory` still fires if the **row's** total `cci_count_input > requirement_large_cci_set_advisory_threshold` (default 80) — not as a chunking trigger (none is implemented at v0.1) but as a Practitioner signal that the row is unusually dense. Processing proceeds per-Domain regardless.

---

## 4. Stage-by-Stage Implementation

### 4.1 Stage 1 — Pre-flight, CCI/Domain Assembly, Re-run Detection (DM)

**Precondition check (hard stop):**
Query `AnalysisPass` for `mechanism="DomainDerivation"` AND `row_ref = current_row` AND `project_id = current_project`. If not found, or `execution_status = "Failed"`: set `execution_status = "Failed"` on the Pass 3d AnalysisPass; `failure_reason = "Pass 3c prerequisite not met — no completed Domain Derivation pass found for this row"`. Exit. (An IdempotentRerun Pass 3c with `execution_status = "Completed"` satisfies the gate — same rule as the Pass 3c → Pass 3b gate.)

**CCI and Domain assembly:**
- Eligible CCIs: query `cell_content_item JOIN zachman_cell WHERE zachman_cell.row_target = str(current_row) AND cell_content_item.project_id = current_project`. Record `cci_count_input = len(eligible_ccis)`.
- Active Domains: query `SELECT domain_id, name, description, cell_content_item_refs FROM domain WHERE project_id = :pid AND row_target = str(current_row) AND retired_at IS NULL`. Record `domain_count_input = len(active_domains)`.

**Zero-CCI early exit:**
If `cci_count_input == 0`: write AnalysisPass with `execution_status = "CompletedWithWarnings"`, `mechanism_data.run_scenario` as applicable, warning `no_cci_input`. Update RequirementRegister with `member_ids = query_all_active_requirement_ids(project_id)` — the project-wide active Requirement set (`SELECT requirement_id FROM requirement WHERE project_id = :pid AND retired_at IS NULL`, no `row_target` filter). **Do NOT write `member_ids = []` unconditionally** — Requirements from other rows must be preserved (same register-preservation rule as Pass 3c §4.1 DomainRegister). Exit. (NQPS Row 4, zero CCIs, exercises this path — see Fixture 2 note.)

**Pass 3c invariant guard:**
If `cci_count_input > 0 AND domain_count_input == 0`: set `execution_status = "Failed"`, `failure_reason = "Pass 3c invariant violated — CCIs exist for row but no active Domains cover them"`. This should be unreachable given Pass 3c Non-Loss (VER-3c-05), but is asserted as a referential safety guard rather than silently producing orphan Requirements. Exit.

**Large-set advisory:**
If `cci_count_input > requirement_large_cci_set_advisory_threshold`: set `mechanism_data.large_cci_set_advisory = true`.

**Re-run scenario detection (two-part hash — MD-3):**
Compute `current_hash` per MD-3. Query most recent non-Failed Pass 3d AnalysisPass for this `row_ref` and `project_id`. If none: `scenario = "FirstRun"`. If found:
- `prior_hash = prior_pass.outputs["mechanism_data"]["requirement_input_hash"]`
- If `current_hash == prior_hash`: `scenario = "IdempotentRerun"`.
- Else:
  - `prior_domain_ids = prior_pass.outputs["mechanism_data"]["domain_id_set"]` (the sorted active Domain-id list stored on the prior run).
  - **Domain-set rule (MD-3):** if `sorted(active_domain_ids) != prior_domain_ids`: `scenario = "FullRerun"`. A change to the Domain set requires full re-derivation under per-Domain scoping.
  - Else (Domain set unchanged; CCI delta only):
    - `prior_cci_count = prior_pass.outputs["mechanism_data"]["cci_count_input"]`.
    - **Zero-division guard:** if `prior_cci_count == 0` (prior run was a `no_cci_input` exit): treat as `"FirstRun"`.
    - Otherwise call `query_covered_cci_ids_for_row(row_ref, project_id)` — a live query returning the ci_ids already covered by active Requirements for this row: `SELECT DISTINCT jsonb_array_elements_text(cci_refs) AS ci_id FROM requirement WHERE project_id = :pid AND row_target = :row AND retired_at IS NULL`. (Live query, **not** a stored snapshot — same convention as Pass 3c `query_committed_cci_ids_for_row`.) Compute `new_cci_count = len(eligible_ci_ids - covered_ci_ids)`.
    - If `new_cci_count / prior_cci_count >= requirement_rerun_threshold`: `scenario = "FullRerun"`. Else: `scenario = "IncrementalRerun"`.

**IdempotentRerun exit:**
Write AnalysisPass with `execution_status = "Completed"`, `mechanism_data.run_scenario = "IdempotentRerun"`, `mechanism_data.requirement_input_hash = current_hash`, `mechanism_data.idempotent = true`. Existing Requirements and RequirementRegister unchanged. Exit.

**Error cases:**
- Database connection failure during assembly: `execution_status = "Failed"`, `failure_reason = "CCI/Domain assembly query failed: {error}"`.
- CCI referencing a non-existent ZachmanCell: log `cci_referential_integrity_violation` in `execution_warnings`; exclude offending CCI from eligible set; continue.

### 4.2 Stage 2 — Per-Domain AI Derivation Act (IM)

**FirstRun / FullRerun path (per-Domain loop — MD-1):**
For each active Domain `d` in `active_domains`:
- Expand `d.cell_content_item_refs`; assemble `domain_cci_set` as a list of `{ci_id, column, classification_type, description}` for each member CCI (joined from `eligible_ccis`).
- Invoke `requirement_derivation_prompt.py` with:
  - `row_ref`: integer
  - `abstraction_level_phrase`: row abstraction guidance (see §5.4)
  - `requirement_type_guidance`: principle-based column→type reasoning block (see §5.4)
  - `domain`: `{domain_id, name, description}`
  - `domain_cci_set`: the member CCI dicts above
- Pass to Claude Sonnet (model per Row 4 Applied §4.5 — `claude-sonnet-4-20250514`). Parse against `requirement_derivation_response_schema.py`. On parse failure: one retry with identical prompt. Second failure: log `domain_derivation_parse_failure` against the Domain in `validation_failures` and skip the Domain. If **all** Domains fail to parse: `execution_status = "Failed"`, `failure_reason = "AI derivation response parse failure for all Domains after retry"`. Exit. (A partial failure — some Domains parsed — proceeds; the skipped Domain's CCIs become orphans caught by CHK-3d-05 Non-Loss repair.)
- Each proposal's `cci_refs` is expected to be drawn from `domain_cci_set`; out-of-set refs are stripped by CHK-3d-03 in Stage 3.

Accumulate all proposals across Domains into a single proposal set, each tagged with its `source_domain_id` (an in-memory field used by Stage 4 only — not a Requirement attribute).

**IncrementalRerun path:**
Reachable only when the Domain set is unchanged (MD-3). New CCIs all belong to existing Domains. For each Domain owning ≥1 new CCI:
- Assemble existing Requirement summaries for that Domain: `{requirement_id, statement, requirement_type}` for active Requirements whose `cci_refs` intersect the Domain.
- Assemble `new_domain_ccis`: the Domain's CCIs not yet covered by any active Requirement.
- Invoke `requirement_incremental_prompt.py` with `abstraction_level_phrase`, `requirement_type_guidance`, `domain`, `existing_requirements`, `new_domain_ccis`.
- Parse against `requirement_incremental_response_schema.py`. One retry. Persistent failure: fall back to FullRerun (log `incremental_fallback_to_fullrerun` in `execution_warnings`; re-invoke Stage 2 on the FullRerun path for the whole row).

**AI model fingerprinting:**
Record one `ai_model_fingerprints` entry per AI call: `{stage: "stage2_domain_<domain_id>", model: "claude-sonnet-4-20250514", input_tokens: N, output_tokens: M}`. Repair calls fingerprinted separately in Stage 3 (`stage3_repair`).

**LPM constraint enforcement:**
The prompt instructs the AI: "Do NOT copy CCI description text verbatim as the requirement statement; express the obligation in normative form." LPM is enforced at the prompt-instruction level. Automated verbatim-copy detection is not implemented at v0.1 — it is a plausibility criterion (PLB-3d-04) for Practitioner review.

### 4.3 Stage 3 — Structural Validation (DM, with conditional IM repair)

All checks run in sequence on the accumulated proposal set. All are pure in-memory operations (no DB calls) except the Non-Loss repair prompt, which is an IM conditional sub-act.

**CHK-3d-01 — No empty statement:**
For each proposal: if `statement` is empty or whitespace-only, reject. Record `{check_id: "CHK-3d-01", source_domain_id, detail: "empty statement"}` in `mechanism_data.validation_failures`.

**CHK-3d-02 — No empty cci_refs:**
If `len(cci_refs) == 0`, reject. Record in `validation_failures`.

**CHK-3d-03 — cci_refs resolve to the source Domain's eligible membership:**
For each proposal: compute the source Domain's member ci_ids. Remove any `cci_refs` entry not in that membership (out-of-Domain or non-existent ref); log stripped entries in `validation_failures`. If `cci_refs` is empty after stripping: reject (as CHK-3d-02). This enforces MD-1: a Requirement derived for Domain `d` references only `d`'s CCIs.

**CHK-3d-04 — fit_criteria integrity:**
If `fit_criteria` is present but empty/whitespace-only: strip it (treat as absent) and log advisory `fit_criteria_empty_stripped`. (Ledger rule: if present, MUST NOT be empty.) If `requirement_type == "Performance"` and `fit_criteria` is absent after this step: log advisory `performance_missing_fit_criteria` — informational only (ledger says SHOULD, not MUST); surfaced for Practitioner review via PLB-3d-05.

**CHK-3d-05 — Non-Loss (every CCI covered by ≥1 Requirement):**
Compute `covered = {ref for p in proposals for ref in p.cci_refs}`. Compute `orphaned = eligible_ci_ids - covered`.
If `orphaned` is non-empty: invoke the repair prompt (IM sub-act).
- For each orphaned ci_id, resolve its owning Domain(s) from active Domain membership (guaranteed non-empty by Pass 3c Non-Loss; the §4.1 invariant guard already excluded the zero-Domain case).
- Assemble `requirement_repair_prompt.py` with: `orphaned_ccis` (list of `{ci_id, column, classification_type, description, owning_domain_id, owning_domain_name}`), `requirement_type_guidance`. Instruct the AI to produce a Requirement covering each orphaned CCI, scoped within its owning Domain.
- Parse against `requirement_repair_response_schema.py`. One attempt only (no retry — persistent failure is recorded, not retried). Tag each repair proposal with `source_domain_id = owning_domain_id`.
- Merge repair proposals into the proposal set. Re-compute `orphaned`. Any remaining orphan is a **persistent orphan**: record in `mechanism_data.orphaned_ccis`; set `execution_status = "CompletedWithWarnings"`; raise a Concern entity (CN-NNN) for the project/row describing the uncovered CCI (same Concern-raising convention as Pass 3c §4.3 / Fixture 6).

**CHK-3d-06 — Failure path:**
If the proposal set is empty after CHK-3d-01..03 (all proposals rejected) **and** the Non-Loss repair produced nothing: `execution_status = "Failed"`, `failure_reason = "No valid Requirement proposals survived validation"`. No Requirements committed.

**CHK-3d-07 — Exact-duplicate collapse:**
If two surviving proposals have identical `statement` (case-insensitive) **and** identical `cci_refs` set: collapse to one (retain first; union is a no-op since refs are identical). Record advisory `duplicate_requirement_collapsed` in `execution_warnings`. (No name-uniqueness analogue to Pass 3c CHK-3c-03 exists — Requirements have no unique name attribute. Near-duplicate but non-identical statements are a plausibility concern, PLB-3d-01, not a structural merge.)

**ADVC-3d-01 — Requirement-per-Domain soft bounds:**
For each source Domain, count its surviving Requirements. Let `m = len(domain.cell_content_item_refs)`. If a Domain produced `0` Requirements: this manifests as orphaned CCIs handled by CHK-3d-05 (no separate advisory needed). If a Domain produced `> m` Requirements (more Requirements than it has CCIs): log `requirement_count_advisory` in `execution_warnings` with `{domain_id, requirement_count, cci_count}` — a signal of over-decomposition for Practitioner review (PLB-3d-06). Informational only; entity production proceeds.

### 4.4 Stage 4 — Entity Production and Ledger Commit (DM)

**4.4.1 requirement_id allocation:**
`query_max_requirement_id(project_id)` over the `requirement` table **including** retired rows (ids are never reused). Allocate sequentially from the next available `R###`. See §5.3.

**4.4.2 domain_refs DM-derivation (MD-2):**
For each surviving proposal, compute `domain_refs = sorted({d.domain_id for d in active_domains if set(proposal.cci_refs) & set(d.cell_content_item_refs)})`. Assert `len(domain_refs) >= 1` (guaranteed under MD-1, since `cci_refs ⊆ source Domain membership after CHK-3d-03). Assert every referenced Domain has `row_target == str(current_row)` (guaranteed — only current-row Domains were queried). A proposal yielding empty `domain_refs` after this computation is a defect — fail closed: reject the proposal and log `{check_id: "MD-2", detail: "domain_refs derivation empty"}` in `validation_failures`; re-run CHK-3d-05 Non-Loss on the reduced set.

**4.4.3 Requirement entity construction:**
For each proposal build a `Requirement` with: allocated `requirement_id`; `statement`; `requirement_type`; `row_target = str(current_row)`; `confidence`; `cci_refs`; derived `domain_refs`; optional `rationale`, `fit_criteria`, `verification_method`, `priority` if present; `answer_refs = []` (Phase 10 mechanism populates later).

**4.4.4 FullRerun retirement:**
On FullRerun: set `retired_at = now()` on all active Requirements for this row before inserting the new set. `query_max_requirement_id` includes retired ids; new ids continue the sequence (no reuse). Build `mechanism_data.retirement_mapping` — one entry per retired Requirement, with `inferred_successor_requirement_id` populated if statement similarity ≥ 0.50 against a new Requirement (same heuristic as Pass 3c retirement_mapping).

**4.4.5 downstream_rerun_required:**
Query whether Phase 5 (Cell Quality) or Phase 6/8 (Coverage) AnalysisPasses exist for this project/row. If any exist and this run committed a non-trivial change (FullRerun, or Incremental that added/retired Requirements): set `mechanism_data.downstream_rerun_required = true`. The orchestrator surfaces an advisory to the Practitioner; downstream phases are NOT auto-re-triggered (same posture as Pass 3c §4.4 / §10).

**4.4.6 Transaction:**
In a single transaction: insert (and, on FullRerun, retire) Requirements; replace `RequirementRegister.member_ids` with `query_all_active_requirement_ids(project_id)` (project-wide, all rows, `retired_at IS NULL`); write the Pass 3d AnalysisPass. Atomicity guaranteed — partial commit is impossible. On rollback: `execution_status = "Failed"`, Requirements remain in pre-run state.

**4.4.7 execution_status determination:**
`Completed` unless: (a) a persistent orphan was recorded (CHK-3d-05) → `CompletedWithWarnings`; (b) `incremental_fallback_to_fullrerun` was logged → `CompletedWithWarnings`; (c) a Failed condition fired earlier → `Failed`. Informational advisories alone do not change status.

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

`cci_refs` and `domain_refs` are JSONB arrays of string ids stored directly on the row (same JSONB-array-on-row convention as Pass 3c `cell_content_item_refs` — no join table). The `retired_at` soft-delete column mirrors the `domain` table.

**`requirement_register`:** single seeded row per project (migration seeds it, same as DomainRegister): `register_id` (PK), `project_id`, `register_type = 'Requirement'`, `member_ids` JSONB, `completeness_rule` TEXT, `confidence` DOUBLE PRECISION.

**Ledger normative rules (transcribed from v2.12 — all enforced):** `requirement_id` unique and matches `^R\d{3}$`; `statement` not empty; `cci_refs` not empty; `domain_refs` ≥ 1 entry referencing an existing Domain; if `fit_criteria` present it is not empty; `requirement_type` in enum; if `requirement_type == Performance`, `fit_criteria` SHOULD be present; `row_target` in "1".."6"; `row_target` equals the row of every CCI in `cci_refs` and every Domain in `domain_refs`; `confidence` in 0.0..1.0. Exactly one RequirementRegister; `member_ids` contains all `requirement_id` values.

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
The AI does NOT return `requirement_id`, `row_target`, `domain_refs`, or `answer_refs` — those are produced deterministically in Stage 4 (`requirement_id`, `row_target`, `domain_refs`) or deferred (`answer_refs`). Enum membership is enforced here at the parse boundary (MD-5).

**`requirement_incremental_response_schema.py` — IncrementalRerun:**

**IMPORTANT — DISTINCT CLASS.** Same field shape as `RequirementProposal` but a distinct class, `IncrementalRequirementProposal`. Do NOT import or alias the primary class. Incremental proposals cover only `new_domain_ccis`; `cci_refs` entries outside the new-CCI set for the Domain are stripped in Stage 3 (CHK-3d-03 applies to the Domain membership, and a post-merge advisory `incremental_ref_outside_new_set` is logged if an incremental proposal referenced an already-covered CCI).

**`requirement_repair_response_schema.py` — CHK-3d-05 Non-Loss repair:**

**IMPORTANT — DISTINCT CLASS.** `RepairRequirementProposal` is a distinct class from both schemas above. It produces proposals covering orphaned ci_ids. Field shape matches `RequirementProposal`; the distinguishing semantics are that every proposal must cover ≥1 orphaned ci_id and is scoped to a single owning Domain. The three schema classes (`RequirementProposal`, `IncrementalRequirementProposal`, `RepairRequirementProposal`) handle different operations and MUST be defined as separate classes in separate files; sharing or aliasing them risks silent field-mismatch bugs (same discipline as Pass 3c §5.2 distinct-schema warning).

### 5.3 Identifier conventions

- Requirement: `R###` — global per-project sequence; zero-padded 3 digits; allocated in Stage 4.4.1; never reused (includes retired). **Known constraint:** max 999 Requirement instances per project (R001–R999, including retired). For projects with many FullRerun cycles, this ceiling could be approached. Tracked as a known v0.1 limitation — if a project exceeds 800 allocated ids, raise a tracker finding for a 4-digit format extension (R####). (Same ceiling caveat as `domain_id`.)
- RequirementRegister: single register per project; `register_id` seeded at project creation by migration.
- AnalysisPass: `P###` — global sequence, allocated by the common AnalysisPass writer utility.

### 5.4 Requirement statement and type guidance — prompt constants

Two principle-based guidance blocks are injected into `requirement_derivation_prompt.py`, `requirement_incremental_prompt.py`, and `requirement_repair_prompt.py`. Both are principle-based, not pattern-based (MD-5 / D4): they teach the AI *how to reason*, not what requirements to expect from a prior project.

**(a) Statement formulation discipline** (from segmentation spec v9.2): each requirement statement is **atomic** (one obligation), expresses a **single intent**, is phrased **normatively** ("The system shall…" / "X shall…" at the row-appropriate subject), and introduces **no actors, behaviours, or constraints not present in the source CCIs**. Compound statements joined by "and" that carry two distinct obligations are split into two Requirements (the same "two-step concept test" discipline applied to Domain naming in Pass 3c — first seek a single unifying obligation; if none, split).

**(b) requirement_type reasoning signals** (extracted from `sys_engage_specification_v2.md` as principle, per D4):
- **Why-column CCIs** (motivation, rules, policy) → lean `Constraint`.
- **How-column / What-column / When-column CCIs** (function, entity behaviour, event) → lean `Functional`.
- CCIs expressing a measurable threshold, rate, latency, or capacity → `Performance` (and the statement SHOULD carry `fit_criteria`).
- CCIs expressing a quality attribute (usability, maintainability, portability) → `Suitability` or `Non-Functional` per the attribute.
These are reasoning signals for the AI to weigh against the CCI's content and the row's abstraction level — not a deterministic lookup. The enum is enforced deterministically at parse; the value choice is the AI's.

**Row abstraction guidance** reuses the Pass 3c `ROW_GUIDANCE` abstraction-level vocabulary per row (a Row 1 requirement statement reads at enterprise-scope abstraction; a Row 3 statement at logical-design abstraction). The same row-vocabulary discipline that governs Domain naming governs requirement-statement vocabulary. The block is injected inline in the prompt templates; no separate vocabulary module.

---

## 6. Mode Discipline Realisation

Pass 3d uses the mode discipline decorator pattern (Row 4 Applied §4.7), identical structure to Pass 3c §6.

| Stage / Sub-act | Declared mode | Decorator constraint | AnalysisPass record |
|---|---|---|---|
| Stage 1 — Pre-flight | DM | No AI calls permitted | `mode_active: ["DM"]` |
| Stage 2 — Per-Domain derivation | IM | AI call per Domain; LPM on CCI text | `mode_active: ["IM"]`; one fingerprint per Domain call |
| Stage 2 — Retry (parse failure) | IM | Second AI call; same constraint | Retry fingerprint appended |
| Stage 3 — Structural checks (CHK-3d-01..04, 06, 07; ADVC-3d-01) | DM | No AI calls (except repair sub-act) | `mode_active: ["DM"]` |
| Stage 3 — Non-Loss repair (conditional IM) | IM | AI call; `repair_prompt_issued = true` | Repair fingerprint `stage3_repair` recorded separately |
| Stage 4 — Entity production | DM | No AI calls; `domain_refs` derivation + ledger write | `mode_active: ["DM"]` |

`declared_transformation_modes = ["IM", "DM"]`; `mode_active` primary value is `"IM"` (Stage 2 is the primary act). **Do not record `mode_active: "LPM"`** — LPM is a preservation constraint on CCI text handling, not a transformation mode (this was the Pass 3c PMT build-correction; carry it forward to avoid the same error). Mode violations (a DM stage making an AI call, or an IM stage making none when required) are recorded in `mechanism_data.mode_violations` and set `execution_status = "CompletedWithWarnings"`.

**LPM constraint** applies throughout: CCI `description` text is read-only context; the AI is instructed not to reproduce it verbatim in `statement`. Automated detection is deferred to a future tracker finding if evidence shows violations.

---

## 7. Audit Trail Population

The AnalysisPass `outputs` JSONB for `mechanism="RequirementDerivation"` has the structure below. All fields required; zero-value arrays present as `[]`, not null, not omitted. `execution_warnings` is a **standard top-level AnalysisPass field**, not a sub-field of `mechanism_data` (same placement as Pass 3c §7).

`execution_warnings` types written by Pass 3d: `no_cci_input` (§4.1 → CompletedWithWarnings); `cci_referential_integrity_violation` (informational); `incremental_fallback_to_fullrerun` (→ CompletedWithWarnings); `fit_criteria_empty_stripped`, `performance_missing_fit_criteria`, `duplicate_requirement_collapsed`, `requirement_count_advisory`, `incremental_ref_outside_new_set`, `chk3d05_repair_performed`, `chk3d05_repair_failed` (informational, except where noted).

```jsonc
{
  "mechanism_data": {
    // --- Stage 1 ---
    "run_scenario":              "FirstRun",        // one of four scenario names
    "requirement_input_hash":    "<sha256-hex>",    // two-part hash (CCI-ids + active Domain-ids), MD-3
    "domain_id_set":             ["D001","D002"],   // sorted active Domain-ids at run time (for MD-3 comparison)
    "cci_count_input":           7,                 // 0 on zero-CCI exit
    "domain_count_input":        3,
    "large_cci_set_advisory":    false,
    "idempotent":                false,             // true on IdempotentRerun only

    // --- Stage 3 ---
    "repair_prompt_issued":      false,
    "orphaned_ccis":             [],                // persistent orphans after repair
    "validation_failures":      [],                 // [{check_id, source_domain_id, detail}]
    "duplicate_requirements_collapsed": [],         // [{kept_statement, collapsed_count}]

    // --- Stage 4 ---
    "requirement_count_produced": 5,                // 0 on IdempotentRerun/Failed
    "requirement_count_retired":  0,                // non-zero on FullRerun only
    "requirement_type_distribution": {              // counts per enum value
      "Functional": 3, "Constraint": 2, "Performance": 0,
      "Suitability": 0, "Non-Functional": 0
    },
    "requirements_produced": [                      // per-Requirement summary
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

VER-3d-08 checks `mechanism_data` completeness only; `execution_warnings` completeness is verified by the common AnalysisPass schema validator. `row_ref` is set both as a top-level AnalysisPass field and inside `mechanism_data` (Pass 3c convention).

---

## 8. Verification Criteria

### 8.1 Decidable criteria (automated — pytest)

All implemented in `tests/test_requirement_derivation.py`, Neon test DB with transaction-rollback isolation (same pattern as `tests/test_domain_derivation.py`).

| ID | Criterion | pytest assertion |
|---|---|---|
| **VER-3d-01** | All `requirement_id` match `^R\d{3}$` | `re.fullmatch` for all in project |
| **VER-3d-02** | All `requirement_id` unique within project (active + retired) | `len(set(ids)) == len(ids)` |
| **VER-3d-03** | Every Requirement has non-empty `statement` and ≥1 `cci_refs` | `len(statement) > 0` and `jsonb_array_length(cci_refs) >= 1` |
| **VER-3d-04** | All `cci_refs` resolve to CCIs with matching `row_target` | expand `cci_refs`; JOIN `cell_content_item → zachman_cell`; assert `row_target == requirement.row_target` |
| **VER-3d-05** | Non-Loss: every eligible CCI appears in ≥1 Requirement's `cci_refs` | union of `cci_refs` across active Requirements for the row ⊇ `eligible_ci_ids` |
| **VER-3d-06** | RequirementRegister `member_ids` == active `requirement_id` set (all rows) | set equality, `retired_at IS NULL`, no `row_target` filter; integration test must exercise ≥2 rows |
| **VER-3d-07** | AnalysisPass `mechanism="RequirementDerivation"`, `row_ref=current_row` exists | presence query |
| **VER-3d-08** | `mechanism_data` present; all required fields non-null | schema validation against §7 field list |
| **VER-3d-09** | All `requirement_type` values in enum | `requirement_type in {Functional,Constraint,Performance,Suitability,Non-Functional}` |
| **VER-3d-10** | All `domain_refs` ≥1 entry; all resolve to existing Domains with matching `row_target` | expand `domain_refs`; JOIN `domain`; assert exists and `domain.row_target == requirement.row_target` |
| **VER-3d-11** | IdempotentRerun: requirement set unchanged; `mechanism_data.idempotent == true`; status=Completed | snapshot before/after; assert equality + flag |
| **VER-3d-12** | FullRerun: `requirement_count_retired` == prior active count for the row | query prior active count; assert equality |
| **VER-3d-13** | `requirement_count_produced >= 1` when `cci_count_input > 0` | conditional assertion |
| **VER-3d-14** | No Requirement has `fit_criteria` present-but-empty | `fit_criteria IS NULL OR length(fit_criteria) > 0` for all |

### 8.2 Plausibility checklist for Practitioner review

1. **PLB-3d-01 — Statement atomicity:** Each statement expresses one obligation. Compound statements joined by "and" carrying two distinct obligations should have been split (§5.4a). Near-duplicate statements (non-identical, so not collapsed by CHK-3d-07) are flagged for review.
2. **PLB-3d-02 — Row-appropriate abstraction:** Statement vocabulary matches the row's abstraction level (Row 1 enterprise-scope; Row 3 logical-design). Implementation vocabulary at Row 1/2 is a PLB failure.
3. **PLB-3d-03 — requirement_type plausibility:** The assigned type matches the source CCI columns (Why → Constraint, How/What/When → Functional, measurable threshold → Performance). Review `requirement_type_distribution` for anomalies (e.g. a Why-heavy Domain producing only Functional requirements).
4. **PLB-3d-04 — No inferred content (LPM):** The statement introduces no actor, behaviour, or constraint absent from the source CCIs, and does not reproduce CCI description text verbatim.
5. **PLB-3d-05 — Performance fit_criteria:** Every `Performance` Requirement carries meaningful `fit_criteria`. Where `performance_missing_fit_criteria` is in `execution_warnings`, the Practitioner supplies or confirms acceptance criteria.
6. **PLB-3d-06 — Requirement-per-Domain balance:** Where `requirement_count_advisory` fired (a Domain produced more Requirements than CCIs), review for over-decomposition — multiple thin Requirements that should be one, or a genuine fan-out.

---

## 9. Test Fixtures

All seven implemented in `tests/test_requirement_derivation.py`; AI stubs via monkeypatch (same pattern as Pass 3c §9).

### 9.1 Fixture 1 — PMT Row 2: FirstRun happy path
**Test:** `test_pmt_row2_firstrun`. Setup: PMT Row 2 with Domains D001–D003 committed (Pass 3c state) and their CCIs. AI stub returns 1–2 RequirementProposals per Domain.
**Assertions:** VER-3d-05 (all CCIs covered); VER-3d-09; VER-3d-10 (each Requirement's `domain_refs` == its source Domain); `requirement_count_produced >= domain_count_input`; RequirementRegister populated.

### 9.2 Fixture 2 — NQPS Row 3: FirstRun (and zero-CCI note)
**Test:** `test_nqps_row3_firstrun`. Setup: NQPS Row 3 Domains + CCIs.
**Assertions:** VER-3d-05; VER-3d-09; PLB-3d-03 distribution sane. **Companion zero-CCI assertion** (`test_nqps_row4_zero_cci`): NQPS Row 4 (zero CCIs) → `no_cci_input`, `CompletedWithWarnings`, RequirementRegister preserves other-row members, Stage 2 not invoked.

### 9.3 Fixture 3 — PMT Row 2: IdempotentRerun
**Test:** `test_pmt_row2_idempotent_rerun`. Setup: run Fixture 1, then re-invoke with identical CCI and Domain sets.
**Assertions:** VER-3d-11; `run_scenario == "IdempotentRerun"`; Stage 2 AI stub `assert_not_called()`; `requirement_input_hash` matches prior.

### 9.4 Fixture 4 — PMT Row 2: IncrementalRerun (one new CCI)
**Test:** `test_pmt_row2_incremental_rerun`. Setup: run Fixture 1; add one new CCI to an existing Domain (Domain set unchanged → Incremental reachable per MD-3). AI incremental stub returns one new RequirementProposal covering the new CCI.
**Assertions:** `run_scenario == "IncrementalRerun"`; VER-3d-05 after delta; existing `requirement_id`s preserved; prior AnalysisPass unchanged; new AnalysisPass written.

### 9.5 Fixture 5 — Non-Loss repair: orphaned CCI recovered
**Test:** `test_noloss_repair_prompt_recovery`. Setup: PMT Row 2 FirstRun; primary stub omits one CCI from all proposals. CHK-3d-05 detects 1 orphan.
**Repair stub:** returns one RepairRequirementProposal covering the orphan, scoped to its owning Domain.
**Assertions:** `repair_prompt_issued == true`; `orphaned_ccis == []`; VER-3d-05 passes; `execution_status == "Completed"`; `ai_model_fingerprints` has the per-Domain entries plus `stage3_repair`.

### 9.6 Fixture 6 — Persistent orphan after repair failure
**Test:** `test_noloss_repair_persistent_orphan`. Setup: primary stub omits one CCI; repair stub returns `[]`.
**Assertions:** `repair_prompt_issued == true`; `orphaned_ccis == [<ci_id>]`; `execution_status == "CompletedWithWarnings"`; VER-3d-05 asserted to **fail** here (the test verifies the orphan is *recorded*); a Concern CN-NNN exists for the project/row referencing the orphan.

### 9.7 Fixture 7 — FullRerun: Domain-set change forces full re-derivation
**Test:** `test_pmt_row2_fullrerun`. Setup: run Fixture 1; simulate a Pass 3c FullRerun that retired D001–D003 and committed D004–D006 over the same CCIs (Domain-id set changed → MD-3 forces FullRerun). Invoke Pass 3d.
**Primary stub (FullRerun):** returns proposals for the new Domains.
**Assertions:** `run_scenario == "FullRerun"`; prior Requirements have `retired_at IS NOT NULL`; new Requirements allocated from next available `R###` (no reuse); VER-3d-12 (`requirement_count_retired` == prior active count); VER-3d-05 on the new set; `domain_refs` reference the new Domain-ids; `downstream_rerun_required` reflects Phase 5/6 presence.

---

## 10. Edge Cases

| Edge case | Implementation handling |
|---|---|
| **Zero CCIs for the row** | Stage 1 early exit: `CompletedWithWarnings`, `no_cci_input`; RequirementRegister updated with project-wide active member set (not `[]`). Stage 2 not invoked. (NQPS Row 4.) |
| **CCIs exist but zero active Domains** | §4.1 invariant guard → `Failed` ("Pass 3c invariant violated"). Should be unreachable given VER-3c-05; asserted rather than silently producing orphans. |
| **Single CCI in a Domain** | Stage 2 receives a one-CCI Domain; AI returns ≥1 Requirement covering it. VER-3d-05 passes for that CCI. |
| **A Domain yields zero Requirements** | Its CCIs become orphans; CHK-3d-05 Non-Loss repair derives covering Requirements. If repair fails: persistent orphan, Concern raised. |
| **AI proposes cci_refs outside the source Domain** | Stripped by CHK-3d-03; if proposal empties, rejected; resulting orphans handled by CHK-3d-05. |
| **Performance requirement without fit_criteria** | `performance_missing_fit_criteria` advisory (informational); PLB-3d-05 surfaces it for Practitioner completion. Not a failure (ledger SHOULD). |
| **fit_criteria present but empty** | Stripped to absent (CHK-3d-04); `fit_criteria_empty_stripped` advisory. (Ledger MUST-not-empty satisfied.) |
| **AI parse failure for one Domain (others succeed)** | Domain skipped; logged in `validation_failures`; its CCIs become orphans handled by CHK-3d-05. |
| **AI parse failure for all Domains after retry** | `Failed`, `failure_reason = "AI derivation response parse failure for all Domains after retry"`. No Requirements committed. |
| **IncrementalRerun AI parse failure → FullRerun fallback** | `incremental_fallback_to_fullrerun` advisory; Stage 2 re-invoked on FullRerun path. If FullRerun also fails: `Failed`. |
| **Domain-id set changed since prior run** | MD-3 forces FullRerun even if the CCI set is unchanged — per-Domain scoping is invalidated by a Domain reshuffle. |
| **FullRerun with Phase 5/6 already complete** | `downstream_rerun_required = true`; orchestrator surfaces advisory; downstream not auto-re-triggered; dangling downstream refs remain until Practitioner re-runs. |
| **Repair AI response is empty list** | Persistent-orphan path: orphans recorded, `CompletedWithWarnings`, Concern raised; entity production proceeds on surviving Requirements. |
| **FullRerun retirement transaction rollback** | Single transaction → no partial retirement; Requirements remain pre-run; AnalysisPass `Failed`. |
| **RequirementRegister seed missing** | `Failed`, `failure_reason = "RequirementRegister not found — migration may not have run"`. Deployment-config error, not runtime. |
| **Large CCI set (>80 for the row)** | `large_cci_set_advisory` recorded; per-Domain processing proceeds (per-Domain calls remain small). No chunking at v0.1. |

---

## 11. Cross-Mechanism Interactions

### 11.1 Upstream

| Mechanism | What it provides | Dependency type |
|---|---|---|
| **Pass 3c — Domain Derivation** | `domain` rows (with `cell_content_item_refs`) — Pass 3d reads active Domains as the per-Domain derivation scope and as the basis for DM-derived `domain_refs`. | Hard dependency — orchestrator checks Pass 3c `execution_status ∈ {Completed, CompletedWithWarnings}` (IdempotentRerun `Completed` satisfies the gate). |
| **Pass 3b — CCI Construction** | `cell_content_item` rows — the source content from which Requirements are derived. | Transitive (via Pass 3c, which already depends on 3b). Pass 3d reads CCIs directly for descriptions. |

### 11.2 Downstream

| Mechanism | What this provides | Dependency type |
|---|---|---|
| **Phase 5 — Cell Quality** | `requirement` rows for quality assessment. | Analytical — Requirements must be committed first. |
| **Phase 6 / Phase 8 — Coverage Analysis** | `requirement` rows (with `cci_refs`, `domain_refs`) as coverage inventory. Read-only with respect to Requirements. | Analytical. |
| **Phase 10 — Gap/Question/Answer** | Populates `answer_refs` on existing Requirements; may create Requirements via Answer resolution. | Writes back to `answer_refs`; not a Pass 3d concern at v0.1. |

### 11.3 Ledger coordination

Mechanisms coordinate via ledger reads, not direct calls (Row 4 Applied §4.11). Pass 3d reads CCIs and Domains from the ledger; writes Requirements, RequirementRegister, and AnalysisPass in a single transaction at completion. The orchestrator (`core/orchestrator.py`) enforces sequencing by querying AnalysisPass records before invoking each mechanism. No mechanism imports or calls another directly.

---

## 12. Build Notes

### 12.1 Tracker findings relevant to this build

| Finding | Status | Relevance |
|---|---|---|
| **F80** | Open | Cross-row Domain name duplication (NQPS "Quality Governance" at Row 1 and Row 2). Pass 3d consumes Domains by `domain_id`, never by `name` (MD-2), so the duplication is harmless to derivation. The residual Practitioner-presentation concern (two same-named Domains visible at review) is **not** resolved by `domain_id` consumption alone. Per D5: log this disposition against F80, leave F80 **Open** (do not close Wont-Fix); presentation-layer name disambiguation is deferred to review tooling, not Pass 3d. |
| **F66** | Action-Required (bookkeeping) | F66 appears under both *Action-Required* and the *Resolved* "F45–F79" range in the v0.51 Status Summary — likely the range sweep. Reconcile at the next tracker increment. No Pass 3d implementation impact. |

### 12.2 OQ resolutions committed at this spec

| OQ | Resolution |
|---|---|
| **OQ-3d-01** | Re-run input hash scope — resolved per D3: two-part hash over sorted CCI-ids and sorted active Domain-ids (§4.1, MD-3). A Domain-id-set change forces FullRerun. |
| **OQ-3d-02** | `domain_refs` provenance — resolved per D2: DM-derived in Stage 4 by intersecting `cci_refs` with active Domain membership (MD-2, §4.4.2). The AI never proposes `domain_refs`. |
| **OQ-3d-03** | Stage 2 granularity — resolved per D1a: per-Domain derivation (MD-1). Forward-compatible with whole-row (D1b) via the general `domain_refs` intersection; switching later changes only the Stage 2 loop boundary. |
| **OQ-3d-04** | Requirement-per-Domain bounds — soft advisory ADVC-3d-01 (§4.3): a Domain producing more Requirements than it has CCIs logs `requirement_count_advisory`. No hard bound; over/under-decomposition is a Practitioner review concern (PLB-3d-06). |

### 12.3 Replit Agent task structure

**Primary input documents:**
- This spec (Row 4 Mechanism Spec — Requirement Derivation v0.1) — implementation authority (all detail including DDL in §5.1)
- Pass 3c Mechanism Spec v0.24 — architectural authority (four-stage pattern, re-run/repair/retirement conventions)
- Row 4 Understanding v0.25 §14 — framework (module structure, ProjectProfile params, VER→pytest, fixture table)

**Reference documents:**
- Row 4 Applied v0.2 — common architectural commitments
- Canonical Ledger v2.12 — Requirement, RequirementRegister, AnalysisPass schemas
- Segmentation spec v9.2 — statement formulation discipline (§5.4a)

**Build sequence:**
1. Alembic migration `add_requirement_tables` — `requirement` table (with `cci_refs`/`domain_refs`/`answer_refs` JSONB and `retired_at`) and RequirementRegister seed. DDL from §5.1.
2. Alembic migration `add_requirement_profile_params` — two ProjectProfile columns (Understanding §14.2).
3. Write `schemas/requirement_derivation_response_schema.py`, `schemas/requirement_incremental_response_schema.py`, `schemas/requirement_repair_response_schema.py` (§5.2 — three DISTINCT classes, no sharing).
4. Write `prompts/requirement_derivation_prompt.py`, `prompts/requirement_incremental_prompt.py`, `prompts/requirement_repair_prompt.py` with the §5.4 guidance blocks inline.
5. Write `stage1_preflight.py` → `stage4_entity_production.py` and `__init__.py` orchestrator.
6. Write `tests/test_requirement_derivation.py` with Fixtures 1–7 (§9); AI stubs via monkeypatch.
7. Run migrations; run pytest; verify VER-3d-01..14 on Fixtures 1, 2, 3, 4, 7.
8. Verify Fixture 5 (repair recovery) and Fixture 6 (persistent orphan) against their specific assertions.

**Deviations from Pass 3c to watch:**
- Stage 2 is a **per-Domain loop**, not a single whole-row call — one AI call per active Domain.
- `domain_refs` is **DM-derived in Stage 4**, never AI-proposed — the response schema omits it.
- Re-run hash is **two-part** (CCI-ids + Domain-ids); a Domain-set change forces FullRerun.
- No name-uniqueness merge (no Pass 3c CHK-3c-03 analogue) — Requirements have no unique name; CHK-3d-07 collapses only exact statement+cci_refs duplicates.
- Non-Loss repair derives a **covering Requirement** for orphaned CCIs (not a Domain) and scopes the repair to the orphan's owning Domain.
- `requirement_type` enum enforced at parse boundary; value choice is principle-based (no lookup table).

---

## Document End

End of SysEngage Row 4 Mechanism: Requirement Derivation v0.1.

Initial specification — no prior version. Establishes Pass 3d on the Pass 3c architectural pattern with the four confirmed design decisions (D1a per-Domain Stage 2; D2 DM-derived `domain_refs`; D3 two-part re-run hash; D4 principle-based `requirement_type` guidance) and the F80 disposition (D5: logged, left Open).

Companion artefacts:
- SysEngage_Row_4_Mechanism_Domain_Derivation_v0_24.md — architectural authority for the four-stage pattern
- SysEngage_Row_4_Understanding_v0_25.md — structural framework (§14 addendum)
- SysEngage_Issues_Tracker_v0_51.md — finding disposition (F80, F66)
- sysengage_minimal_ledger_spec_v2_12.md — canonical Requirement / RequirementRegister schema authority
