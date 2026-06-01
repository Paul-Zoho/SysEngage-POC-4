# SysEngage Row 4 Mechanism: Domain Derivation

**Implementation specification — depth tier (i)+**

Filename: SysEngage_Row_4_Mechanism_Domain_Derivation_v0_24.md

Version: 0.24 (Nuanced "and"/"&" test across all rows — two-step test replaces blunt prohibition; Row 1 "and" test added; repair prompts required to enforce naming prohibition; Row 2 "retention" added to vocabulary avoid list. Supersedes v0.23.)

Date: 26 May 2026

**Purpose.** Implementation specification for the Domain Derivation mechanism (Pass 3c). v0.24 replaces the blunt "and"/"&" prohibition with a two-step test: (1) if a single concept covers both sub-themes, use it; (2) if not, split. Applies to all rows including Row 1. Repair prompts now explicitly required to enforce naming prohibition. Supersedes v0.23.

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
| **Row 4 Understanding v0.24** | §13 | Pass 3c implementation framework: module structure (row_abstraction_vocabulary.py absent), re-run scenarios (prose), ProjectProfile parameters (three), mode discipline, VER criteria → pytest mapping, 7-fixture table, Replit Agent handoff. |
| **Row 4 Understanding v0.2** | §9.4 | Prompt architecture pattern |
| **Row 4 Understanding v0.2** | §9.5 | Non-determinism handling: re-run semantics, AI model fingerprinting |
| **Row 4 Applied v0.2** | All sections | Common architectural commitments: Python 3.12+, FastAPI, Neon PostgreSQL via SQLAlchemy + Alembic, Pydantic v2, Claude Sonnet via Anthropic API, pytest, transactional discipline, mode discipline decorator |
| **Canonical Ledger v2.12** | Domain, DomainRegister, AnalysisPass element types | Authoritative schemas. Domain has six canonical attributes only: domain_id, name, description, classification_type, row_target, cell_content_item_refs. |
| **Row 3 v1.1** | §E.12.1 | domain_qualifier and upstream_domain_ref were Row 3 extensions. Both withdrawn — domain_qualifier is redundant with row_target; upstream_domain_ref is navigable via existing CCI → Requirement → Domain canonical trace path. Tracker F53 raises Row 3 v1.1 §E.12.1 amendment. |
| **Tracker v0.50** | F43, F53, F58 | F43: Action-Required (pass catalogue mode label). F53: Action-Required (Row 3 Understanding §E.12.1 amendment). F58: v0.12 execution_warnings/no_cci_input fixes (Resolved). |

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
  stage3_structural_validation.py          # DM: CHK-3c-01..06 checks; ADVC-3c-01 domain count advisory;
                                           #     repair prompt dispatch (IM conditional)
  stage4_entity_production.py              # DM: domain_id allocation; Domain entity construction;
                                           #     FullRerun retirement; ledger transaction; DomainRegister replace;
                                           #     AnalysisPass write
  prompts/
    domain_grouping_prompt.py              # Template: FirstRun / FullRerun — full CCI set grouping
    domain_incremental_prompt.py           # Template: IncrementalRerun — new CCIs vs existing Domain summaries
    domain_repair_prompt.py                # Template: CHK-3c-04 repair — orphaned CCIs to be assigned
    domain_single_cci_repair_prompt.py     # Template: CHK-3c-07 repair — isolated single-CCI domains to be absorbed
    domain_split_repair_prompt.py          # Template: CHK-3c-08 repair — over-concentrated domain to be split
  schemas/
    domain_grouping_response_schema.py     # Pydantic: primary grouping response (name, description,
                                           #           classification_type, cci_refs)
    domain_incremental_response_schema.py  # Pydantic: IncrementalRerun response (action: assign|new)
    domain_repair_response_schema.py       # Pydantic: CHK-3c-04 repair response (action-based: assign|new).
                                           #           DISTINCT — uses domain_name: str NOT domain_id: str.
                                           #           Must NOT be shared. See §5.2 IMPORTANT warning.
    domain_single_cci_repair_response_schema.py  # Pydantic: CHK-3c-07 repair response (assign only; uses
                                                 #           domain_name: str). DISTINCT class from all other
                                                 #           schemas — see §5.2 IMPORTANT warning.
    domain_split_repair_response_schema.py       # Pydantic: CHK-3c-08 split response (list of SplitDomainProposal).
                                                 #           DISTINCT class — see §5.2 IMPORTANT warning.
