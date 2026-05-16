# SysEngage Row 3 Mechanism: CellContentItem Construction

**Architectural mechanism specification — v0.2**

Filename: SysEngage_Row_3_Mechanism_CCI_Construction_v0_2.md

Version: 0.2 (Signal column attribute removal — batch processing model)

Date: 16 May 2026

**Purpose.** Specifies the designed mechanism by which SysEngage constructs CellContentItem (CCI) entities from the Signal set produced by Pass 3a (Row-Lens Source Re-Analysis). Signals are taken as evidence and transformed into atomic, classified content items that serve as the analytical bridge between raw classification evidence (Signals) and formal outputs (Domains, Requirements). Operates under DM (Derivation Mode) as the primary mode, with IM (Interpretive Mode) for the AI-assisted derivation and deduplication acts. Runs once per active row (Row-sequential), after Pass 3a completes.

**Status.** v0.2 — revised to remove dependency on a `column` attribute on Signal entities. v0.1 specified that Signals would be grouped by column before CCI derivation, implying a `column` field on Signal. That field does not exist in canonical ledger spec v2.12 and was not specified by any Pass 3a mechanism spec. v0.2 replaces per-column grouping with batch processing: the full eligible Signal set is partitioned into fixed-size batches; each batch is presented to the AI with all six column interrogatives simultaneously; the AI assigns both `column` and `classification_type` as part of the CCI derivation act. Duplicates produced across batches are caught by the existing Step 4 deduplication sweep. No Signal schema change required.

**Changes from v0.1.** (1) §1 Mechanism scope: removed "Group by column"; replaced with batch processing model. (2) §3.3 Configuration inputs: added `cci_batch_size`. (3) Step 2: removed Step 2b column grouping; replaced with batch partitioning. (4) Step 3: changed from per-cell iteration to per-batch iteration; AI prompt now presents all six column interrogatives; response schema gains `column` field. (5) Stage 3b: vocabulary validation now checks both `column` and `classification_type`. (6) §9.1 and §9.5 edge cases: reframed from per-cell to per-batch. (7) §11.2 open questions: records the Signal column attribute authoring gap and its resolution.

**Precedence rule.** Where this artefact's content appears to differ from POC source documents, the SysEngage Row 1 v1.2 / Row 2 v1.2 / Row 3 v1.1 Understanding documents take precedence. Where any spec content appears to differ from canonical ledger spec v2.12, the canonical ledger spec takes precedence.

---

## 1. Mechanism Identification

| **Mechanism name** | CellContentItem Construction |
| --- | --- |
| **Mechanism ID** | MECH-R3-004 |
| **Mechanism scope** | Upsert all six ZachmanCells for the current row. Partition the eligible Signal set into fixed-size batches. For each batch, present all Signals to the AI with all six Zachman column interrogatives simultaneously; the AI derives candidate CCIs and assigns each to a column as part of the derivation act. Deduplicate candidates per cell using structural pre-filter followed by AI semantic review — duplicates produced across batches are caught here. Commit surviving CCIs to the ledger with identifiers allocated per cell sequence. On re-run, extend existing CCIs rather than replacing them. Produce an AnalysisPass execution record. |
| **Operational location** | Phase 3 Pass 3b — CellContentItem Construction (PH003 per Row 2 v1.2 §3.9.3 / Row 3 v1.1 §3.9.3). Executes after Pass 3a completes; before Pass 3c (Domain derivation). |
| **Mechanism class** | Derivation mechanism with AI-assisted interpretation. Primary mode is DM (entity production from AI output is rule-based). IM is active for Stage 3a (AI derivation act) and Stage 4b (AI semantic deduplication review). LPM is the preservation constraint — Signal descriptions and source text are never rewritten. |
| **Row applicability** | Row-sequential. Runs once per active row. All six ZachmanCells are always upserted regardless of Signal population. Empty cells are valid outputs — they drive Phase 5 Cell Quality Analysis findings. |
| **Primary outputs** | (1) ZachmanCell entities (ZC-R{n}-C-{column}) — six per row, upserted on every run. (2) CellContentItem entities (CCI-ROW{n}-C-{column}-{seq}) — one per distinct classified content item per cell. (3) AnalysisPass execution record — mechanism="CellContentItemConstruction". |
| **Outputs NOT produced** | Signal entities — produced by Pass 3a. Domain entities — produced by Pass 3c. Requirement entities — produced by Pass 3d. Risk entities — deferred to Safety/Cyber Security mechanism activation at designated phases (see F41). Boundary candidate CCIs — deferred to Phase 5 Robustness mechanism (see F40). |
| **Mechanism Stakeholder owner** | No dedicated SG-04 Mechanism Stakeholder. SH001 (SysEngage Tool Stakeholder) covers structural review. SG-01 (Practitioner) covers all quality review. SG-03 (AI Model) carries execution attribution via AnalysisPass. |

