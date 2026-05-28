# SysEngage Row 4 Mechanism: Domain Derivation

**Implementation specification — depth tier (i)+**

Filename: SysEngage_Row_4_Mechanism_Domain_Derivation_v0_10.md

Version: 0.10 (eighth Agent review — four noted findings resolved: cci_refs added to repair assign-to-new fallback §4.3; invalid domain_id fallback name source corrected §5.2; domain count advisory added as ADVC-3c-01 in §4.3; execution_warnings placement clarified in §7. Understanding references updated to v0.14; tracker reference updated to v0.36)

Date: 26 May 2026

**Purpose.** Implementation specification for the Domain Derivation mechanism (Pass 3c). v0.10 closes four noted findings from the eighth Agent review, making the spec fully self-contained for implementation handoff. Supersedes v0.9.

**Excludes.** Per Row 4 Understanding §8.1: NO pseudo-code, NO function signatures, NO code-level interface definitions. Pseudocode in §13 of the Row 4 Understanding is framework guidance only; this spec does not repeat it.

---

## 1. Mechanism Identification

| Attribute | Value |
|---|---|
| **Mechanism name** | Domain Derivation |
| **Row 3 Mechanism Spec reference** | SysEngage_Row_3_Mechanism_Domain_Derivation_v0_1.md — all sections |
| **Operational location** | Phase 3 Pass 3c. Executes after Pass 3b (CellContentItem Construction) completes; before Pass 3d (Requirement Derivation). Four stages: Stage 1 (pre-flight + CCI assembly + re-run scenario detection, DM), Stage 2 (AI grouping act, IM), Stage 3 (structural validation + conditional repair, DM + IM conditional), Stage 4 (entity production + ledger commit, DM). |
| **Mechanism class** | AI-involving. IM-primary (Stage 2 AI grouping; Stage 3 conditional repair prompt). DM-envelope (Stage 1 pre-flight; Stage 3 structural checks; Stage 4 entity production, ledger write). LPM preservation constraint throughout — CCI descriptions are read, not rewritten. |
| **Module location** | `mechanisms/domain_derivation/` directory. See §3.1 for file structure. |
| **Row applicability** | Row-sequential. Runs once per active row. |
| **Mechanism Stakeholder** | None. SH001 covers structural review. SG-01 covers Practitioner quality review. SG-03 carries execution attribution via AnalysisPass. |

---

## 2. Cross-References

| Source | Reference | What this provides |
|---|---|---|
| **Row 3 Mechanism Spec v0.1** | All sections | Architectural authority: four-stage pass structure, six structural checks (CHK-3c-01..06), Non-Loss enforcement, repair prompt pattern, re-run scenarios, verification criteria, plausibility criteria, test fixtures, edge cases. Note: domain_qualifier and upstream_domain_ref referenced in v0.1 are withdrawn in this spec — row_target is sufficient; cross-row tracing navigates CCI → Requirement → Domain. |
| **Row 4 Understanding v0.14** | §13 | Pass 3c implementation framework: module structure (row_abstraction_vocabulary.py absent), re-run scenarios (prose), ProjectProfile parameters (three), mode discipline, VER criteria → pytest mapping, 7-fixture table, Replit Agent handoff. |
| **Row 4 Understanding v0.2** | §9.4 | Prompt architecture pattern |
| **Row 4 Understanding v0.2** | §9.5 | Non-determinism handling: re-run semantics, AI model fingerprinting |
| **Row 4 Applied v0.2** | All sections | Common architectural commitments: Python 3.12+, FastAPI, Neon PostgreSQL via SQLAlchemy + Alembic, Pydantic v2, Claude Sonnet via Anthropic API, pytest, transactional discipline, mode discipline decorator |
| **Canonical Ledger v2.12** | Domain, DomainRegister, AnalysisPass element types | Authoritative schemas. Domain has six canonical attributes only: domain_id, name, description, classification_type, row_target, cell_content_item_refs. |
| **Row 3 v1.1** | §E.12.1 | domain_qualifier and upstream_domain_ref were Row 3 extensions. Both withdrawn — domain_qualifier is redundant with row_target; upstream_domain_ref is navigable via existing CCI → Requirement → Domain canonical trace path. Tracker F53 raises Row 3 v1.1 §E.12.1 amendment. |
| **Tracker v0.36** | F43, F53, F55 | F43: Action-Required (pass catalogue mode label). F53: Action-Required (Row 3 Understanding §E.12.1 amendment). F55: seventh-review corrections (Resolved). |

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
  stage4_entity_production.py              # DM: domain_id allocation; Domain entity construction;
                                           #     FullRerun retirement; ledger transaction; DomainRegister replace;
                                           #     AnalysisPass write
  prompts/
    domain_grouping_prompt.py              # Template: FirstRun / FullRerun — full CCI set grouping
    domain_incremental_prompt.py           # Template: IncrementalRerun — new CCIs vs existing Domain summaries
    domain_repair_prompt.py                # Template: CHK-3c-04 repair — orphaned CCIs to be assigned
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

**MD-2 — Four re-run scenarios via hash-based detection.** Pass 3b's re-run behaviour is extend-on-rerun (additive). Pass 3c has four distinct code paths (FirstRun / IdempotentRerun / IncrementalRerun / FullRerun) selected by SHA-256 hash comparison of the sorted ci_id list against the prior AnalysisPass record. The hash is stored in `AnalysisPass.outputs.mechanism_data.cci_set_hash` on every run. See §4.1 for detection logic.

**MD-3 — Three prompt templates, three Pydantic schemas.** Different re-run scenarios and the repair path require structurally different AI outputs. Each prompt has its own template file and response schema rather than a single polymorphic schema. The DM entity-production stage reads from the validated schema output, not the raw AI string.

