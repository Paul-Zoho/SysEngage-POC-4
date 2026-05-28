# SysEngage Row 4 Mechanism: Domain Derivation

**Implementation specification — depth tier (i)+**

Filename: SysEngage_Row_4_Mechanism_Domain_Derivation_v0_7.md

Version: 0.7 (sixth Agent review — §10 zero-CCI edge case corrected to match §4.1 fix; §5.1 extended with full CREATE TABLE DDL, completing the v0.10 Understanding structural refactor; §5.1 DDL cross-reference and §12.3 step 1 updated; Understanding references updated to v0.11; tracker reference updated to v0.33)

Date: 26 May 2026

**Purpose.** Implementation specification for the Domain Derivation mechanism (Pass 3c). v0.7 propagates the §4.1 zero-CCI DomainRegister fix to §10 (edge case table), and inserts the full CREATE TABLE DDL into §5.1 — making the Mechanism Spec the single authoritative source for all implementation detail, consistent with the v0.10/v0.11 Understanding structural refactor intent. Supersedes v0.6.

**Excludes.** Per Row 4 Understanding §8.1: NO pseudo-code, NO function signatures, NO code-level interface definitions. Pseudocode in §13 of the Row 4 Understanding is framework guidance only; this spec does not repeat it.

---

## 1. Mechanism Identification

| Attribute | Value |
|---|---|
| **Mechanism name** | Domain Derivation |
| **Row 3 Mechanism Spec reference** | SysEngage_Row_3_Mechanism_Domain_Derivation_v0_1.md — all sections |
| **Operational location** | Phase 3 Pass 3c. Executes after Pass 3b (CellContentItem Construction) completes; before Pass 3d (Requirement Derivation). Four stages: Stage 1 (pre-flight + CCI assembly + re-run scenario detection, DM), Stage 2 (AI grouping act, IM), Stage 3 (structural validation + conditional repair, DM + IM conditional), Stage 4 (entity production + ledger commit, DM). |
| **Mechanism class** | AI-involving. IM-primary (Stage 2 AI grouping; Stage 3 conditional repair prompt). DM-envelope (Stage 1 pre-flight; Stage 3 structural checks; Stage 4 entity production, domain_qualifier assignment, upstream_domain_ref heuristic, ledger write). LPM preservation constraint throughout — CCI descriptions are read, not rewritten. |
| **Module location** | `mechanisms/domain_derivation/` directory. See §3.1 for file structure. |
| **Row applicability** | Row-sequential. Runs once per active row. domain_qualifier determined deterministically from row_target (see §5.3). |
| **Mechanism Stakeholder** | None. SH001 covers structural review. SG-01 covers Practitioner quality review. SG-03 carries execution attribution via AnalysisPass. |

---

## 2. Cross-References

| Source | Reference | What this provides |
|---|---|---|
| **Row 3 Mechanism Spec v0.1** | All sections | Architectural authority: four-stage pass structure, six structural checks (CHK-3c-01..06), Non-Loss enforcement, repair prompt pattern, re-run scenarios, domain_qualifier mapping, verification criteria (VER-3c-01..12), plausibility criteria (PLB-3c-01..06), test fixtures, edge cases |
| **Row 4 Understanding v0.11** | §13 | Pass 3c implementation framework: module structure (directory tree), re-run scenarios (prose), ProjectProfile parameters, mode discipline, VER criteria → pytest mapping, full 7-fixture table, Replit Agent handoff. Implementation detail (pseudocode, DDL, schemas) lives in this spec §5.1, not the Understanding. |
| **Row 4 Understanding v0.2** | §9.4 | Prompt architecture pattern: template registry, parameterisation contract, response schema, lens definition locus |
| **Row 4 Understanding v0.2** | §9.5 | Non-determinism handling: decidable vs plausibility split, re-run semantics, AI model fingerprinting |
| **Row 4 Applied v0.2** | All sections | Common architectural commitments: Python 3.12+, FastAPI, Neon PostgreSQL via SQLAlchemy + Alembic, Pydantic v2, Claude Sonnet via Anthropic API, pytest, transactional discipline, mode discipline decorator |
| **Canonical Ledger v2.12** | Domain, DomainRegister, AnalysisPass element types | Authoritative schemas. Pydantic models in `schemas/` mirror these. |
| **Row 3 v1.1** | §E.12.1 | domain_qualifier enum and upstream_domain_ref attribute definitions |
| **Tracker v0.33** | F43, F44, F46–F52 | F43/F44: Action-Required. F46–F51: Resolved spec correction records. F52: sixth-review corrections (Resolved). |

---

## 3. Architectural Approach

### 3.1 Module structure

```
mechanisms/domain_derivation/
  __init__.py                              # Orchestration entry point — Stages 1–4 in sequence
  stage1_preflight.py                      # DM: Pass 3b prerequisite check; eligible CCI query;
                                           #     large-set advisory; re-run scenario detection; idempotent exit
  stage2_ai_grouping.py                    # IM: primary AI grouping call; Pydantic validation at boundary;
                                           #     one retry on parse failure; IncrementalRerun branch
  stage3_structural_validation.py          # DM: CHK-3c-01..06 checks; cross-cutting advisory;
                                           #     IM conditional: repair prompt dispatch on CHK-3c-04 failure
  stage4_entity_production.py              # DM: domain_id allocation; domain_qualifier mapping;
                                           #     upstream_domain_ref heuristic; Domain entity construction;
                                           #     FullRerun retirement; ledger transaction; DomainRegister replace;
                                           #     AnalysisPass write
  prompts/
    domain_grouping_prompt.py              # Template: FirstRun / FullRerun — full CCI set grouping
    domain_incremental_prompt.py           # Template: IncrementalRerun — new CCIs vs existing Domain summaries
    domain_repair_prompt.py                # Template: CHK-3c-04 repair — orphaned CCIs to be assigned
    row_abstraction_vocabulary.py          # Dict: row_target → {abstraction_level_phrase, domain_qualifier_label}
  schemas/
    domain_grouping_response_schema.py     # Pydantic: primary grouping response (name, description,
                                           #           classification_type, cci_refs)
    domain_incremental_response_schema.py  # Pydantic: IncrementalRerun response (action: assign|new)
    domain_repair_response_schema.py       # Pydantic: repair prompt response (action-based: assign|new).
                                           #           DISTINCT from incremental schema — uses domain_name: str
                                           #           NOT domain_id: str. Must NOT be shared or imported
                                           #           across schema files. See §5.2 IMPORTANT warning.
```

### 3.2 Major design decisions

**MD-1 — No batching.** Pass 3b uses fixed-size Signal batches because Signal counts can be large (ProjectProfile.cci_batch_size, default 20). Pass 3c takes all CCIs for the row in a single AI call. The CCI set is the already-distilled Pass 3b output — it is substantially smaller than the Signal set. No batching loop is implemented. If a future project produces >80 CCIs for a single row, a `large_cci_set_advisory` fires (§3.3) but processing still proceeds as a single call.

**MD-2 — Four re-run scenarios via hash-based detection.** Pass 3b's re-run behaviour is extend-on-rerun (additive). Pass 3c has four distinct code paths (FirstRun / IdempotentRerun / IncrementalRerun / FullRerun) selected by SHA-256 hash comparison of the sorted ci_id list against the prior AnalysisPass record. The hash is stored in `AnalysisPass.outputs.domain_data.cci_set_hash` on every run. See §4.1 for detection logic.

**MD-3 — Three prompt templates, three Pydantic schemas.** Different re-run scenarios and the repair path require structurally different AI outputs. Each prompt has its own template file and response schema rather than a single polymorphic schema. The DM entity-production stage reads from the validated schema output, not the raw AI string.

**MD-4 — cell_content_item_refs as join table, not JSONB array.** The `domain.cell_content_item_refs` attribute from the canonical ledger spec is implemented as the `domain_cci_membership` join table at the physical layer. This enables efficient bidirectional queries ("which CCIs belong to Domain D?" and "which Domains contain CCI C?") and enforces referential integrity at the database level. The JSON serialisation for the ledger API uses the JSONB array form, assembled by query.

