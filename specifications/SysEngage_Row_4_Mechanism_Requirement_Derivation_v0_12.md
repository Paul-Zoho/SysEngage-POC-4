# SysEngage Row 4 Mechanism: Requirement Derivation

**Implementation specification — physical / builder tier**

Filename: SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_5.md

Version: 0.12 (Supersedes v0.11 — concern-atomicity + non-redundancy authoring guidance. Realises Row 3 Requirement Derivation v0.9 §4.1.1. Adds a shared §5.4 cross-row block ("Concern-atomicity and non-redundancy") instructing the AI to (1) author one obligation per requirement at the CONCERN level — a requirement whose grouped CCIs span distinct concerns (different classification types across different Zachman columns) that it does not all voice must be split per obligation, so every concern is *voiced*, not merely referenced (the unvoiced-but-referenced concern is a silent Non-Loss failure and makes the requirement a downstream merge-magnet); and (2) not voice the same concern twice (no near-duplicate restatements, even from overlapping CCI sets — CHK-3d-07 collapses only exact duplicates). New soft diagnostic **ADVC-3d-03** records, decidably, requirements whose `cci_refs` span ≥2 classification types across ≥2 columns (`concern_atomicity_flags`) so over-bundling is measurable across runs. Motivated by PMT R2 Run11: a 4-concern requirement (R025: How/Process + How/Rule + What/Attribute + Why/Constraint) acted as a merge-magnet, and ~40% of a one-paragraph source's Row 2 requirements were near-duplicates — both upstream over-generation that inflate the downstream merge load. The complementary automatic Non-Loss guard on the merge itself is a Requirement Matching concern (deferred pending a re-run under this guidance). No hard reject added (concern-atomicity is an IM judgement, not decidable — guidance shapes generation, ADVC-3d-03 only instruments). CHK-3d-07/09, subject taxonomy, entity/state extraction, schema unchanged.)

Version: 0.11 (Supersedes v0.10 — entity-vs-state reduction. Realises Row 3 Requirement Derivation v0.8 §4.1.1(c). Confirmed against the PMT source, which uses one noun — "task" — in states ("available", "completed", "claimed"): §4.4.3a entity extraction now reduces a STATE/lifecycle-qualified phrase to the BARE entity + state as an attribute ("available tasks"/"completed tasks" → entity `task`, status available/completed), never a compound canonical; and §5.4 Row 1 entity-vocabulary gains the bare-noun clause (the entity is the bare source noun; states and roles are attributes, NOT separate entities — do not coin "task opportunity", "completed achievement", "economic activity", "household economy" for `task`). Fixes the Row 1 Run2 relapse where v0.10 stopped wholesale abstraction ("work unit") but the model coined state-qualified entities, fragmenting one `task` into separate canonicals and re-opening the cross-row resolution gap. Option A (entity flat; state is an attribute value, recorded via the existing DataDictionaryEntry.attributes) — no DD schema or matching change. Rows 2–6 §5.4 unchanged; §4.4.3a state-reduction applies to all rows.)

Version: 0.10 (Supersedes v0.9 — Row 1 domain-entity vocabulary preservation. Realises Row 3 Requirement Derivation v0.7 §4.1.1(c). Adds a source-entity-preservation rule to §5.4 REQUIREMENT_ROW_GUIDANCE["1"]: abstraction at Row 1 lives in the subject and verb, NOT in renaming the domain entities — keep the Source's domain nouns ("task", "reward", "earnings"); do NOT coin abstract paraphrases ("work unit", "value-generating activity", "strategic value exchange mechanism"). Fixes the observed Row 1 failure where entity-paraphrase produced statements with no extractable entity (entity_extraction_empty → terms_presented=0 → empty Row 1 DD → zero cross-row candidates → zero refine links). The existing "do not reproduce verbatim" rule is reframed so "derive" means re-cast to normative form, NOT relabel entities. Worded as domain-entity preservation, not literal echoing (genuine implementation/UI nouns still neutralise to their domain entity). No change to subject/verb/type guidance, atomicity, or schema. Rows 2–6 unchanged.)

Version: 0.9 (Supersedes v0.8 — Row 2 subject taxonomy / boundary test. Realises Row 3 Requirement Derivation v0.6 §4.1.1(a) / Row 2 Understanding §2.3.3 (R2-AMEND-9, OD-R2-30). The §5.4 REQUIREMENT_ROW_GUIDANCE["2"] subject block is rewritten from "THE BUSINESS (or a named business role) only" to a FOUR-class taxonomy chosen by the BOUNDARY TEST: actor/stakeholder (crosses the boundary inward), system (the boundary affordance — WHAT the system provides, never HOW), business (off-boundary responsibility), named business role (off-boundary accountability). Vocabulary block made subject-class-aware; the no-realisation-vocabulary rule is repositioned as the WHAT/HOW guard that keeps a system-subject statement at Row 2. Atomicity block gains the over-generation brake (author the column-aspects the source expresses; actor-action and its system-affordance are a complementary pair, not independent duplicates). CHK-3d-08 Row 2 subject taxonomy widened accordingly (system-subject at Row 2 no longer a mismatch). Fixes the observed false-merge cascade (R023/R034-class) at its root: the subject slot now carries discriminating actor/system/business information instead of a constant "the business". No change to Stage 2/4 mechanics, DD binding (§4.4.3a), atomicity hard-reject (CHK-3d-09), or schema. Row 1 / Rows 3–6 subject guidance unchanged.)

Version: 0.8 (Supersedes v0.7 — DD term extraction corrected to entity reduction. Realises Row 3 Requirement Derivation v0.5 §5.5 / Data Dictionary v0.2 §3.1. The §4.4.3a term-extraction step is rewritten from a DM slot-reuse ("present the Object slot") to an IM entity reduction: identify the domain entity/entities the Object denotes and present those entity-grade noun phrases to the DD, never the verbatim Object-slot clause. Fixes the observed defect where clausal Objects were stored as DD canonical names (e.g. "a mechanism enabling household members to select and claim available work opportunities."), making every entry a unique one-off and defeating resolution. Extraction is now model-assisted and fingerprinted. New VER-3d-19 (entity-grade term guard). No change to Stage 2 derivation, atomicity, typing, domain_refs, or refines_refs.)

Version: 0.7 (Supersedes v0.6 — DD Object-slot binding activated; realises Row 3 Requirement Derivation v0.4 §5.5 / F90. New Stage 4 sub-step §4.4.3a presents each Functional Object slot / Structural entity / asserted relationship / named value to the Data Dictionary service's resolve-and-record (Row 4 Data Dictionary Service v0.1), which returns the canonical DataDictionaryEntry and records provenance back to the Requirement — this is the DD's incremental population path. The binding is a DM/service step; the derivation AI does not propose DD bindings (§4.2 contract extended). Stage 4 mechanism_data gains a dd_binding block; new VER-3d-17 (every Object/entity presented and resolved-or-flagged) and VER-3d-18 (DD non-empty after a producing run — the regression guard against the empty-DD defect). No change to Stage 2 derivation, atomicity (CHK-3d-09), typing, domain_refs (MD-2), or refines_refs (Matching-populated). Object-slot binding was declared-only through v0.6; v0.7 makes it operative.)

Version: 0.6 (Supersedes v0.5. Interrogative-elaboration increment, realising Row 3 Requirement Derivation v0.3 / findings F87/F88. Changes: (1) §5.4 — shared interrogative-completeness guidance added across all five row blocks: the AI formulates statements by filling the type-required slots (Functional When/Who/Action/Object; Constraint Rule/Subject/Condition/Criteria; Structural composition via Object-recursion), interrogating source content per slot, making the row's set generatively complete and surfacing Structural requirements — staying within the row (no cross-row parent invention). (2) New ADVC-3d-02 — interrogative slot-completeness advisory (soft; logs `interrogative_completeness_advisory` for PLB-3d-07): flags thin type-required slots / un-interrogated Objects, distinct from the HARD CHK-3d-09 atomicity reject. Soft because completeness is generative guidance, and an over-eager hard gate would reject legitimately-terminal requirements. See §12.9 for the v0.5→v0.6 change detail. This completes the F87/F88 guidance that v0.5 explicitly deferred.)

Date: 03 June 2026

**Abstraction level:** Row 4 — Builder / Physical. This spec is the implementable realisation of the mechanism. Every design decision traces to the Row 3 (logical) Requirement Derivation spec; where this spec makes a physical choice the Row 3 spec deferred (an OQ), that resolution is recorded in §12.2.

**Purpose.** Implementation specification for the Requirement Derivation mechanism (Pass 3d). Derives Requirement entities from the CCIs grouped by Pass 3c Domains, with full CCI traceability and deterministic Domain attribution. Architectural pattern is the four-stage IM-primary / DM-envelope pattern shared with Domain Derivation; the logical authority is the Row 3 Requirement Derivation spec. This spec records the physical realisation: module structure, DDL, response schemas, literal prompt guidance, audit structure, fixtures, and VER→pytest mapping.

**Status:** Rows 1–2 validated (Row 1: PMT Run 5 / NQPS Run 2; Row 2: PMT Row 2 Run 1 / NQPS Row 2 Run 1). Rows 3–5 authored, pending test (candidate guidance). §5.4 REQUIREMENT_ROW_GUIDANCE["1"]–["5"] are fully authored; Row 6 is a short-phrase stub. Supersedes v0.3; see §12.7 for the change detail.

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
| **Canonical Ledger v2.13** | Requirement, RequirementRegister, AnalysisPass | Authoritative schemas. Requirement gains `refines_refs` (optional) and the collapsed three-value `requirement_type` (F82/F89). Normative rules transcribed in §5.1. |
| **Segmentation spec v9.2** | Statement formulation | Atomic, single-intent, normative, no inferred actors/behaviours. Realised in §5.4 guidance. |
| **sys_engage_specification_v2.md** | §Phase 3 Requirement Generation, §ADR | POC source for type-classification reasoning signals. Read as principle (D4), realised as §5.4 reasoning block — not a lookup table. |
| **Tracker v0.54** | F80, F81 | F80 (Open, derivation half closed): consume Domains by domain_id (§4.4.2). F81 (Open): Rows 1–2 validated; Rows 3–5 guidance authored here (§5.4), candidate/pending test; Row 6 stub. |

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

**CHK-3d-04 — fit_criteria integrity.** Present-but-empty → strip, log `fit_criteria_empty_stripped`. `verification_method=="Measurement"` and fit_criteria absent → log `measurement_missing_fit_criteria` (informational; PLB-3d-05).

**CHK-3d-05 — Non-Loss.** `orphaned = eligible_ci_ids - {ref for p in proposals for ref in p.cci_refs}`. If non-empty: invoke repair (IM sub-act). For each orphan resolve owning Domain(s) (non-empty by Pass 3c Non-Loss). Assemble `requirement_repair_prompt.py` with `orphaned_ccis=[{ci_id,column,classification_type,description,owning_domain_id,owning_domain_name}]` + REQUIREMENT_ROW_GUIDANCE. Parse against repair schema; one attempt (no retry). Tag repair proposals `source_domain_id=owning_domain_id`. Merge; recompute `orphaned`. Persistent orphan → record in `mechanism_data.orphaned_ccis`; `execution_status="CompletedWithWarnings"`; raise Concern (CN-NNN). `execution_warnings += chk3d05_repair_performed` / `chk3d05_repair_failed` as applicable.

**CHK-3d-06 — Failure path.** Proposal set empty after CHK-3d-01..03 **and** repair produced nothing → `execution_status="Failed"`, `failure_reason="No valid Requirement proposals survived validation"`.

**CHK-3d-07 — Exact-duplicate collapse.** Two proposals with identical `statement` (case-insensitive) **and** identical `cci_refs` set → collapse to first; log `duplicate_requirement_collapsed`. (No name-uniqueness analogue — Requirements have no unique name. Near-duplicates → PLB-3d-01.)

**CHK-3d-08 — Row-appropriate statement subject (decidable; realises Row 3 §4 Stage 3 / closes F81 detection).** For each surviving Requirement, test the statement's grammatical subject against the row's permitted subject set (§5.4(a)). At Row 1 the subject must be the enterprise; a statement opening "The system shall…" (or otherwise system/component-subjected) at Row 1 is a mismatch. **At Row 2 the permitted set is {the business, a named business role, an actor/stakeholder, the system} (the four-class taxonomy, R2-AMEND-9 / OD-R2-30): an actor-subject ("a child can claim…") and a system-subject ("the system shall make … claimable") are NOT mismatches at Row 2; only an out-of-set subject (e.g. "the enterprise shall…" at Row 2) is.** The WHAT-vs-HOW discrimination for a system-subject statement (does it name realisation — Row 3 — rather than the provided capability?) is a *vocabulary* concern enforced by §5.4's no-realisation-vocabulary guidance, NOT by this subject check; CHK-3d-08 tests the subject only. **Severity (resolves Row 3 OQ-3d-03): soft** — a mismatch logs `subject_vocabulary_mismatch` in `mechanism_data.subject_vocabulary_flags` (`[{requirement_id_placeholder, row, detected_subject}]`) and surfaces via PLB-3d-02; it does NOT reject the Requirement or block production. Rationale: validated across Rows 1–3, 5 production runs (Tracker F81) — the §5.4 guidance held subject discipline at 100%, so the check has been a clean backstop rather than a frequent rejecter; soft severity is retained. The check is a decidable detector (subject extraction is a closed test), consistent with classifying it CHK not PLB.

**CHK-3d-09 — Typed-slot atomicity (decidable, HARD; realises Row 3 §4.1.1(b) / F88).** For each surviving Requirement, validate the statement against the slot pattern its `requirement_type` selects (F88):
- *Functional* → `[Condition,] Subject shall Action Object`. Required slots present: Subject, Action, Object.
- *Constraint* → `Subject shall comply-with Constraint-Rule [under Condition] [to Criteria]`. Required: Subject, Constraint Rule.
- *Structural* → `Entity comprises/has/relates-to Structural-element`. Required: Entity, structural assertion.

Reject (log `atomicity_violation {requirement_id_placeholder, violation}` in `validation_failures`) when any of: **compound condition** (two+ conditions joined by and/or); **compound object** (two+ independent objects joined by conjunction, unless an inseparable single concept — the conjunction is flagged decidably, and inseparable-concept is a Practitioner-reviewable exception, PLB-3d-01); **multiple constraint rules / criteria** in one statement; **missing required slot** for the type.

**Severity: HARD (rejects).** Unlike CHK-3d-08 (soft, surface-form subject), a compound or slotless statement is a structural defect — it explodes the verification test space and cannot be elaborated downward (the recursive object-interrogation needs a single object). A rejected proposal's CCIs return to the orphan pool and are re-covered via CHK-3d-05 repair (the repair prompt instructs atomic single-obligation statements). The decidable detector is conjunction/slot-presence analysis; the inseparable-single-concept judgement is the one soft edge (logged, not auto-rejected). This is the physical realisation of the F88 hard-atomicity constraint (v0.4 carried only the soft "and"-test in guidance).

**ADVC-3d-01 — Requirement-per-Domain soft bounds.** Per source Domain, count surviving Requirements; `m = len(domain.cell_content_item_refs)`. Zero Requirements → manifests as orphans (CHK-3d-05). `> m` Requirements → log `requirement_count_advisory {domain_id, requirement_count, cci_count}` (PLB-3d-06). Informational; production proceeds.

**ADVC-3d-03 — Concern-atomicity advisory (soft diagnostic; realises Row 3 §4.1.1 concern-atomicity).** For each surviving Requirement, compute the spread of its `cci_refs` over CCI classification types and Zachman columns. A Requirement whose `cci_refs` span **≥2 distinct classification types across ≥2 distinct columns** is flagged `concern_atomicity_advisory {requirement_id_placeholder, cci_refs, classification_types, columns}` in `mechanism_data.concern_atomicity_flags`. This is a **decidable diagnostic** (classification_type and column are CCI fields), not an IM act. **Severity: soft** — informational; production proceeds; it does NOT reject or auto-split. Rationale for soft (not hard): a multi-column / multi-type CCI span is a reliable *signal* of possible concern over-bundling (the R025 case — How/Process + How/Rule + What/Attribute + Why/Constraint in one statement) but not proof, since a legitimately-single obligation can draw on facets from two columns; whether to split is the IM judgement made at authoring under the §5.4 concern-atomicity guidance. The flag instruments the requirement set so over-bundling is measurable across runs — the data source for judging whether the §5.4 guidance is holding — exactly as `subject_vocabulary_flags` (CHK-3d-08) instruments subject discipline. A persistently high `concern_atomicity_flags` count after the guidance lands is the evidence that would justify promoting concern-atomicity from guidance to a harder mechanism.

**ADVC-3d-02 — Interrogative slot completeness (advisory; realises Row 3 §4.1.1(f) / F87/F88).** For each surviving Requirement, check whether the slots its `requirement_type` requires are *filled* (Functional: Subject/Action/Object present, Condition where the source implies a trigger; Constraint: Subject/Constraint-Rule, Criteria where Measurement-verified; Structural: entity + composition/attribute/relationship assertion). This is distinct from CHK-3d-09 (which HARD-rejects compound/missing-required-slot *atomicity* violations): ADVC-3d-02 is a **soft generative-completeness advisory** — it flags a requirement whose type-required slots are thin or whose Object was not interrogated to structure where the source implied it, logging `interrogative_completeness_advisory {requirement_id_placeholder, type, thin_slots}` for Practitioner review (PLB-3d-07). Rationale for soft (not hard): interrogative completeness is a *generative guidance* property (it makes the AI surface more, validated in the F87 sandbox) — its absence is an under-elaboration to review, not a structural defect to reject. A missing *required* slot is already hard-caught by CHK-3d-09; ADVC-3d-02 catches the softer "could have been interrogated further" case. Informational; production proceeds. (Why advisory and not hard: an over-eager hard completeness gate would reject legitimately-terminal requirements — a Row 1 enterprise constraint need not decompose to an Object the way a Functional behaviour does. The row-and-type-awareness is in the guidance, §5.4; the check only flags thinness for review.)

### 4.4 Stage 4 — Entity Production and Ledger Commit (DM)

Realises Row 3 §4 Stage 4.

**4.4.1 requirement_id allocation.** `query_max_requirement_id(project_id)` including retired rows. Allocate forward from next `R###`. §5.3.

**4.4.2 domain_refs DM-derivation (MD-2).** Per surviving proposal: `domain_refs = sorted({d.domain_id for d in active_domains if set(proposal.cci_refs) & set(d.cell_content_item_refs)})`. Assert `len(domain_refs) >= 1` (guaranteed under MD-1 post-CHK-3d-03) and every referenced Domain `row_target == str(current_row)`. Empty result → fail closed: reject proposal, log `{check_id:"MD-2", detail:"domain_refs derivation empty"}` in `validation_failures`; re-run CHK-3d-05 on the reduced set.

**4.4.3 Requirement construction.** Build each Requirement: allocated `requirement_id`; `statement`; `requirement_type`; `row_target=str(current_row)`; `confidence`; `cci_refs`; derived `domain_refs`; `refines_refs=[]` (F82 — populated later by the Requirement Matching service, NOT by Pass 3d; §5.5 / F93); optional `rationale`/`fit_criteria`/`verification_method`/`priority` where present; `answer_refs=[]`. The Requirement's controlled-vocabulary terms are then bound to the Data Dictionary in §4.4.3a (the binding is recorded in the DD, not as a field on the Requirement — the canonical Requirement payload is unchanged, ledger v2.14).

**4.4.3a Object-slot DD binding (activates Row 3 v0.4 §5.5; F90).** For each surviving Requirement, extract its controlled-vocabulary terms and present them to the Data Dictionary service (Row 4 Data Dictionary Service v0.1):

1. **Entity extraction from the Object (IM).** Identify the **domain entity/entities the Object denotes** — the controlled-vocabulary noun(s) the obligation concerns — and present *those*, not the verbatim Object slot. At lower rows the Object is often already entity-grade ("task", "child earnings") and reduction is near-identity; at Row 1 the Object is typically clausal ("a mechanism enabling household members to select and claim available work opportunities") and MUST be reduced to its entity head(s) (here: `work opportunity`, `household member`). A statement may yield zero, one, or several entity terms. This is an **interpretive act** (which noun is the domain entity vs an incidental modifier / verb nominalisation like "a mechanism enabling…"), so it is **model-assisted, not a verbatim slot copy**: the CHK-3d-09 slot parse bounds *where* to look (the Object slot), but reducing that slot to its entity head(s) is IM. The presented term MUST be an entity-grade noun phrase; presenting the Object clause or the full statement is prohibited (it defeats the DD — each clause is unique, resolves to nothing shared, and yields one canonical entry per statement). Structural → the **entity** asserted, plus any **relationship** `(entity_a, relation, entity_b)` the statement asserts; any **value referenced by name** in any type (e.g. `Task.status.available`) → the attribute value.

   **Reduce STATE / lifecycle qualifiers to the bare entity (do NOT coin a qualified entity).** A phrase naming the entity *in a state* — "available tasks", "completed tasks", "claimed task" — reduces to the **bare entity** (`task`) with the state carried as an **attribute** (status = available / completed / claimed), recorded on the entry's `attributes` (DD §4.4 value-record), NOT minted as a separate canonical ("task opportunity", "completed achievement"). Likewise do not substitute a near-synonym or role/abstraction-qualified coinage for a source entity ("economic activity", "work unit", "household economy" for `task`/`child`). The rule: the presented term is the **bare source noun**; lifecycle states and role qualifiers are attributes *of* that entity, never new entities. This is what makes the available / completed / claimed states of one entity resolve to ONE canonical rather than three — and what keeps Row 1 and Row 2 sharing the same `task` canonical for cross-row matching.
2. **Resolve-and-record (service call).** For each extracted term call the DD service `resolve_and_record(term, context=statement, provenance_ref=requirement_id)` (DD spec §4.1–§4.4). The service performs its own three-way judgement (canonical-match → synonym; no-match → new canonical entry; ambiguous → flagged) and returns the canonical `DataDictionaryEntry`. Relationships call the relationship-record operation (DD §4.3) after both endpoints resolve; named values call the value-record operation (DD §4.4). **These calls are what populate the DD** — Pass 3d is the DD's primary caller and the DD accretes incrementally across the run and across rows.
3. **Bind / flag.** Resolved → the Requirement's Object/entity is bound (the binding lives in the DD via the entry's `provenance_ref` and synonym register; nothing is written onto the Requirement element). **Unresolved / flagged** → record `dd_unresolved {requirement_id, term, reason}` in `mechanism_data.dd_binding` (§4.4.3b). The Requirement is still produced (Non-Loss); the unresolved term is the signal that the Matching service must treat this Requirement as not-yet-matchable (Matching §4.1 / VER-rm-07).
4. **Idempotency.** Re-presenting the same term resolves against existing entries and does not duplicate them (DD §6). On IdempotentRerun of Pass 3d, no DD calls are made (no new requirements).

**Mode.** The entity extraction (step 1) is an **IM act** — a model-assisted reduction of the Object to its domain entity/entities — and its fingerprint IS recorded in the Pass 3d AnalysisPass `ai_model_fingerprints` (stage label `stage4_dd_entity_extraction`), alongside the Stage 2 derivation fingerprints. The DD service's own resolution judgement (same/new/ambiguous) is a separate IM act, fingerprinted within the DD service, not here. The derivation AI does not author DD entries — it presents candidate entity terms; the DD service decides resolution. (This corrects the v0.7 framing of extraction as a cheap DM slot-reuse, which produced verbatim clausal terms.)

**Ordering.** §4.4.3a runs inside Stage 4, after §4.4.3 construction and before the §4.4.6 transaction commit, so the DD is populated within Pass 3d. The Requirement Matching service (Phase 3e) subsequently reads the populated DD. Runner-level: Matching MUST NOT run for a row before that row's Pass 3d (with §4.4.3a) has committed; a Matching invocation finding an empty DD is a precondition failure (defer/halt), not a free-text fallback.

**4.4.3b dd_binding audit.** Stage 4 records a `dd_binding` block in `mechanism_data` (sibling to `subject_vocabulary_flags`, `validation_failures`):

```jsonc
"dd_binding": {
  "terms_presented": 18, "resolved": 16, "new_canonical": 7,
  "synonyms_recorded": 9, "relationships_recorded": 2, "values_recorded": 1,
  "dd_unresolved": [ { "requirement_id": "R019", "term": "pocket money allocation", "reason": "flagged_ambiguous" } ]
}
```

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
| `requirement_type` | VARCHAR(16) | NOT NULL; CHECK IN ('Functional','Constraint','Structural') |
| `row_target` | VARCHAR(1) | NOT NULL; CHECK IN ('1','2','3','4','5','6') |
| `rationale` | TEXT | NULL |
| `cci_refs` | JSONB | NOT NULL; CHECK jsonb_array_length >= 1 |
| `domain_refs` | JSONB | NOT NULL; CHECK jsonb_array_length >= 1 |
| `refines_refs` | JSONB | NOT NULL DEFAULT '[]'; «refine» links to row n-1 Requirements (F82); MAY be empty at any row; populated by the Matching service, NOT by Pass 3d |
| `fit_criteria` | TEXT | NULL; CHECK (fit_criteria IS NULL OR length(fit_criteria) > 0) |
| `verification_method` | VARCHAR(16) | NULL; CHECK IN ('Test','Analysis','Inspection','Demonstration','Measurement') |
| `priority` | VARCHAR(8) | NULL; CHECK IN ('High','Medium','Low') |
| `answer_refs` | JSONB | NOT NULL DEFAULT '[]' |
| `confidence` | DOUBLE PRECISION | NOT NULL; CHECK 0.0 <= confidence <= 1.0 |
| `retired_at` | TIMESTAMPTZ | NULL (soft-delete for FullRerun) |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() |

`cci_refs`/`domain_refs`/`answer_refs` are JSONB arrays on the row (same JSONB-array-on-row convention as the sibling `cell_content_item_refs`; no join table). `retired_at` mirrors the `domain` table.

**`requirement_register`:** one seeded row per project (migration seeds it): `register_id` PK, `project_id`, `register_type='Requirement'`, `member_ids` JSONB, `completeness_rule` TEXT, `confidence` DOUBLE PRECISION.

**Ledger normative rules (transcribed v2.13, all enforced):** `requirement_id` unique and `^R\d{3}$`; `statement` non-empty; `cci_refs` non-empty; `domain_refs` ≥1 referencing existing Domain; if `fit_criteria` present, non-empty; if `refines_refs` present, each entry references an existing Requirement at row_target−1 (MAY be empty at any row, F82/F86); `requirement_type` in {Functional, Constraint, Structural}; a Measurement-verified Constraint SHOULD carry `fit_criteria`; `row_target` in "1".."6"; `row_target` equals row of every referenced CCI and Domain; `confidence` 0.0..1.0. Exactly one RequirementRegister; `member_ids` contains all `requirement_id`.

### 5.2 AI response schemas (Pydantic)

**`requirement_derivation_response_schema.py` — primary (FirstRun / FullRerun):**

```
Response root: List[RequirementProposal]
RequirementProposal:
  statement:            str                 (minLength=1)
  requirement_type:     Literal["Functional","Constraint","Structural"]
  cci_refs:             List[str]           (minItems=1)
  rationale:            Optional[str]
  fit_criteria:         Optional[str]
  verification_method:  Optional[Literal["Test","Analysis","Inspection","Demonstration","Measurement"]]
  priority:             Optional[Literal["High","Medium","Low"]]
  confidence:           float               (0.0..1.0)
```
The AI does NOT return `requirement_id`, `row_target`, `domain_refs`, `refines_refs`, or `answer_refs` (Stage 4 / deferred / service-populated). `refines_refs` in particular is established by the separate Requirement Matching service (F85/F93), never proposed by the derivation AI. The AI likewise does **not** propose Data Dictionary bindings: Object-slot/entity/value resolution is the §4.4.3a service call, not an AI output (the AI formulates the statement; the DD service resolves its terms). Enum enforced at parse (MD-5).

**`requirement_incremental_response_schema.py` — IncrementalRerun:** **IMPORTANT — DISTINCT CLASS** `IncrementalRequirementProposal`. Same field shape; do NOT alias the primary class. Covers only `new_domain_ccis`; refs outside the new-CCI set logged `incremental_ref_outside_new_set`.

**`requirement_repair_response_schema.py` — repair:** **IMPORTANT — DISTINCT CLASS** `RepairRequirementProposal`. Same field shape; every proposal covers ≥1 orphaned ci_id, scoped to one owning Domain. The three classes handle different operations and MUST be separate (same discipline as the sibling §5.2 distinct-schema warning).

### 5.3 Identifier conventions

- Requirement `R###` — global per-project sequence, zero-padded 3 digits, allocated Stage 4.4.1, never reused (includes retired). **Scale ceiling (resolves Row 3 OQ-3d-05):** 999 ids per project including retired. If a project exceeds 800 allocated ids, raise a tracker finding for a 4-digit format (R####). Same caveat as `domain_id`.
- RequirementRegister: one per project; `register_id` seeded by migration.
- AnalysisPass: `P###` via the common writer utility.

### 5.4 REQUIREMENT_ROW_GUIDANCE — prompt constants

Realises Row 3 §4.1.1. **DISTINCT from the domain ROW_GUIDANCE** (decision B): that governs domain naming/grouping; this governs requirement-statement formulation. Held in `prompts/requirement_row_guidance.py`, injected by `REQUIREMENT_ROW_GUIDANCE[str(row_ref)]` into the derivation, incremental, and repair prompts. Principle-based, not pattern-based.

**Rows 1–5 are fully authored. Rows 1 and 2 are validated (Row 1: PMT/NQPS Run; Row 2: PMT/NQPS Row 2 Run 1). Rows 3–5 are CANDIDATE guidance, authored ahead of test (NOT yet validated) — they must be confirmed by run evidence before being treated as closed. Row 6 is a short-phrase stub.** Rows 1–2 followed the validate-then-author cadence (the same staged approach as the domain ROW_GUIDANCE); Rows 3–5 were authored together to accelerate the remaining rows on the proven pattern.

**Interrogative completeness — shared across all rows (§4.1.1(f), F87/F88).** Every per-row block instructs the AI to formulate statements by **filling the slots the requirement's type requires**, interrogating the source content for each — not by paraphrasing CCIs. The slot questions, per type (the row block supplies the row-appropriate vocabulary for each):
- **Functional** — *When?* (Condition, if the source implies a trigger) · *Who/what acts?* (Subject, row-appropriate) · *Does what?* (Action) · *To what?* (Object).
- **Constraint** — *What bound?* (Constraint Rule) · *On whom/what?* (Subject) · *When applies?* (Condition?) · *Measured how?* (Criteria — required if Measurement-verified).
- **Structural** — *What is the entity made of?* (composition / attributes / relationships). Reached by interrogating a behavioural Object until the answer is structure rather than further behaviour (the Object-recursion), which surfaces Structural requirements the source only implied.
The interrogation makes the row's requirement set generatively complete against its CCIs and the structure they imply (validated, F87 sandbox). It stays **within the row** — it does not invent cross-row parents (that is the Matching service surfacing gaps and GQA closing them, F84/F85). A statement whose type-required slots are thin is flagged by ADVC-3d-02 (advisory) for review; a *missing required* slot is hard-caught by CHK-3d-09.

**Concern-atomicity and non-redundancy — shared across all rows (Non-Loss; over-merge prevention).** Two authoring failure modes inflate the requirement set and corrupt downstream matching; both are prevented at generation, not patched later:

1. **Concern-atomicity — one obligation per requirement at the CONCERN level, not only the sentence level.** CHK-3d-09 enforces *sentence*-level atomicity (no compound condition/object). This is the deeper rule. The CCIs you group into a single Requirement should correspond to **one obligation**. When the CCIs you would group span **distinct concerns** — different classification types (Process / Rule / Attribute / Constraint / Relationship / Event / Cycle / …) across different Zachman columns (How / What / Why / When / …) — ask whether they are genuinely one obligation. Usually they are not: a *retention rule* (How/Rule), an *accessibility constraint* (Why/Constraint), and a *status attribute* (What/Attribute) are three obligations even though all concern "task-completion records". **Split per distinct obligation, so every concern is VOICED by a requirement — not merely referenced by one.** A Requirement that lists a CCI in its `cci_refs` but does not *state* that CCI's concern leaves the concern silently uncovered (a Non-Loss failure: coverage on paper, no obligation in fact) and makes the Requirement a merge-magnet downstream (narrower, correctly-atomic siblings get judged duplicates of it and retired, dropping their concerns). This is a judgement, NOT "one Requirement per CCI": a legitimately-single obligation may draw on several CCIs (e.g. one relationship asserted by two signals) — the test is *one obligation, all of whose CCIs are facets the single statement actually expresses*.

2. **Non-redundancy — do not voice the same concern twice.** Within the Requirements you produce for a Domain, do not emit two statements asserting the same obligation, even reworded ("scope task visibility to the current week" / "limit task visibility to the current week scope") and even from overlapping CCI sets. Each concern is stated once; if two candidate statements would voice the same CCI's content, produce the single best statement. CHK-3d-07 collapses only *exact* statement+ref duplicates — near-duplicates are yours to not generate, and they are the principal driver of spurious downstream duplicate-merges (each near-duplicate pair becomes a merge the Matching service must resolve, risking retirement of a distinct obligation).

Both rules serve Non-Loss and matching quality directly: a concern-atomic, non-redundant set gives the Matching service almost nothing to merge, so the merge step cannot accidentally retire a distinct obligation. (Instrumentation: ADVC-3d-03 records, decidably, any Requirement whose `cci_refs` span ≥2 classification types across ≥2 columns — a soft over-bundling signal, not a reject.)

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

### Domain entity vocabulary (REQUIRED — preserve the source's nouns)
Abstraction at Row 1 lives in the SUBJECT and the VERB (the enterprise commits to / is
accountable for / establishes) — NOT in renaming the things the enterprise commits to.
KEEP the domain-entity nouns the source uses. If the source says "task", write "task" —
NOT "work unit", "value-generating activity", or "strategic instrument". If the source
says "reward" / "pocket money", write that — NOT "monetary reward as a strategic value
exchange mechanism". Do NOT coin abstract paraphrases (instrument, mechanism, metric,
exchange) for concrete source entities.
  Right:  "The enterprise shall enable children to claim and complete tasks."
  Wrong:  "The enterprise shall establish work units as strategic instruments for value
           creation."
This is a DOMAIN-ENTITY rule, not literal echoing: still neutralise genuinely system- or
UI-level source nouns to their domain entity (source "claim button" / "screen" → the
domain entity "claim" / "task", not "button"). Preserve the DOMAIN nouns (task, reward,
child, earnings); drop only implementation/UI nouns.

The entity is the BARE source noun — not a qualified, compounded, or abstracted form. The
source names ONE entity ("task") and describes it in STATES ("available", "completed",
"claimed"); the entity is `task` and the states are ATTRIBUTES, not separate entities. Do
NOT coin "task opportunity", "completed achievement", "economic activity", or "household
economy" — those are the bare entity (`task`, `child`) dressed in a state or an
abstraction. One entity, one bare name; states and roles are attributes of it.
  Right:  "...children to claim available tasks ... and view completed tasks."   (entity: task)
  Wrong:  "...identify available task opportunities ... view completed achievements." (two coined entities)
Why this matters: a single entity must carry ONE name from enterprise scope down to
realisation. That consistent thread is what the Data Dictionary resolves and what
cross-row refinement matches on; a Row-1-only synonym ("work unit" for "task") OR a
state-qualified coinage ("task opportunity"/"completed achievement" for "task") breaks the
thread (Non-Loss failure) and fragments one entity into several Data Dictionary canonicals.

### requirement_type reasoning (principle-based — choose, do not pattern-match)
Weigh the source CCIs' Zachman columns and content against the row's abstraction level:
- Why-column / motivation / rule / policy / commitment content → lean Constraint.
- How / What / When / capability / function content → lean Functional.
- Content expressing a measurable threshold, rate, latency, or capacity → Constraint,
  verified by Measurement (the statement SHOULD carry fit_criteria — the threshold).
- Content expressing a quality attribute (usability, maintainability, portability) →
  Constraint (a bound on a quality dimension), verified by Inspection or Measurement.
- Content asserting what an entity is — its composition, attributes, or relationships →
  Structural.
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
  statement from it. "Derive" means re-cast the sentence into normative enterprise-
  commitment form; it does NOT mean renaming the domain entities — keep the source's
  domain nouns (see Domain entity vocabulary).
- Do NOT produce one thin requirement per CCI mechanically; consolidate where CCIs
  express one obligation, split where one CCI carries two.
""",

    "2": """
## Row 2 — Owner / Business Level — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the business-owner level — the view of
someone who understands what the enterprise is responsible for delivering and how it
must behave, but who is NOT concerned with how that responsibility is technically
realised. Each requirement expresses a business capability, obligation, or rule the
business must satisfy — stated as a persistent business responsibility, not a workflow
step and not a system function.

### Statement subject (REQUIRED)
Row 2 has FOUR legitimate statement subjects. Choose by the BOUNDARY TEST — do NOT
default to the business. The boundary test: does the party or function this CCI
describes cross the system boundary?

(a) ACTOR / STAKEHOLDER subject — an external party interacting WITH the system
    (reaching in to do something). Subject = the actor; verb = their real action:
      "A child can claim a completed task."
      "A parent can view their child's earnings."
    These are Who-column, boundary-crossing statements. They NAME the system boundary
    and are first-class. Do NOT re-express them as "the business shall enable the child
    to ..." — that buries the actor in the object and loses the boundary. Required
    wherever a CCI describes an actor interacting with the system (the Who column must
    be occupied — Cell Occupancy).

(b) SYSTEM subject — the capability the system PROVIDES at the boundary (the affordance
    meeting the actor), stated as WHAT the system provides, NOT how:
      "The system shall make completed tasks claimable by entitled children."
      "The system shall make a child's earnings visible to the parent."
    Legitimate at Row 2 as a BLACK-BOX affordance. Name the provided capability and NO
    realisation (no API/schema/database/service/endpoint/algorithm/validation rule —
    that is Row 3 HOW). "The system enables claimable tasks" = Row 2 (names the
    mechanism the system provides); "the system exposes a claim operation validating
    entitlement against the ledger" = Row 3 (names the realisation).

(c) BUSINESS subject — what the business does BEHIND the boundary: a responsibility,
    rule, or artefact it maintains:
      "The business shall maintain a record of each task claim."
      "The business shall enforce the weekly reset cycle."

(d) NAMED BUSINESS ROLE — a WHO-column CCI naming an accountable internal role that
    does NOT act through the system (off-boundary accountability):
      "The account holder shall approve ..."

The boundary test, applied:
  - Party acts THROUGH the system (reaches in)        → ACTOR subject (a)
  - System OFFERS the capability to that actor         → SYSTEM subject (b)
  - Function happens BEHIND the boundary (responsibility/rule/record)
                                                        → BUSINESS subject (c)
  - Accountable internal party, off-system             → NAMED BUSINESS ROLE (d)

Subject by Zachman column (illustration — the boundary test decides; this orients):
  Who (external party interacting)     → ACTOR         "a child can claim a task"
  Who (internal accountable party)     → BUSINESS ROLE "the account holder approves"
  How (capability offered to an actor) → SYSTEM        "the system makes tasks claimable"
  How (internal business process)      → BUSINESS      "the business settles compensation"
  What (artefact the business keeps)   → BUSINESS      "maintain a record of each claim"
  When (cycle / trigger)               → BUSINESS (or Condition slot) "enforce weekly reset"
  Why (rule / goal / constraint)       → BUSINESS (Constraint) "enforce approval threshold"

Do NOT use "The enterprise shall ..." — that is Row 1 (Planner) scope vocabulary.
The distinction from Row 1: Row 1 says what the enterprise commits to at scope level
("The enterprise shall recognise child users as participants"); Row 2 says who does
what at the business boundary and what the business is responsible for behind it
("A child can claim a completed task"; "The system shall make tasks claimable"; "The
business shall maintain a record of each claim").

### Normative form and atomicity
- Use the normative "shall" (or "can"/"may" for an ACTOR capability — "a child can claim…"). One obligation per statement.
- Apply the two-step "and" test: (1) is there a single obligation that subsumes both clauses? Use it. (2) If not, split into two requirements.
- OVER-GENERATION BRAKE: a single source concept can span columns (an actor-action, the system-affordance that enables it, and a business record). Author ONLY the column-aspects the source actually expresses — do NOT mechanically manufacture an actor + system + business statement for every concept. Where both an actor-action and its system-affordance ARE expressed, author both but treat them as a COMPLEMENTARY PAIR (the affordance enables the action — related, not two independent obligations, and NOT duplicates of each other). Never state one obligation twice under two different subjects.
- Row 2 statements are STATELESS obligations — a capability/responsibility, NOT a step-by-step sequence ("first X, then Y"). A statement describing an ordered workflow has dropped to Row 3+ and must be re-stated.

### Statement vocabulary
Vocabulary depends on the SUBJECT CLASS:
  ACTOR subject — the actor's real action verb: claim, approve, view, define, submit,
    request. Do NOT wrap it as "be enabled to" / "be able to be given" — name the action.
  SYSTEM subject — the provided capability (WHAT, never HOW): make available, make
    visible, make claimable, present, provide, enable (a capability).
  BUSINESS subject / role — business-responsibility vocabulary: maintain, record,
    govern, settle, approve, authorise, account for, be responsible / accountable for,
    steward, enforce (a business rule), recognise (a business role).
  Avoid at Row 2 (ALL subjects): calculate, process, store, retrieve, aggregate,
    compute, manage, track, retain / retention, generate, display — system-function /
    technical-storage vocabulary belonging to Row 3+ ("retain"/"retention" → "maintain
    a record").
  Avoid (ALL subjects) — the WHAT/HOW guard: any word implying a technical REALISATION
    mechanism — API, schema, database, service, endpoint, algorithm, validation rule.
    This is what keeps a SYSTEM-subject statement a Row 2 black-box affordance (WHAT the
    system provides) rather than a Row 3 design (HOW it provides it).

### requirement_type reasoning (principle-based — choose, do not pattern-match)
Weigh the source CCIs' Zachman columns and content against the business-owner level:
- WHY-column business governance rules / motivation / constraints on business behaviour
  → lean Constraint ("The business shall enforce the approval threshold ...").
- HOW-column business capability declarations / WHAT-column business artefacts the
  business must maintain / WHEN-column business triggers → lean Functional ("The
  business shall maintain a record of ...").
- Content expressing a measurable business threshold, rate, or service level →
  Constraint, verified by Measurement (the statement SHOULD carry fit_criteria).
- Content expressing a business quality attribute → Constraint (quality bound).
- Content asserting what a business entity is (composition/attributes/relationships) → Structural.
Reasoning signals, not a lookup table. Note: at Row 2 the Functional/Constraint balance
is typically more even than at Row 1 — business capability declarations (HOW-column) are
genuinely Functional, while business rules (WHY-column) are genuinely Constraint. Do not
carry a Row-1 lean into Row 2; judge each statement on its source columns.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: include only when the content gives a measurable acceptance basis (more
  common at Row 2 than Row 1 — business service levels and thresholds appear here).
- verification_method (Test/Analysis/Inspection/Demonstration): include when a natural
  method exists for the business responsibility; omit when the content gives no basis.
- priority (High/Medium/Low): include only when the source supports a relative judgement.
  Do NOT default every requirement to High; omit if there is no basis.

### What NOT to do
- Do NOT bury an interacting actor inside an object ("the business shall enable the child to claim …") — author the actor as subject (a). Burying it loses the boundary.
- Do NOT introduce actors, roles, capabilities, or rules not present in the source CCIs.
- Do NOT reproduce CCI description text verbatim — derive a normative statement.
- Do NOT state a workflow sequence; state a stateless capability / responsibility.
- Do NOT frame at enterprise/scope level (Row 1).
- Do NOT describe HOW the system realises a capability (Row 3 — operations, validation, structure); for a system subject, name only WHAT it provides at the boundary.
""",

    # Rows 3–5: AUTHORED AHEAD OF TEST (Mechanism Spec v0.4). Candidate guidance — NOT yet validated
    # against run evidence (Rows 1–2 were validate-then-author; Rows 3–5 authored together to accelerate
    # the remaining rows on the proven pattern). Treat as pending test until run evidence confirms each.
    # Row 6 remains a short-phrase stub. The prompt template handles full blocks and short phrases alike.
    "3": """
## Row 3 — Designer / Logical Level — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the logical design level — the view of a
system designer translating business obligations into logical structures, behaviours,
and rules, WITHOUT committing to any specific technology or implementation. Each
requirement expresses a logical system capability or a logical integrity constraint —
technology-agnostic, but more concrete than a business responsibility.

### Statement subject (REQUIRED)
Row 3 requirement statements take THE SYSTEM as subject, expressed LOGICALLY:
  "The system shall ..."
This is the row where "The system shall …" becomes correct (it is wrong at Rows 1–2).
But the system is described LOGICALLY — what it must do or enforce as a logical design,
NOT how it is built. Do NOT name technologies, platforms, or code constructs (that is
Row 4+). Do NOT frame as a business responsibility ("The business shall…" is Row 2).
The distinction from Row 2: Row 2 says what the business must be able to do ("The
business shall maintain a record of completed tasks"); Row 3 says how the system
logically realises that ("The system shall maintain a logical association between each
task instance and its completion state").

### Normative form and atomicity
- Use the normative "shall". One logical capability or constraint per statement.
- Apply the two-step "and" test; split genuine compound obligations.
- A Row 3 statement may describe a logical state transition or rule, but NOT a
  step-by-step algorithm (that is Row 5). "The system shall transition a task to
  Claimed state when a child claims it" is logical; "the system shall iterate the task
  list and set status=1" is algorithmic (Row 5) and out of level.

### Statement vocabulary
Row 3 statements use logical-design vocabulary:
  Appropriate: logical structure, logical association, state, state transition,
               validate, enforce (an invariant), derive, logical constraint, access
               boundary, visibility, lifecycle, logical model, decision logic
  Avoid: physical technology names (PostgreSQL, React, Redis, AWS, iOS), code constructs
         (class, function, module, endpoint, table, schema), business-obligation language
         (Row 2: stewardship, entitlement, accountability), and algorithmic/output detail
         (Row 5: calculate, compute, format, report — prefer "derive" / "decision logic"
         / "visibility model").

### requirement_type reasoning (principle-based — choose, do not pattern-match)
- WHY-column logical integrity rules / design-level invariants → lean Constraint ("The
  system shall enforce that …").
- HOW-column logical processes / WHAT-column logical structures / WHEN-column logical
  state triggers → lean Functional ("The system shall maintain / validate / derive …").
- Logical performance characteristics (a logical throughput or latency invariant) →
  Constraint, verified by Measurement (with fit_criteria).
- Logical quality attributes → Constraint (quality bound).
- Logical composition/attribute/relationship assertions → Structural.
Reasoning signals, not a lookup. Judge each statement on its source columns; do not
carry a lean from another row.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: include when a logical acceptance basis exists (a state invariant can
  often be expressed as a checkable condition).
- verification_method: Analysis or Inspection are common at Row 3 (logical assessment);
  include when a natural method exists, omit otherwise.
- priority: include only when the source supports a relative judgement; do not default
  to High.

### What NOT to do
- Do NOT name technologies, platforms, or code constructs (Row 4+).
- Do NOT frame as a business responsibility (Row 2) or describe a step-by-step algorithm (Row 5).
- Do NOT reproduce CCI description text verbatim — derive a normative statement.
""",

    "4": """
## Row 4 — Builder / Physical Level — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the physical builder level — the view of a
builder making concrete technology choices and specifying physical components, without
yet writing code or configuring runtime detail. Each requirement expresses a physical
construction obligation — a concrete technology, component, or platform decision.

### Statement subject (REQUIRED)
Row 4 statements take THE SYSTEM or a NAMED PHYSICAL COMPONENT as subject:
  "The system shall ..."           (default)
  "<Named component> shall ..."    (when a CCI identifies a specific physical component,
                                   e.g. "The mobile application shall ...")
Technology and platform names are APPROPRIATE here (unlike Row 3). The distinction from
Row 3: Row 3 says what the system must do logically; Row 4 says how it is physically
realised ("The system shall persist task records in a relational store", "The mobile
application shall run on iOS and Android").

### Normative form and atomicity
- Normative "shall"; one physical construction obligation per statement; apply the "and" test.
- Physical does not mean code-level — a Row 4 statement specifies the technology/component
  choice, not the algorithm or configuration value (those are Row 5).

### Statement vocabulary
Row 4 statements use physical-construction vocabulary:
  Appropriate: platform, component, infrastructure, deployment, interface, integration,
               physical schema, service, API, persist, host, named technologies (iOS,
               Android, relational store, REST, etc.)
  Avoid: business-level language (Row 2), purely logical abstractions with no physical
         specifics (Row 3), and code-level/configuration detail (Row 5: exact field
         types, timeout values, algorithm steps).

### requirement_type reasoning (principle-based)
- WHY-column physical constraints (platform version requirements, hardware limits,
  build-level compliance mandates) → lean Constraint.
- HOW/WHAT/WHERE/WHO physical construction obligations (components, schemas, deployment
  targets, interfaces) → lean Functional.
- Physical performance requirements (concrete throughput, latency, capacity) →
  Constraint, verified by Measurement (with fit_criteria — common and expected at Row 4).
- Physical quality attributes → Constraint (quality bound).
- Physical composition/attribute/relationship assertions (schemas, component structure) → Structural.
Judge each statement on its source columns.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: more frequently warranted at Row 4 (physical performance/capacity has
  measurable acceptance bases).
- verification_method: Test and Demonstration become common at Row 4 (physical artefacts
  are testable); include when a natural method exists.
- priority: include when the source supports it; do not default to High.

### What NOT to do
- Do NOT frame as business (Row 2) or purely logical (Row 3) — name the physical realisation.
- Do NOT drop to code-level/configuration detail (Row 5).
- Do NOT reproduce CCI description text verbatim.

### Sparse rows
Row 4 is often sparse for conceptually-framed source material. If the row has zero CCIs
the mechanism takes the no_cci_input path (e.g. NQPS Row 4) — this guidance is not invoked.
A single physical constraint legitimately yields a single requirement.
""",

    "5": """
## Row 5 — Implementer / Detailed Design Level — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the detailed design level — the view of an
implementer specifying the precise detail needed before a developer writes code:
algorithms, data formats, platform-specific configuration, interface contracts, detailed
runtime behaviours. Each requirement expresses a detailed specification obligation.

### Statement subject (REQUIRED)
Row 5 statements take THE SYSTEM or a NAMED COMPONENT/INTERFACE as subject:
  "The system shall ..."
  "<Named component/interface> shall ..."
The distinction from Row 4: Row 4 chooses the technology ("persist in a relational
store"); Row 5 specifies the detail ("store the reward value as a decimal(10,2) field
with a non-negative constraint"). Row 5 is where exact formats, algorithms, and
configuration values are correct.

### Normative form and atomicity
- Normative "shall"; one detailed specification per statement; apply the "and" test.
- Row 5 statements may specify precise algorithmic steps, exact field definitions,
  exact timing values — the detail a developer needs without making further design
  decisions.

### Statement vocabulary
Row 5 statements use detailed-implementation vocabulary:
  Appropriate: exact field definitions, data types, format constraints, validation
               rules, enumeration values, algorithm steps, timeout values, cycle
               durations, interface contracts, configuration parameters, calculate,
               compute, format (these algorithmic/output verbs are CORRECT at Row 5)
  Avoid: business-level (Row 2) and high-level logical/physical framing without the
         precise detail (Rows 3–4). At Row 5 the detail is the point — a vague
         statement is out of level downward.

### requirement_type reasoning (principle-based)
- WHY-column detailed constraints (precise validation rules, exact platform version
  requirements expressed as implementable constraints) → lean Constraint.
- HOW-column detailed algorithms / WHAT-column detailed data specifications / WHEN-column
  detailed timing → lean Functional.
- Detailed performance specifications (exact latency/throughput targets with values) →
  Constraint, verified by Measurement (the fit_criteria IS the numeric target).
- Detailed quality specifications → Constraint (quality bound).
- Detailed data-structure / format / field composition assertions → Structural.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: frequently warranted at Row 5 and often IS the specification (exact
  values, formats, thresholds).
- verification_method: Test is common at Row 5 (detailed specs are directly testable).
- priority: include when the source supports it; do not default to High.

### What NOT to do
- Do NOT frame at business/logical/physical-choice level without the implementable detail.
- Do NOT reproduce CCI description text verbatim — derive a normative specification.

### Column-sparse rows
Row 5 CCIs often cluster by column (deployment nodes, UI actors, timing cycles). Derive
requirements grouped by their natural implementation boundary; a sparse single-column
row legitimately yields few requirements.
""",

    "6": "Operational level — statements covering runtime procedures and user/operator interactions; "
         "subject is the system or the operator as the operational content dictates. "
         "[Short phrase — operational content is rare in the reference source documents; full block "
         "pending Row 6 requirement-derivation validation if/when operational CCIs appear.]",
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
    "concern_atomicity_flags":   [],                // [{requirement_id, cci_refs, classification_types, columns}] — ADVC-3d-03

    // --- Stage 4 ---
    "requirement_count_produced": 5,
    "requirement_count_retired":  0,                // non-zero on FullRerun only
    "requirement_type_distribution": {
      "Functional": 3, "Constraint": 2, "Structural": 0
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
| **VER-3d-09** | All `requirement_type` in {Functional, Constraint, Structural} | membership check |
| **VER-3d-10** | `domain_refs` ≥1; resolve to existing Domains with matching `row_target` | expand; JOIN `domain`; assert exists + row match |
| **VER-3d-11** | IdempotentRerun: set unchanged; `idempotent==true`; status=Skipped | before/after + flag |
| **VER-3d-12** | FullRerun: `requirement_count_retired` == prior active count | query prior; assert equality |
| **VER-3d-13** | `requirement_count_produced >= 1` when `cci_count_input > 0` | conditional |
| **VER-3d-14** | No `fit_criteria` present-but-empty | `fit_criteria IS NULL OR length>0` |
| **VER-3d-15** | No surviving Requirement violates typed-slot atomicity (CHK-3d-09 hard) | assert `validation_failures` carries no surviving `atomicity_violation`; spot-check survivors parse to required slots for their type |
| **VER-3d-16** | `refines_refs` valid: empty as produced by Pass 3d; if any present (post-Matching), each references an existing Requirement at `row_target − 1` | Pass 3d output: assert all empty. Post-Matching integration: expand; JOIN `requirement`; assert parent row = child row − 1 |
| **VER-3d-17** | Every Functional Object slot and every Structural entity in the produced set was presented to the DD service and is either resolved to a `DataDictionaryEntry` or recorded in `mechanism_data.dd_binding.dd_unresolved` (none silently absent) | `test_dd_binding_complete` — for each survivor, assert its Object/entity term appears once in `dd_binding` as resolved or `dd_unresolved` |
| **VER-3d-18** | Regression guard: after a Pass 3d run that produced ≥1 Requirement, the project Data Dictionary is non-empty (≥1 `DataDictionaryEntry`) | `test_dd_populated_after_derivation` — `requirement_count_produced >= 1 ⇒ count(DataDictionaryEntry) >= 1` |
| **VER-3d-19** | Entity-grade term guard: no candidate term presented to the DD equals the verbatim Object slot or the full statement; DD `canonical.name` values produced by this run are entity-grade noun phrases (sanity bound: short — heuristically ≤ ~5 words — and not terminated by sentence punctuation) | `test_dd_terms_entity_grade` — assert no `dd_binding` term contains the statement's verb phrase / trailing period; spot-check produced canonical names against the bound |

(CHK-3d-08 subject mismatch is recorded in `subject_vocabulary_flags` and reviewed via PLB-3d-02; it is soft severity and not a VER gate. CHK-3d-09 atomicity is HARD — VER-3d-15 gates it. ADVC-3d-02 interrogative-completeness is a soft advisory — it logs `interrogative_completeness_advisory` for PLB-3d-07 review and is not a VER gate, consistent with its generative-guidance nature.)

### 8.2 Plausibility checklist for Practitioner review

Realises Row 3 §8.2.

1. **PLB-3d-01 — Statement atomicity and non-redundancy.** One obligation per statement (sentence-level, CHK-3d-09) AND per concern (§5.4 concern-atomicity guidance; ADVC-3d-03 flags multi-concern spans). Near-duplicates are now prevented at authoring (§5.4 non-redundancy guidance); any not so prevented and not collapsed by CHK-3d-07 are flagged here. Review `concern_atomicity_flags` (ADVC-3d-03) — a requirement bundling distinct cross-column concerns it does not all voice should have been split.
2. **PLB-3d-02 — Row-appropriate abstraction.** Subject and vocabulary match the row. Review `subject_vocabulary_flags` (CHK-3d-08) — any Row 1 statement subjected to "the system" is an abstraction failure to correct. Implementation verbs (calculate, store, retain) at Row 1/2 are PLB failures.
3. **PLB-3d-03 — requirement_type plausibility.** Type matches source CCI columns. Review `requirement_type_distribution` for anomalies. Boundary-case type variance across runs is accepted (Tracker F81 related item).
4. **PLB-3d-04 — No inferred content (LPM).** No actor/behaviour/constraint absent from source CCIs; no verbatim CCI text.
5. **PLB-3d-05 — Measurement fit_criteria.** Every Measurement-verified Constraint carries meaningful `fit_criteria`; complete where `measurement_missing_fit_criteria` fired.
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
| **Measurement-verified Constraint without fit_criteria** | `measurement_missing_fit_criteria` (info); PLB-3d-05. |
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
| **F81** | Open → Rows 1–2 validated, Rows 3–5 authored | REQUIREMENT_ROW_GUIDANCE["1"] and ["2"] validated (Row 1: PMT Run 5 / NQPS Run 2; Row 2: PMT Row 2 Run 1 / NQPS Row 2 Run 1). ["3"]–["5"] authored in this version (v0.4) as candidate guidance, pending test. F81 stays Open scoped to Rows 3–5 (pending test) and Row 6 (stub). |

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
- This spec (Row 4 Requirement Derivation v0.5) — implementation authority (DDL §5.1, schemas §5.2, guidance §5.4)
- Row 3 Requirement Derivation v0.1 — logical authority (stage logic, VER/PLB intent)
- Row 4 Domain Derivation v0.24 — structural sibling (four-stage pattern, audit/fingerprint conventions)
- Row 4 Understanding §14 — framework (module structure, ProjectProfile params, VER→pytest, fixtures)

**Reference:** Row 4 Applied v0.2; Canonical Ledger v2.13; Segmentation spec v9.2.

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

### 12.6 v0.2 → v0.3 change detail

v0.3 is a guidance-content addition only — no change to stages, schemas, DDL, audit structure, or re-run mechanics.

- **§5.4 REQUIREMENT_ROW_GUIDANCE["2"] (new):** the Row 2 stub is replaced with a full block, authored at business-owner abstraction with the same anatomy as Row 1 (statement subject / atomicity / vocabulary / type-reasoning / optional-field policy). Key Row 2 distinctions from Row 1: subject is "The business shall…" (or a named business role), not "The enterprise shall…"; statements are stateless business-capability obligations, not scope-level commitments and not workflows; the Functional/Constraint balance is expected to be more even than Row 1 (business capability declarations are genuinely Functional, business rules genuinely Constraint), with an explicit instruction not to carry the Row 1 Constraint lean into Row 2.
- **Row 1 guidance unchanged** and now carries its validation record (PMT Run 5 / NQPS Run 2).
- **Rows 3–6** remain short-phrase stubs.
- **No code-path change** beyond loading the expanded `REQUIREMENT_ROW_GUIDANCE["2"]` block — the prompt template already injects `REQUIREMENT_ROW_GUIDANCE[str(row_ref)]` for any row. Row 2 testing requires no mechanism change, only the guidance content added here plus Pass 3c Row 2 Domains in the ledger.

**Re-implementation impact:** update `prompts/requirement_row_guidance.py` with the Row 2 block; no other code change. The Row 2 validation step is a Pass 3d run against PMT Row 2 and NQPS Row 2 (both have Row 2 CCIs and Domains).

### 12.7 v0.3 → v0.4 change detail

v0.4 is a guidance-content addition only — no change to stages, schemas, DDL, audit structure, or re-run mechanics.

- **§5.4 REQUIREMENT_ROW_GUIDANCE["3"], ["4"], ["5"] (new):** the three stubs are replaced with full blocks, authored at logical-design (Row 3), physical-builder (Row 4), and detailed-implementation (Row 5) abstraction, each the requirement-statement analogue of the corresponding sibling domain ROW_GUIDANCE block. Key per-row distinctions: Row 3 is where "The system shall…" becomes correct but expressed *logically* (no technology names, no algorithms); Row 4 introduces named technologies/components and physical realisation; Row 5 introduces exact detail (formats, algorithms, values) and is where algorithmic/output verbs like "calculate"/"compute"/"format" become correct. Each block carries the standard anatomy (subject / atomicity / vocabulary / type-reasoning / optional-field policy) and explicit "what NOT to do" boundaries against the adjacent rows.
- **IMPORTANT — Rows 3–5 are candidate, not validated.** Rows 1–2 were validated before the next row was authored. Rows 3–5 were authored together, ahead of run evidence, to accelerate the remaining rows on the proven pattern. They MUST be confirmed by run evidence (per-row test against PMT and NQPS) before being treated as closed. This is a deliberate, recorded departure from the validate-then-author cadence.
- **Rows 1–2 unchanged**; Row 6 remains a short-phrase stub.
- **No code-path change** beyond loading the expanded `REQUIREMENT_ROW_GUIDANCE["3"]`–`["5"]` blocks — the prompt template already injects `REQUIREMENT_ROW_GUIDANCE[str(row_ref)]` for any row.

**Re-implementation impact:** update `prompts/requirement_row_guidance.py` with the three blocks; no other code change. Validation steps: Pass 3d runs against PMT Rows 3/4/5 and NQPS Rows 3/5 (NQPS Row 4 has zero CCIs → no_cci_input path, guidance not invoked).

### 12.8 v0.4 → v0.5 change detail

v0.5 is the Tier 2 reconciliation to the closed cross-row/structural design (findings F82–F93). It realises Row 3 Requirement Derivation v0.2 and ledger v2.13. Unlike v0.2–v0.4 (guidance-content additions), v0.5 changes **schema and validation**:

- **Ledger v2.13 schema reconciliation:** DDL `requirement_type` CHECK and Pydantic `Literal` collapsed to `Functional|Constraint|Structural` (F89); `verification_method` CHECK/Literal gains `Measurement`; new `refines_refs` JSONB column (F82), `NOT NULL DEFAULT '[]'`. Transcribed normative rules updated to v2.13 (refines_refs rule; Measurement-fit-criteria rule replacing the Performance one).
- **New hard check CHK-3d-09 (F88):** typed-slot atomicity, decidable, HARD-rejecting. Compound condition/object, multiple constraint rules, or a missing required slot for the type → reject; CCIs return to the orphan pool for CHK-3d-05 repair. Gated by VER-3d-15. This is the physical enforcement of the F88 hard-atomicity constraint that v0.4 carried only as soft guidance.
- **CHK-3d-08 severity unchanged (soft) but re-justified:** now soft because validated across Rows 1–3/5 (the §5.4 guidance holds subject discipline), not because evidence is pending.
- **§5.4 guidance type-vocabulary reconciled** in all five blocks: former Performance/Suitability/quality-attribute → Constraint (Measurement/Inspection-verified); composition/attribute/relationship → Structural.
- **§4.4.3 / response schema:** `refines_refs=[]` at construction; AI never returns it (Matching-service populated, F85/F93).
- **VER-3d-15, VER-3d-16 added** (atomicity gate; refines_refs validity).

**Explicitly NOT in v0.5 (deferred to later authoring steps, per F93 sequence):**
- The full **F87/F88 interrogative-elaboration guidance** — CSPO slot-elicitation prompts and per-requirement interrogative completeness questions that expand §5.4. v0.5 reconciles the *type vocabulary* of the guidance blocks and adds the *atomicity check*, but does not yet rewrite the prompts to elicit slot-structured CSPO statements or to run the interrogative completeness sweep. That is the next guidance-authoring increment.
- The **Requirement Matching service** and **Data Dictionary service** internals (F85/F90) — declared as interfaces (refines_refs population, Object-slot binding) per Row 3 v0.2 §5.5; specified in their own service specs.

**Re-implementation impact:** Alembic migration to alter `requirement_type` CHECK, add `Measurement` to `verification_method` CHECK, add `refines_refs` JSONB column (existing rows default `[]`); implement CHK-3d-09 in `stage3_structural_validation.py`; update the three response schemas' type Literal; update `requirement_row_guidance.py` type-reasoning lines. Existing PMT/NQPS data migrates per ledger v2.13 Appendix D (Performance/Suitability→Constraint, Non-Functional→Structural).

### 12.9 v0.5 → v0.6 change detail

v0.6 adds the interrogative-elaboration guidance that v0.5 explicitly deferred (the §12.8 "Explicitly NOT in v0.5" item). It is **guidance + advisory only** — no schema, DDL, or hard-check change.

- **§5.4 shared interrogative-completeness guidance:** a preamble across all five row blocks instructing slot-filling-by-interrogation (type-required slots, with the Object-recursion that surfaces Structural requirements), making the row's set generatively complete and explicitly staying within the row (no cross-row parent invention — that is Matching/GQA).
- **ADVC-3d-02 (new, soft advisory):** flags thin type-required slots / un-interrogated Objects (`interrogative_completeness_advisory`, PLB-3d-07). Distinct from the HARD CHK-3d-09 atomicity reject. Soft because interrogative completeness is generative guidance; a hard completeness gate would wrongly reject legitimately-terminal requirements (e.g. an abstract Row 1 constraint).

**Re-implementation impact:** update `prompts/requirement_row_guidance.py` with the shared interrogative preamble (and per-row slot vocabulary); implement ADVC-3d-02 as a soft advisory in `stage3_structural_validation.py` (logging only, no reject). No migration, no schema change.

**Still NOT in v0.7 (deferred):** the Requirement Matching service internals remain its own spec (Row 3/4 Requirement Matching v0.2). **The Data Dictionary Object-slot binding is now active (§4.4.3a) — Pass 3d populates the DD; the DD service's internal resolution mechanics remain in the DD spec (Row 3/4 Data Dictionary v0.1).** The state-completeness capability (F91) remains deferred.

## Document End

End of SysEngage Row 4 Mechanism: Requirement Derivation v0.12.

Physical realisation of the Row 3 (logical) Requirement Derivation spec v0.7, against ledger v2.15. Reconciled type/atomicity/schema (v0.5) + interrogative elaboration (v0.6) + DD Object-slot binding (v0.7) + DD entity-reduction extraction (v0.8) + Row 2 subject taxonomy / boundary test (v0.9) + **Row 1 domain-entity vocabulary preservation (v0.10)**: §5.4 REQUIREMENT_ROW_GUIDANCE["1"] gains a source-entity-preservation rule — Row 1 abstraction lives in subject and verb, not in renaming domain entities; keep the source's domain nouns (task, reward, earnings), do not coin abstract paraphrases. Fixes the empty-Row-1-DD / zero-cross-row-recall failure at its root (entity-paraphrase left no entity to extract). The fix also removes the need for cross-abstraction DD synonymy: one entity, one name, all rows. §5.4 four-class Row 2 subjects; CHK-3d-08 widened taxonomy; CHK-3d-09 hard atomicity; ADVC-3d-02 advisory; DD binding §4.4.3a (entity reduction); VER-3d-17/18/19. `refines_refs` populated by Requirement Matching (Row 3/4 v0.3). F80 Open; F81 Open; F82/F87/F88/F89/F90 derivation portions realised here; Row 2 subject taxonomy realises R2-AMEND-9 / OD-R2-30.

Companion artefacts:
- SysEngage_Row_3_Mechanism_Requirement_Derivation_v0_7.md — logical authority (§4.1.1(c) domain-entity preservation; §4.1.1(a) subject taxonomy)
- SysEngage_Row_2_Understanding_v1_5.md §2.3.3 — subject taxonomy & boundary semantics
- SysEngage_Row_3_Mechanism_Data_Dictionary_v0_2.md / Row_4 v0.1 — the service §4.4.3a calls
- SysEngage_Row_3_Mechanism_Requirement_Matching_v0_3.md / Row_4 v0.3 — populates `refines_refs`; subject-class distinctness + empty-candidate-set corrections are the remaining Matching cascade items
- SysEngage_Row_4_Domain_Derivation_v0_24.md — structural sibling
- SysEngage_Issues_Tracker_v0_65.md — F80–F93 disposition
- sysengage_minimal_ledger_spec_v2_15.md — canonical schema authority