**MD-4 — cell_content_item_refs as join table, not JSONB array.** The `domain.cell_content_item_refs` attribute from the canonical ledger spec is implemented as the `domain_cci_membership` join table at the physical layer. This enables efficient bidirectional queries ("which CCIs belong to Domain D?" and "which Domains contain CCI C?") and enforces referential integrity at the database level. The JSON serialisation for the ledger API uses the JSONB array form, assembled by query.

**MD-5 — FullRerun uses soft-delete (retired_at timestamp), not hard delete.** Retiring Domains on FullRerun preserves referential integrity for any existing `Requirement.domain_refs` entries from a prior Pass 3d run. Hard deletion would leave dangling FK references. The `retired_at TIMESTAMPTZ` column (null = active) is the retirement flag. `query_max_domain_id` includes retired Domains in its maximum calculation to prevent id reuse.

**MD-6 — domain_qualifier and upstream_domain_ref withdrawn.** Both Row 3 Understanding v1.1 §E.12.1 extensions are removed. `domain_qualifier` is redundant with `row_target`. `upstream_domain_ref` duplicates a trace already navigable via `Domain.cell_content_item_refs → CCI → signal_refs → Requirement (row n-1) → domain_refs → Domain (row n-1)`. Neither attribute appears in the canonical ledger v2.12 Domain schema. Neither is produced by this mechanism. Tracker F53 raises the Row 3 Understanding §E.12.1 amendment required as a consequence.

**MD-7 — Repair prompt is a conditional IM sub-act of Stage 3, not a separate Stage.** When CHK-3c-04 detects orphaned CCIs, a second AI call is made within Stage 3. The mode discipline decorator records both the primary (Stage 2) and the repair (Stage 3 sub-act) IM invocations separately in `AnalysisPass`. One repair attempt only — persistent orphans are recorded in `orphaned_ccis` and a Concern is raised; they do not block entity production.

### 3.3 Large CCI set advisory threshold

Before Stage 2 is invoked, Stage 1 checks `len(eligible_ccis)` against `ProjectProfile.domain_large_cci_set_advisory_threshold` (default 80). If exceeded: `mechanism_data.large_cci_set_advisory = true` is set in the AnalysisPass and an advisory is logged. Processing continues — this is informational only. The Row 4 Mechanism Spec does not define a chunking strategy for Pass 3c at v0.1; if future empirical evidence shows that large CCI sets degrade AI grouping quality, a chunking extension should be raised as a new tracker finding.

---

## 4. Stage-by-Stage Implementation

### 4.1 Stage 1 — Pre-flight and CCI Assembly (DM)

**Precondition check (hard stop):**
Query `AnalysisPass` for `mechanism="CellContentItemConstruction"` AND `row_ref = current_row` AND `project_id = current_project`. If not found, or `execution_status = "Failed"`: set `execution_status = "Failed"` on Pass 3c AnalysisPass; `failure_reason = "Pass 3b prerequisite not met — no completed CCI Construction pass found for this row"`. Exit.

**CCI assembly:**
Query `cell_content_item` JOIN `zachman_cell` WHERE `zachman_cell.row_target = str(current_row)` AND `cell_content_item.project_id = current_project`. This is the eligible CCI set. Record `cci_count_input = len(eligible_ccis)`.

**Zero-CCI early exit:**
If `cci_count_input == 0`: write AnalysisPass with `execution_status = "CompletedWithWarnings"`, `mechanism_data.run_scenario = "FirstRun"` (or whichever applies), warning `no_cci_input`. Update DomainRegister with `member_ids = query_all_active_domain_ids(project_id)` — the project-wide active domain set at the time of this run (`SELECT domain_id FROM domain WHERE project_id = :pid AND retired_at IS NULL`, no `row_target` filter). **Do NOT write `member_ids = []` unconditionally.** If other rows' Domains exist in the project (e.g., Row 2 Domains D001–D003 already committed), they must be preserved in the register. If no Domains exist anywhere in the project, the query returns an empty list and `member_ids = []` is the correct outcome — but it must be derived from the query, not hardcoded. Exit.

**Large-set advisory:**
If `cci_count_input > domain_large_cci_set_advisory_threshold`: set `mechanism_data.large_cci_set_advisory = true`.

**Re-run scenario detection:**
Compute `current_hash = SHA-256("|".join(sorted([c.ci_id for c in eligible_ccis])))`.
Query most recent non-Failed Pass 3c AnalysisPass for this `row_ref` and `project_id`. If none: `scenario = "FirstRun"`. If found:
- `prior_hash = prior_pass.outputs["mechanism_data"]["cci_set_hash"]`
- If `current_hash == prior_hash`: `scenario = "IdempotentRerun"`
- Else:
  - `prior_cci_count = prior_pass.outputs["mechanism_data"]["cci_count_input"]`
  - **Zero-division guard:** If `prior_cci_count == 0` (prior run completed with `no_cci_input` warning — no Domains were committed): treat as `"FirstRun"`. There is nothing to extend or retire.
  - Otherwise: call `query_committed_cci_ids_for_row(row_ref, project_id)` — a database query on `domain_cci_membership` that returns the set of ci_ids covered by active Domains for this row/project at the time of the last Pass 3c run. This is **not** a stored field in `mechanism_data`; it requires a live DB query. Compute `new_cci_count = len(eligible_ci_ids - prior_committed_ci_ids)`.
  - If `new_cci_count / prior_cci_count >= domain_rerun_threshold`: `scenario = "FullRerun"`. Else: `scenario = "IncrementalRerun"`.