```

### 3.2 Major design decisions

**MD-1 — No batching.** Pass 3b uses fixed-size Signal batches because Signal counts can be large (ProjectProfile.cci_batch_size, default 20). Pass 3c takes all CCIs for the row in a single AI call. The CCI set is the already-distilled Pass 3b output — it is substantially smaller than the Signal set. No batching loop is implemented. If a future project produces >80 CCIs for a single row, a `large_cci_set_advisory` fires (§3.3) but processing still proceeds as a single call.

**MD-2 — Four re-run scenarios via hash-based detection.** Pass 3b's re-run behaviour is extend-on-rerun (additive). Pass 3c has four distinct code paths (FirstRun / IdempotentRerun / IncrementalRerun / FullRerun) selected by SHA-256 hash comparison of the sorted ci_id list against the prior AnalysisPass record. The hash is stored in `AnalysisPass.outputs.mechanism_data.cci_set_hash` on every run. See §4.1 for detection logic.

**MD-3 — Three prompt templates, three Pydantic schemas.** Different re-run scenarios and the repair path require structurally different AI outputs. Each prompt has its own template file and response schema rather than a single polymorphic schema. The DM entity-production stage reads from the validated schema output, not the raw AI string.

**MD-4 — cell_content_item_refs stored as JSONB array on domain table.** The canonical ledger v2.12 Domain schema defines `cell_content_item_refs` as a `string[]` attribute on the Domain entity. This is implemented as a `cell_content_item_refs JSONB NOT NULL DEFAULT '[]'` column on the `domain` table — matching the canonical schema directly. A separate `domain_cci_membership` join table is not used. Rationale: the join table would duplicate a canonical attribute; the canonical JSON export would require an assembly step; and the first PMT production ledger export confirmed that the join table approach produced Domain entities with `cell_content_item_refs` absent from the payload, breaking canonical compliance and Phase 6/8 coverage analysis. The JSONB array approach produces canonical-compliant Domain payloads without an assembly step. A GIN index on `domain.cell_content_item_refs` can be added if Phase 6/8 reverse-lookup queries ("which Domains contain CCI X?") require optimisation.

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
  - Otherwise: call `query_committed_cci_ids_for_row(row_ref, project_id)` — a database query that returns the set of ci_ids covered by active Domains for this row/project. Executes: `SELECT DISTINCT jsonb_array_elements_text(cell_content_item_refs) AS ci_id FROM domain WHERE project_id = :pid AND row_target = :row AND retired_at IS NULL`. This is **not** a stored field in `mechanism_data`; it requires a live DB query. Compute `new_cci_count = len(eligible_ci_ids - prior_committed_ci_ids)`.
  - If `new_cci_count / prior_cci_count >= domain_rerun_threshold`: `scenario = "FullRerun"`. Else: `scenario = "IncrementalRerun"`.

**Implementation note on `query_committed_cci_ids_for_row`:** This function executes `SELECT domain_id, jsonb_array_elements_text(cell_content_item_refs) AS ci_id FROM domain WHERE project_id = :pid AND row_target = :row AND retired_at IS NULL`. The result represents the CCI coverage footprint of the last committed Domain set. It must **not** be confused with a stored snapshot in the AnalysisPass record — the AnalysisPass stores only the hash, not the ci_id list.

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
Construct existing Domain summaries from ledger: for each active Domain for this row/project, produce `{domain_id, name, description, cci_ref_count}`. Assemble new CCI delta: CCIs in `eligible_ccis` not present in any active Domain's `cell_content_item_refs` array.
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

**IncrementalRerun assign-action handling:** On IncrementalRerun, Stage 2 produces two outputs: (1) `domain_entities` — new Domain proposals (action="new"), passed to Stage 4 for entity construction; (2) `assign_membership_inserts` — a list of `(existing_domain_id, new_ci_id)` tuples derived from action="assign" outputs. `assign_updates` is an in-memory structure produced during Stage 2 output processing. It is **not written in Stage 3** — Stage 3 has no DB calls of any kind. It is passed to Stage 4 and written inside the Stage 4 transaction (see §4.4.3 step 3b).

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

**CHK-3c-07 — Single-artefact domain absorption (IM conditional):**
After CHK-3c-06, identify single-CCI domains:
```
single_cci_proposals = [p for p in proposals if len(p.cci_refs) == 1]
```

**Exception — do not fire if:**
- `cci_count_input <= 1`: degenerate sparse row (e.g. Row 4 PMT). A single Domain with a single CCI is the correct outcome when only one CCI exists. Skip CHK-3c-07 silently.
- `len(proposals) == 1`: nothing to absorb into. Skip silently.
- All proposals have `len(cci_refs) == 1`: circular absorption risk. Log advisory `{type: "chk3c07_all_domains_single_cci"}` and skip.

**If single-CCI domains exist and exceptions do not apply:**
Issue a CHK-3c-07 repair prompt (IM). Parameters:
- `isolated_ccis`: list of `{ci_id, column, classification_type, description}` — the CCIs from all single-CCI proposals
- `available_domains`: list of `{name, description, cci_count}` — all non-single-CCI proposals
- `row_guidance`: same `ROW_GUIDANCE[str(row_ref)]` block used in Stage 2

Parse response against `domain_single_cci_repair_response_schema.py` — a `List[SingleCCIAssignAction]` where each action specifies `{ci_id: str, target_domain_name: str, rationale: str}`. Uses `domain_name` (not `domain_id`). DISTINCT class from all other schemas — see §5.2.

**Naming prohibition (must be explicit in prompt):** The CHK-3c-07 repair prompt MUST include: "Any new domain names produced must not use 'and' or '&' without first confirming no single concept covers both sub-themes. If a single concept exists, use it as the name. If no single concept exists and 'and' is unavoidable, that signals two distinct domains — but this prompt only assigns, not splits."

**Merge operation:**
For each `SingleCCIAssignAction`: match `target_domain_name` case-insensitively against non-single-CCI proposals; add `ci_id` to the matched proposal's `cci_refs`. Remove all single-CCI proposals from the proposals list. Re-run CHK-3c-04 (Non-Loss) as a safety check to confirm all CCIs are still covered.

Record in `mechanism_data`:
- `single_cci_absorption_issued: true`
- `absorptions: List[{ci_id, absorbed_from_domain_name, absorbed_into_domain_name}]`

Append to `execution_warnings`: `{type: "chk3c07_absorption_performed", count: N}` — informational only; does not change `execution_status`.

**Repair failure fallback:**
If parse fails (two retries): log `{type: "chk3c07_repair_failed", isolated_ci_ids: [...]}` to `execution_warnings`. Leave single-CCI proposals in place. Do NOT fail the run — a single-CCI domain is preferable to a Failed AnalysisPass. Set `single_cci_absorption_issued: false`. PLB-3c-06 will surface the residual single-CCI domains for Practitioner review.

**CHK-3c-08 — Over-concentrated domain split (IM conditional):**
After CHK-3c-07, before ADVC-3c-01, check for over-concentrated domains:
```
concentration_threshold = floor(eligible_count / 2)
concentrated_proposals = [p for p in proposals if len(p.cci_refs) > concentration_threshold]
```

**Exception — do not fire if:**
- `eligible_count <= 4`: sparse row — splitting would produce near-empty domains. Skip silently.
- `len(proposals) == 1`: only one domain; cannot split into meaningful sub-domains without knowing the full row context. Skip silently.
- All proposals exceed the threshold: circular split risk — every domain is concentrated, which may reflect genuine CCI distribution. Log advisory `{type: "chk3c08_all_domains_concentrated"}` and skip.

**If concentrated domains exist and exceptions do not apply:**
Issue a CHK-3c-08 split repair prompt (IM). Parameters:
- `concentrated_domain`: `{name, description, cci_refs}` of the over-concentrated proposal (handle multiple concentrated domains in one call if present)
- `other_domains`: list of `{name, description, cci_count}` — existing non-concentrated proposals for context
- `row_guidance`: same `ROW_GUIDANCE[str(row_ref)]` block — row-appropriate reasoning
- `concentration_threshold`: the threshold value — so the AI understands the scale

Parse response against `domain_split_repair_response_schema.py` — a `List[SplitDomainProposal]` where each proposal specifies `{name: str, description: str, cci_refs: List[str], rationale: str}`. DISTINCT class from all other schemas — see §5.2.

**Naming prohibition (must be explicit in prompt):** The CHK-3c-08 split repair prompt MUST include: "Each split domain name must not use 'and' or '&'. If a sub-theme appears to require 'and', find the single concept that unifies those CCIs and use that as the name. The purpose of splitting is to produce coherently-named single-concept domains — not domains whose names are themselves compound."

**Merge operation:**
Remove the concentrated proposal(s). Add each `SplitDomainProposal` as a new proposal. Verify Non-Loss: union of all split proposals' `cci_refs` must equal the original concentrated domain's `cci_refs` — if any ci_id is missing, add it to the largest split proposal and log an advisory. Re-run CHK-3c-04 (Non-Loss) safety check across all proposals. Re-run CHK-3c-07 to check whether any newly split proposals are themselves single-CCI (the two checks may chain).

Record in `mechanism_data`:
- `domain_split_issued: true`
- `splits: List[{original_domain_name, split_into: List[{name, cci_count}]}]`

Append to `execution_warnings`: `{type: "chk3c08_split_performed", count: N}` — informational only; does not change `execution_status`.

**Repair failure fallback:**
If parse fails (two retries): log `{type: "chk3c08_repair_failed", concentrated_domain_name: name, cci_count: N}` to `execution_warnings`. Leave the concentrated proposal in place. Do NOT fail the run — an over-concentrated domain is preferable to a Failed AnalysisPass. Set `domain_split_issued: false`. PLB-3c-03 will surface the residual concentration for Practitioner review.

**ADVC-3c-01 — Domain count bounds advisory (OQ-3c-01 resolution):**
After CHK-3c-06 (and after CHK-3c-07 if it ran), before exiting Stage 3, compute soft-bounds advisory. Use `eligible_count = len(eligible_ccis)` (available from Stage 1; same value as `mechanism_data.cci_count_input`) and `proposal_count = len(proposals)`:

```
lower_bound = 1 + ceil(eligible_count / 15)
upper_bound = floor(eligible_count / 2)
```

**Inverted-range guard (sparse row protection):** If `upper_bound < lower_bound`, the formula has produced an incoherent range — this occurs when `eligible_count <= 3` (e.g. Row 4 PMT with 1 CCI produces lower=2, upper=0). In this case: skip the advisory entirely. No entry is written to `execution_warnings`. A single domain from a sparse CCI set is the correct outcome, not an advisory condition.

Only if `upper_bound >= lower_bound` and (`proposal_count < lower_bound` OR `proposal_count > upper_bound`):
- Append to `execution_warnings`: `{type: "domain_count_advisory", domain_count: proposal_count, cci_count: eligible_count, lower_bound: lower_bound, upper_bound: upper_bound}`
- This is advisory only — does not affect `execution_status`; does not block entity production.

`execution_warnings` is a standard top-level AnalysisPass field outside `mechanism_data` — see §7 for the complete enumeration of all advisory types and their status impact.

### 4.4 Stage 4 — Entity Production and Ledger Commit (DM)

**4.4.1 domain_id allocation:**
Query `MAX(CAST(SUBSTRING(domain_id, 2) AS INTEGER)) FROM domain WHERE project_id = current_project` (no `retired_at` filter — must include both active and retired Domains to prevent id reuse). If null (no prior Domains): `next_seq = 1`. Else: `next_seq = max_val + 1`. Allocate D001, D002, ... incrementally across the proposals.

On `IncrementalRerun`: existing active Domains retain their domain_ids. Only new Domains (from `action="new"` repair entries or new Domain proposals in the incremental AI response) receive new ids from `next_seq`.

On `FullRerun`: record `domain_count_retired` = count of currently active Domains for this row/project. Set `retired_at = NOW()` on all active Domains for this row/project. Then allocate fresh domain_ids for all proposals from `next_seq`.

**4.4.2 Domain entity construction:**
Construct Domain entities from the validated proposals. Each Domain carries the six canonical attributes: `domain_id`, `name`, `description`, `classification_type`, `row_target`, and `cell_content_item_refs` (stored as a JSONB array directly on the domain row — no assembly from a join table). No `domain_qualifier` or `upstream_domain_ref` — both withdrawn (see §3.2 MD-6). Cross-row Domain tracing is available via the canonical path `Domain → cell_content_item_refs → CCI → signal_refs → Requirement (row n-1) → domain_refs → Domain (row n-1)`.

**4.4.3 Ledger transaction:**
Open a single Postgres transaction. Within the transaction:
1. For `FullRerun`: execute `UPDATE domain SET retired_at = NOW() WHERE project_id = current_project AND row_target = str(row_ref) AND retired_at IS NULL`.
2. `INSERT INTO domain (domain_id, project_id, name, description, classification_type, row_target, cell_content_item_refs)` for each new Domain entity — `cell_content_item_refs` is the JSONB array of ci_ids from the proposal directly. No separate membership table insert.

   *(Note: step 3a — `domain_cci_membership` INSERTs — was retired in v0.14 when `cell_content_item_refs` moved to a JSONB array on the `domain` row. Step numbering is preserved for downstream reference continuity.)*

3b. **IncrementalRerun only:** For each `(existing_domain_id, new_cci_refs)` in `assign_updates`: `UPDATE domain SET cell_content_item_refs = cell_content_item_refs || :new_refs::jsonb WHERE domain_id = :id AND project_id = :pid AND retired_at IS NULL`. Appends new ci_ids to the existing array atomically. If `assign_updates` is empty or scenario is not IncrementalRerun, this step is skipped.
4. `UPDATE register SET member_ids = :new_member_ids WHERE register_type = 'Domain' AND project_id = current_project` — where `new_member_ids` is the JSON array of **all active domain_ids across all rows for this project**. The query MUST be `SELECT domain_id FROM domain WHERE project_id = :pid AND retired_at IS NULL` — **no `row_target` filter**. Scoping to `row_target = str(row_ref)` is a common mistake that silently drops Domains from other rows.

If the transaction rolls back: `execution_status = "Failed"`, `failure_reason = "Ledger transaction rolled back: {error}"`. No partial commit.

**4.4.4 FullRerun retirement mapping:**
**Timing is critical:** Capture `prior_active_domains = query_active_domains_for_row(row_ref, project_id)` before opening the ledger transaction. Compute `retirement_mapping` by Jaccard token overlap between each retiring Domain name and each new proposal name: tokenise both names (lowercase split), compute `|intersection| / |union|`. If best overlap ≥ **0.50**, assign that proposal as `inferred_successor_domain_id`. Else: `null`. The 0.50 threshold is hardcoded — the former `domain_upstream_match_threshold` ProjectProfile parameter was withdrawn along with `upstream_domain_ref`; this threshold is not configurable. Record `{old_domain_id: "D001", inferred_successor_domain_id: "D007" | null}` for each retiring Domain. Store in `mechanism_data.retirement_mapping`. Only then open the transaction and execute the retirement UPDATE. Computing this mapping after the UPDATE is an implementation error.

**4.4.5 downstream_rerun_required flag:**
If `scenario == "FullRerun"`: query whether any AnalysisPass with `mechanism="RequirementDerivation"` and `row_ref = current_row` and `project_id = current_project` exists with `execution_status ∈ {"Completed", "CompletedWithWarnings"}`. If yes: set `mechanism_data.downstream_rerun_required = true`. Else: `false`.

**4.4.6 AnalysisPass write:**
Write outside the main ledger transaction (same pattern as Pass 3b Step 6). Populate all fields of `mechanism_data` per §7.

**Scope of this rule:** §4.4.6 governs runs that reach Stage 4. Stage 1 early exits (zero-CCI path, §4.1) bypass Stage 4 entirely and set `execution_status = "CompletedWithWarnings"` directly — they are not governed by this section.

AnalysisPass `execution_status` for runs that reach Stage 4 is determined as follows:

- `"Failed"` — if any hard stop was hit: Pass 3b prerequisite not met; AI parse failure after retry; zero domains survived validation; ledger transaction rollback.
- `"CompletedWithWarnings"` — if, and only if, one or more of these conditions hold: (a) persistent orphaned CCIs remain in `mechanism_data.orphaned_ccis` after the repair attempt; (b) IncrementalRerun AI parse failed and the run fell back to FullRerun — this is signalled by `incremental_fallback_to_fullrerun` in `execution_warnings` and is the one `execution_warnings` entry that directly triggers `CompletedWithWarnings`; (c) mode violations are recorded in `mechanism_data.mode_violations`.
- `"Completed"` — all other outcomes that reach Stage 4, including: IdempotentRerun (distinguished by `mechanism_data.idempotent = true`); successful repair (all orphans recovered); runs where only informational advisories were logged (`large_cci_set_advisory`, `domain_count_advisory`, `duplicate_domain_name_merged`, `repair_assign_name_not_found`, `incremental_assign_invalid_domain_id`, `cci_referential_integrity_violation`). These `execution_warnings` entries are informational only and do NOT trigger `CompletedWithWarnings`.

On IdempotentRerun: `mechanism_data` contains hash, scenario, and `idempotent = true` — domain production fields are zero-valued.

---

## 5. Schema and Validation

### 5.1 SQLAlchemy / Pydantic models and Database DDL

**Database DDL — `domain` table:**

The authoritative CREATE TABLE statement for the Alembic migration. This is the canonical DDL — it supersedes all earlier versions in Understanding §13.8 documents.

```sql
CREATE TABLE domain (
    domain_id                VARCHAR(10)  NOT NULL,   -- D### format; regex ^D\d{3}$
    project_id               VARCHAR(50)  NOT NULL,
    name                     TEXT         NOT NULL,
    description              TEXT         NOT NULL,
    classification_type      TEXT,
    row_target               VARCHAR(1)   NOT NULL
                                 CHECK (row_target IN ('1','2','3','4','5','6')),
    cell_content_item_refs   JSONB        NOT NULL DEFAULT '[]',
    retired_at               TIMESTAMPTZ,
    created_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (domain_id, project_id)
);
-- GIN index for reverse-lookup queries ("which Domains contain CCI X?")
-- Add if Phase 6/8 coverage analysis query performance requires it:
-- CREATE INDEX idx_domain_cci_refs ON domain USING GIN (cell_content_item_refs);