---

## 2. Cross-References to Understanding Documents

| **Source** | **Reference** | **Commitment grounded by reference** |
| --- | --- | --- |
| **Row 1 v1.2** | §8.1 Non-Loss Principle | Every Signal in the eligible set must produce at least one CCI candidate or be explicitly recorded as non-productive in the AnalysisPass. Silent discard is not permitted. |
| **Row 1 v1.2** | §8.2 Verbatim Preservation Principle | Signal descriptions and source text are read, not rewritten. CCI descriptions are derived statements, not copies of Signal text. LPM applies as preservation constraint throughout. |
| **Row 1 v1.2** | §8.3 Mode Declaration Principle | Pass 3b declares DM as primary mode with IM sub-acts. Mode violations recorded on AnalysisPass. |
| **Row 1 v1.2** | §8.4 Ambiguity Preservation Principle | Where AI semantic review produces an Ambiguous verdict for a candidate pair, both candidates survive with reduced confidence rather than one being arbitrarily suppressed. |
| **Row 2 v1.2** | §3.9.3 Pass 3b description | Authoritative purpose: construct atomic CCIs from Signals per ZachmanCell. Inputs: Signal, ZachmanCell. Outputs: CellContentItem. Primary mode: DM. |
| **Row 3 v1.1** | §3.9.3 Pass 3b description | Row 3 inheritance of canonical Pass 3b. No Row 3-specific deviations for this pass beyond standard row-abstraction differences in CCI content character. |
| **Canonical Ledger v2.12** | Element Type — ZachmanCell | Authoritative schema: cell_id (ZC-R{row}-C-{column}), row_target, column. Six instances per row. |
| **Canonical Ledger v2.12** | Element Type — CellContentItem | Authoritative schema: ci_id, cell_id, classification_type, signal_refs, description, trigger_condition (optional), justification (optional), confidence. Identifier format: CCI-ROW{n}-C-{column}-{seq}. Sequence scoped per ZachmanCell. |
| **Canonical Ledger v2.12** | Element Type — AnalysisPass | Authoritative schema for execution record. mechanism="CellContentItemConstruction". |
| **Tracker v0.27** | F40 | §8.12 Behaviour-Structure Boundary Preservation — boundary analysis deferred to Phase 5 Robustness mechanism. Pass 3b does NOT produce boundary candidate CCIs. |
| **Tracker v0.27** | F41 | Safety/CyberSec mechanism evaluation deferred to designated analysis phases. Pass 3b does NOT produce Risk entities. |

---

## 3. Inputs

### 3.1 Primary input — eligible Signal set

All Signal entities for the current row where:
- `Signal.row_target == str(current_row)`
- If `Signal.derived_from_concern_id` is non-null: the referenced Concern MUST be in state `Resolved` (not `Open`, not `Dispositioned`)

This is a runtime query — not a stored entity. The eligible Signal set is held in memory for the duration of Pass 3b and discarded on completion. Re-running Pass 3b after a Phase 10 Concern resolution automatically picks up updated Signals because the query re-executes from scratch.

**Data integrity check:** Any Signal referencing an Open Concern is a data integrity violation — flagged in AnalysisPass failure detail and excluded from processing. Pass 3b does not block on this condition but records it.

### 3.2 Secondary input — existing ZachmanCells and CCIs (re-run only)

On re-run, the existing committed ZachmanCells and CCIs for the current row are read from the ledger. These are the baseline against which new candidates are deduplicated in Stage 4b (Step 4b-iii). On first run, these sets are empty.

### 3.3 Configuration inputs