**MD-5 — FullRerun uses soft-delete (retired_at timestamp), not hard delete.** Retiring Domains on FullRerun preserves referential integrity for any existing `Requirement.domain_refs` entries from a prior Pass 3d run. Hard deletion would leave dangling FK references. The `retired_at TIMESTAMPTZ` column (null = active) is the retirement flag. `query_max_domain_id` includes retired Domains in its maximum calculation to prevent id reuse.

**MD-6 — upstream_domain_ref is a DM heuristic, not an AI call.** For Row 3 Domains, `find_upstream_match` computes Jaccard token overlap between the proposed Domain name and each Row 2 Domain name in the same project. If overlap ≥ `domain_upstream_match_threshold` (default 0.50), the best-matching Row 2 domain_id is assigned. No AI is involved. Unmatched Domains leave `upstream_domain_ref = null` and are recorded in `AnalysisPass.outputs.domain_data.unmatched_upstream_refs` for Practitioner review.

**MD-7 — Repair prompt is a conditional IM sub-act of Stage 3, not a separate Stage.** When CHK-3c-04 detects orphaned CCIs, a second AI call is made within Stage 3. The mode discipline decorator records both the primary (Stage 2) and the repair (Stage 3 sub-act) IM invocations separately in `AnalysisPass`. One repair attempt only — persistent orphans are recorded in `orphaned_ccis` and a Concern is raised; they do not block entity production.

### 3.3 Large CCI set advisory threshold

Before Stage 2 is invoked, Stage 1 checks `len(eligible_ccis)` against `ProjectProfile.domain_large_cci_set_advisory_threshold` (default 80). If exceeded: `domain_data.large_cci_set_advisory = true` is set in the AnalysisPass and an advisory is logged. Processing continues — this is informational only. The Row 4 Mechanism Spec does not define a chunking strategy for Pass 3c at v0.1; if future empirical evidence shows that large CCI sets degrade AI grouping quality, a chunking extension should be raised as a new tracker finding.

---

## 4. Stage-by-Stage Implementation

### 4.1 Stage 1 — Pre-flight and CCI Assembly (DM)

**Precondition check (hard stop):**
Query `AnalysisPass` for `mechanism="CellContentItemConstruction"` AND `row_ref = current_row` AND `project_id = current_project`. If not found, or `execution_status = "Failed"`: set `execution_status = "Failed"` on Pass 3c AnalysisPass; `failure_reason = "Pass 3b prerequisite not met — no completed CCI Construction pass found for this row"`. Exit.

**CCI assembly:**
Query `cell_content_item` JOIN `zachman_cell` WHERE `zachman_cell.row_target = str(current_row)` AND `cell_content_item.project_id = current_project`. This is the eligible CCI set. Record `cci_count_input = len(eligible_ccis)`.

**Zero-CCI early exit:**
If `cci_count_input == 0`: write AnalysisPass with `execution_status = "CompletedWithWarnings"`, `domain_data.run_scenario = "FirstRun"` (or whichever applies), warning `no_cci_input`. Update DomainRegister with `member_ids = query_all_active_domain_ids(project_id)` — the project-wide active domain set at the time of this run (`SELECT domain_id FROM domain WHERE project_id = :pid AND retired_at IS NULL`, no `row_target` filter). **Do NOT write `member_ids = []` unconditionally.** If other rows' Domains exist in the project (e.g., Row 2 Domains D001–D003 already committed), they must be preserved in the register. If no Domains exist anywhere in the project, the query returns an empty list and `member_ids = []` is the correct outcome — but it must be derived from the query, not hardcoded. Exit.

**Large-set advisory:**
If `cci_count_input > domain_large_cci_set_advisory_threshold`: set `domain_data.large_cci_set_advisory = true`.

**Re-run scenario detection:**
Compute `current_hash = SHA-256("|".join(sorted([c.ci_id for c in eligible_ccis])))`.
Query most recent non-Failed, non-Skipped Pass 3c AnalysisPass for this `row_ref` and `project_id`. If none: `scenario = "FirstRun"`. If found:
- `prior_hash = prior_pass.outputs["domain_data"]["cci_set_hash"]`
- If `current_hash == prior_hash`: `scenario = "IdempotentRerun"`
- Else:
  - `prior_cci_count = prior_pass.outputs["domain_data"]["cci_count_input"]`
  - **Zero-division guard:** If `prior_cci_count == 0` (prior run completed with `no_cci_input` warning — no Domains were committed): treat as `"FirstRun"`. There is nothing to extend or retire.
  - Otherwise: call `query_committed_cci_ids_for_row(row_ref, project_id)` — a database query on `domain_cci_membership` that returns the set of ci_ids covered by active Domains for this row/project at the time of the last Pass 3c run. This is **not** a stored field in `domain_data`; it requires a live DB query. Compute `new_cci_count = len(eligible_ci_ids - prior_committed_ci_ids)`.
  - If `new_cci_count / prior_cci_count >= domain_rerun_threshold`: `scenario = "FullRerun"`. Else: `scenario = "IncrementalRerun"`.

**Implementation note on `query_committed_cci_ids_for_row`:** This function executes `SELECT DISTINCT ci_id FROM domain_cci_membership JOIN domain USING (domain_id, project_id) WHERE domain.project_id = :pid AND domain.row_target = :row AND domain.retired_at IS NULL`. The result represents the CCI coverage footprint of the last committed Domain set. It must **not** be confused with a stored snapshot in the AnalysisPass record — the AnalysisPass stores only the hash, not the ci_id list.

**IdempotentRerun exit:**
Write AnalysisPass with `execution_status = "Skipped"`, `domain_data.run_scenario = "IdempotentRerun"`, `cci_set_hash = current_hash`. Existing Domains and DomainRegister unchanged. Exit.

**Error cases:**
- Database connection failure during CCI query: `execution_status = "Failed"`, `failure_reason = "CCI assembly query failed: {error}"`.
- Referential integrity violation (CCI references non-existent ZachmanCell): log warning in AnalysisPass `execution_warnings`; exclude offending CCI from eligible set; continue.

### 4.2 Stage 2 — AI Grouping Act (IM)

**FirstRun / FullRerun path:**
Invoke `domain_grouping_prompt.py` with parameters:
- `row_ref`: integer (current row)
- `abstraction_level_phrase`: from `row_abstraction_vocabulary.py[str(row_ref)]["abstraction_level_phrase"]`
- `domain_qualifier_label`: from `row_abstraction_vocabulary.py[str(row_ref)]["domain_qualifier_label"]`
- `cci_set`: list of dicts `{ci_id, column, classification_type, description}` for all eligible CCIs
- `cci_count`: `len(eligible_ccis)`

Pass assembled prompt to Claude Sonnet (model: per Row 4 Applied §4.5 — `claude-sonnet-4-20250514`). Parse response against `domain_grouping_response_schema.py` (Pydantic). If parse fails: one retry with identical prompt. Second parse failure: `execution_status = "Failed"`, `failure_reason = "AI grouping response parse failure after retry"`. Exit.

**IncrementalRerun path:**
Construct existing Domain summaries from ledger: for each active Domain for this row/project, produce `{domain_id, name, description, cci_ref_count}`. Assemble new CCI delta: CCIs in `eligible_ccis` not present in any existing Domain's `domain_cci_membership`.
Invoke `domain_incremental_prompt.py` with:
- `abstraction_level_phrase`, `domain_qualifier_label`: same as above
- `existing_domains`: list of Domain summary dicts
- `new_ccis`: list of new CCI dicts
- `new_cci_count`: count of new CCIs

Parse against `domain_incremental_response_schema.py`. One retry on parse failure. Persistent failure: fall back to FullRerun (log advisory `incremental_fallback_to_fullrerun` in AnalysisPass execution_warnings; re-invoke Stage 2 on the FullRerun path).

**AI model fingerprinting:**
Record `ai_model_fingerprints` on AnalysisPass: `{stage: "stage2_primary", model: "claude-sonnet-4-20250514", input_tokens: N, output_tokens: M}`. This is the same fingerprinting pattern as Pass 3b Stage 3a.

**LPM constraint enforcement:**
The prompt explicitly instructs the AI: "Do NOT copy CCI description text verbatim as Domain descriptions." This is the LPM constraint at the prompt level. Stage 3 does not perform automated verbatim-copy detection — this is a plausibility criterion (PLB-3c-05) for Practitioner review.