-- DomainRegister seed row (one per project)
INSERT INTO register (register_id, register_type, project_id, member_ids, completeness_rule)
VALUES ('DR-001', 'Domain', :project_id, '[]',
        'This register SHALL contain the identifiers of ALL Domain elements present in the ledger.');
```

**Migration author notes:**
- `cell_content_item_refs` is a JSONB array on the `domain` table — matching the canonical ledger v2.12 Domain schema directly. No `domain_cci_membership` join table. The join table approach was retired after the first PMT production run confirmed it produced Domain entities with `cell_content_item_refs` absent from the canonical payload.
- IncrementalRerun assign-action updates use Postgres array append: `cell_content_item_refs = cell_content_item_refs || :new_refs::jsonb`.
- `retired_at IS NULL` = active Domain. `query_max_domain_id` must NOT filter on `retired_at` — retired ids must be counted to prevent reuse.
- Migration file: `migrations/XXXX_add_domain_tables.py`.

**`DomainModel` (SQLAlchemy ORM — `domain` table):**
Maps to the DDL above. Key attributes:
- `domain_id`: String, PK component; CHECK `domain_id ~ '^D\d{3}$'`
- `project_id`: String, PK component
- `name`: String NOT NULL
- `description`: Text NOT NULL
- `classification_type`: String nullable
- `row_target`: String NOT NULL; CHECK IN ('1','2','3','4','5','6')
- `cell_content_item_refs`: JSONB NOT NULL DEFAULT '[]' — list of ci_id strings
- `retired_at`: TIMESTAMPTZ nullable; null = active; non-null = retired
- `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()
- Composite PK: `(domain_id, project_id)`