**Implementation note on `query_committed_cci_ids_for_row`:** This function executes `SELECT DISTINCT ci_id FROM domain_cci_membership JOIN domain USING (domain_id, project_id) WHERE domain.project_id = :pid AND domain.row_target = :row AND domain.retired_at IS NULL`. The result represents the CCI coverage footprint of the last committed Domain set. It must **not** be confused with a stored snapshot in the AnalysisPass record — the AnalysisPass stores only the hash, not the ci_id list.

**IdempotentRerun exit:**
Write AnalysisPass with `execution_status = "Completed"`, `mechanism_data.run_scenario = "IdempotentRerun"`, `mechanism_data.cci_set_hash = current_hash`, `mechanism_data.idempotent = true`. Existing Domains and DomainRegister unchanged. Exit.

**Error cases:**
- Database connection failure during CCI query: `execution_status = "Failed"`, `failure_reason = "CCI assembly query failed: {error}"`.
- Referential integrity violation (CCI references non-existent ZachmanCell): log warning in AnalysisPass `execution_warnings`; exclude offending CCI from eligible set; continue.

### 4.2 Stage 2 — AI Grouping Act (IM)

**FirstRun / FullRerun path:**
Invoke `domain_grouping_prompt.py` with parameters:
- `row_ref`: integer (current row)
- `abstraction_level_phrase`: brief description of the row's abstraction level — injected directly from a simple inline dict keyed on `row_ref` (see §5.4). No separate vocabulary module needed.
- `cci_set`: list of dicts `{ci_id, column, classification_type, description}` for all eligible CCIs
- `cci_count`: `len(eligible_ccis)`

Pass assembled prompt to Claude Sonnet (model: per Row 4 Applied §4.5 — `claude-sonnet-4-20250514`). Parse response against `domain_grouping_response_schema.py` (Pydantic). If parse fails: one retry with identical prompt. Second parse failure: `execution_status = "Failed"`, `failure_reason = "AI grouping response parse failure after retry"`. Exit.

**IncrementalRerun path:**
Construct existing Domain summaries from ledger: for each active Domain for this row/project, produce `{domain_id, name, description, cci_ref_count}`. Assemble new CCI delta: CCIs in `eligible_ccis` not present in any existing Domain's `domain_cci_membership`.
Invoke `domain_incremental_prompt.py` with:
- `abstraction_level_phrase`: same as above
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
For each proposed Domain: if `len(cci_refs) == 0`, reject the Domain. Record `{check_id: "CHK-3c-01", domain_name: name, detail: "empty cci_refs"}` in `mechanism_data.validation_failures`. If all Domains are rejected: treat as Stage 2 parse failure; invoke one retry. Persistent failure: `execution_status = "Failed"`.

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
  - For `action="assign"` entries: match `domain_name` case-insensitively against existing proposals; add `new_cci_refs` to the matched proposal's `cci_refs`. If no match: treat as `action="new"` — use `domain_name` as the Domain name, `description = "Domain created from repair assignment — review recommended"`, `classification_type = null`, `cci_refs = action.new_cci_refs`. Advisory logged: `{type: "repair_assign_name_not_found", domain_name: name}`.
  - For `action="new"` entries: add the new Domain proposal to the proposals list.
- Re-compute `covered` and `orphaned` after merge.
- Record `repair_prompt_issued = true` in `mechanism_data`.
- Record repair AI fingerprint: `{stage: "stage3_repair", model: "claude-sonnet-4-20250514", input_tokens: N, output_tokens: M}`.

If `orphaned` is still non-empty after repair:
- Record all persistent orphaned ci_ids in `mechanism_data.orphaned_ccis`.
- Set `execution_status = "CompletedWithWarnings"`.
- Raise Concern entity (CNNNN): `description = "Pass 3c Domain Derivation: {N} CCI(s) could not be assigned to any Domain after repair attempt. Practitioner review required. Orphaned ci_ids: {list}"`, `source_refs = [orphaned ci_ids]`. The `practitioner_id` field on the Concern is sourced from the `practitioner_id` parameter passed to the mechanism's `run()` entry point — the same parameter pattern used by Pass 3a (Row-Lens Source Re-Analysis). The orchestrator supplies this value from the active session context.
- Continue to Stage 4 (committed Domain set excludes persistent orphans — they are not assigned to any Domain).

**CHK-3c-05 — Cross-cutting advisory:**
For each ci_id in `eligible_ci_ids`: count how many proposals include it in `cci_refs`. If `count > domain_cross_cutting_advisory_threshold`: record advisory `{ci_id: ci_id, domain_count: count}` in `mechanism_data.cross_cutting_advisories`. Not a failure.

**CHK-3c-06 — At least one Domain survives:**
If `len(proposals) == 0` after CHK-3c-01 through CHK-3c-04: this is a degenerate failure (all proposals rejected). `execution_status = "Failed"`, `failure_reason = "zero domains survived structural validation"`. Exit.

**ADVC-3c-01 — Domain count bounds advisory (OQ-3c-01 resolution):**
After CHK-3c-06, before exiting Stage 3, compute soft-bounds advisory:
- If `len(proposals) < 1 + ceil(cci_count_input / 15)` OR `len(proposals) > cci_count_input / 2`:
  - Append to `execution_warnings`: `{type: "domain_count_advisory", domain_count: len(proposals), cci_count: cci_count_input, lower_bound: 1 + ceil(cci_count_input / 15), upper_bound: floor(cci_count_input / 2)}`
  - This is advisory only — does not affect `execution_status`; does not block entity production.