### 4.3 Stage 3 — Structural Validation (DM, with conditional IM repair)

All six checks run in sequence on the parsed AI proposal. All are pure in-memory operations on the validated Pydantic object — no database calls in this stage (except the repair prompt AI call, which is IM conditional).

**IncrementalRerun assign-action handling:** On IncrementalRerun, Stage 2 produces two outputs: (1) `domain_entities` — new Domain proposals (action="new"), passed to Stage 4 for entity construction; (2) `assign_membership_inserts` — a list of `(existing_domain_id, new_ci_id)` tuples derived from action="assign" outputs. `assign_membership_inserts` is an in-memory structure produced during Stage 2 output processing. It is **not written in Stage 3** — Stage 3 has no DB calls of any kind. It is passed to Stage 4 and written inside the Stage 4 transaction (see §4.4.4 step 3b).

**CHK-3c-01 — No empty cci_refs:**
For each proposed Domain: if `len(cci_refs) == 0`, reject the Domain. Record `{check_id: "CHK-3c-01", domain_name: name, detail: "empty cci_refs"}` in `domain_data.validation_failures`. If all Domains are rejected: treat as Stage 2 parse failure; invoke one retry. Persistent failure: `execution_status = "Failed"`.

**CHK-3c-02 — All cci_refs resolve to eligible set:**
Compute `eligible_ci_ids = {c.ci_id for c in eligible_ccis}`. For each proposed Domain: remove any `cci_refs` entry not in `eligible_ci_ids` (invalid ref). Log stripped entries in `validation_failures`. If after stripping a Domain's `cci_refs` is empty: reject the Domain (same logging as CHK-3c-01).

**CHK-3c-03 — No duplicate Domain names:**
If two or more proposed Domains share the same `name` (case-insensitive): merge them (union of `cci_refs`; retain first `description` and `classification_type`). Record advisory in AnalysisPass `execution_warnings`: `{type: "duplicate_domain_name_merged", domain_name: name}`.

**CHK-3c-04 — Non-Loss (every CCI covered):**
Compute `covered = {ref for p in proposals for ref in p.cci_refs}`. Compute `orphaned = eligible_ci_ids - covered`.
If `orphaned` is non-empty: invoke repair prompt (IM sub-act).

Repair prompt invocation:
- Assemble `domain_repair_prompt.py` with: `orphaned_ccis` (list of `{ci_id, column, classification_type, description}`), `current_proposals` (list of `{name, description, cci_ref_count}`).
- Parse response against `domain_repair_response_schema.py` (action-based schema — see §5.2). One attempt only (no retry on repair prompt — persistent failure is recorded, not retried).
- Merge repair response into proposals using action-based logic:
  - For `action="assign"` entries: match `domain_name` case-insensitively against existing proposals; add `new_cci_refs` to the matched proposal's `cci_refs`. If no match: treat as `action="new"` (advisory logged: `{type: "repair_assign_name_not_found", domain_name: name}`).
  - For `action="new"` entries: add the new Domain proposal to the proposals list.
- Re-compute `covered` and `orphaned` after merge.
- Record `repair_prompt_issued = true` in `domain_data`.
- Record repair AI fingerprint: `{stage: "stage3_repair", model: "claude-sonnet-4-20250514", input_tokens: N, output_tokens: M}`.

If `orphaned` is still non-empty after repair:
- Record all persistent orphaned ci_ids in `domain_data.orphaned_ccis`.
- Set `execution_status = "CompletedWithWarnings"`.
- Raise Concern entity (CNNNN): `description = "Pass 3c Domain Derivation: {N} CCI(s) could not be assigned to any Domain after repair attempt. Practitioner review required. Orphaned ci_ids: {list}"`, `source_refs = [orphaned ci_ids]`. The `practitioner_id` field on the Concern is sourced from the `practitioner_id` parameter passed to the mechanism's `run()` entry point — the same parameter pattern used by Pass 3a (Row-Lens Source Re-Analysis). The orchestrator supplies this value from the active session context.
- Continue to Stage 4 (committed Domain set excludes persistent orphans — they are not assigned to any Domain).

**CHK-3c-05 — Cross-cutting advisory:**
For each ci_id in `eligible_ci_ids`: count how many proposals include it in `cci_refs`. If `count > domain_cross_cutting_advisory_threshold`: record advisory `{ci_id: ci_id, domain_count: count}` in `domain_data.cross_cutting_advisories`. Not a failure.

**CHK-3c-06 — At least one Domain survives:**
If `len(proposals) == 0` after CHK-3c-01 through CHK-3c-04: this is a degenerate failure (all proposals rejected). `execution_status = "Failed"`, `failure_reason = "zero domains survived structural validation"`. Exit.

### 4.4 Stage 4 — Entity Production and Ledger Commit (DM)

**4.4.1 domain_id allocation:**
Query `MAX(CAST(SUBSTRING(domain_id, 2) AS INTEGER)) FROM domain WHERE project_id = current_project` (includes retired Domains — `retired_at IS NOT NULL`). If null (no prior Domains): `next_seq = 1`. Else: `next_seq = max_val + 1`. Allocate D001, D002, ... incrementally across the proposals.

On `IncrementalRerun`: existing active Domains retain their domain_ids. Only new Domains (from `action="new"` repair entries or new Domain proposals in the incremental AI response) receive new ids from `next_seq`.

On `FullRerun`: record `domain_count_retired` = count of currently active Domains for this row/project. Set `retired_at = NOW()` on all active Domains for this row/project. Then allocate fresh domain_ids for all proposals from `next_seq`.

**4.4.2 domain_qualifier assignment:**
Apply deterministic mapping from `row_abstraction_vocabulary.py` (or inline constant — either is acceptable):

```
QUALIFIER_MAP = {"1": "Conceptual", "2": "Conceptual", "3": "Logical",
                 "4": "Physical", "5": "Physical", "6": "Physical"}
qualifier = QUALIFIER_MAP[str(row_ref)]
```

**4.4.3 upstream_domain_ref heuristic (Row 3 only):**
If `str(row_ref) == "3"`:
Query all active Row 2 Domains for this project (`row_target = "2"`, `retired_at IS NULL`).
For each Row 3 proposal, compute Jaccard token overlap between `proposal.name.lower().split()` and each Row 2 Domain name's token set. If best overlap ≥ `domain_upstream_match_threshold` (default 0.50): set `upstream_domain_ref = best_match.domain_id`. Else: `upstream_domain_ref = null`; record `domain_id` in `domain_data.unmatched_upstream_refs`.

If `str(row_ref) != "3"`: `upstream_domain_ref = null` for all Domains (no heuristic applied at other rows).

**4.4.4 Ledger transaction:**
Open a single Postgres transaction. Within the transaction:
1. For `FullRerun`: execute `UPDATE domain SET retired_at = NOW() WHERE project_id = current_project AND row_target = str(row_ref) AND retired_at IS NULL`.
2. `INSERT INTO domain (domain_id, project_id, name, description, classification_type, row_target, domain_qualifier, upstream_domain_ref)` for each new Domain entity (action="new" proposals only).
3a. `INSERT INTO domain_cci_membership (domain_id, project_id, ci_id)` for each (domain_id, ci_id) pair in the **new Domain** proposals (memberships for newly created Domains).
3b. **IncrementalRerun only:** `INSERT INTO domain_cci_membership (domain_id, project_id, ci_id)` for each `(existing_domain_id, new_ci_id)` in `assign_membership_inserts`. This list is produced in-memory during Stage 2 output processing and passed to Stage 4. It is **not** written in Stage 3 — Stage 3 has no DB calls. If `assign_membership_inserts` is empty or scenario is not IncrementalRerun, this step is skipped.
4. `UPDATE register SET member_ids = :new_member_ids WHERE register_type = 'Domain' AND project_id = current_project` — where `new_member_ids` is the JSON array of **all active domain_ids across all rows for this project**. The DomainRegister is a project-level register, not a row-level register. The query that collects `new_member_ids` MUST be `SELECT domain_id FROM domain WHERE project_id = :pid AND retired_at IS NULL` — **no `row_target` filter**. Scoping this query to `row_target = str(row_ref)` is a common mistake that would silently drop Domains from other rows from the register.