**`DomainSchema` (Pydantic — canonical ledger API representation):**
Mirrors the canonical ledger v2.12 Domain element exactly — six attributes, read directly from `DomainModel.cell_content_item_refs` (no join, no assembly):
```
domain_id:              str  — regex ^D\d{3}$
name:                   str
description:            str
classification_type:    Optional[str]
row_target:             str  — Literal["1","2","3","4","5","6"]
cell_content_item_refs: List[str]  — read from domain.cell_content_item_refs
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

**`domain_single_cci_repair_response_schema.py` — CHK-3c-07 single-CCI absorption:**

**IMPORTANT — DISTINCT CLASS:** `SingleCCIAssignAction` uses `domain_name: str` to reference the target domain. It is a distinct class from `AssignAction` in `domain_repair_response_schema.py` and from `AssignAction` in `domain_incremental_response_schema.py`. Do NOT import or share these classes across files. The critical difference:
- `domain_incremental_response_schema.py` AssignAction: `domain_id: str` — references an existing committed Domain by ID
- `domain_repair_response_schema.py` AssignAction: `domain_name: str` — references a proposal by name (CHK-3c-04 repair)
- `domain_single_cci_repair_response_schema.py` SingleCCIAssignAction: `domain_name: str` — references a non-single-CCI proposal by name (CHK-3c-07 repair)

```
SingleCCIAssignAction:
  ci_id:               str   — the ci_id being absorbed (must be from isolated_ccis list)
  target_domain_name:  str   — name of the receiving Domain (case-insensitive match against available_domains)
  rationale:           str   — AI explanation of why this assignment is appropriate

SingleCCIRepairResponse:
  assignments: List[SingleCCIAssignAction]
  # Only assign actions — no new Domain creation. Every isolated ci_id must appear in exactly one assignment.
```

**`domain_split_repair_response_schema.py` — CHK-3c-08 over-concentration split:**

**IMPORTANT — DISTINCT CLASS:** `SplitDomainProposal` is a new proposal schema — distinct from all other schemas. It produces new domain proposals (with `cci_refs`) from the concentrated domain's CCI set. It does NOT use `domain_name` for referencing an existing domain (unlike CHK-3c-04 and CHK-3c-07 schemas). The four schemas all handle different operations and must never be shared:
- `domain_repair_response_schema.py`: assign/new actions with `domain_name` reference → CHK-3c-04
- `domain_incremental_response_schema.py`: assign/new actions with `domain_id` reference → IncrementalRerun
- `domain_single_cci_repair_response_schema.py`: assign-only with `domain_name` reference → CHK-3c-07
- `domain_split_repair_response_schema.py`: new proposals with `cci_refs` lists → CHK-3c-08

```
SplitDomainProposal:
  name:         str        — name of the new sub-domain (must not use 'and' or '&')
  description:  str        — description of the new sub-domain's responsibility
  cci_refs:     List[str]  — ci_ids from the original concentrated domain assigned to this sub-domain
  rationale:    str        — AI explanation of why these CCIs form a coherent sub-domain

SplitRepairResponse:
  proposals: List[SplitDomainProposal]
  # Must produce 2 or more proposals. Union of all cci_refs must equal the original domain's cci_refs.
  # No CCI may appear in more than one proposal (no duplication).