- `row_ref` — integer 1–6. Determines ZachmanCell identifiers and CCI identifier format.
- `practitioner_id` — populated on AnalysisPass.
- `column_vocabulary` — per-column classification_type vocabulary (see §5.1). Sourced from mechanism configuration; not per-run AI judgment.
- `cci_batch_size` — integer. Maximum number of Signals per AI invocation batch in Step 3. Sourced from `ProjectProfile.cci_batch_size` (default: 20). Controls context window pressure; does not affect analytical correctness — duplicates produced across batches are caught by Step 4 deduplication.

---

## 4. What the Mechanism Does — Step-Level Activities

Pass 3b executes in six sequential steps.

---

### Step 1 — Assemble Eligible Signal Set

**Mode:** DM. No AI involvement.

Execute the runtime query defined in §3.1. Collect all qualifying Signals into an in-memory working set ordered by `signal_id` ascending (lexicographic stability for determinism). Record the count for AnalysisPass.

This step produces no ledger writes. The Signal set is transient.

---

### Step 2 — Upsert ZachmanCells and Partition Signals into Batches

**Mode:** DM. No AI involvement.

**Step 2a — ZachmanCell upsert.** For the current row, upsert all six ZachmanCells:

```
ZC-R{row}-C-What
ZC-R{row}-C-How
ZC-R{row}-C-Where
ZC-R{row}-C-Who
ZC-R{row}-C-When
ZC-R{row}-C-Why
```

Upsert (not insert) because Pass 3b may be re-run. If the ZachmanCell already exists, it is left unchanged — the upsert is idempotent. Update ZachmanCellRegister to include all six cell_ids for this row (also idempotent).

**Step 2b — Batch partitioning.** Partition the eligible Signal working set into batches of size `ProjectProfile.cci_batch_size` (default 20), ordered by `signal_id` ascending. The final batch may be smaller than the configured size. Batch boundaries have no analytical significance — they exist solely to manage AI context window size. Every Signal appears in exactly one batch.

If the Signal working set is empty: no batches are produced. Step 3 is skipped. All six ZachmanCells have been upserted and the mechanism proceeds to Step 4 (which finds no candidates) and then Steps 5 and 6.

**Output:** Six ZachmanCells committed to ledger. Ordered list of Signal batches held in memory.

---

### Step 3 — Per-Batch CCI Construction (IM + DM)

For each Signal batch from Step 2, execute the three-stage construction sequence.

**Stage 3a — AI derivation act (IM).**