`execution_warnings` is populated in §4.2 (IncrementalRerun fallback), §4.3 CHK-3c-03 (duplicate name merge), and here (domain count advisory). It is a standard top-level AnalysisPass field outside `mechanism_data` — see §7 for clarification. All three advisory types are accumulated into the same `execution_warnings` list on the AnalysisPass record.

### 4.4 Stage 4 — Entity Production and Ledger Commit (DM)

**4.4.1 domain_id allocation:**
Query `MAX(CAST(SUBSTRING(domain_id, 2) AS INTEGER)) FROM domain WHERE project_id = current_project` (includes retired Domains — `retired_at IS NOT NULL`). If null (no prior Domains): `next_seq = 1`. Else: `next_seq = max_val + 1`. Allocate D001, D002, ... incrementally across the proposals.

On `IncrementalRerun`: existing active Domains retain their domain_ids. Only new Domains (from `action="new"` repair entries or new Domain proposals in the incremental AI response) receive new ids from `next_seq`.

On `FullRerun`: record `domain_count_retired` = count of currently active Domains for this row/project. Set `retired_at = NOW()` on all active Domains for this row/project. Then allocate fresh domain_ids for all proposals from `next_seq`.

**4.4.2 Domain entity construction:**
Construct Domain entities from the validated proposals. Each Domain carries the six canonical attributes: `domain_id`, `name`, `description`, `classification_type`, `row_target`, and `cell_content_item_refs` (assembled at query time from `domain_cci_membership`). No `domain_qualifier` or `upstream_domain_ref` — both withdrawn (see §3.2 MD-6). Cross-row Domain tracing is available via the canonical path `Domain → cell_content_item_refs → CCI → signal_refs → Requirement (row n-1) → domain_refs → Domain (row n-1)`.

**4.4.3 Ledger transaction:**
Open a single Postgres transaction. Within the transaction:
1. For `FullRerun`: execute `UPDATE domain SET retired_at = NOW() WHERE project_id = current_project AND row_target = str(row_ref) AND retired_at IS NULL`.
2. `INSERT INTO domain (domain_id, project_id, name, description, classification_type, row_target)` for each new Domain entity (action="new" proposals only).
3a. `INSERT INTO domain_cci_membership (domain_id, project_id, ci_id)` for each (domain_id, ci_id) pair in the **new Domain** proposals (memberships for newly created Domains).
3b. **IncrementalRerun only:** `INSERT INTO domain_cci_membership (domain_id, project_id, ci_id)` for each `(existing_domain_id, new_ci_id)` in `assign_membership_inserts`. This list is produced in-memory during Stage 2 output processing and passed to Stage 4. It is **not** written in Stage 3 — Stage 3 has no DB calls. If `assign_membership_inserts` is empty or scenario is not IncrementalRerun, this step is skipped.
4. `UPDATE register SET member_ids = :new_member_ids WHERE register_type = 'Domain' AND project_id = current_project` — where `new_member_ids` is the JSON array of **all active domain_ids across all rows for this project**. The query MUST be `SELECT domain_id FROM domain WHERE project_id = :pid AND retired_at IS NULL` — **no `row_target` filter**. Scoping to `row_target = str(row_ref)` is a common mistake that silently drops Domains from other rows.

If the transaction rolls back: `execution_status = "Failed"`, `failure_reason = "Ledger transaction rolled back: {error}"`. No partial commit.

**4.4.4 FullRerun retirement mapping:**
**Timing is critical:** Capture `prior_active_domains = query_active_domains_for_row(row_ref, project_id)` before opening the ledger transaction. Compute `retirement_mapping` by Jaccard token overlap between each retiring Domain name and each new proposal name: tokenise both names (lowercase split), compute `|intersection| / |union|`. If best overlap ≥ **0.50**, assign that proposal as `inferred_successor_domain_id`. Else: `null`. The 0.50 threshold is hardcoded — the former `domain_upstream_match_threshold` ProjectProfile parameter was withdrawn along with `upstream_domain_ref`; this threshold is not configurable. Record `{old_domain_id: "D001", inferred_successor_domain_id: "D007" | null}` for each retiring Domain. Store in `mechanism_data.retirement_mapping`. Only then open the transaction and execute the retirement UPDATE. Computing this mapping after the UPDATE is an implementation error.

**4.4.5 downstream_rerun_required flag:**
If `scenario == "FullRerun"`: query whether any AnalysisPass with `mechanism="RequirementDerivation"` and `row_ref = current_row` and `project_id = current_project` exists with `execution_status ∈ {"Completed", "CompletedWithWarnings"}`. If yes: set `mechanism_data.downstream_rerun_required = true`. Else: `false`.

**4.4.6 AnalysisPass write:**
Write outside the main ledger transaction (same pattern as Pass 3b Step 6). Populate all fields of `mechanism_data` per §7. AnalysisPass `execution_status` reflects the Stage 3 outcome: `Completed` if no warnings/orphans (including IdempotentRerun — `mechanism_data.idempotent = true` distinguishes it from a full run); `CompletedWithWarnings` if orphans, advisories, or IncrementalRerun fallback occurred; `Failed` only if a hard stop was hit. On IdempotentRerun: `mechanism_data` contains hash, scenario, and `idempotent = true` — domain production fields are zero-valued.

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
    retired_at           TIMESTAMPTZ,             -- null = active; non-null = retired (FullRerun soft-delete)
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    PRIMARY KEY (domain_id, project_id)
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
- Migration file: `migrations/XXXX_add_domain_tables.py`.