```
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

### 5.4 Row abstraction guidance — prompt constants

Each row has a structured guidance block injected into `domain_grouping_prompt.py` and `domain_incremental_prompt.py`. This replaces the previous single-phrase `ROW_ABSTRACTION_PHRASES` dict. The guidance is principle-based, not pattern-based — it teaches the AI *how to reason* at each row's abstraction level, not what themes to expect. This is intentional: the system must work for any source document, not just projects whose domain structure resembles a prior POC.

**Row 2–5 guidance blocks** are held in separate POC documents and will be integrated in subsequent spec versions after Row 1 has been validated in production. The `ROW_GUIDANCE` dict below is therefore partial — Row 2–5 entries retain the previous short phrase pending their own validation cycle.

```python
ROW_GUIDANCE = {
    "1": """
## Row 1 — Planner / Scope Layer

At this row you are working at the enterprise scope level — the view of a senior
executive or board member who needs to understand what the enterprise is committing
to and why, without reference to how any system works.

### What a Row 1 domain represents
A Row 1 domain is a bounded enterprise concern — a cluster of things the enterprise
must care about, be accountable for, or govern. It is NOT:
- An application feature or system function
- A process step or workflow
- A technical component or implementation partition
- A single CCI grouped alone for convenience

A Row 1 domain SHOULD be nameable to a non-technical executive without explanation.
If the name requires knowledge of how the system works, it is at the wrong level.

### Vocabulary signals
Row 1 domain names use nouns of enterprise concern:
  Appropriate: accountability, governance, participation, oversight, stewardship,
               obligation, entitlement, transparency, commitment, responsibility
  Avoid: calculate, display, track, manage, process, generate, store, retrieve
         (these describe system functions — they belong at Row 2 or below)

### Cross-column integration
Row 1 domains span multiple Zachman columns. An enterprise concern inherently
involves what is at stake (WHAT), why it matters (WHY), who is accountable (WHO),
how commitment is expressed (HOW), and when it applies (WHEN). A domain drawing
from only one Zachman column is likely too narrow — consider absorbing it into a
broader concern.

### What to look for in the CCI set
Group CCIs by the enterprise-level concern they express, not by the interrogative
that produced them or the feature they describe. Ask: if you stripped away all the
system-specific details, what is the enterprise fundamentally committing to?

Common enterprise-level concern themes that emerge at this level include:
- Who participates and what their relationship to the enterprise is
- What the enterprise is accountable for delivering or maintaining
- What governs or constrains behaviour across the enterprise
- What information the enterprise must retain and be answerable for

These are illustrative, not prescriptive — use the CCI content to discover what
concerns this specific enterprise actually has. Do not force CCIs into a theme if
the content does not support it.

### Prohibition rules
- Do NOT create a domain containing only one CCI
- Do NOT name a domain after a Zachman interrogative ("WHO Domain", "WHY Domain")
- Do NOT use feature-level or function-level names for domains
- Do NOT create overlapping domains where the same concern appears in two groups

### The "and" test
If a proposed domain name requires 'and' or '&', apply this two-step test:
1. **Is there a single concept that encompasses both sub-themes without 'and'?**
   If yes — use that single concept name. Example: "Regulatory and Social
   Responsibility" becomes "Corporate Responsibility Governance". The grouping is
   correct; the name just needs to identify the unifying concept.
2. **If no single concept exists** — the domain likely contains two distinct
   enterprise concerns that fail differently. Create two domains instead.

- Do NOT use 'and' or '&' in domain names without first applying the "and" test.
  If the test yields a single-concept name, use it. If not, split into two domains.
""",

    "2": """
## Row 2 — Owner / Business Level

At this row you are working at the business-owner level — the view of someone who
understands what the enterprise is responsible for delivering and how it must behave,
but who is not concerned with how that responsibility is technically realised.

### What a Row 2 domain represents
A Row 2 domain is a bounded, persistent business responsibility. Three tests determine
whether a candidate is a genuine domain:
- **Bounded:** A single scope statement can be written for it without using 'and'.
  If 'and' is required, it is probably two domains.
- **Persistent:** The responsibility applies across the lifecycle — it is not a single
  activity or event.
- **Distinct failure mode:** When this responsibility fails, it fails differently from
  neighbouring responsibilities. If two candidates fail in the same way, they are
  probably one domain.

A Row 2 domain is NOT:
- A system function or algorithm ("Earnings Calculator", "Task Processor")
- A workflow step or process phase
- A technical component, API, schema, or database concept
- A single actor in isolation ("Child User Domain")
- A Zachman column heading ("HOW Domain", "WHO Domain")

### Row 2 Zachman column semantics
Row 2 CCIs express the following at each column:
- **WHAT**: Business artefacts — the things that exist and are exchanged in the
  business (entities, relationships, attributes). Not data models or schemas.
- **HOW**: Business capability declarations — what the business must be able to do,
  stated as stateless obligations. NOT step-by-step workflows or process sequences.
- **WHERE**: Business context and boundary — where the business operates, the scope
  of its reach.
- **WHO**: Business roles and accountabilities — who is responsible and accountable.
  Not interaction sequences or system actors.
- **WHEN**: Business lifecycle and triggers — what business events cause things to
  happen, what cycles govern operations. Not schedules or technical timers.
- **WHY**: Business governance rules and motivation — why things must be true, what
  constraints govern business behaviour, what the business is trying to achieve.

Group CCIs by the business responsibility they collectively express, drawing across
columns. A domain drawing from only one column is likely too narrow.

### Domain qualification questions
For each proposed domain, ask:
- Can a single scope statement be written for it without using 'and' or '&'?
  If 'and' / '&' is required, it is probably two domains — split it.
- Does it align with a **single business objective**, or multiple?
  If multiple objectives are present, the domain should be split by objective.
- Does it persist across multiple business contexts and user roles?
- When this domain fails, does it fail differently from the others?
- Could this responsibility evolve independently without forcing changes to neighbours?
- Are there **overlapping domains** that need to be consolidated or separated?
  If a domain's name requires 'and' or '&', it is a candidate for separation into two.

If the answer to any question is 'no', reconsider the boundary.

### Vocabulary signals
Row 2 domain names use business responsibility vocabulary:
  Appropriate: accountability, entitlement, stewardship, governance, settlement,
               participation, oversight, obligation, responsibility, record
  Avoid: calculate, process, store, retrieve, aggregate, compute, manage, track,
         retain, retention
         (these describe system functions or technical storage — they belong at
         Row 3 or below; use 'stewardship', 'record', or 'accountability' instead)
  Also avoid: any word that implies a technical mechanism (API, schema, database,
              algorithm, service, endpoint)
  Avoid: 'and' or '&' in domain names without first applying the "and" test above

### Stakeholder actors
Business actors (WHO-column CCIs) are rarely a standalone domain on their own —
they are actors *within* business responsibilities. Group the actor alongside the
CCIs that describe their primary business responsibility rather than isolating
them as a separate actor domain.

### Prohibition rules
- Do NOT create a domain containing only one CCI
- Do NOT isolate a stakeholder actor as a standalone domain
- Do NOT use workflow or function verbs in domain names
- Do NOT use 'and' or '&' in domain names without first applying the "and" test:
  (1) Is there a single concept that covers both sub-themes? If yes, use it.
  (2) If no single concept exists, the domain contains two distinct concerns
      — create two domains instead.
- Do NOT create domains whose boundaries cannot be explained to a business owner
""",
    "3": """
## Row 3 — Designer / Logical Level

At this row you are working at the logical design level — the view of a system
designer who is translating business obligations into logical structures, behaviours,
and rules, without committing to any specific technology or implementation.

### What a Row 3 domain represents
A Row 3 domain is a bounded logical design responsibility — a coherent cluster of
logical structures, behaviours, or constraints that must be designed together and
can be assessed for logical completeness independently. It IS NOT:
- A business capability (that belongs at Row 2)
- A physical technology component or platform (that belongs at Row 4)
- A code module, class, or implementation unit
- A deployment or runtime concern

A Row 3 domain should be describable to a technically-minded architect without
naming any specific technology. If the name requires knowing the implementation
platform, it is at the wrong level.

### Row 3 Zachman column semantics
- **WHAT**: Logical data structures — entities, relationships, attributes, and
  constraints expressed as a logical model (not physical tables or schemas)
- **HOW**: Logical processes and rules — how the system logically transforms,
  validates, or routes information; logical state transitions; NOT code or algorithms
- **WHERE**: Logical system boundary and interaction topology — how logical components
  relate and communicate; NOT physical deployment targets or infrastructure
- **WHO**: Logical actors and roles — the system's logical participants and their
  authorisation boundaries; NOT UI components or physical user interfaces
- **WHEN**: Logical event and state model — what conditions trigger logical state
  changes; NOT schedules, timers, or cron configurations
- **WHY**: Logical constraints and integrity rules — the design-level invariants the
  system must enforce; NOT business policies (Row 2) or code assertions (Row 5)

### Domain qualification questions
- Does this cluster of CCIs share a logical design boundary that can be assessed
  for completeness independently?
- Would a change to this logical design necessarily ripple through all CCIs in
  the cluster?
- Does this domain fail differently from neighbouring domains — in a way that a
  designer (not a business owner, not a developer) would recognise?
- Can the domain be described in one sentence without naming any technology?
- Can the domain be described in one sentence **without using 'and' or '&'**?
  If 'and' is required, it likely contains two distinct logical design concerns — split it.
- Does it align with a **single logical design objective**, or multiple?

### Vocabulary signals
Row 3 domain names use logical design vocabulary:
  Appropriate: logical model, logical structure, logical behaviour, state management,
               constraint enforcement, data model, interaction model, access model,
               visibility model, lifecycle, derivation logic, decision logic
  Avoid: physical technology names (PostgreSQL, React, Redis, AWS, iOS), code
         patterns (class, function, module, endpoint), business policy language
         (obligation, stewardship, entitlement — those are Row 2)
  Avoid: 'computation', 'calculation', 'reporting' — these imply algorithmic or
         output-level detail that belongs at Row 5. Prefer 'derivation logic',
         'decision model', or 'visibility model' at Row 3.
  Avoid: 'and' or '&' in domain names — these signal two distinct logical concerns
         merged into one domain

### Cross-column integration
Row 3 domains should integrate logical structure (WHAT) with logical behaviour (HOW)
and logical constraints (WHY). A domain drawing from only HOW is likely a process
description, not a logical design responsibility. A domain drawing from only WHY is
likely a constraint definition that should be anchored to a structural or behavioural
domain.

### Sparse CCI sets at Row 3
Row 3 sometimes has few CCIs if the source document is operationally-framed. When
the CCI set is sparse (fewer than 8 CCIs), expect 2–3 domains. Do not force more
domains than the CCI content supports — a smaller number of richer domains is
preferable to many thin ones.

### Prohibition rules
- Do NOT create a domain containing only one CCI (unless cci_count_input == 1)
- Do NOT name a domain after a technology, platform, or framework
- Do NOT use business-obligation language (Row 2 vocabulary) in domain names
- Do NOT create domains that only describe a single Zachman column in isolation
- Do NOT use 'and' or '&' in domain names without first applying the "and" test:
  (1) Is there a single concept that covers both sub-themes? If yes, use it.
  (2) If no single concept exists, the domain contains two distinct concerns
      — create two domains instead.
- Do NOT use 'computation', 'calculation', or 'reporting' as primary descriptors —
  these are Row 5 vocabulary; use 'derivation logic', 'decision model', or
  'visibility model' instead
""",

    "4": """
## Row 4 — Builder / Physical Level

At this row you are working at the physical builder level — the view of a builder
who is making concrete technology choices and specifying physical components,
without yet writing code or configuring runtime details.

### What a Row 4 domain represents
A Row 4 domain is a bounded physical construction responsibility — a coherent cluster
of physical technology choices, component specifications, or platform decisions that
must be built together. It IS NOT:
- A business responsibility (Row 2)
- A logical design concern (Row 3)
- A code-level implementation detail, configuration value, or runtime parameter (Row 5)

A Row 4 domain names a physical technology area that a builder would take
responsibility for constructing. The domain name can and should reference specific
technologies, platforms, or physical components.

### Row 4 Zachman column semantics
- **WHAT**: Physical data artefacts — physical schemas, storage formats, data
  structures as they will actually be built
- **HOW**: Physical processes and algorithms — the concrete mechanisms that realise
  logical behaviours; specific APIs, service contracts, integration patterns
- **WHERE**: Physical deployment targets — specific platforms, infrastructure nodes,
  hosting environments (e.g. iOS, Android, Windows, AWS region)
- **WHO**: Physical user interfaces and system interfaces — the concrete components
  through which actors interact with the system
- **WHEN**: Physical scheduling and triggering — specific timers, cron jobs, event
  queues, scheduling mechanisms
- **WHY**: Physical constraints — platform version requirements, hardware limits,
  compliance mandates expressed as build-level constraints

### Domain qualification questions
- Does this cluster of CCIs require the same physical technology or platform context?
- Would a builder owning this domain have a coherent, bounded construction scope?
- Does this domain fail differently from neighbouring domains — in the way a builder
  (not a designer, not a developer) would recognise?
- Can the domain be described in terms of physical artefacts without describing code?
- If the domain name requires 'and' or '&', apply the "and" test: first ask
  whether a single concept covers both sub-themes. If yes, use that concept name.
  If no single concept exists, the domain has two distinct construction areas — split it.

### Vocabulary signals
Row 4 domain names use physical construction vocabulary:
  Appropriate: platform, component, infrastructure, deployment, interface,
               integration, physical schema, service, API, build, configuration
  Avoid: business-level language (Row 2), logical abstractions without physical
         specifics (Row 3), code-level implementation detail (Row 5)
  Avoid: 'and' or '&' in domain names — these signal two distinct physical
         construction areas merged into one domain

### Sparse CCI sets at Row 4
Row 4 is often sparse for systems whose primary content is conceptual or logical.
A single-CCI row is legitimate — if only one physical constraint or component exists
in the source material, one domain is the correct outcome. Do not invent domains to
fill expected counts. The CHK-3c-07 single-CCI absorption rule does not fire when
cci_count_input == 1.

### Cross-column integration
Row 4 domains should reflect genuine physical construction boundaries. A deployment
platform domain (WHERE-heavy) is valid at Row 4 because physical platform concerns
are genuinely coherent at this level. A domain drawing from only WHY (a physical
constraint) is thinner but may be unavoidable when the source material contains
only a constraint at this row.

### Prohibition rules
- Do NOT create domains that describe business obligations (Row 2 vocabulary)
- Do NOT create domains that describe logical design without physical specifics
- Do NOT name a domain after a logical concept without its physical realisation
- Do NOT use 'and' or '&' in domain names without first applying the "and" test:
  (1) Is there a single concept that covers both sub-themes? If yes, use it.
  (2) If no single concept exists, the domain contains two distinct concerns
      — create two domains instead.
""",

    "5": """
## Row 5 — Implementer / Detailed Design Level

At this row you are working at the detailed design level — the view of an implementer
who is specifying the precise detail needed to build and configure the system:
algorithms, data formats, platform-specific configurations, interface contracts,
and detailed runtime behaviours.

### What a Row 5 domain represents
A Row 5 domain is a bounded detailed implementation responsibility — a coherent
cluster of detailed specifications that an implementer must produce together.
It IS NOT:
- A business responsibility (Row 2)
- A logical design concern (Row 3)
- A high-level physical construction decision (Row 4)

A Row 5 domain represents a coherent area of detailed specification — the things
an implementer needs to fully specify before a developer can write code without
making additional design decisions.

### Row 5 Zachman column semantics
- **WHAT**: Detailed data specifications — exact field definitions, data types,
  format constraints, validation rules, enumeration values
- **HOW**: Detailed algorithms and process specifications — step-by-step logic,
  precise transformation rules, error handling specifications
- **WHERE**: Detailed deployment specifications — exact platform versions, node
  configurations, network topology details, infrastructure parameters
- **WHO**: Detailed interface specifications — precise UI component definitions,
  interaction specifications, user interface configurations per actor
- **WHEN**: Detailed timing specifications — exact cycle durations, timeout values,
  scheduling parameters, event sequencing constraints
- **WHY**: Detailed constraint specifications — precise validation rules, platform
  version requirements expressed as implementable constraints

### Domain qualification questions
- Does this cluster of CCIs share a detailed specification boundary that an
  implementer would own together?
- Could an implementer produce a complete detailed specification for this domain
  without needing decisions from neighbouring domains?
- Does this domain fail differently from neighbouring domains — in a way that an
  implementer (not a designer, not a business owner) would recognise?
- If the domain name requires 'and' or '&', apply the "and" test: first ask
  whether a single concept covers both sub-themes. If yes, use that concept name.
  If no single concept exists, the domain has two distinct specification areas — split it.

### Vocabulary signals
Row 5 domain names use detailed implementation vocabulary:
  Appropriate: interface, configuration, specification, deployment, platform-specific,
               detailed, implementation, cycle, timing, format, contract
  Avoid: business-level language (Row 2), logical abstractions (Row 3), generic
         high-level physical terms without specifics (Row 4)
  Avoid: 'and' or '&' in domain names — these signal two distinct specification
         areas merged into one domain

### Column-sparse CCI sets at Row 5
Row 5 CCIs often cluster in specific columns depending on the source document's
focus. A Row 5 CCI set containing only WHERE and WHO CCIs (platform deployment
nodes and user interface actors) is legitimate — group them by their natural
implementation boundary. WHERE CCIs (deployment nodes) naturally form a deployment
infrastructure domain. WHO CCIs (UI actors) naturally form a user interface
specification domain. WHEN CCIs (timing cycles) may be absorbed into the domain
whose behaviour they govern.

For sparse CCI sets, prefer fewer, richer domains over many thin ones. A domain
containing 2–3 CCIs from complementary columns is preferable to isolated single-
column domains.

### Prohibition rules
- Do NOT create a domain containing only one CCI (unless cci_count_input == 1)
- Do NOT use business-level or logical-level vocabulary in domain names
- Do NOT create overlapping domains where the same specification concern appears twice
- Do NOT force more domains than the CCI content supports
- Do NOT use 'and' or '&' in domain names without first applying the "and" test:
  (1) Is there a single concept that covers both sub-themes? If yes, use it.
  (2) If no single concept exists, the domain contains two distinct concerns
      — create two domains instead.
""",
    "6": "operational level — runtime procedures, user interactions, support processes, and operational behaviours",
}
```

The prompt template accesses `ROW_GUIDANCE[str(row_ref)]` and injects the full structured block as a prompt section. All rows 1–5 now carry structured principle-based guidance blocks. Row 6 retains a short phrase (operational content is rare in source documents). The prompt template handles both forms — Row 6's short phrase is injected inline; Rows 1–5 blocks are injected verbatim as prompt sections.

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

**Build correction note (from PMT production ledger):** The first PMT Pass 3c production run produced `mode_active: "LPM"` and `declared_transformation_modes: ["LPM"]` on all DomainDerivation AnalysisPasses. This is incorrect — LPM is a preservation constraint applied to CCI text handling, not a transformation mode. The correct values are `mode_active: "IM"` (the primary mode, Stage 2 AI call) and `declared_transformation_modes: ["IM", "DM"]`. The implementation must be corrected.

**LPM constraint** applies throughout: CCI `description` text is passed to the AI as read-only context. The AI is instructed not to reproduce CCI descriptions verbatim in Domain descriptions. The LPM constraint is enforced at the prompt instruction level (§4.1.2 of the Row 3 Mechanism Spec). Automated detection of verbatim copy is not implemented at v0.1 — deferred to a future tracker finding if empirical evidence shows LPM violations are occurring.

---

## 7. Audit Trail Population

The AnalysisPass `outputs` JSONB field for mechanism `"DomainDerivation"` has the following structure. All fields are required. Zero-value arrays must be present as `[]`, not null, not omitted.

**`execution_warnings` — placement clarification:** `execution_warnings` is a **standard top-level AnalysisPass field**, not a sub-field of `mechanism_data`. It is defined at the AnalysisPass model level (same pattern as Pass 3b and all other mechanisms) and is populated by the AnalysisPass writer utility with any advisory entries accumulated during the run.

Most `execution_warnings` entries are informational and do not change `execution_status`. The **one exception** is `incremental_fallback_to_fullrerun`: when this entry is present, `execution_status` is `CompletedWithWarnings` per §4.4.6 condition (b). `no_cci_input` is a Stage 1 early-exit advisory governed by §4.1 directly (produces `CompletedWithWarnings` there); §4.4.6 does not apply to the zero-CCI path. See §4.4.6 for the full `execution_status` determination rule.

Pass 3c writes to `execution_warnings` in the following cases:

| Advisory type | Source | When | Status impact |
|---|---|---|---|
| `no_cci_input` | §4.1 | Zero-CCI Stage 1 early exit | Governed by §4.1 → CompletedWithWarnings |
| `cci_referential_integrity_violation` | §4.1 | CCI references non-existent ZachmanCell; excluded | Informational only |
| `incremental_fallback_to_fullrerun` | §4.2 | IncrementalRerun AI parse failure; fell back to FullRerun | **CompletedWithWarnings** (§4.4.6 condition b) |
| `duplicate_domain_name_merged` | §4.3 CHK-3c-03 | Two or more proposals had the same name; merged | Informational only |
| `domain_count_advisory` | §4.3 ADVC-3c-01 | Domain count outside soft bounds | Informational only |
| `repair_assign_name_not_found` | §4.3 repair | Repair assign action domain_name unmatched; treated as new | Informational only |
| `incremental_assign_invalid_domain_id` | §5.2 | IncrementalRerun assign action domain_id invalid; treated as new | Informational only |
| `chk3c07_absorption_performed` | §4.3 CHK-3c-07 | Single-CCI domain(s) absorbed into neighbouring domains | Informational only |
| `chk3c07_repair_failed` | §4.3 CHK-3c-07 | CHK-3c-07 repair prompt failed after retries; single-CCI domains left in place | Informational only |
| `chk3c07_all_domains_single_cci` | §4.3 CHK-3c-07 | All proposals have exactly one CCI — circular absorption risk; CHK-3c-07 skipped | Informational only |
| `chk3c08_split_performed` | §4.3 CHK-3c-08 | Over-concentrated domain(s) split into sub-domains | Informational only |
| `chk3c08_repair_failed` | §4.3 CHK-3c-08 | CHK-3c-08 split prompt failed after retries; concentrated domain left in place | Informational only |
| `chk3c08_all_domains_concentrated` | §4.3 CHK-3c-08 | All proposals exceed concentration threshold — circular split risk; CHK-3c-08 skipped | Informational only |

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
    "single_cci_absorption_issued":  false,                // boolean; true if CHK-3c-07 repair was attempted
    "absorptions":                   [],                   // List[{ci_id, absorbed_from_domain_name,
                                                           //        absorbed_into_domain_name}]
                                                           // non-empty when single_cci_absorption_issued=true
    "domain_split_issued":           false,                // boolean; true if CHK-3c-08 split was attempted
    "splits":                        [],                   // List[{original_domain_name,
                                                           //        split_into: [{name, cci_count}]}]
                                                           // non-empty when domain_split_issued=true

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
| **VER-3c-03** | Every Domain has ≥1 entry in `cell_content_item_refs` | `jsonb_array_length(cell_content_item_refs) >= 1` for all active domains |
| **VER-3c-04** | All ci_ids in `cell_content_item_refs` resolve to `cell_content_item` with matching `row_target` | For each domain: expand `cell_content_item_refs` array; JOIN against `cell_content_item`; assert `zachman_cell.row_target == domain.row_target` for all |
| **VER-3c-05** | Every eligible CCI ci_id appears in at least one Domain's `cell_content_item_refs` | Collect union of all arrays across active domains for this row; assert `eligible_ci_ids ⊆ covered_ci_ids` |
| **VER-3c-06** | DomainRegister `member_ids` contains exactly the active domain_ids for this project | Query active Domains across all rows (`retired_at IS NULL`, no `row_target` filter); assert set equality with register `member_ids`. **Test care:** single-row fixtures pass this trivially; integration tests exercising Row 2 then Row 3 in the same project must assert register contains Domains from both rows. |
| **VER-3c-07** | AnalysisPass with `mechanism="DomainDerivation"` and `row_ref=current_row` exists | Presence query |
| **VER-3c-08** | `AnalysisPass.outputs.mechanism_data` present; all required fields non-null | Schema validation against expected field list |
| **VER-3c-09** | Domain entity has exactly the six canonical attributes (domain_id, name, description, classification_type, row_target, cell_content_item_refs) — no domain_qualifier or upstream_domain_ref columns in DB row | Assert `domain_qualifier` and `upstream_domain_ref` columns absent from `domain` table schema |
| **VER-3c-10** | On IdempotentRerun: domain_ids and `cell_content_item_refs` arrays unchanged; `mechanism_data.idempotent == true` | Snapshot before/after run; assert equality; assert idempotent flag |
| **VER-3c-11** | On FullRerun: `domain_count_retired` equals pre-run active Domain count for this row | Query active count before run; assert equals `mechanism_data["domain_count_retired"]` |
| **VER-3c-12** | `domain_count_produced ≥ 1` when `cci_count_input > 0` | Conditional assertion |
| **VER-3c-13** | No active Domain has `jsonb_array_length(cell_content_item_refs) == 1`, unless `cci_count_input == 1` (degenerate sparse row — e.g. Row 4 PMT with a single CCI). If CHK-3c-07 absorption succeeded, no single-CCI domains should remain. If `chk3c07_repair_failed` is in `execution_warnings`, assert that each residual single-CCI domain is documented in `execution_warnings[chk3c07_repair_failed].isolated_ci_ids`. | Conditional assertion |
| **VER-3c-14** | No active Domain has `jsonb_array_length(cell_content_item_refs) > floor(cci_count_input / 2)`, unless: `cci_count_input <= 4` (sparse row exception); OR all domains exceed the threshold (circular split condition); OR `chk3c08_repair_failed` is in `execution_warnings` (in which case the concentrated domain must be documented there). If CHK-3c-08 split succeeded, no over-concentrated domains should remain. | Conditional assertion |

### 8.2 Plausibility checklist for Practitioner review

1. **PLB-3c-01 — Domain names:** No name should be generic ("Miscellaneous", "Other", "General"). Each should reflect a recognisable concern at the row's abstraction level (see §5.4 `ROW_GUIDANCE`). For Row 1 specifically: if the domain name describes a system function, a process step, or requires knowledge of how the system works, it is at the wrong abstraction level — consider a FullRerun with the Row 1 guidance reviewed.

2. **PLB-3c-02 — Column span:** For each Domain, expand `cell_content_item_refs` and group by `cell_content_item.zachman_cell.column`. A Domain containing CCIs from only one column is flagged for review. Exception: a Why-only Domain (pure constraint domain) may be valid — verify intentionality. At Row 1, single-column domains are a strong signal of insufficient abstraction — the Row 1 guidance block explicitly instructs cross-column integration.

3. **PLB-3c-03 — Residual over-concentrated domain (post CHK-3c-08):** Any Domain containing more CCIs than `floor(cci_count_input / 2)` that survived CHK-3c-08 is flagged for mandatory Practitioner review. Normal paths to this state: (a) `cci_count_input <= 4` — sparse row exception; (b) `chk3c08_repair_failed` in `execution_warnings` — the split repair prompt failed; (c) all domains exceeded the threshold (circular split). In case (b), the Practitioner should manually review whether the domain should be split or whether the high CCI count reflects a genuine single business responsibility. High CCI count combined with 'and' / '&' in the domain name is a strong signal for splitting.

4. **PLB-3c-04 — Cross-cutting CCIs:** Review `mechanism_data.cross_cutting_advisories`. Is each flagged CCI genuinely cross-cutting? A What-column Entity CCI appearing in every Domain suggests Domain boundaries are too coarse — consider a FullRerun.

5. **PLB-3c-05 — Row-appropriate vocabulary:** For Row 1 Domains: enterprise-concern vocabulary (accountability, governance, participation, oversight, entitlement, obligation). Presence of function verbs (calculate, track, display, manage) in Row 1 domain names is a PLB failure. For Row 3 Domains: logical-design vocabulary (logical structure, logical behaviour, state management). For Row 2 Domains: business vocabulary (process, entity, rule, role). Absence of implementation vocabulary ("database table", "API endpoint") at Row 3 is a positive signal.

6. **PLB-3c-06 — Residual single-artefact domain (post CHK-3c-07):** Any Domain containing exactly one CCI that survived CHK-3c-07 is flagged for mandatory Practitioner review. Normal paths to this state: (a) `cci_count_input == 1` — degenerate sparse row, single-CCI Domain is the correct outcome; (b) `chk3c07_repair_failed` in `execution_warnings` — the absorption repair prompt failed. In case (b), the Practitioner should manually decide whether to accept the single-CCI Domain or trigger a FullRerun. In case (a), no action is needed. Sourced from POC §1.1.5: "Domains SHALL NOT be single-artefact containers" — CHK-3c-07 is the automated enforcement; PLB-3c-06 is the residual Practitioner check for cases where automation could not resolve it.

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
- VER-3c-10: domain_ids and `cell_content_item_refs` arrays identical to post-Fixture-1 state; `mechanism_data.idempotent == true`
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
- D001's `cell_content_item_refs` now includes `CCI-ROW2-C-When-001`
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
**Setup:** PMT Row 2 FirstRun. Primary AI stub omits `CCI-ROW2-C-Why-001`. Repair AI stub returns an empty action list `[]` — parses successfully as a valid `List[DomainRepairAction]` but produces no CCI coverage, so the orphaned CCIs persist after the merge step.

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
| **Single CCI for the row** | Stage 2 receives a one-CCI list. AI returns one Domain containing the single CCI. VER-3c-03 passes. CHK-3c-07 skipped (`cci_count_input <= 1` exception). ADVC-3c-01 inverted-range guard fires (`lower_bound = 2 > upper_bound = 0`) — **no advisory written**. execution_status = Completed. PLB-3c-02 advisory flagged (single-column, single-CCI Domain) for Practitioner awareness only. |
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
| **Phase 2 — Mechanism Activation** | `project_profile` row — provides three domain-specific parameters (§13.9 of Row 4 Understanding v0.24). | Soft prerequisite — ProjectProfile must exist. If any parameter is NULL, default value is substituted. |

### 11.2 Downstream

| Mechanism | What this mechanism produces for it | Dependency type |
|---|---|---|
| **Pass 3d — Requirement Derivation** | `domain` rows (including `cell_content_item_refs`) — Pass 3d reads Domains and assigns `Requirement.domain_refs`. | Hard dependency — orchestrator checks for Pass 3c `execution_status ∈ {Completed, CompletedWithWarnings}` before Pass 3d may begin. IdempotentRerun produces `execution_status = Completed` with `mechanism_data.idempotent = true`; this satisfies the gate. |
| **Phase 6 / Phase 8 — Domain Coverage Analysis** | `domain` rows (including `cell_content_item_refs` arrays) — Phase 6 Pass 1 / Phase 8 Pass 1 enumerate Domains and their CCI membership as the analysis inventory. Coverage analysis is read-only with respect to Domains. | Analytical dependency — Domains must be committed before Phase 6/8 runs. |

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
| **OQ-3c-01** | Domain count soft bounds advisory implemented in Stage 3 ADVC-3c-01: `lower_bound = 1 + ceil(cci_count / 15)`, `upper_bound = floor(cci_count / 2)`. Inverted-range guard: if `upper_bound < lower_bound` (occurs when `cci_count <= 3`), advisory is skipped entirely — the formula is incoherent for sparse rows and a single Domain from a sparse CCI set is the correct outcome. If range is valid and domain_count is outside it, advisory logged in `execution_warnings` with type `domain_count_advisory`. |
| **OQ-3c-02** | ~~`domain_upstream_match_threshold` implemented as ProjectProfile parameter~~ — **withdrawn**. OQ-3c-02 resolves as: upstream_domain_ref is not produced by this mechanism; the ProjectProfile parameter is not needed. |
| **OQ-3c-03** | FullRerun retirement uses soft-delete (`retired_at` column). `query_max_domain_id` includes retired Domains. Active Domain query filters `retired_at IS NULL`. |

### 12.3 Replit Agent task structure

**Primary input documents:**
- This spec (Row 4 Mechanism Spec — Domain Derivation v0.24) — implementation authority (all detail including DDL in §5.1)
- Row 3 Mechanism Spec v0.1 — architectural authority (note: domain_qualifier and upstream_domain_ref mentioned there are withdrawn)
- Row 4 Understanding v0.24 §13 — framework (module structure, prose descriptions, ProjectProfile parameters, VER criteria mapping, fixture table)

**Reference documents:**
- Row 4 Applied v0.2 — common architectural commitments
- Row 4 Understanding v0.5 §12 — reference implementation patterns from Pass 3b
- Canonical Ledger v2.12 — Domain and DomainRegister schemas (six Domain attributes only)

**Build sequence for the Agent:**
1. Write Alembic migration: `add_domain_tables` — use the DDL from **this spec §5.1**. Note: the `domain` table has NO `domain_qualifier` or `upstream_domain_ref` columns — simpler than previous spec versions.
2. Write `schemas/domain_grouping_response_schema.py`, `schemas/domain_incremental_response_schema.py`, `schemas/domain_repair_response_schema.py` (§5.2)
3. `ROW_GUIDANCE` is defined inline in the prompt template files (§5.4). Row 1 uses a structured multi-paragraph guidance block; Rows 2–5 use short phrases. The prompt template handles both forms. No separate vocabulary module needed.
4. Write `prompts/domain_grouping_prompt.py`, `prompts/domain_incremental_prompt.py`, `prompts/domain_repair_prompt.py`
5. Write `stage1_preflight.py` through `stage4_entity_production.py` and `__init__.py` orchestrator
6. Write `tests/test_domain_derivation.py` with Fixtures 1–7 (§9); AI stubs via monkeypatch
7. Run migration; run pytest; verify VER-3c-01 through VER-3c-12 all pass on Fixtures 1, 3, 4, 7
8. Verify Fixture 5 (repair recovery) and Fixture 6 (persistent orphan) match their specific assertions

**Deviations from Pass 3b pattern to watch for:**
- No Step 2 (ZachmanCell upsert) — Pass 3c does not produce ZachmanCells
- No batching loop in Stage 2 — single AI call, no `for batch in batches`
- No `domain_cci_membership` table — `cell_content_item_refs` is stored as a JSONB array directly on the `domain` row (canonical schema match)
- Soft-delete column `retired_at` on Domain table — not present on any prior entity table
- IncrementalRerun path in Stage 2 uses a different prompt template and response schema than FirstRun/FullRerun
- Repair prompt is a second AI call inside Stage 3, not part of Stage 2

---

## Document End

End of SysEngage Row 4 Mechanism: Domain Derivation v0.24.

Changes from v0.23 (nuanced "and"/"&" test + repair prompt naming enforcement):
- **§5.4 ROW_GUIDANCE["1"] (new):** "and" test block added to prohibition rules. Row 1 previously had no "and" guidance. Evidence: PMT R11 D003 "Earnings Transparency and Stewardship"; NQPS R4 D005 "Regulatory and Social Responsibility" (correct grouping, imprecise name).
- **§5.4 ROW_GUIDANCE["1"]–["5"]:** Blunt prohibition ("if you need 'and', create two domains") replaced with two-step test: (1) is there a single concept that covers both sub-themes without 'and'? Use it. (2) If no single concept exists, split. This distinguishes naming precision failures from grouping failures. Example: "Regulatory and Social Responsibility" → "Corporate Responsibility Governance" (naming fix, not a split).
- **§5.4 ROW_GUIDANCE["2"] vocabulary:** "retain" and "retention" added to avoid list — these are technical storage vocabulary; Row 2 business level should use "stewardship", "record", or "accountability". Evidence: PMT R11 D009 "Historical Record Retention".
- **§4.3 CHK-3c-07 repair prompt:** Explicit naming prohibition requirement added — the repair prompt template must state that new domain names must not use 'and'/'&' without first applying the "and" test.
- **§4.3 CHK-3c-08 split repair prompt:** Explicit naming prohibition requirement added — the split prompt must state that each split domain name must not be compound. Evidence: PMT R11 D011 "Earnings Derivation and Aggregation Logic" / D013 "Task Availability and Persistence Model" produced by CHK-3c-08 without the prohibition in the repair prompt.

Changes from v0.22: CHK-3c-08; ROW_GUIDANCE["2"] strengthened.
Changes from v0.21: ADVC-3c-01 inverted-range guard.

Companion artefacts:
- SysEngage_Row_3_Mechanism_Domain_Derivation_v0_1.md — architectural authority
- SysEngage_Row_4_Understanding_v0_24.md — structural framework (unchanged)
- SysEngage_Issues_Tracker_v0_50.md — finding disposition