Present the batch's Signals to the AI with:
- The current row's abstraction lens
- All six column interrogatives and their analytical framing (What / How / Where / Who / When / Why at this row's abstraction level)
- The complete column vocabulary — permitted `classification_type` values for each column (see §5.1)
- Each Signal's `signal_id`, `description`, `signal_type`, and `confidence`

The AI produces, for each distinct classified content item it identifies across all six columns:
- `column` — one of {What, How, Where, Who, When, Why}
- `classification_type` — from the permitted vocabulary for the assigned column
- `description` — a derived statement of classified meaning (not a copy of Signal text)
- `signal_refs` — the Signal id(s) from which this item was derived (at least one)
- `confidence` — derivation confidence, 0.0–1.0
- `trigger_condition` (optional)
- `justification` (optional)

A single Signal may produce more than one candidate CCI where it contains multiple distinct classified items, potentially across different columns. Multiple Signals may ground a single CCI where they converge on the same classified content. The AI determines column placement as part of the derivation act — this is an interpretive judgment, not a mechanical partition.

**Stage 3b — Entity production (DM).**

For each AI output item, construct a candidate CCI struct with all attributes populated except `ci_id` (allocated at Step 5). Validate:
- `column` is one of {What, How, Where, Who, When, Why} — reject if not
- `classification_type` is within the permitted vocabulary for the assigned `column` (§5.1) — reject if not
- `signal_refs` is non-empty — reject if empty
- `confidence` is within 0.0–1.0 — reject if outside range
- `description` is non-empty — reject if empty

Rejected items recorded in AnalysisPass `candidates_rejected`. Not silently dropped.

The candidate CCI struct carries `cell_id = ZC-R{row_ref}-C-{column}` derived deterministically from the AI-assigned `column`.

**Stage 3c — Pydantic validation at AI response boundary.**

Parse the full AI response against the `cci_construction_response_schema`. Items that fail schema validation are recorded in AnalysisPass failure detail; valid items added to the candidate buffer.

**AI failure handling:** Retry up to 3 times with exponential backoff (1s, 2s, 4s). If all retries fail for a batch: that batch produces no candidates. Recorded in AnalysisPass failure detail. Execution continues with remaining batches. execution_status = CompletedWithWarnings if other batches succeeded; Failed if all batches failed.

---

### Step 4 — Per-Cell Deduplication Sweep (DM + IM)

For each cell's candidate CCI set from Step 3, execute the three-stage deduplication sequence. On re-run, the sweep also includes existing committed CCIs for the cell (read from ledger in §3.2).

**Stage 4a — DM structural pre-filter.**

Identify candidate duplicate pairs where:
- `classification_type` values match exactly, AND
- `signal_refs` sets are identical (same elements, same Signal ids)

Identical `classification_type` + identical `signal_refs` is a near-certain duplicate — the same Signals produced the same classification twice. Merge these pairs immediately using the merge rule (see §4.1) without AI involvement.

**Stage 4b — AI semantic review (IM).**

For remaining candidate CCIs within the cell (those not collapsed in Stage 4a), group by `classification_type` and present same-type pairs to the AI for semantic equivalence judgment. The AI determines for each pair:

- **Duplicate** — both CCIs express the same classified meaning despite different wording or partially different `signal_refs`. Apply merge rule.
- **Distinct** — both CCIs express genuinely different content. Both survive.
- **Ambiguous** — AI cannot determine equivalence. Both survive with confidence values reduced by 0.1 (floor at 0.0). Flagged in AnalysisPass for Phase 9 review.

On re-run: the AI semantic review also compares new candidates against existing committed CCIs for the cell. An existing CCI is treated as a candidate in the semantic review — if a new candidate is a duplicate of an existing committed CCI, the merge rule applies to the existing CCI (its `signal_refs` and `confidence` are updated in-place).

**Stage 4c — DM merge execution.**

For each confirmed duplicate pair (from Stage 4a or Stage 4b):
- `signal_refs` = union of both sets (no duplicates in the list)
- `confidence` = higher of the two values
- `description` = AI-informed merged description where the lower-confidence candidate contains nuance absent from the higher-confidence description; otherwise the higher-confidence candidate's description
- Record the merge in the AnalysisPass with both original descriptions preserved for audit

**Over-aggressive consolidation flag:** If a cell's candidate count reduces by more than `ProjectProfile.cci_consolidation_threshold` (default: 0.80, i.e. 80% reduction), flag as a Robustness finding in AnalysisPass. Not an error; a signal for Practitioner review.

---

### Step 5 — Assign Identifiers and Commit

**Mode:** DM. No AI involvement.

For each surviving candidate CCI (new — not an update to an existing CCI):
- Allocate `ci_id` = `CCI-ROW{row}-C-{column}-{seq}` where `seq` is the next available three-digit sequence number for this ZachmanCell. Sequence is scoped per ZachmanCell and is never reset — on re-run, new CCIs continue from the current maximum, not from 001.
- Validate the fully populated CCI against the canonical ledger schema.
- Write to ledger.

For each existing committed CCI that was merged in Step 4 (updated `signal_refs` or `confidence`):
- Update in-place. `ci_id` is preserved unconditionally — never reassigned.
- No new sequence number allocated.

Update CellContentItemRegister with all new `ci_id` values.

Malformed candidates (schema validation failure) are recorded in AnalysisPass failure detail, not silently dropped.

---

### Step 6 — Produce AnalysisPass Record

**Mode:** DM. Fully deterministic. Runs after all five steps complete.

| **Attribute** | **Value** |
| --- | --- |
| `pass_id` | Next available P### in sequence |
| `pass_type` | "Per-row" |
| `mechanism` | "CellContentItemConstruction" |
| `execution_status` | Completed / CompletedWithWarnings / Failed |
| `mode_active` | "DM" |
| `declared_transformation_modes` | ["IM", "DM"] |
| `outputs.cci_data` | See §7 |
| `outputs.mode_violations` | Empty array on clean run |
| `pass_started_at` | Timestamp at Step 1 entry |
| `pass_completed_at` | Timestamp at AnalysisPass commit |
| `elapsed_ms` | Derived |
| `ai_model_fingerprints` | List of AI model versions used in Steps 3a and 4b |

---

### 4.1 Merge Rule (referenced by Step 4)

When two CCI candidates are confirmed as duplicates:

| **Attribute** | **Merge outcome** |
| --- | --- |
| `ci_id` | Existing CCI's id preserved; new candidate has no id yet at this stage |
| `signal_refs` | Union of both sets, no duplicates |
| `confidence` | Higher of the two values |
| `description` | AI-informed merge: higher-confidence candidate's description as base; incorporate nuance from lower-confidence candidate's description where it adds meaning not present in the base. If no nuance: higher-confidence description unchanged. |
| `classification_type` | Must match for merge to have been triggered — unchanged |
| `trigger_condition` | Merged if both have values; higher-confidence candidate's value if only one has it |
| `justification` | Concatenated with separator if both have values |

Audit trail: both original descriptions are recorded in AnalysisPass `outputs.cci_data.merges` for the run.

---

## 5. Column Vocabulary

### 5.1 Permitted classification_type values per column

These are the stable vocabulary terms for `classification_type`. The AI is prompted to use these terms. Generators MUST use this vocabulary within a single ledger.

| **Column** | **Permitted classification_type values** |
| --- | --- |
| **What** | Entity, Attribute, Relationship |
| **How** | Process, Function, Rule |
| **Where** | Location, Node, Network |
| **Who** | Actor, Role, Organisation |
| **When** | Event, Cycle, Trigger |
| **Why** | Goal, Principle, Constraint |

These vocabulary terms are row-agnostic — the same terms apply at all rows. The abstraction level of the content within each classification varies by row (Row 1: strategic; Row 2: conceptual; Row 3: logical; Row 4: physical; etc.).

---

## 6. Designed Mechanism Structure

### 6.1 Step execution order and sequencing constraints

```
Pass 3b — CellContentItem Construction
  ├─ Step 1 — Assemble eligible Signal set (DM, transient)
  ├─ Step 2 — Upsert ZachmanCells + group Signals by cell (DM, ledger write)
  ├─ Step 3 — Per-cell CCI construction
  │     Stage 3a — AI derivation act (IM)
  │     Stage 3b — Entity production (DM)
  │     Stage 3c — Pydantic validation at AI response boundary
  ├─ Step 4 — Per-cell deduplication sweep
  │     Stage 4a — DM structural pre-filter
  │     Stage 4b — AI semantic review (IM)
  │     Stage 4c — DM merge execution
  ├─ Step 5 — Assign identifiers and commit (DM, ledger write)
  └─ Step 6 — Produce AnalysisPass record (DM, ledger write)
```

- Step 1 MUST complete before Step 2 — Signal set must be assembled before grouping.
- Step 2 MUST complete before Step 3 — ZachmanCells must exist before CCIs reference them.
- Step 3 MUST complete for all populated cells before Step 4 — deduplication requires the full candidate set per cell.
- Step 4 MUST complete before Step 5 — identifier allocation applies only to surviving candidates.
- Step 5 MUST complete before Step 6 — entity counts must be final before AnalysisPass is committed.

### 6.2 Mode discipline

| **Step / Stage** | **Mode** | **Constraint** |
| --- | --- | --- |
| Step 1 — Signal query | DM | Deterministic query. No AI involvement. |
| Step 2 — ZachmanCell upsert + grouping | DM | Deterministic upsert and partition. No AI involvement. |
| Stage 3a — AI derivation | IM | AI judgment for CCI content derivation. LPM: Signal descriptions never rewritten. |
| Stage 3b — Entity production | DM | Rule-based construction from AI output. |
| Stage 3c — Pydantic validation | DM | Schema validation. Deterministic. |
| Stage 4a — Structural pre-filter | DM | Deterministic duplicate detection. No AI involvement. |
| Stage 4b — AI semantic review | IM | AI judgment for semantic equivalence. |
| Stage 4c — Merge execution | DM | Rule-based merge from AI verdicts. |
| Step 5 — Identifier allocation and commit | DM | Deterministic sequence allocation and ledger write. |
| Step 6 — AnalysisPass production | DM | Deterministic record construction. |

### 6.3 Re-run semantics

Pass 3b may be re-run after a Phase 10 Concern resolution updates the eligible Signal set. Re-run behaviour:

- Step 1 re-executes the Signal query — the updated Signal set is the input.
- Step 2 upserts ZachmanCells idempotently — existing cells are unchanged.
- Steps 3 and 4 execute normally on the new candidate set, with Stage 4b extending the deduplication sweep to include existing committed CCIs for the cell.
- Step 5: new CCIs are committed with next-sequence identifiers. Existing CCIs are updated in-place where merged. No existing CCI is deleted.
- Step 6 produces a new AnalysisPass record for the re-run. The prior AnalysisPass is retained for audit.

---

## 7. Audit Trail Population (AnalysisPass outputs)

`outputs.cci_data` sub-structure:

| **Field** | **Content** |
| --- | --- |
| `row_ref` | Integer — current row |
| `cells_populated` | Count of ZachmanCells with at least one committed CCI |
| `cells_empty` | Count of ZachmanCells with no committed CCIs (6 − cells_populated) |
| `ccis_created` | Count of new CCI entities committed this run |
| `ccis_merged` | Count of existing CCI entities updated (signal_refs or confidence updated) this run |
| `candidates_rejected` | Count of candidate CCIs that failed schema validation |
| `merges` | Array of merge audit records: `{surviving_ci_id, original_descriptions: [str, str], merged_signal_refs: [str]}` |
| `consolidation_flags` | Array of cells where consolidation ratio exceeded threshold: `{cell_id, candidates_in, ccis_out, ratio}` |
| `integrity_violations` | Array of Signals excluded due to referencing Open Concerns: `{signal_id, concern_id}` |

---

## 8. Verification Criteria

### 8.1 Decidable criteria (automated verification)

| **ID** | **Criterion** | **Verification method** |
| --- | --- | --- |
| **VER-3b-01** | All six ZachmanCells for the current row exist in the ledger after Pass 3b completes | Query ledger: count ZachmanCell where row_target = str(row_ref). Must equal 6. |
| **VER-3b-02** | All CCI ci_id values match canonical format `^CCI-ROW[1-6]-C-(What\|How\|Where\|Who\|When\|Why)-\d{3}$` | Regex validation against all ci_id values for this row. |
| **VER-3b-03** | Every CCI's `cell_id` references an existing ZachmanCell | Referential integrity check: all CCI.cell_id values resolve to a ZachmanCell in the ledger. |
| **VER-3b-04** | Every CCI's `signal_refs` is non-empty and each entry references an existing Signal | Referential integrity check: all entries in CCI.signal_refs resolve to a Signal in the ledger. |
| **VER-3b-05** | Every CCI's `classification_type` is within the column's permitted vocabulary (§5.1) | Enumeration check per column. |
| **VER-3b-06** | Every CCI's `confidence` is within [0.0, 1.0] | Range check. |
| **VER-3b-07** | CCI identifier sequences are scoped per ZachmanCell — no sequence number appears in more than one cell | For each column, verify ci_id sequence numbers are unique within that column's CCI set for this row. |
| **VER-3b-08** | CellContentItemRegister contains all ci_id values for this row | Query register: member_ids must include every CCI.ci_id where CCI.cell_id.row = str(row_ref). |
| **VER-3b-09** | AnalysisPass exists with mechanism="CellContentItemConstruction" and row_ref = current_row | Query AnalysisPass by mechanism string and row_ref. |
| **VER-3b-10** | Every Signal in the eligible set either grounds at least one CCI or appears in AnalysisPass integrity_violations | For each Signal in the Step 1 working set: signal_id appears in at least one CCI.signal_refs, OR signal_id appears in AnalysisPass.outputs.cci_data.integrity_violations. Non-Loss check. |

### 8.2 Plausibility criteria (Practitioner review)

| **ID** | **Criterion** | **Review guidance** |
| --- | --- | --- |
| **PLB-3b-01** | CCI descriptions are derived statements, not verbatim copies of Signal descriptions | Spot-check: select 5 CCIs and compare descriptions to the Signal descriptions in their signal_refs. Descriptions should be re-expressed, not copied. |
| **PLB-3b-02** | classification_type assignments are appropriate for the column and row abstraction level | Spot-check: for each populated cell, review 2–3 CCIs and assess whether the classification_type fits the column's interrogative and the row's abstraction level. |
| **PLB-3b-03** | Merged CCIs' descriptions capture the combined meaning of both merged candidates | Review merges listed in AnalysisPass.outputs.cci_data.merges. For each merge, check that the surviving description reflects the content of both original descriptions. |
| **PLB-3b-04** | Consolidation flags (where present) represent genuine deduplication, not over-aggressive merging | For each consolidation-flagged cell, review a sample of the surviving CCIs and compare to the Signal set for that cell. Assess whether distinct content was lost. |

---

## 9. Edge Cases

### 9.1 A batch produces no valid CCIs

If Stage 3c rejects all candidates from a batch (all fail Pydantic validation or vocabulary checks), that batch contributes no CCIs. The AnalysisPass records the rejection count in `candidates_rejected`. Other batches are unaffected. If all batches produce no valid candidates, all six ZachmanCells remain empty. Phase 5 will surface as coverage findings. Not a Pass 3b failure unless all batches fail due to AI error.

### 9.2 No eligible Signals (Signal set is empty)

If the Step 1 query returns zero Signals (e.g. all Pass 3a content was blocked by open Concerns), Step 2b produces no batches. Step 3 is skipped. All six ZachmanCells are still upserted in Step 2a. Zero CCIs are produced. AnalysisPass records `ccis_created = 0`. execution_status = Completed (not Failed — zero CCIs is a valid outcome; Phase 5 and Phase 9 surface the coverage implications).

### 9.3 Re-run with no new Signals

If re-run after a Phase 10 resolution but the Signal set is unchanged (Concern resolved but produced no new Signal, e.g. Dispositioned), Step 3 produces no new candidates. Step 4 finds no new candidates to deduplicate. Step 5 produces no new CCIs and no updates to existing CCIs. AnalysisPass records `ccis_created = 0`, `ccis_merged = 0`. execution_status = Completed.

### 9.4 Signal referencing an Open Concern

Detected in Step 1. Signal is excluded from the working set. Recorded in `outputs.cci_data.integrity_violations`. This is a data integrity condition — it means Pass 3a produced a Signal with a non-null `derived_from_concern_id` pointing to an Open Concern, which violates the mutual exclusion rule. The AnalysisPass records it for audit; execution continues with the remaining valid Signals.

### 9.5 AI invocation failure during Stage 3a or 4b

If the Claude API call fails (network error, rate limit, timeout):
- Retry up to 3 times with exponential backoff (1s, 2s, 4s delays).
- If all retries fail for a batch (Stage 3a): that batch produces no candidates. Signals in that batch are recorded in AnalysisPass failure detail as unprocessed. They are not recorded in `integrity_violations` — this is a mechanism execution failure, not a data integrity condition.
- If all retries fail for a Stage 4b semantic review invocation: the affected candidates survive without AI deduplication — they proceed to Step 5 as if all verdicts were Distinct. This is conservative (may produce more CCIs than necessary) but preserves Non-Loss.
- execution_status = CompletedWithWarnings if some batches / deduplication calls succeeded; Failed if all Stage 3a invocations failed.

### 9.6 Over-aggressive consolidation detection

If a cell's candidate count reduces by more than `ProjectProfile.cci_consolidation_threshold` (default 0.80) during Step 4, the consolidation flag is recorded in AnalysisPass `outputs.cci_data.consolidation_flags`. This is a Robustness observation, not an error. The surviving CCIs are committed normally. Practitioner may review and use Phase 10 to surface additional CCIs if distinct content was incorrectly merged.

---

## 10. Cross-Mechanism Interactions

### 10.1 Upstream mechanisms (this mechanism consumes from)

| **Mechanism** | **What this mechanism receives** | **Dependency type** |
| --- | --- | --- |
| **Pass 3a — Row-Lens Source Re-Analysis** | Signal entities — the eligible Signal set is the sole analytical input. Concern-blocked content excluded. | Hard prerequisite — Pass 3a MUST complete with execution_status ∈ {Completed, CompletedWithWarnings} before Pass 3b begins. |
| **Phase 2 — Mechanism Activation** | ProjectProfile — provides `cci_consolidation_threshold` and other configuration parameters. | Soft prerequisite — Phase 2 MUST be complete; ProjectProfile stable. |

### 10.2 Downstream mechanisms (this mechanism feeds into)

| **Mechanism** | **What this mechanism produces for it** | **Dependency type** |
| --- | --- | --- |
| **Pass 3c — Domain Derivation** | CellContentItem entities — the full CCI set for the row is the sole input to Pass 3c. | Hard dependency — Pass 3c cannot begin until Pass 3b has completed. |
| **Pass 3d — Requirement Derivation** | CellContentItem entities — Pass 3d consumes CCIs indirectly via Domains from Pass 3c. | Indirect dependency via Pass 3c. |
| **Phase 5 — Cell Quality Analysis** | ZachmanCell entities and CellContentItem entities — Phase 5 evaluates cell population and coverage patterns. Empty cells surfaced as coverage findings here. | Analytical dependency — Phase 5 consumes Pass 3b outputs. |

### 10.3 Deferred mechanism interactions

| **Mechanism** | **Deferral rationale** |
| --- | --- |
| **Robustness mechanism — Phase 5** | Behavioural-structural boundary analysis (§8.12) deferred to Phase 5 where full cross-cell context is available (F40). |
| **Safety mechanism** | CCI-level threat evaluation deferred to designated Safety mechanism activation phases (F41). |
| **Cyber Security mechanism** | CCI-level threat evaluation deferred to designated Cyber Security mechanism activation phases (F41). |

---

## 11. Build Notes

### 11.1 Findings carried forward to tracker

| **Finding** | **Status** | **Relevance to this mechanism** |
| --- | --- | --- |
| **F40** | Open | §8.12 Behaviour-Structure Boundary Preservation incorrectly positioned at Pass 3b in Row 2 v1.1 / Row 3 v1.1 Understanding. Boundary analysis deferred to Phase 5 Robustness. Pass 3b does NOT produce boundary candidate CCIs. Row 2 / Row 3 Understanding amendment required. |
| **F41** | Open | Safety/CyberSec mechanism evaluation incorrectly positioned at Pass 3b in Row 2 v1.1 §3.9.3. Inline mechanism evaluation deferred to designated mechanism activation phases. Pass 3b does NOT produce Risk entities. Row 2 / Row 3 Understanding amendment required. |

### 11.2 Open questions

**OQ-3b-01 — RESOLVED v0.2.** Signal `column` attribute: v0.1 specified that Signals would be grouped by column in Step 2b, implying a `column` field on the Signal entity. This field does not exist in canonical ledger spec v2.12 and was not specified by any Pass 3a mechanism spec. The attribute was referenced without specification grounding — an authoring error. Resolution: remove pre-grouping entirely. The AI assigns `column` as part of the CCI derivation act (Stage 3a), and the response schema includes `column` as a first-class field. No Signal schema change required. Batch processing replaces per-column grouping; cross-batch duplicates are caught by the existing Step 4 deduplication sweep.

### 11.3 Template observations

This spec follows the 11-section structure established by Row-Lens Source Re-Analysis v0.3. Deviations:
- §4.1 Merge Rule is an additional sub-section referenced by Step 4 — needed because the merge logic is referenced from multiple stages and benefits from a single canonical definition.
- §5 Column Vocabulary is new relative to the Row-Lens Source Re-Analysis template — Pass 3b introduces per-column classification vocabulary that is mechanism-specific and must be explicitly specified.
- §9 Edge cases includes re-run scenarios more prominently than previous specs, reflecting the re-run-aware design of Steps 4 and 5.

---

## Document End

End of SysEngage Row 3 Mechanism: CellContentItem Construction v0.2.

Changes from v0.1: batch processing model replacing per-column grouping; Signal `column` attribute dependency removed; AI assigns column as part of derivation act; response schema gains `column` field; OQ-3b-01 resolved.

Companion artefacts produced with this spec:
- SysEngage_Row_4_Understanding_v0_3.md — Row 4 Understanding additions for Pass 3b (updated to v0.2 content)
- SysEngage_Row_4_Mechanism_CCI_Construction_v0_2.md — Row 4 implementation specification
- SysEngage_Issues_Tracker_v0_27.md — tracker current state