If the transaction rolls back (constraint violation, connection failure): `execution_status = "Failed"`, `failure_reason = "Ledger transaction rolled back: {error}"`. No partial commit. Domain entities and DomainRegister remain as they were before Stage 4.

**4.4.5 FullRerun retirement mapping:**
**Timing is critical:** The `retirement_mapping` must be computed **before** the retirement UPDATE runs, using the pre-retirement active domain list. Capture `prior_active_domains = query_active_domains_for_row(row_ref, project_id)` before opening the ledger transaction. Then compute name-similarity matches between `prior_active_domains` and the new proposals (same Jaccard heuristic, same `domain_upstream_match_threshold`). Record `{old_domain_id: "D001", inferred_successor_domain_id: "D007"}` or `{old_domain_id: "D002", inferred_successor_domain_id: null}` for each retiring Domain. Store in `domain_data.retirement_mapping`. Only then open the transaction and execute the retirement UPDATE. Computing `retirement_mapping` after the UPDATE (`retired_at IS NOT NULL` filter would exclude the domains just retired) is an implementation error.

**4.4.6 downstream_rerun_required flag:**
If `scenario == "FullRerun"`: query whether any AnalysisPass with `mechanism="RequirementDerivation"` and `row_ref = current_row` and `project_id = current_project` exists with `execution_status ∈ {"Completed", "CompletedWithWarnings"}`. If yes: set `domain_data.downstream_rerun_required = true`. Else: `false`.

**4.4.7 AnalysisPass write:**
Write outside the main ledger transaction (same pattern as Pass 3b Step 6). Populate all fields of `domain_data` per §7. AnalysisPass `execution_status` reflects the Stage 3 outcome: `Completed` if no warnings/orphans; `CompletedWithWarnings` if orphans, advisories, or IncrementalRerun fallback occurred; `Failed` only if a hard stop was hit. On `Skipped` (IdempotentRerun): the AnalysisPass is written with `execution_status = "Skipped"` and minimal `domain_data` (hash, scenario, counts from query — no domain production fields populated beyond zero values).

---

## 5. Schema and Validation

### 5.1 SQLAlchemy / Pydantic models and Database DDL

**Database DDL — `domain` table:**

The authoritative CREATE TABLE statement for the Alembic migration. This is the canonical DDL — it supersedes all earlier versions in Understanding §13.8 documents.

```sql
CREATE TABLE domain (
    domain_id            VARCHAR(10)  NOT NULL,   -- D### format; regex ^D\d{3}$
    project_id           VARCHAR(50)  NOT NULL,   -- composite PK component
    name                 TEXT         NOT NULL,
    description          TEXT         NOT NULL,
    classification_type  TEXT,                    -- nullable; optional attribute
    row_target           VARCHAR(1)   NOT NULL
                             CHECK (row_target IN ('1','2','3','4','5','6')),
    domain_qualifier     VARCHAR(12)  NOT NULL
                             CHECK (domain_qualifier IN ('Conceptual','Logical','Physical')),
    upstream_domain_ref  VARCHAR(10),             -- nullable; self-referential FK (see constraint below)
    retired_at           TIMESTAMPTZ,             -- null = active; non-null = retired (FullRerun soft-delete)
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    PRIMARY KEY (domain_id, project_id),

    -- Self-referential FK: Row 3 Domains reference Row 2 Domains in the same project.
    -- DEFERRABLE INITIALLY DEFERRED: on FullRerun, new Row 3 Domains may be inserted
    -- before their referenced Row 2 Domains are committed in the same transaction.
    -- ON DELETE RESTRICT: retiring a Row 2 Domain must not cascade-delete Row 3 Domains.
    CONSTRAINT fk_upstream_domain
        FOREIGN KEY (upstream_domain_ref, project_id)
        REFERENCES domain (domain_id, project_id)
        ON DELETE RESTRICT
        DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE domain_cci_membership (
    domain_id   VARCHAR(10) NOT NULL,
    project_id  VARCHAR(50) NOT NULL,
    ci_id       VARCHAR(60) NOT NULL,
    PRIMARY KEY (domain_id, project_id, ci_id),
    FOREIGN KEY (domain_id, project_id) REFERENCES domain(domain_id, project_id),
    FOREIGN KEY (ci_id, project_id)     REFERENCES cell_content_item(ci_id, project_id)
);

-- DomainRegister seed row (one per project, seeded at migration time)
INSERT INTO register (register_id, register_type, project_id, member_ids, completeness_rule)
VALUES ('DR-001', 'Domain', :project_id, '[]',
        'This register SHALL contain the identifiers of ALL Domain elements present in the ledger.');
-- member_ids is updated as a JSONB array on every Pass 3c run;
-- always derived from query_all_active_domain_ids(project_id), never hardcoded.
```

**Migration author notes:**
- `cell_content_item_refs` is normalised as `domain_cci_membership` (join table), not a JSONB array. Enables efficient bidirectional queries; enforces FK integrity.
- `retired_at IS NULL` = active Domain. All active-Domain queries must include this filter. `query_max_domain_id` must NOT filter on `retired_at` — retired ids must be counted to prevent reuse.
- Self-referential FK with Alembic: create the table first (no FK), then `op.create_foreign_key()` in the same revision. Alembic handles self-referential constraints correctly in this pattern.
- Migration file: `migrations/XXXX_add_domain_tables.py`.

**`DomainModel` (SQLAlchemy ORM — `domain` table):**
Maps to the DDL above. Key attributes:
- `domain_id`: String, PK component; CHECK `domain_id ~ '^D\d{3}$'`
- `project_id`: String, PK component
- `name`: String NOT NULL
- `description`: Text NOT NULL
- `classification_type`: String nullable
- `row_target`: String NOT NULL; CHECK IN ('1','2','3','4','5','6')
- `domain_qualifier`: String NOT NULL; CHECK IN ('Conceptual','Logical','Physical')
- `upstream_domain_ref`: String nullable; FK to `domain.domain_id` (same project); DEFERRABLE INITIALLY DEFERRED
- `retired_at`: TIMESTAMPTZ nullable; null = active; non-null = retired
- `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- Composite PK: `(domain_id, project_id)`

**`DomainCCIMembershipModel` (SQLAlchemy ORM — `domain_cci_membership` table):**
- `domain_id`: String; FK to `domain(domain_id, project_id)`
- `project_id`: String; part of composite FK
- `ci_id`: String; FK to `cell_content_item(ci_id, project_id)`
- Composite PK: `(domain_id, project_id, ci_id)`

**`DomainSchema` (Pydantic — canonical ledger API representation):**
Mirrors the canonical ledger v2.12 Domain element. Produced from `DomainModel` JOIN `DomainCCIMembershipModel` for serialisation:
```
domain_id:              str  — regex ^D\d{3}$
name:                   str
description:            str
classification_type:    Optional[str]
row_target:             str  — Literal["1","2","3","4","5","6"]
cell_content_item_refs: List[str]  — assembled from domain_cci_membership query
domain_qualifier:       Literal["Conceptual","Logical","Physical"]
upstream_domain_ref:    Optional[str]
```

### 5.2 AI response schemas (Pydantic)

**`domain_grouping_response_schema.py` — primary grouping (FirstRun / FullRerun):**
```
Response root: List[DomainProposal]

DomainProposal:
  name:                str  (minLength=2, maxLength=60)
  description:         str  (minLength=10)
  classification_type: Optional[str]
  cci_refs:            List[str]  (minItems=1)
```
Validation: `name` must not be empty; `cci_refs` must be non-empty; `description` must be non-empty. Parse is strict — extra fields rejected.

**`domain_incremental_response_schema.py` — IncrementalRerun:**
```
Response root: List[DomainIncrementalAction]

DomainIncrementalAction (discriminated union on `action`):
  action: Literal["assign"] → AssignAction:
    domain_id:    str  — must match ^D\d{3}$
    new_cci_refs: List[str]  (minItems=1)
  action: Literal["new"]    → NewDomainAction:
    name:                str
    description:          str
    classification_type:  Optional[str]
    cci_refs:             List[str]  (minItems=1)