**`DomainModel` (SQLAlchemy ORM — `domain` table):**
Maps to the DDL above. Key attributes:
- `domain_id`: String, PK component; CHECK `domain_id ~ '^D\d{3}$'`
- `project_id`: String, PK component
- `name`: String NOT NULL
- `description`: Text NOT NULL
- `classification_type`: String nullable
- `row_target`: String NOT NULL; CHECK IN ('1','2','3','4','5','6')
- `retired_at`: TIMESTAMPTZ nullable; null = active; non-null = retired
- `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- Composite PK: `(domain_id, project_id)`

**`DomainCCIMembershipModel` (SQLAlchemy ORM — `domain_cci_membership` table):**
- `domain_id`: String; FK to `domain(domain_id, project_id)`
- `project_id`: String; part of composite FK
- `ci_id`: String; FK to `cell_content_item(ci_id, project_id)`
- Composite PK: `(domain_id, project_id, ci_id)`

**`DomainSchema` (Pydantic — canonical ledger API representation):**
Mirrors the canonical ledger v2.12 Domain element exactly — six attributes:
```
domain_id:              str  — regex ^D\d{3}$
name:                   str
description:            str
classification_type:    Optional[str]
row_target:             str  — Literal["1","2","3","4","5","6"]
cell_content_item_refs: List[str]  — assembled from domain_cci_membership query
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
Validation: for `assign` actions, `domain_id` must reference an existing active Domain for this row/project (checked post-parse in Stage 3). If `domain_id` does not match any active Domain: converted to a `new` action with `name = domain_id` (the invalid id used as placeholder), `description = "IncrementalRerun assign action referenced non-existent domain_id — review recommended"`, `classification_type = null`, `cci_refs = action.new_cci_refs`. Advisory logged: `{type: "incremental_assign_invalid_domain_id", domain_id: domain_id}`.

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

### 5.4 Row abstraction level phrases — inline constant

The `abstraction_level_phrase` injected into prompts is a simple inline dict in `domain_grouping_prompt.py` and `domain_incremental_prompt.py`. No separate module needed — `domain_qualifier_label` has been removed along with `domain_qualifier`.

```python
ROW_ABSTRACTION_PHRASES = {
    "1": "enterprise contextual scope — strategic boundaries, compliance, and high-level operational context",
    "2": "business conceptual level — business processes, entities, roles, events, and rules",
    "3": "logical design level — logical structures, behaviours, interactions, and state models; technology-agnostic",
    "4": "physical builder level — specific technologies, components, deployment targets, and implementation patterns",
    "5": "detailed design level — algorithms, data formats, implementation specifications, and detailed configurations",
    "6": "operational level — runtime procedures, user interactions, support processes, and operational behaviours",
}
```

This constant is defined once in the prompt template file. It is not imported by `stage4_entity_production.py` — Stage 4 no longer needs a qualifier mapping.

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

**Mode violations** (a DM stage making an AI call, or an IM stage making no AI call when one was required) are recorded in `mechanism_data.mode_violations` as `[{stage: str, violation_type: str, detail: str}]` and set `execution_status = "CompletedWithWarnings"`.

**LPM constraint** applies throughout: CCI `description` text is passed to the AI as read-only context. The AI is instructed not to reproduce CCI descriptions verbatim in Domain descriptions. The LPM constraint is enforced at the prompt instruction level (§4.1.2 of the Row 3 Mechanism Spec). Automated detection of verbatim copy is not implemented at v0.1 — deferred to a future tracker finding if empirical evidence shows LPM violations are occurring.

---

## 7. Audit Trail Population

The AnalysisPass `outputs` JSONB field for mechanism `"DomainDerivation"` has the following structure. All fields are required. Zero-value arrays must be present as `[]`, not null, not omitted.

**`execution_warnings` — placement clarification:** `execution_warnings` is a **standard top-level AnalysisPass field**, not a sub-field of `mechanism_data`. It is defined at the AnalysisPass model level (same pattern as Pass 3b and all other mechanisms) and is populated by the AnalysisPass writer utility with any advisory entries accumulated during the run. Pass 3c accumulates entries in three places:
- §4.2: `{type: "incremental_fallback_to_fullrerun"}` — IncrementalRerun AI parse failure triggering FullRerun
- §4.3 CHK-3c-03: `{type: "duplicate_domain_name_merged", domain_name: name}` — merged duplicate proposals
- §4.3 ADVC-3c-01: `{type: "domain_count_advisory", domain_count: N, cci_count: M, lower_bound: L, upper_bound: U}` — domain count outside soft bounds
- §4.3: `{type: "repair_assign_name_not_found", domain_name: name}` — repair assign-to-new fallback
- §5.2: `{type: "incremental_assign_invalid_domain_id", domain_id: id}` — IncrementalRerun invalid domain_id fallback

`execution_warnings` is not listed in the `mechanism_data` JSONB below. It lives at the AnalysisPass level alongside `mechanism_data`. VER-3c-08 checks `mechanism_data` completeness only; `execution_warnings` completeness is verified by the common AnalysisPass schema validator.