```
Validation: for `assign` actions, `domain_id` must reference an existing active Domain for this row/project (checked post-parse in Stage 3). Invalid `domain_id` in an `assign` action → converted to `new` action with the same name as the referenced Domain (advisory logged).

**`domain_repair_response_schema.py` — repair prompt:**
Action-based, identical in shape to `domain_incremental_response_schema.py`. The repair response is a **delta**, not a full replacement of the proposal set. The AI returns a list of actions (assign existing ci_ids to an existing Domain, or propose a new Domain for orphaned ci_ids). The merge logic in Stage 3 (§4.3) applies these actions to the existing proposal set.

```
Response root: List[DomainRepairAction]

DomainRepairAction (discriminated union on `action`):
  action: Literal["assign"] → AssignAction:
    domain_name:  str  — name of the existing Domain to assign to (matched case-insensitively)
    new_cci_refs: List[str]  (minItems=1)  — orphaned ci_ids to add
  action: Literal["new"]    → NewDomainAction:
    name:                str
    description:          str
    classification_type:  Optional[str]
    cci_refs:             List[str]  (minItems=1)  — must include only orphaned ci_ids
```

**IMPORTANT — distinct Pydantic classes, do not share:** The `AssignAction` in this schema uses `domain_name: str`. The `AssignAction` in `domain_incremental_response_schema.py` uses `domain_id: str`. These are different fields on classes that share a name. They MUST be defined as separate classes in separate schema files and must never be imported across files. Sharing or aliasing them will cause silent field-mismatch bugs where the wrong key is used during merge.

Note: the repair prompt uses `domain_name` (string) rather than `domain_id` to reference existing Domains, because the AI has only seen Domain names in the repair prompt context. Stage 3 resolves the name to a proposal in memory by case-insensitive match. If the name does not match any existing proposal: treat as `"new"` action (advisory logged).

### 5.3 Identifier conventions

- Domain: `D###` — global per-project sequence; zero-padded 3 digits; allocated in Stage 4.4.1; never reused. **Known constraint:** this format supports a maximum of 999 Domain instances per project (D001–D999, including retired Domains since ids are not reused). For projects with many FullRerun cycles or very large CCI sets, this ceiling could be approached. Tracked as a known v0.1 limitation — if a project exceeds 800 allocated ids, raise a new tracker finding for a format extension (e.g., D#### for 4-digit sequences).
- DomainRegister: single register per project; `register_id` assigned at project creation (migration seeds it).
- AnalysisPass: `P###` — global sequence, same as all other mechanisms; allocated by the common AnalysisPass writer utility.

### 5.4 `row_abstraction_vocabulary.py` — canonical content

This module is the single source of truth for the row-target → abstraction level phrase and Domain qualifier label mapping. The Row 4 Mechanism Spec defines the concrete content:

```python
ROW_ABSTRACTION_VOCABULARY = {
    "1": {
        "abstraction_level_phrase": (
            "enterprise contextual scope — strategic boundaries, compliance, "
            "and high-level operational context"
        ),
        "domain_qualifier_label": "Conceptual Domain",
    },
    "2": {
        "abstraction_level_phrase": (
            "business conceptual level — business processes, entities, "
            "roles, events, and rules"
        ),
        "domain_qualifier_label": "Conceptual Domain",
    },
    "3": {
        "abstraction_level_phrase": (
            "logical design level — logical structures, behaviours, interactions, "
            "and state models; technology-agnostic"
        ),
        "domain_qualifier_label": "Logical Domain",
    },
    "4": {
        "abstraction_level_phrase": (
            "physical builder level — specific technologies, components, "
            "deployment targets, and implementation patterns"
        ),
        "domain_qualifier_label": "Physical Domain",
    },
    "5": {
        "abstraction_level_phrase": (
            "detailed design level — algorithms, data formats, implementation "
            "specifications, and detailed configurations"
        ),
        "domain_qualifier_label": "Physical Domain",
    },
    "6": {
        "abstraction_level_phrase": (
            "operational level — runtime procedures, user interactions, "
            "support processes, and operational behaviours"
        ),
        "domain_qualifier_label": "Physical Domain",
    },
}
```

This dict is imported by `domain_grouping_prompt.py`, `domain_incremental_prompt.py`, and `stage4_entity_production.py` (for the QUALIFIER_MAP). It must not be duplicated elsewhere.

---

## 6. Mode Discipline Realisation

Pass 3c uses the mode discipline decorator pattern established at Row 4 Applied §4.7.

| Stage / Sub-act | Declared mode | Decorator constraint | AnalysisPass record |
|---|---|---|---|
| Stage 1 — Pre-flight | DM | No AI calls permitted | `mode_active: ["DM"]` |
| Stage 2 — Primary AI grouping | IM | AI call required; LPM on CCI text | `mode_active: ["IM"]`; fingerprint recorded |
| Stage 2 — Retry (if parse failure) | IM | Second AI call; same constraint | Retry fingerprint appended |
| Stage 3 — Structural checks (CHK-3c-01..06) | DM | No AI calls (except repair sub-act) | `mode_active: ["DM"]` |
| Stage 3 — Repair prompt (conditional IM) | IM | AI call; `repair_prompt_issued = true` | Repair fingerprint recorded separately |
| Stage 4 — Entity production | DM | No AI calls; ledger write | `mode_active: ["DM"]` |

**Mode violations** (a DM stage making an AI call, or an IM stage making no AI call when one was required) are recorded in `domain_data.mode_violations` as `[{stage: str, violation_type: str, detail: str}]` and set `execution_status = "CompletedWithWarnings"`.

**LPM constraint** applies throughout: CCI `description` text is passed to the AI as read-only context. The AI is instructed not to reproduce CCI descriptions verbatim in Domain descriptions. The LPM constraint is enforced at the prompt instruction level (§4.1.2 of the Row 3 Mechanism Spec). Automated detection of verbatim copy is not implemented at v0.1 — deferred to a future tracker finding if empirical evidence shows LPM violations are occurring.

---

## 7. Audit Trail Population

The AnalysisPass `outputs` JSONB field for mechanism `"DomainDerivation"` has the following structure. All fields are required. Zero-value arrays must be present as `[]`, not null, not omitted.

```jsonc
{
  "domain_data": {
    // --- Stage 1 fields ---
    "run_scenario":                  "FirstRun",           // string: one of four scenario names
    "cci_set_hash":                  "<sha256-hex>",       // SHA-256 of sorted ci_id list
    "cci_count_input":               7,                    // integer; 0 on zero-CCI exit
    "large_cci_set_advisory":        false,                // boolean

    // --- Stage 2 fields ---
    // (populated after AI call; zero-values if Stage 2 not reached)

    // --- Stage 3 fields ---
    "repair_prompt_issued":          false,                // boolean
    "orphaned_ccis":                 [],                   // List[str] ci_ids of persistent orphans
    "cross_cutting_advisories":      [],                   // List[{ci_id, domain_count}]
    "validation_failures":           [],                   // List[{check_id, domain_name, detail}]

    // --- Stage 4 fields ---
    "domain_count_produced":         3,                    // integer; 0 on Skipped/Failed
    "domain_count_retired":          0,                    // integer; non-zero on FullRerun only
    "domains_produced": [                                  // List of per-domain summaries
      {
        "domain_id":               "D001",
        "name":                    "Pocket Money Management",
        "cci_ref_count":           4,
        "cross_cutting_cci_count": 0                       // CCIs appearing in >1 Domain
      }
    ],
    "unmatched_upstream_refs":       [],                   // List[str] domain_ids with no Row 2 match
    "downstream_rerun_required":     false,                // boolean
    "retirement_mapping":            [],                   // List[{old_domain_id, inferred_successor}]
                                                           // non-empty on FullRerun only

    // --- Mode discipline ---
    "mode_violations":               [],                   // List[{stage, violation_type, detail}]

    // --- AI fingerprints (all IM calls for this run) ---
    "ai_model_fingerprints": [
      {
        "stage":         "stage2_primary",
        "model":         "claude-sonnet-4-20250514",
        "input_tokens":  450,
        "output_tokens": 280
      }
      // Additional entries for retry and/or repair prompt, if issued
    ]
  }
}
```

The `ai_model_fingerprints` array accumulates entries for every IM call made during the run: Stage 2 primary, Stage 2 retry (if issued), Stage 3 repair (if issued). Each entry records `stage`, `model`, `input_tokens`, `output_tokens`. On `Skipped` runs, `ai_model_fingerprints` is `[]`.

---

## 8. Verification Criteria

### 8.1 Decidable criteria (automated — pytest)

All implemented in `tests/test_domain_derivation.py`. Tests use the Neon PostgreSQL test database with transaction rollback for isolation (same pattern as `tests/test_cci_construction.py`).

| ID | Criterion | pytest assertion |
|---|---|---|
| **VER-3c-01** | All `domain_id` values match `^D\d{3}$` | `re.fullmatch(r'^D\d{3}$', d.domain_id)` for all domains in project |
| **VER-3c-02** | All `domain_id` values unique within project (active + retired) | `len(set(ids)) == len(ids)` |
| **VER-3c-03** | Every Domain has ≥1 row in `domain_cci_membership` | COUNT query per domain_id ≥ 1 |
| **VER-3c-04** | All ci_ids in `domain_cci_membership` resolve to `cell_content_item` with matching `row_target` | JOIN check: `cell_content_item.zachman_cell.row_target == domain.row_target` |
| **VER-3c-05** | Every eligible CCI ci_id appears in at least one `domain_cci_membership` row | Set difference: `eligible_ci_ids - covered_ci_ids == empty` |
| **VER-3c-06** | DomainRegister `member_ids` contains exactly the active domain_ids for this project | Query active Domains across all rows (`retired_at IS NULL`, no `row_target` filter); assert set equality with register `member_ids`. **Test care:** single-row fixtures (§9.1–9.7) pass this trivially. Integration tests that exercise Row 2 then Row 3 in the same project must assert the register contains Domains from both rows — scoping the assertion to `row_target = current_row` is incorrect and masks the cross-row register update. |
| **VER-3c-07** | AnalysisPass with `mechanism="DomainDerivation"` and `row_ref=current_row` exists | Presence query |
| **VER-3c-08** | `AnalysisPass.outputs.domain_data` present; all required fields non-null | Schema validation against expected field list |
| **VER-3c-09** | `domain_qualifier` matches deterministic mapping for `row_target` | Assert `QUALIFIER_MAP[d.row_target] == d.domain_qualifier` for all active domains |
| **VER-3c-10** | On IdempotentRerun: domain_ids and `domain_cci_membership` rows unchanged | Snapshot before/after run; assert equality |
| **VER-3c-11** | On FullRerun: `domain_count_retired` equals pre-run active Domain count for this row | Query active count before run; assert equals `domain_data["domain_count_retired"]` |
| **VER-3c-12** | `domain_count_produced ≥ 1` when `cci_count_input > 0` | Conditional assertion |

### 8.2 Plausibility checklist for Practitioner review

Corresponds to PLB-3c-01..06 from Row 3 Mechanism Spec §8.2.

1. **PLB-3c-01 — Domain names:** Select all Domain names for the row. No name should be generic ("Miscellaneous", "Other", "General", "Uncategorised"). Each name should reflect a recognisable architectural responsibility. If any generic name appears, review the AI grouping prompt for the run and consider a FullRerun after improving the `abstraction_level_phrase`.

2. **PLB-3c-02 — Column span:** For each Domain, query `domain_cci_membership` and group by `cell_content_item.zachman_cell.column`. A Domain containing CCIs from only one column is flagged for review. Exception: a Why-only Domain (pure constraint domain) may be architecturally valid — verify intentionality.

3. **PLB-3c-03 — Domain count:** For PMT Row 2 (approx 7–12 CCIs): expect 2–4 Domains. For NQPS Row 3 (approx 4 CCIs): expect 1–2 Domains. The soft advisory bounds implemented in Stage 3 (OQ-3c-01 resolution: advisory if `domain_count < 1 + ceil(cci_count / 15)` or `domain_count > cci_count / 2`) are a starting heuristic. Review `domain_data.large_cci_set_advisory` and `domain_count_produced` together.

4. **PLB-3c-04 — Cross-cutting CCIs:** Review `domain_data.cross_cutting_advisories`. For each entry: is the CCI genuinely cross-cutting (e.g., an audit constraint that applies to all capabilities)? If a What-column Entity CCI appears in every Domain, Domain boundaries are likely too coarse — consider a FullRerun with a modified prompt.

5. **PLB-3c-05 — Row-appropriate vocabulary:** For Row 3 Domains, verify descriptions use logical-design vocabulary (logical structure, logical behaviour, state management, interface). Absence of business vocabulary ("stakeholders", "strategic objective") and implementation vocabulary ("database table", "API endpoint") is a positive signal. For Row 2 Domains, verify business vocabulary (process, entity, rule, role).

6. **PLB-3c-06 — upstream_domain_ref plausibility (Row 3 only):** Review `domain_data.unmatched_upstream_refs`. For each unmatched Row 3 Domain: is there a plausible Row 2 Conceptual Domain it could trace to? If yes, the `domain_upstream_match_threshold` may need lowering — record in tracker. If no: the Row 3 Domain may represent a new logical concern with no Row 2 counterpart (valid outcome, especially for cross-cutting logical concerns).

---

## 9. Test Fixtures

### 9.1 Fixture 1 — PMT Row 2: FirstRun happy path

**Test function:** `test_pmt_row2_firstrun`
**AI stub:** Returns a hardcoded `DomainProposal` list grouping the 7 PMT CCIs into 3 Domains:
- `"Pocket Money Transaction Management"`: CCI-ROW2-C-What-001, CCI-ROW2-C-What-002, CCI-ROW2-C-How-001
- `"Parental Oversight and Approval"`: CCI-ROW2-C-How-002, CCI-ROW2-C-Who-002, CCI-ROW2-C-Why-001
- `"Child Account Holder"`: CCI-ROW2-C-Who-001

**Pre-conditions in test DB:**
- `row_ref = 2`, `project_id = "PMT-TEST"`
- Pass 3b AnalysisPass present with `execution_status = "Completed"`
- 7 CCIs seeded (as per Row 3 Mechanism Spec §9.1 fixture)
- No prior Domain Derivation AnalysisPass

**Assertions:**
- VER-3c-01, VER-3c-02, VER-3c-03, VER-3c-04, VER-3c-05, VER-3c-06, VER-3c-07, VER-3c-08 all pass
- VER-3c-09: `domain_qualifier == "Conceptual"` for all Domains
- VER-3c-12: `domain_count_produced == 3`
- `domain_data.run_scenario == "FirstRun"`
- `domain_data.repair_prompt_issued == false`
- `domain_data.orphaned_ccis == []`
- 3 domain_ids allocated starting from D001 (or next available)

### 9.2 Fixture 2 — NQPS Row 3: FirstRun, Logical qualifier

**Test function:** `test_nqps_row3_firstrun`
**AI stub:** Returns 2 Domains grouping 4 NQPS Row 3 CCIs:
- `"Quality Compliance Behaviour"`: CCI-ROW3-C-How-001, CCI-ROW3-C-Who-001
- `"ISO Standard Reference Structure"`: CCI-ROW3-C-What-001, CCI-ROW3-C-Why-001

**Pre-conditions:** `row_ref = 3`, `project_id = "NQPS-TEST"`, Pass 3b complete, 4 CCIs seeded.

**Assertions:**
- VER-3c-05, VER-3c-09 (`domain_qualifier == "Logical"`), VER-3c-12
- `domain_data.run_scenario == "FirstRun"`
- For Row 3: `upstream_domain_ref` is null for both Domains (no Row 2 Domains seeded in test DB for NQPS-TEST → both appear in `unmatched_upstream_refs`)

### 9.3 Fixture 3 — PMT Row 2: IdempotentRerun

**Test function:** `test_pmt_row2_idempotent_rerun`
**Setup:** Run Fixture 1 first (creates Domains D001–D003 and AnalysisPass P001). Then re-invoke Pass 3c with the same CCI set.

**AI stub:** Not invoked — Stage 1 detects IdempotentRerun and exits before Stage 2.

**Assertions:**
- VER-3c-10: domain_ids and `domain_cci_membership` rows identical to post-Fixture-1 state
- New AnalysisPass written with `execution_status = "Skipped"`, `run_scenario = "IdempotentRerun"`
- Stage 2 AI stub `assert_not_called()` — confirms no AI invocation occurred