```jsonc
{
  "mechanism_data": {
    // --- Stage 1 fields ---
    "run_scenario":                  "FirstRun",           // string: one of four scenario names
    "cci_set_hash":                  "<sha256-hex>",       // SHA-256 of sorted ci_id list
    "cci_count_input":               7,                    // integer; 0 on zero-CCI exit
    "large_cci_set_advisory":        false,                // boolean
    "idempotent":                    false,                // boolean; true on IdempotentRerun only

    // --- Stage 3 fields ---
    "repair_prompt_issued":          false,                // boolean
    "orphaned_ccis":                 [],                   // List[str] ci_ids of persistent orphans
    "cross_cutting_advisories":      [],                   // List[{ci_id, domain_count}]
    "validation_failures":           [],                   // List[{check_id, domain_name, detail}]

    // --- Stage 4 fields ---
    "domain_count_produced":         3,                    // integer; 0 on IdempotentRerun/Failed
    "domain_count_retired":          0,                    // integer; non-zero on FullRerun only
    "domains_produced": [                                  // List of per-domain summaries
      {
        "domain_id":               "D001",
        "name":                    "Pocket Money Management",
        "cci_ref_count":           4,
        "cross_cutting_cci_count": 0                       // CCIs appearing in >1 Domain
      }
    ],
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

The `ai_model_fingerprints` array accumulates entries for every IM call made during the run: Stage 2 primary, Stage 2 retry (if issued), Stage 3 repair (if issued). On IdempotentRerun: `ai_model_fingerprints` is `[]` and `idempotent = true`.

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
| **VER-3c-06** | DomainRegister `member_ids` contains exactly the active domain_ids for this project | Query active Domains across all rows (`retired_at IS NULL`, no `row_target` filter); assert set equality with register `member_ids`. **Test care:** single-row fixtures pass this trivially; integration tests exercising Row 2 then Row 3 in the same project must assert register contains Domains from both rows. |
| **VER-3c-07** | AnalysisPass with `mechanism="DomainDerivation"` and `row_ref=current_row` exists | Presence query |
| **VER-3c-08** | `AnalysisPass.outputs.mechanism_data` present; all required fields non-null | Schema validation against expected field list |
| **VER-3c-09** | Domain entity has exactly the six canonical attributes (domain_id, name, description, classification_type, row_target, cell_content_item_refs) — no domain_qualifier or upstream_domain_ref columns in DB row | Assert `domain_qualifier` and `upstream_domain_ref` columns absent from `domain` table schema |
| **VER-3c-10** | On IdempotentRerun: domain_ids and `domain_cci_membership` rows unchanged; `mechanism_data.idempotent == true` | Snapshot before/after run; assert equality; assert idempotent flag |
| **VER-3c-11** | On FullRerun: `domain_count_retired` equals pre-run active Domain count for this row | Query active count before run; assert equals `mechanism_data["domain_count_retired"]` |
| **VER-3c-12** | `domain_count_produced ≥ 1` when `cci_count_input > 0` | Conditional assertion |

### 8.2 Plausibility checklist for Practitioner review

1. **PLB-3c-01 — Domain names:** No name should be generic ("Miscellaneous", "Other", "General"). Each should reflect a recognisable architectural responsibility at the row's abstraction level (see §5.4 `ROW_ABSTRACTION_PHRASES`). If generic names appear, review the AI grouping prompt and consider a FullRerun.

2. **PLB-3c-02 — Column span:** For each Domain, group `domain_cci_membership` by `zachman_cell.column`. A Domain containing CCIs from only one column is flagged for review. Exception: a Why-only Domain (pure constraint domain) may be valid — verify intentionality.

3. **PLB-3c-03 — Domain count:** For PMT Row 2 (~7–12 CCIs): expect 2–4 Domains. For NQPS Row 3 (~4 CCIs): expect 1–2 Domains. Review `mechanism_data.large_cci_set_advisory` and `domain_count_produced` together.

4. **PLB-3c-04 — Cross-cutting CCIs:** Review `mechanism_data.cross_cutting_advisories`. Is each flagged CCI genuinely cross-cutting? A What-column Entity CCI appearing in every Domain suggests Domain boundaries are too coarse — consider a FullRerun.

5. **PLB-3c-05 — Row-appropriate vocabulary:** For Row 3 Domains: logical-design vocabulary (logical structure, logical behaviour, state management). For Row 2 Domains: business vocabulary (process, entity, rule, role). Absence of implementation vocabulary ("database table", "API endpoint") at Row 3 is a positive signal.

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
- VER-3c-09: `domain_qualifier` and `upstream_domain_ref` columns absent from domain table
- VER-3c-12: `domain_count_produced == 3`
- `mechanism_data.run_scenario == "FirstRun"`
- `mechanism_data.repair_prompt_issued == false`
- `mechanism_data.orphaned_ccis == []`
- 3 domain_ids allocated starting from D001 (or next available)

### 9.2 Fixture 2 — NQPS Row 3: FirstRun

**Test function:** `test_nqps_row3_firstrun`
**AI stub:** Returns 2 Domains grouping 4 NQPS Row 3 CCIs:
- `"Quality Compliance Behaviour"`: CCI-ROW3-C-How-001, CCI-ROW3-C-Who-001
- `"ISO Standard Reference Structure"`: CCI-ROW3-C-What-001, CCI-ROW3-C-Why-001

**Pre-conditions:** `row_ref = 3`, `project_id = "NQPS-TEST"`, Pass 3b complete, 4 CCIs seeded.

**Assertions:**
- VER-3c-05, VER-3c-09, VER-3c-12
- `mechanism_data.run_scenario == "FirstRun"`
- PLB-3c-05: Domain descriptions use logical-design vocabulary

### 9.3 Fixture 3 — PMT Row 2: IdempotentRerun

**Test function:** `test_pmt_row2_idempotent_rerun`
**Setup:** Run Fixture 1 first (creates Domains D001–D003 and AnalysisPass P001). Then re-invoke Pass 3c with the same CCI set.

**AI stub:** Not invoked — Stage 1 detects IdempotentRerun and exits before Stage 2.

**Assertions:**
- VER-3c-10: domain_ids and `domain_cci_membership` rows identical to post-Fixture-1 state; `mechanism_data.idempotent == true`
- New AnalysisPass written with `execution_status = "Completed"`, `run_scenario = "IdempotentRerun"`
- Stage 2 AI stub `assert_not_called()` — confirms no AI invocation occurred

### 9.4 Fixture 4 — PMT Row 2: IncrementalRerun with one new CCI

**Test function:** `test_pmt_row2_incremental_rerun`
**Setup:** Run Fixture 1 first. Then add one new CCI to the test DB:
- `CCI-ROW2-C-When-001`: `classification_type="BusinessEvent"`, `description="Weekly allowance payment event"`

**AI stub (incremental prompt):** Returns one `assign` action: `{action: "assign", domain_id: "D001", new_cci_refs: ["CCI-ROW2-C-When-001"]}` (assigning the new CCI to "Pocket Money Transaction Management").

**Assertions:**
- `mechanism_data.run_scenario == "IncrementalRerun"`
- VER-3c-05: all 8 CCIs (7 original + 1 new) now covered
- D001's `domain_cci_membership` now includes `CCI-ROW2-C-When-001`
- D002 and D003 membership unchanged
- `mechanism_data.downstream_rerun_required == false` (no Pass 3d has run)
- New AnalysisPass written; prior AnalysisPass (P001) unchanged

### 9.5 Fixture 5 — Non-Loss repair: orphaned CCI recovered

**Test function:** `test_noloss_repair_prompt_recovery`
**Setup:** PMT Row 2 FirstRun. AI stub (primary) returns only 2 Domains, omitting `CCI-ROW2-C-Why-001` from all proposals. CHK-3c-04 detects 1 orphaned CCI.

**AI stub (repair prompt):** Returns one `new` action: `{action: "new", name: "Transaction Approval Rules", description: "Constraint governing parental approval thresholds", cci_refs: ["CCI-ROW2-C-Why-001"]}`.

**Assertions:**
- `mechanism_data.repair_prompt_issued == true`
- `mechanism_data.orphaned_ccis == []` (orphan recovered by repair)
- VER-3c-05: all 7 CCIs covered
- `domain_count_produced == 3` (2 from primary + 1 from repair)
- `execution_status == "Completed"` (not CompletedWithWarnings — repair succeeded)
- `ai_model_fingerprints` has 2 entries: `stage2_primary` and `stage3_repair`

### 9.6 Fixture 6 — Persistent orphan after repair failure

**Test function:** `test_noloss_repair_persistent_orphan`
**Setup:** PMT Row 2 FirstRun. Primary AI stub omits `CCI-ROW2-C-Why-001`. Repair AI stub returns an empty proposal list (degenerate repair response — parse fails gracefully, repair merge produces no new coverage).

**Assertions:**
- `mechanism_data.repair_prompt_issued == true`
- `mechanism_data.orphaned_ccis == ["CCI-ROW2-C-Why-001"]`
- `execution_status == "CompletedWithWarnings"`
- VER-3c-05 **fails** — this is expected and asserted to fail in this fixture (the test verifies the orphan is *recorded*, not that it is covered)
- A Concern entity CN-NNN exists in the DB for this project/row with description referencing the orphaned CCI

### 9.7 Fixture 7 — FullRerun: domain_id retirement and fresh allocation

**Test function:** `test_pmt_row2_fullrerun`
**Setup:** Run Fixture 1 (Domains D001–D003 active). Then add 2 new CCIs (pushing `new_cci_count / prior_cci_count` above threshold 0.20). Set `domain_rerun_threshold = 0.20` in ProjectProfile. Invoke Pass 3c.

**AI stub (primary, FullRerun):** Returns 3 new Domain proposals grouping all 9 CCIs.

**Assertions:**
- `mechanism_data.run_scenario == "FullRerun"`
- D001, D002, D003 now have `retired_at IS NOT NULL`
- 3 new active Domains allocated starting from D004 (next available after D003)
- VER-3c-11: `domain_count_retired == 3`
- VER-3c-05: all 9 CCIs covered by new Domains
- `mechanism_data.retirement_mapping` has 3 entries (one per retired Domain, with `inferred_successor_domain_id` populated if name similarity ≥ 0.50)
- `mechanism_data.downstream_rerun_required == false` (no Pass 3d has run in test setup)

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
| **Row 3 — no Row 2 Domains exist** | Not applicable — `upstream_domain_ref` is withdrawn. Cross-row Domain tracing uses the canonical CCI → Requirement → Domain path. No Domain entity attribute is affected by whether Row 2 Domains exist. |
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
| **Phase 2 — Mechanism Activation** | `project_profile` row — provides three domain-specific parameters (§13.9 of Row 4 Understanding v0.14). | Soft prerequisite — ProjectProfile must exist. If any parameter is NULL, default value is substituted. |

### 11.2 Downstream

| Mechanism | What this mechanism produces for it | Dependency type |
|---|---|---|
| **Pass 3d — Requirement Derivation** | `domain` and `domain_cci_membership` rows — Pass 3d reads Domains and assigns `Requirement.domain_refs`. | Hard dependency — orchestrator checks for Pass 3c `execution_status ∈ {Completed, CompletedWithWarnings}` before Pass 3d may begin. IdempotentRerun produces `execution_status = Completed` with `mechanism_data.idempotent = true`; this satisfies the gate. |
| **Phase 6 / Phase 8 — Domain Coverage Analysis** | `domain` and `domain_cci_membership` rows — Phase 6 Pass 1 / Phase 8 Pass 1 enumerate Domains as the analysis inventory. Coverage analysis is read-only with respect to Domains. | Analytical dependency — Domains must be committed before Phase 6/8 runs. |

### 11.3 Ledger coordination

Per Row 4 Applied §4.11: mechanisms coordinate via ledger reads, not direct calls. Pass 3c reads CCIs from the ledger; writes Domains, DomainRegister, and AnalysisPass in transactions at completion. Pass 3d reads Domains from the ledger; it does not call Pass 3c directly.

The orchestrator (`core/orchestrator.py`) enforces pass sequencing by querying AnalysisPass records before invoking each mechanism. No mechanism imports or calls another mechanism directly.

---

## 12. Build Notes

### 12.1 Tracker findings relevant to this build

| Finding | Status | Relevance |
|---|---|---|
| **F-3c-01 (= F43)** | Action-Required | Pass 3c mode label in Row 2 v1.2 §3.9.3 records "DM + Robustness". Correct characterisation is IM-primary, DM-envelope. Row 2 Understanding amendment at next revision cycle. No implementation impact. |
| **F-3c-02 (= F44)** | Resolved | Row 1 domain_qualifier default — moot. domain_qualifier has been withdrawn entirely. F44 can be closed: no migration required, no default to confirm. |
| **F3** | Resolved | Domain Dual Relationship fully addressed. |
| **F53** | Action-Required | Row 3 Understanding v1.1 §E.12.1 amendment required — domain_qualifier and upstream_domain_ref were defined there as Row 3 extensions. Both withdrawn in this spec. §E.12.1 should be updated to record the withdrawal rationale and remove the attribute definitions. |

### 12.2 OQ resolutions committed at this spec

| OQ | Resolution in this spec |
|---|---|
| **OQ-3c-01** | Domain count soft bounds advisory implemented in Stage 3: advisory if `domain_count < 1 + ceil(cci_count / 15)` or `domain_count > cci_count / 2`. Logged in `execution_warnings` with type `domain_count_advisory`. |
| **OQ-3c-02** | ~~`domain_upstream_match_threshold` implemented as ProjectProfile parameter~~ — **withdrawn**. OQ-3c-02 resolves as: upstream_domain_ref is not produced by this mechanism; the ProjectProfile parameter is not needed. |
| **OQ-3c-03** | FullRerun retirement uses soft-delete (`retired_at` column). `query_max_domain_id` includes retired Domains. Active Domain query filters `retired_at IS NULL`. |

### 12.3 Replit Agent task structure

**Primary input documents:**
- This spec (Row 4 Mechanism Spec — Domain Derivation v0.10) — implementation authority (all detail including DDL in §5.1)
- Row 3 Mechanism Spec v0.1 — architectural authority (note: domain_qualifier and upstream_domain_ref mentioned there are withdrawn)
- Row 4 Understanding v0.14 §13 — framework (module structure, prose descriptions, ProjectProfile parameters, VER criteria mapping, fixture table)

**Reference documents:**
- Row 4 Applied v0.2 — common architectural commitments
- Row 4 Understanding v0.5 §12 — reference implementation patterns from Pass 3b
- Canonical Ledger v2.12 — Domain and DomainRegister schemas (six Domain attributes only)

**Build sequence for the Agent:**
1. Write Alembic migration: `add_domain_tables` — use the DDL from **this spec §5.1**. Note: the `domain` table has NO `domain_qualifier` or `upstream_domain_ref` columns — simpler than previous spec versions.
2. Write `schemas/domain_grouping_response_schema.py`, `schemas/domain_incremental_response_schema.py`, `schemas/domain_repair_response_schema.py` (§5.2)
3. The `row_abstraction_vocabulary.py` module is withdrawn. Use the `ROW_ABSTRACTION_PHRASES` inline dict from §5.4 directly in the prompt template files.
4. Write `prompts/domain_grouping_prompt.py`, `prompts/domain_incremental_prompt.py`, `prompts/domain_repair_prompt.py`
5. Write `stage1_preflight.py` through `stage4_entity_production.py` and `__init__.py` orchestrator
6. Write `tests/test_domain_derivation.py` with Fixtures 1–7 (§9); AI stubs via monkeypatch
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

End of SysEngage Row 4 Mechanism: Domain Derivation v0.10.

Changes from v0.9 (eighth Agent review — 4 noted findings):
- **Finding 1 (§4.3):** Repair assign-to-new fallback: `cci_refs = action.new_cci_refs` added. Without this, the synthetic Domain would have no membership, immediately producing a VER-3c-05 failure.
- **Finding 2 (§5.2):** Invalid domain_id fallback in IncrementalRerun assign validation: self-defeating "same name as the referenced Domain" replaced with `name = domain_id` (the invalid id as placeholder), explicit description, `classification_type = null`, `cci_refs = action.new_cci_refs`.
- **Finding 3 (§4.3):** OQ-3c-01 domain count advisory added as named check ADVC-3c-01 immediately after CHK-3c-06. Fires when `domain_count < 1 + ceil(cci_count/15)` OR `domain_count > cci_count/2`. Logs to `execution_warnings` with type `domain_count_advisory`.
- **Finding 4 (§7):** `execution_warnings` placement clarified: standard top-level AnalysisPass field, not inside `mechanism_data`. Full enumeration of all five advisory types that Pass 3c populates into `execution_warnings`.
- Cross-references: Understanding v0.13 → v0.14; tracker v0.35 → v0.36; self-reference v0.9 → v0.10.

Changes from v0.8: two significant findings (retirement threshold; repair fallback field values).
Changes from v0.7: ledger compliance (domain_qualifier, upstream_domain_ref withdrawn; Skipped → Completed; domain_data → mechanism_data).

Companion artefacts:
- SysEngage_Row_3_Mechanism_Domain_Derivation_v0_1.md — architectural authority
- SysEngage_Row_4_Understanding_v0_14.md — implementation framework
- SysEngage_Issues_Tracker_v0_36.md — finding disposition

Next artefact in sequence:
- SysEngage_Row_4_Mechanism_Domain_Derivation_v0_11.md — after Replit Agent build and first PMT/NQPS production run