### 9.4 Fixture 4 — PMT Row 2: IncrementalRerun with one new CCI

**Test function:** `test_pmt_row2_incremental_rerun`
**Setup:** Run Fixture 1 first. Then add one new CCI to the test DB:
- `CCI-ROW2-C-When-001`: `classification_type="BusinessEvent"`, `description="Weekly allowance payment event"`

**AI stub (incremental prompt):** Returns one `assign` action: `{action: "assign", domain_id: "D001", new_cci_refs: ["CCI-ROW2-C-When-001"]}` (assigning the new CCI to "Pocket Money Transaction Management").

**Assertions:**
- `domain_data.run_scenario == "IncrementalRerun"`
- VER-3c-05: all 8 CCIs (7 original + 1 new) now covered
- D001's `domain_cci_membership` now includes `CCI-ROW2-C-When-001`
- D002 and D003 membership unchanged
- `domain_data.downstream_rerun_required == false` (no Pass 3d has run)
- New AnalysisPass written; prior AnalysisPass (P001) unchanged

### 9.5 Fixture 5 — Non-Loss repair: orphaned CCI recovered

**Test function:** `test_noloss_repair_prompt_recovery`
**Setup:** PMT Row 2 FirstRun. AI stub (primary) returns only 2 Domains, omitting `CCI-ROW2-C-Why-001` from all proposals. CHK-3c-04 detects 1 orphaned CCI.

**AI stub (repair prompt):** Returns one `new` action: `{action: "new", name: "Transaction Approval Rules", description: "Constraint governing parental approval thresholds", cci_refs: ["CCI-ROW2-C-Why-001"]}`.

**Assertions:**
- `domain_data.repair_prompt_issued == true`
- `domain_data.orphaned_ccis == []` (orphan recovered by repair)
- VER-3c-05: all 7 CCIs covered
- `domain_count_produced == 3` (2 from primary + 1 from repair)
- `execution_status == "Completed"` (not CompletedWithWarnings — repair succeeded)
- `ai_model_fingerprints` has 2 entries: `stage2_primary` and `stage3_repair`

### 9.6 Fixture 6 — Persistent orphan after repair failure

**Test function:** `test_noloss_repair_persistent_orphan`
**Setup:** PMT Row 2 FirstRun. Primary AI stub omits `CCI-ROW2-C-Why-001`. Repair AI stub returns an empty proposal list (degenerate repair response — parse fails gracefully, repair merge produces no new coverage).

**Assertions:**
- `domain_data.repair_prompt_issued == true`
- `domain_data.orphaned_ccis == ["CCI-ROW2-C-Why-001"]`
- `execution_status == "CompletedWithWarnings"`
- VER-3c-05 **fails** — this is expected and asserted to fail in this fixture (the test verifies the orphan is *recorded*, not that it is covered)
- A Concern entity CN-NNN exists in the DB for this project/row with description referencing the orphaned CCI

### 9.7 Fixture 7 — FullRerun: domain_id retirement and fresh allocation

**Test function:** `test_pmt_row2_fullrerun`
**Setup:** Run Fixture 1 (Domains D001–D003 active). Then add 2 new CCIs (pushing `new_cci_count / prior_cci_count` above threshold 0.20). Set `domain_rerun_threshold = 0.20` in ProjectProfile. Invoke Pass 3c.

**AI stub (primary, FullRerun):** Returns 3 new Domain proposals grouping all 9 CCIs.

**Assertions:**
- `domain_data.run_scenario == "FullRerun"`
- D001, D002, D003 now have `retired_at IS NOT NULL`
- 3 new active Domains allocated starting from D004 (next available after D003)
- VER-3c-11: `domain_count_retired == 3`
- VER-3c-05: all 9 CCIs covered by new Domains
- `domain_data.retirement_mapping` has 3 entries (one per retired Domain, with `inferred_successor_domain_id` populated if name similarity ≥ 0.50)
- `domain_data.downstream_rerun_required == false` (no Pass 3d has run in test setup)

---

## 10. Edge Cases

All edge cases from Row 3 Mechanism Spec §10 have the following implementation handling:

| Edge case | Implementation handling |
|---|---|
| **Zero CCIs for the row** | Stage 1 exits early after writing AnalysisPass (`CompletedWithWarnings`, warning `no_cci_input`) and updating DomainRegister with `member_ids = query_all_active_domain_ids(project_id)` (project-wide active Domain set — **not** `member_ids = []` unconditionally). Stage 2 not invoked. See §4.1 for the full early-exit behaviour. |
| **Single CCI for the row** | Stage 2 receives a one-CCI list. AI stub in Fixture: AI returns one Domain containing the single CCI. VER-3c-03 passes. Stage 3 CHK-3c-05 advisory not triggered (domain_count == 1, cannot exceed threshold). PLB-3c-02 advisory flagged (single-column, single-CCI Domain). |
| **AI proposes one Domain for all CCIs** | Structurally valid; CHK-3c-01..06 all pass. PLB-3c-03 advisory fires if CCI count is large. Practitioner review via plausibility checklist. |
| **AI proposes more Domains than CCIs** | Some Domains will fail CHK-3c-01 (empty after CHK-3c-02 stripping) or will not survive CHK-3c-02. `validation_failures` populated. If all Domains rejected → CHK-3c-06 triggers failure path. |
| **AI parse failure on retry** | `execution_status = "Failed"`; `failure_reason = "AI grouping response parse failure after retry"`. No Domains committed. AnalysisPass written with Failed status. |
| **IncrementalRerun AI parse failure → FullRerun fallback** | Advisory `incremental_fallback_to_fullrerun` logged. Stage 2 re-invoked on FullRerun path. If FullRerun also fails: `execution_status = "Failed"`. |
| **FullRerun with existing Pass 3d complete** | `downstream_rerun_required = true` in AnalysisPass. Orchestrator surfaces advisory to Practitioner. Pass 3d is NOT automatically re-triggered. Dangling `Requirement.domain_refs` remain until Practitioner initiates Pass 3d re-run. |
| **Row 3 — no Row 2 Domains exist** | `upstream_domain_ref = null` for all Row 3 Domains. All domain_ids appear in `unmatched_upstream_refs`. Valid outcome — Row 2 Domains may not yet have been produced, or may not exist for this project. |
| **Repair prompt AI response is empty list** | Persistent orphan path. Orphaned ci_ids recorded. `execution_status = "CompletedWithWarnings"`. Concern raised. Entity production proceeds on surviving Domains. |
| **FullRerun retirement transaction rollback** | If the UPDATE (retirement) or INSERT (new Domains) rolls back: Domains remain in their pre-run state. AnalysisPass written with `execution_status = "Failed"`. No partial retirement — atomicity guaranteed by single transaction. |
| **DomainRegister UPDATE conflict** | If no DomainRegister seed row exists (migration not applied): `execution_status = "Failed"`, `failure_reason = "DomainRegister not found — migration may not have run"`. This is a deployment configuration error, not a runtime error. |
| **Large CCI set (>80)** | Advisory recorded; Stage 2 called with full CCI set as a single prompt. At v0.1, no chunking is implemented. If context limit is exceeded (Anthropic API returns a context length error): `execution_status = "Failed"`, `failure_reason = "AI context limit exceeded — CCI set too large for single call"`. Raise tracker finding for chunking extension. |
| **cross_cutting_advisory_threshold exceeded** | Advisory recorded in `cross_cutting_advisories`; not a failure. Entity production proceeds. PLB-3c-04 surfaces in Practitioner review checklist. |

---

## 11. Cross-Mechanism Interactions

### 11.1 Upstream

| Mechanism | What this mechanism consumes | Dependency type |
|---|---|---|
| **Pass 3b — CCI Construction** | `cell_content_item` rows for current row/project — the full CCI set is the sole analytical input to Stage 2. | Hard prerequisite — Pass 3b MUST have `execution_status ∈ {Completed, CompletedWithWarnings}`. Stage 1 enforces this; failure causes Pass 3c to abort. |
| **Phase 2 — Mechanism Activation** | `project_profile` row — provides four domain-specific parameters (§13.9 of Row 4 Understanding v0.11). | Soft prerequisite — ProjectProfile must exist. If any parameter is NULL, default value is substituted. |

### 11.2 Downstream

| Mechanism | What this mechanism produces for it | Dependency type |
|---|---|---|
| **Pass 3d — Requirement Derivation** | `domain` and `domain_cci_membership` rows — Pass 3d reads Domains and assigns `Requirement.domain_refs`. | Hard dependency — orchestrator checks for Pass 3c `execution_status ∈ {Completed, CompletedWithWarnings, Skipped}` before Pass 3d may begin. |
| **Phase 6 / Phase 8 — Domain Coverage Analysis** | `domain` and `domain_cci_membership` rows — Phase 6 Pass 1 / Phase 8 Pass 1 enumerate Domains as the analysis inventory. Coverage analysis is read-only with respect to Domains. | Analytical dependency — Domains must be committed before Phase 6/8 runs. |

### 11.3 Ledger coordination

Per Row 4 Applied §4.11: mechanisms coordinate via ledger reads, not direct calls. Pass 3c reads CCIs from the ledger; writes Domains, DomainRegister, and AnalysisPass in transactions at completion. Pass 3d reads Domains from the ledger; it does not call Pass 3c directly.

The orchestrator (`core/orchestrator.py`) enforces pass sequencing by querying AnalysisPass records before invoking each mechanism. No mechanism imports or calls another mechanism directly.

---

## 12. Build Notes

### 12.1 Tracker findings relevant to this build

| Finding | Status | Relevance |
|---|---|---|
| **F-3c-01** | Open | Pass 3c mode label in Row 2 v1.2 §3.9.3 records "DM + Robustness". Correct characterisation is IM-primary, DM-envelope (per Row 3 Mechanism Spec v0.1 §2 note). Row 2 Understanding amendment at next revision cycle. No implementation impact. |
| **F-3c-02** | Action-Required | Row 1 domain_qualifier default. This spec applies `QUALIFIER_MAP["1"] = "Conceptual"` — a reasonable default pending confirmation from Row 1 Understanding authors. **Urgency: this must be confirmed before the first Row 1 production run that produces Domains.** If the correct qualifier differs, a data migration will be required to update committed Row 1 Domain instances — far cheaper to confirm before any Row 1 Domains are written than after. The implementation proceeds with "Conceptual" as the working default; the tracker item (now F44) is Action-Required. |
| **F3** | Recommended Resolved | Domain Dual Relationship addressed by Row 3 Mechanism Spec v0.1 and this spec. Recommend Practitioner marks F3 Resolved after accepting these two artefacts. |

### 12.2 OQ resolutions committed at this spec

| OQ | Resolution in this spec |
|---|---|
| **OQ-3c-01** | Domain count soft bounds advisory implemented in Stage 3 via `stage3_structural_validation.py`: advisory if `domain_count < 1 + ceil(cci_count / 15)` or `domain_count > cci_count / 2`. Logged in `execution_warnings` with type `domain_count_advisory`. |
| **OQ-3c-02** | `domain_upstream_match_threshold` implemented as ProjectProfile parameter (default 0.50). Configurable per project. |
| **OQ-3c-03** | FullRerun retirement uses soft-delete (`retired_at` column). `query_max_domain_id` includes retired Domains. Active Domain query filters `retired_at IS NULL`. |

### 12.3 Replit Agent task structure

The Replit Agent handoff package for Pass 3c implementation:

**Primary input documents:**
- This spec (Row 4 Mechanism Spec — Domain Derivation v0.7) — implementation authority (all detail including DDL in §5.1)
- Row 3 Mechanism Spec v0.1 — architectural authority (especially §4 stage structure, §5 schema, §8 verification criteria, §9 test fixtures)
- Row 4 Understanding v0.11 §13 — framework (module structure, prose descriptions, ProjectProfile parameters, VER criteria mapping, fixture table)

**Reference documents:**
- Row 4 Applied v0.2 — common architectural commitments (stack, transactional discipline, mode decorator pattern, AnalysisPass writer utility)
- Row 4 Understanding v0.5 §12 — reference implementation patterns from Pass 3b (Pydantic boundary, AnalysisPass population, transactional discipline, AI stub pattern for tests)
- Canonical Ledger v2.12 — Domain and DomainRegister schemas

**Reference implementation:**
- `mechanisms/cci_construction/` — primary reference: AI invocation pattern, Pydantic response schema validation, AnalysisPass writer, transactional discipline
- `mechanisms/row_lens_source_reanalysis/` — secondary reference: mode decorator, AI model fingerprinting

**Build sequence for the Agent:**
1. Write Alembic migration: `add_domain_tables` — use the DDL from **this spec §5.1** (the authoritative CREATE TABLE statements for `domain`, `domain_cci_membership`, and the DomainRegister seed row, including `retired_at TIMESTAMPTZ`, `CONSTRAINT fk_upstream_domain`, CHECK constraints, and migration author notes). The DDL no longer lives in the Understanding.
2. Write `schemas/domain_grouping_response_schema.py`, `schemas/domain_incremental_response_schema.py`, `schemas/domain_repair_response_schema.py` (§5.2 of this spec)
3. Write `prompts/row_abstraction_vocabulary.py` (§5.4 of this spec — concrete dict content provided)
4. Write `prompts/domain_grouping_prompt.py`, `prompts/domain_incremental_prompt.py`, `prompts/domain_repair_prompt.py` using prompt templates from Row 3 Mechanism Spec §4.1
5. Write `stage1_preflight.py` through `stage4_entity_production.py` and `__init__.py` orchestrator
6. Write `tests/test_domain_derivation.py` with Fixtures 1–7 (§9 of this spec); AI stubs via monkeypatch
7. Run migration; run pytest; verify VER-3c-01 through VER-3c-12 all pass on Fixtures 1, 3, 4, 7
8. Verify Fixture 5 (repair recovery) and Fixture 6 (persistent orphan) match their specific assertions

**Deviations from Pass 3b pattern to watch for:**
- No Step 2 (ZachmanCell upsert) — Pass 3c does not produce ZachmanCells
- No batching loop in Stage 2 — single AI call, no `for batch in batches`
- `domain_cci_membership` table instead of JSONB array for `cell_content_item_refs`
- Soft-delete column `retired_at` on Domain table — not present on any prior entity table
- IncrementalRerun path in Stage 2 uses a different prompt template and response schema than FirstRun/FullRerun
- Repair prompt is a second AI call inside Stage 3, not part of Stage 2

---

## Document End

End of SysEngage Row 4 Mechanism: Domain Derivation v0.7.

Changes from v0.6 (sixth Agent review — Finding 1 significant, Finding 2 noted):
- **Finding 1 (§10):** Zero-CCI edge case table row corrected — `member_ids = []` replaced with `query_all_active_domain_ids(project_id)` and "do not hardcode" qualifier added. Now consistent with §4.1.
- **Finding 2 (§5.1, §12.3):** Full CREATE TABLE DDL (domain, domain_cci_membership, DomainRegister seed) inserted into §5.1 — Mechanism Spec is now the single authoritative DDL source. §5.1 cross-reference to Understanding removed. §12.3 step 1 updated from "see Understanding v0.8 §13.8" to "use this spec §5.1". Circular DDL reference eliminated.
- **Cross-references:** Understanding v0.10 → v0.11; tracker v0.32 → v0.33; self-reference v0.6 → v0.7.

Changes from v0.5: §4.1 zero-CCI DomainRegister write; §13 Understanding restructure reference.
Changes from v0.4: §4.3, §4.4.4 IncrementalRerun atomicity.
Changes from v0.3: §3.1 repair schema comment.
Changes from v0.2: three second-review notes.
Changes from v0.1: eleven first-review corrections.

Companion artefacts:
- SysEngage_Row_3_Mechanism_Domain_Derivation_v0_1.md — architectural authority (unchanged)
- SysEngage_Row_4_Understanding_v0_11.md — implementation framework (structural guidance only)
- SysEngage_Issues_Tracker_v0_33.md — finding disposition

Next artefact in sequence:
- SysEngage_Row_4_Mechanism_Domain_Derivation_v0_8.md — after Replit Agent build and first PMT/NQPS production run
