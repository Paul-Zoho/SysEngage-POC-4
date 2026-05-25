# SysEngage Row 4 Mechanism: CellContentItem Construction

**Implementation specification — depth tier (i)+**

Filename: SysEngage_Row_4_Mechanism_CCI_Construction_v0_15.md

Version: 0.15 (column_interrogatives.py — named-instance instruction for Where column at Rows 4 and 5)

Date: 16 May 2026

**Purpose.** Implementation specification for the CellContentItem Construction mechanism (Pass 3b). v0.15 tightens Stage 3a-pre criteria 2 and 3 to eliminate false positive splits on verbs, adjectives, and common nouns, and adds a diagnostic logging requirement to Stage 4b for `stage4a_routed` groups.

**Excludes.** Per Row 4 Understanding §8.1: NO pseudo-code, NO function signatures, NO code-level interface definitions.

---

## 1. Mechanism Identification

| **Mechanism name** | CellContentItem Construction |
| --- | --- |
| **Row 3 Mechanism Spec reference** | SysEngage_Row_3_Mechanism_CCI_Construction_v0_14.md — all sections |
| **Operational location** | Phase 3 Pass 3b. Executes after Pass 3a completes; before Pass 3c. Six steps: Step 1 (Signal query, DM), Step 2 (ZachmanCell upsert + batch partitioning, DM), Step 3 (per-batch CCI derivation, IM+DM), Step 4 (per-cell deduplication, DM+IM+DM), Step 5 (identifier allocation + commit, DM), Step 6 (AnalysisPass production, DM). |
| **Mechanism class** | AI-involving. IM for derivation acts (Stage 3a, Stage 4b). DM for all other stages, entity production, and ledger writes. LPM preservation constraint throughout. |
| **Module location** | `mechanisms/cci_construction/` directory. See §3.1 for file structure. |
| **Row applicability** | Row-sequential. Six ZachmanCells always upserted regardless of Signal population. Empty cells are valid outputs. |
| **Mechanism Stakeholder** | None. SH001 covers structural review. SG-01 covers Practitioner quality review. SG-03 carries execution attribution via AnalysisPass. |

---

## 2. Cross-References

| **Source** | **Reference** | **What this provides** |
| --- | --- | --- |
| **Row 3 Mechanism Spec v0.14** | All sections | Architectural spec including tightened Stage 3a-pre criteria and Stage 4b diagnostic logging |
| **Row 4 Understanding v0.4** | §12 | Pass 3b implementation framework: batch processing pattern, Signal-to-CCI derivation pattern (all-column prompt), deduplication pattern, re-run-aware commit pattern, module structure |
| **Row 4 Understanding v0.2** | §9.4 Prompt Architecture Pattern | Prompt template registry, parameterisation contract, response schema, Pydantic validation at boundary |
| **Row 4 Understanding v0.2** | §9.5 Non-Determinism Handling | Decidable vs plausibility split; re-run semantics; AI model fingerprinting |
| **Row 4 Applied v0.2** | All sections | Common architectural commitments: Python 3.12+, FastAPI, Neon PostgreSQL via SQLAlchemy + Alembic, Pydantic v2, Claude Sonnet via Anthropic API, pytest, transactional discipline |
| **Canonical Ledger v2.12** | ZachmanCell, CellContentItem, AnalysisPass element types | Authoritative schemas. Pydantic models in schemas/ mirror these. |
| **Tracker v0.27** | F40, F41 | F40: boundary analysis deferred to Phase 5. F41: Safety/CyberSec deferred to designated phases. Pass 3b produces neither boundary candidates nor Risk entities. |

---

## 3. Architectural Approach

### 3.1 Module structure

```
mechanisms/cci_construction/
  __init__.py                            # Orchestration entry point — Steps 1–6
  step1_signal_assembly.py               # DM: eligible Signal query
  step2_zachman_cell_upsert.py           # DM: ZachmanCell upsert + batch partitioning
  step3_cci_derivation.py                # DM pre-processor + IM+DM: enumeration split + AI derivation + entity production
  step4_deduplication.py                 # DM+IM+DM: per-cell structural pre-filter + AI cluster review + merge
  step5_commit.py                        # DM: identifier allocation + ledger write
  step6_analysis_pass.py                 # DM: AnalysisPass record production
  prompts/
    cci_derivation_prompt.py             # Template: per-batch Signal-to-CCI derivation (all 6 columns)
    dedup_cluster_review_prompt.py       # Template: per-cell cluster-based deduplication review
    column_interrogatives.py             # Row × Column framing table — named-instance instruction removed v0.13
    column_vocabulary.py                 # Permitted classification_type values per column
    named_entity_vocabulary.py           # Named entity vocabulary for Stage 3a-pre heuristic detection
  schemas/
    cci_construction_response_schema.py  # Pydantic: AI derivation response (includes column field)
    dedup_cluster_review_response_schema.py  # Pydantic: AI cluster review response
```

### 3.2 Major design decisions

- **ZachmanCell composite primary key `(cell_id, project_id)`** — ZachmanCell is project-scoped. Using `cell_id` alone as PK causes silent cross-project data corruption: a second project's Step 2a upsert hits ON CONFLICT DO NOTHING and inherits the first project's row with the wrong `project_id`. The composite PK `(cell_id, project_id)` is the correct design, mirroring `CellContentItemModel`. The upsert conflict target is `(cell_id, project_id)`.

- **CellContentItem FK is a cascading composite reference** — `CellContentItemModel.cell_id` FKs into `zachman_cell`. Once ZachmanCell PK becomes composite `(cell_id, project_id)`, the FK on CCI must reference both columns. Since CCIs already carry `project_id`, the constraint is naturally satisfiable — it enforces that a CCI can only reference a ZachmanCell owned by the same project.

- **`stage4a_similarity_threshold` ProjectProfile parameter** — Stage 4a description similarity check uses this threshold (default 0.60). Read from ProjectProfile at mechanism invocation time. Stored as a float 0.0–1.0 in the ProjectProfile table alongside `cci_batch_size` and `cci_consolidation_threshold`.

### 3.5 column_interrogatives.py — Named-Instance Additions (v0.12)

`prompts/column_interrogatives.py` maps `{row_ref: {column: interrogative_framing}}`. v0.12 adds named-instance instruction to the Where column entries for rows 4 and 5.

The existing Where column framing for rows 4 and 5 describes physical nodes, infrastructure, and deployment contexts. Append the following paragraph to the Where column entry for **row 4** and **row 5** only:

```
NAMED DEPLOYMENT TARGETS: When a Signal describes multiple named platforms,
operating systems, or infrastructure components (e.g. iOS, Android, Windows;
AWS, Azure, GCP; Server A, Server B), produce ONE CCI per named target.
Do not consolidate named targets into a single aggregate CCI description.
Each named target is a distinct physical node that may have different
constraints, costs, or compatibility requirements downstream.

Example: a Signal describing 'iOS, Android, and Windows deployment' produces:
  - Node CCI: "iOS mobile platform deployment node"  (signal_refs: [SG_X])
  - Node CCI: "Android mobile platform deployment node"  (signal_refs: [SG_X])
  - Node CCI: "Windows desktop platform deployment node"  (signal_refs: [SG_X])

Do NOT produce: "Multi-platform deployment supporting iOS, Android, and Windows"
```

This addition applies ONLY to rows 4 and 5 Where column entries. Rows 1, 2, and 3 do not receive this instruction — at those abstraction levels, Where content is conceptual or logical and named-instance consolidation is not the primary risk.

**Verification:** After applying this update, Stage 3a for Row 4 or 5 batches containing SG545 (or equivalent Signal describing multiple named platforms) should produce three separate Node CCIs — one per named platform — each with `signal_refs: ['SG545']`. The `stage4a_named_instance_routed` warning in execution_warnings confirms Stage 4a detected the group; the cluster review outcome confirms Stage 4b preserved all three.

- **Cross-batch deduplication via Step 4** — because all batches present all six columns, two batches may independently derive the same CCI. This is expected and harmless — Step 4's per-cell deduplication sweep (structural pre-filter + AI semantic review) catches cross-batch duplicates using the same mechanism as cross-stream duplicates.

- **AI invocations outside the transaction** — Stage 3a and Stage 4b AI calls are made before the Postgres transaction opens. Results held in memory. The transaction writes only the validated, deterministic entity set.

- **Per-cell AI invocation** — one AI call per populated cell in Stage 3a; one AI call per populated cell in Stage 4b (if candidates require semantic review). Cells are processed independently — a Stage 3a failure for one cell does not block other cells.

- **Re-run-aware deduplication** — Stage 4b reads existing committed CCIs for the cell from the ledger and includes them in the semantic review. New candidates are only committed if they survive deduplication against both other new candidates and existing CCIs.

- **Immutable existing CCIs** — existing `ci_id` values are never changed. On re-run, existing CCIs may be updated in-place (signal_refs, confidence, description) but their identifiers are permanent.

- **Sequence continuity across re-runs** — new CCI identifier sequences continue from the ledger's current maximum for each cell. Sequence numbers are never reset.

- **Column vocabulary enforced at entity production boundary** — `classification_type` values are validated against `column_vocabulary.py` at Stage 3b, not left to AI discretion alone. AI responses containing out-of-vocabulary classification_types are rejected at the Pydantic boundary.

### 3.3 Dependencies

- **Claude Sonnet via Anthropic API** — per Row 4 Applied AI Model commitment. Used in Stage 3a (CCI derivation) and Stage 4b (semantic deduplication review).
- **SQLAlchemy 2.x** — ORM for entity persistence.
- **Pydantic v2** — entity validation and AI response schema validation.
- **anthropic Python SDK** — API client for Claude invocations.
- **Standard library** — typing, dataclasses for support.

### 3.4 Schema Requirements (v0.3 additions)

**Migration required (additive — new migration file, e.g. `007_zachman_cell_composite_pk.py`):**

```sql
-- Step 1: Drop existing single-column PK
ALTER TABLE zachman_cell DROP CONSTRAINT zachman_cell_pkey;

-- Step 2: Add composite PK
ALTER TABLE zachman_cell ADD PRIMARY KEY (cell_id, project_id);

-- Step 3: Update CellContentItem FK to composite reference
-- (exact SQL depends on existing FK constraint name — check information_schema)
ALTER TABLE cell_content_item
  DROP CONSTRAINT cell_content_item_cell_id_fkey,
  ADD CONSTRAINT cell_content_item_cell_fk
    FOREIGN KEY (cell_id, project_id)
    REFERENCES zachman_cell (cell_id, project_id);
```

**Existing test data:** Any `zachman_cell` rows written before this migration may have `project_id` pointing at the wrong project. Clear or re-verify test data after migration.

**db_reader fix:** Once ZachmanCells are correctly project-scoped, the db_reader filter `ZachmanCellModel.project_id == project_id` works correctly. Remove any CCI-reference workaround that was added to compensate for the broken scoping — if the workaround is still needed after migration, the scoping is still broken.

---

## 4. Step-by-Step Implementation

### 4.1 Step 1 — Assemble Eligible Signal Set

**Mode:** DM. No AI involvement. No ledger write.

**Query logic:**
- SELECT all Signal entities WHERE `row_target = str(row_ref)`
- For each Signal WHERE `derived_from_concern_id IS NOT NULL`: verify referenced Concern has `state = 'Resolved'`. If state ≠ 'Resolved' (Open or Dispositioned): exclude Signal from working set; record `{signal_id, concern_id}` in `integrity_violations` buffer.
- Order result by `signal_id` ASC for determinism.

**Output:** In-memory Signal list (the eligible working set). Count recorded for AnalysisPass.

**Edge cases:**
- Zero eligible Signals: working set is empty. Step 3 will be skipped for all cells. Six ZachmanCells still upserted in Step 2.
- All Signals reference Open Concerns: working set is empty; all excluded Signals appear in integrity_violations.

---

### 4.2 Step 2 — Upsert ZachmanCells and Partition Signals into Batches

**Mode:** DM. No AI involvement. Ledger write (ZachmanCell upsert, committed in own short transaction before main mechanism transaction).

**Step 2a — ZachmanCell upsert:**

For each column in `[What, How, Where, Who, When, Why]`:
- Construct `cell_id = f"ZC-R{row_ref}-C-{column}"`
- UPSERT into ZachmanCell table with conflict target `(cell_id, project_id)`:
  ```sql
  INSERT INTO zachman_cell (cell_id, project_id, row_target, column)
  VALUES (?, ?, ?, ?)
  ON CONFLICT (cell_id, project_id) DO NOTHING
  ```
- This is unconditional — every column is upserted regardless of Signal population or AI output. Do not gate the upsert loop on any condition.
- After all six upserts: UPDATE ZachmanCellRegister `member_ids` to include all six cell_ids (idempotent set union, scoped to this project).

Commit this short transaction immediately before the main mechanism transaction opens. Rationale: ZachmanCells must exist for referential integrity on CCI INSERT in Step 5; if the main transaction rolls back, ZachmanCells remain (idempotent, correct).

**Step 2b — Batch partitioning:**

Partition the eligible Signal working set (ordered by `signal_id` ASC) into batches of size `ProjectProfile.cci_batch_size` (default 20). The final batch may be smaller. Store as an ordered list of Signal lists.

If Signal working set is empty: produce zero batches. Step 3 is skipped. Proceed to Step 4 (which finds no candidates), then Steps 5 and 6.

**Output:** Six ZachmanCells committed to ledger. Ordered batch list held in memory.

---

### 4.3 Step 3 — Per-Batch CCI Construction

**Mode:** DM (Stage 3a-pre) + IM (Stage 3a) + DM (Stage 3b, 3c). Per-batch iteration. Ledger write deferred to Step 5.

For each batch in the ordered batch list from Step 2:

**Stage 3a-pre — Named-item enumeration pre-processor (DM):**

Before calling the AI, scan each Signal in the batch using the heuristic enumeration detector. All five detection criteria must be satisfied for a Signal to be split (see Row 3 Mechanism Spec §4 Stage 3a-pre for full criteria):

1. Enumeration pattern detected (comma/conjunction list, items 1–4 words each)
2. Items are proper nouns or named entities (capitalisation check + `named_entity_vocabulary.py`)
3. Category homogeneity (all items same semantic class — platform names, location names, actor names etc.)
4. Column context supports named instances (Where, Who, or What column most likely; not Why/When/How)
5. List length 2–10

**When all criteria are satisfied:** Replace the original Signal in the batch with N virtual sub-signals (one per detected item), each carrying `signal_refs: [original_signal_id]` and a scoped description. Record the split in `enumeration_splits` buffer: `{original_signal_id, item_count, items: [str]}`.

The five criteria per Row 3 Mechanism Spec §4 Stage 3a-pre. **Criteria 2 and 3 tightened in v0.14/v0.15:**

**Criterion 2 — Proper nouns or named entities (tightened):** Each list item must satisfy ALL of:
- Starts with a capital letter, AND
- Is present in `named_entity_vocabulary.py` OR is a proper noun (NNP/NNPS part-of-speech tag)
- Is NOT a verb in any tense ("Captures", "Mandates", "Enables")
- Is NOT an adjective ("Historical", "Available", "Completed")
- Is NOT a generic common noun without named-entity vocabulary entry ("task", "data", "record", "item")

If any item in the list fails, the entire Signal is not split.

**Criterion 3 — Category homogeneity (tightened):** All items must be mappable to a single shared named-entity category in `named_entity_vocabulary.py`. Items not in the vocabulary cannot satisfy homogeneity — their absence is disqualifying.

**`named_entity_vocabulary.py` content guidance:** The vocabulary must include at minimum: platform names (iOS, Android, Windows, macOS, Linux, iPadOS), cloud providers (AWS, Azure, GCP), common geographic proper nouns, common role/actor proper nouns. The vocabulary is extensible — items can be added as new project inputs reveal new named-entity types. Do not add generic common nouns, verbs, or adjectives to the vocabulary.

**When any criterion fails:** Signal passes through unchanged.

The expanded batch (sub-signals replacing split Signals, unsplit Signals unchanged) is the input to Stage 3a.

**Stage 3a — AI derivation (IM):**

Construct prompt from `cci_derivation_prompt.py` with parameters:
- `row_ref`: integer
- `all_column_interrogatives`: the full six-column framing for this row (from `column_interrogatives.py[row_ref]`)
- `all_column_vocabularies`: dict of permitted classification_type values per column (from `column_vocabulary.py`)
- `signals`: list of `{signal_id, description, signal_type, confidence}` for this batch

Call Claude Sonnet API. Record AI model version fingerprint.

Parse response against `cci_construction_response_schema.py`. The schema includes `column` as a required field:
```json
{
  "items": [
    {
      "column": "What|How|Where|Who|When|Why",
      "classification_type": "string",
      "description": "string",
      "signal_refs": ["string"],
      "confidence": 0.0,
      "trigger_condition": "string or null",
      "justification": "string or null"
    }
  ]
}
```

Validation failure: record malformed items in `candidates_rejected` buffer; proceed with valid items (PartialSuccess for this batch).

**Stage 3b — Entity production (DM):**

For each valid AI response item:
- Validate `column` is in `{What, How, Where, Who, When, Why}` — reject if not; record in `candidates_rejected`
- Validate `classification_type` is in `column_vocabulary.py[column]` — reject if not; record in `candidates_rejected`
- Validate `signal_refs` non-empty — reject if empty; record in `candidates_rejected`
- Validate `confidence` ∈ [0.0, 1.0] — reject; record if outside range
- Validate `description` non-empty — reject; record if empty
- Construct candidate CCI struct: `{cell_id=f"ZC-R{row_ref}-C-{column}", classification_type, description, signal_refs, confidence, trigger_condition, justification}`

**Stage 3c — Pydantic validation (DM):**

Apply `CCICandidateModel` validation. Additional cross-field validations:
- Each `signal_refs` entry must resolve to a Signal in the current working set
- `cell_id` must match a valid ZachmanCell for the current row

Malformed candidates recorded in `candidates_rejected`. Valid candidates added to the global candidate buffer (across all batches).

**AI failure handling:**
- Retry up to 3 times with exponential backoff (1s, 2s, 4s).
- If all retries fail for a batch: that batch produces no candidates. Signals in the batch recorded in AnalysisPass failure detail as unprocessed. Continue to next batch.
- execution_status = CompletedWithWarnings if some batches succeeded; Failed if all batches failed.

---

### 4.4 Step 4 — Per-Cell Deduplication Sweep

**Mode:** DM (Stage 4a) + IM (Stage 4b) + DM (Stage 4c). Per-cell iteration across the global candidate buffer from Step 3. No ledger write (merge execution updates in-memory structs and populates update buffer).

After all batches in Step 3 have been processed, group the global candidate buffer by `cell_id`. For each cell that has candidates:

**Stage 4a — Structural pre-filter (DM):**

For each pair of candidates in the buffer, evaluate three conditions:

1. `classification_type` match: string equality
2. `signal_refs` match: set equality (`set(a.signal_refs) == set(b.signal_refs)`)
3. Description similarity: token overlap ≥ `ProjectProfile.stage4a_similarity_threshold` (default 0.60)

**Similarity calculation (DM):** Tokenise each description by splitting on whitespace and punctuation, lowercasing, and removing common English stopwords. Compute the Jaccard similarity of the two token sets: `|intersection| / |union|`. If the result is ≥ the threshold, descriptions are materially similar.

**Routing rules:**
- All three conditions hold → structural duplicate. Apply merge rule (§4.4.1). Remove the lower-confidence candidate; update the higher-confidence candidate's struct.
- Conditions 1 and 2 hold, condition 3 does not → materially different descriptions despite same type and refs. Route both candidates to Stage 4b by including them in the cell's Stage 4b working set. Do not merge at Stage 4a.
- Condition 1 alone holds → Stage 4b handles normally.

Process all pairs exhaustively before proceeding (N² comparison — acceptable for expected CCI counts per cell).

**Stage 4b — AI cluster review (IM):**

**Connection handling:** Acquire a fresh database connection for the existing CCI read — do not reuse any connection held open since Step 3. Execute: SELECT all CCIs WHERE `cell_id = current_cell_id AND project_id = current_project_id`. If the query raises a connection or operational error: retry up to 3 times with 1s/2s/4s backoff. If all retries fail: set `existing_ccis = []`; add `{warning_type: "step4_read_failure", detail: {cell_id: current_cell_id}}` to the `execution_warnings` buffer; proceed with new candidates only.

**NoneType guard:** Before entering the cluster review, validate every item in the combined set (new candidates + existing CCIs). Any item that is None or lacks a `confidence` attribute is excluded from the cluster review; add `{warning_type: "step4_nonetype_excluded", detail: {cell_id: current_cell_id, ci_id_or_ref: item_ref}}` to the `execution_warnings` buffer. Do not allow a NoneType to reach Stage 4b or 4c logic.

Combine surviving new candidates and existing CCIs. Group by `classification_type`. For each group with more than one member:

**Stage 4a routing context:** When Stage 4a routes a candidate pair to Stage 4b because condition 3 failed (dissimilar descriptions despite matching type and signal_refs), mark those candidates with `stage4a_routed=True` on their in-memory struct before passing to Stage 4b.

For each group, check whether any candidates carry `stage4a_routed=True`:
- If **any member** of the group carries `stage4a_routed=True` (whether a new candidate or an existing CCI): use the **named-instance preservation directive** variant of `dedup_cluster_review_prompt.py` for the entire group. The prompt instructs the AI: "Stage 4a has determined that these items are confirmed distinct named instances derived from the same Signal. They share the same classification type and signal_refs but have materially different descriptions. You MUST return ALL items as Distinct. Do not merge any of them regardless of semantic similarity. The distinctness is a structural fact established by the derivation process, not a judgment you are being asked to make." Record `stage4a_named_instance_routed` in `execution_warnings`. The AI's latitude to merge is removed for these groups.

  **Diagnostic logging — REQUIRED until OQ-3b-11 is resolved:** For any group entering this branch, the implementation MUST write the following to the mechanism's structured debug log before calling the AI and after receiving the response:
  ```
  [STAGE4B_DIAGNOSTIC] cell_id={cell_id} classification_type={ctype} member_count={n}
  [STAGE4B_PROMPT] {full prompt text as sent to Claude API}
  [STAGE4B_RESPONSE] {raw AI response JSON as received}
  [STAGE4B_VERDICT] surviving_ci_id={id} merge_applied={true|false}
  ```
  The diagnostic log must be written to a retrievable location (stdout, a named log file, or the test run output). It must capture the exact prompt sent and the exact JSON response received — not a summary or paraphrase. This is required to resolve OQ-3b-11: determine whether the AI is returning Duplicate despite the directive (prompt failure) or returning Distinct but Stage 4c applies a merge anyway (implementation bug). Once OQ-3b-11 is resolved, diagnostic logging may be removed.

- If no member carries `stage4a_routed=True`: standard cluster review prompt — identify semantic duplicates across different Signals.

Make **one AI call per group** (or sub-group) using `dedup_cluster_review_prompt.py`:

**Group-size cap:** If a group contains more than 50 members, split into sub-groups of 50 before calling the AI. After all sub-groups are reviewed, apply Stage 4c across all results. Record `step4_sub_group_split` in `execution_warnings`.
- `cell_id` and `column` interrogative context
- All group members: `{ref, source, description, signal_refs, confidence}` where `source ∈ {"new_candidate", "existing_cci"}`
- Instruction: identify clusters of semantically equivalent items; provide a representative description per cluster; flag uncertain equivalences as Ambiguous

Parse response against `dedup_cluster_review_response_schema.py`:
```json
{
  "clusters": [
    {
      "member_refs": ["ref_a", "ref_b"],
      "verdict": "Duplicate",
      "representative_description": "string",
      "rationale": "string"
    }
  ],
  "ambiguous": [
    {
      "member_refs": ["ref_c", "ref_d"],
      "rationale": "string"
    }
  ]
}
```

Items not in any `clusters` or `ambiguous` entry are Distinct — no action required.
Groups with only one member skip the AI call — Distinct by definition.

Call Claude Sonnet API. Record AI model version fingerprint.

**Stage 4c — Merge execution (DM):**

For each `Duplicate` cluster:
- If all members are new candidates: produce one merged candidate struct; discard all others. Apply merge rule (§4.4.1). Record in merges buffer with all original descriptions.
- If one or more members are existing CCIs: retain the existing CCI with the highest confidence. UPDATE its `signal_refs` (union of all members), `confidence` (max of all members), `description` (AI's `representative_description` if non-null). All new candidate members discarded — not committed as new entities. Record in merges buffer.

For each `Ambiguous` entry:
- All listed members survive. Reduce each member's confidence by 0.1 (floor 0.0). Record in consolidation_flags.

**Consolidation threshold check (DM):**

After all verdicts applied: compute `ratio = (candidates_in - surviving_new_candidates) / candidates_in`. If ratio > `ProjectProfile.cci_consolidation_threshold` (default 0.80): record in consolidation_flags buffer.

#### 4.4.1 Merge Rule (DM)

Applied in Stage 4a (structural pre-filter) and Stage 4c (cluster merge execution):

| **Attribute** | **Merge outcome** |
| --- | --- |
| `ci_id` | Existing CCI's id preserved. New candidates in a cluster have no ci_id yet. |
| `signal_refs` | `sorted(list(set.union(*[set(m.signal_refs) for m in cluster_members])))` |
| `confidence` | `max(m.confidence for m in cluster_members)` |
| `description` | AI's `representative_description` if non-null; else description from highest-confidence member. |
| `classification_type` | Unchanged — must match across cluster (enforced by grouping). |
| `trigger_condition` | Highest-confidence member's value; whichever has it if only one does; null if none. |
| `justification` | Concatenate all non-null values with `" | "` separator. |

---

### 4.5 Step 5 — Assign Identifiers and Commit

**Mode:** DM. No AI involvement. Ledger write (all Pass 3b entity writes).

**Transaction boundary opens here.**

**Identifier allocation for new CCIs:**

For each column with surviving new candidate CCIs:
- Query: `SELECT MAX(sequence_number) FROM cci WHERE cell_id = 'ZC-R{row}-C-{column}'`
  - Parse sequence number from existing ci_ids: the trailing `\d{3}` segment
  - If no existing CCIs: max = 0
- Allocate: for each new candidate in column order, assign ci_id = `f"CCI-ROW{row_ref}-C-{column}-{str(next_seq).zfill(3)}"` incrementing from `max + 1`.

**Write operations:**

1. INSERT new CCIs: one row per surviving new candidate (not merged into existing). All attributes from candidate struct plus newly allocated `ci_id`.

2. UPDATE existing CCIs that received merges: for each ci_id in the "merge-into-existing" buffer: UPDATE `signal_refs`, `confidence`, `description` WHERE `ci_id = ?`. No INSERT — the existing row is updated in-place.

3. UPDATE CellContentItemRegister: add all newly INSERTed ci_ids to `member_ids`. UPDATE operations on existing CCIs do not change the register.

**Schema validation:** Each candidate struct is validated against the canonical CCI Pydantic model before INSERT. Validation failure: record in `candidates_rejected`; skip INSERT; continue with remaining candidates.

**Transaction commits here.** If any write fails: full rollback; execution_status = Failed; AnalysisPass records failure.

---

### 4.6 Step 6 — AnalysisPass Record Production

**Mode:** DM. Fully deterministic. Runs after Step 5 transaction commits.

Construct and INSERT AnalysisPass with:

```python
{
    "pass_id": next_p_sequence(),
    "pass_type": "Per-row",
    "mechanism": "CellContentItemConstruction",
    "execution_status": computed_status,
    "mode_active": "DM",
    "declared_transformation_modes": ["IM", "DM"],
    "outputs": {
        "cci_data": {
            "row_ref": row_ref,
            "batches_processed": count_of_batches_attempted,
            "batches_failed": count_of_batches_with_all_retries_exhausted,
            "cells_populated": count_of_cells_with_at_least_one_cci,
            "cells_empty": 6 - cells_populated,
            "ccis_created": count_of_new_inserts,
            "ccis_merged": count_of_existing_cci_updates,
            "candidates_rejected": count_of_rejections_across_all_batches,
            "merges": merges_buffer,
            "consolidation_flags": consolidation_flags_buffer,
            "integrity_violations": integrity_violations_buffer,
            "execution_warnings": execution_warnings_buffer,
            "enumeration_splits": enumeration_splits_buffer  # Stage 3a-pre split records
        },
        "mode_violations": []
    },
    "pass_started_at": step1_start_timestamp,
    "pass_completed_at": now(),
    "elapsed_ms": derived,
    "ai_model_fingerprints": list_of_all_ai_model_versions_used,
    "confidence": mean(all_ai_invocation_confidences)
}
```

`execution_status` computation:
- `Completed`: all cells processed successfully; zero AI failures; zero schema failures.
- `CompletedWithWarnings`: one or more cells had AI failures or schema rejections but at least one cell succeeded and produced CCIs. Integrity violations present. Consolidation flags present.
- `Failed`: all cells failed (AI failure + all retries exhausted for every populated cell); OR Step 5 transaction rolled back.

---

## 5. Schema and Validation

### 5.1 ZachmanCell Pydantic model

Mirrors canonical ledger spec v2.12 ZachmanCell attributes:
- `cell_id` (str, pattern `^ZC-R[1-6]-C-(What|How|Where|Who|When|Why)$`)
- `row_target` (Literal["1","2","3","4","5","6"])
- `column` (Literal["What","How","Where","Who","When","Why"])

### 5.2 CellContentItem Pydantic model

Mirrors canonical ledger spec v2.12 CellContentItem attributes:
- `ci_id` (str, pattern `^CCI-ROW[1-6]-C-(What|How|Where|Who|When|Why)-\d{3}$`)
- `cell_id` (str, pattern `^ZC-R[1-6]-C-(What|How|Where|Who|When|Why)$`)
- `classification_type` (str, min_length=1) — validated against column_vocabulary at Stage 3b
- `signal_refs` (list[str], min_length=1) — each entry pattern `^SG\d{3}$`
- `description` (str, min_length=1)
- `trigger_condition` (str or None)
- `justification` (str or None)
- `confidence` (float, ge=0.0, le=1.0)

### 5.3 AI response schemas

**`cci_construction_response_schema.py`** — for Stage 3a. Includes `column` as a required field. `is_named_instance` is removed in v0.10:
```json
{
  "type": "object",
  "required": ["items"],
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["column", "classification_type", "description", "signal_refs", "confidence"],
        "properties": {
          "column": {"type": "string", "enum": ["What","How","Where","Who","When","Why"]},
          "classification_type": {"type": "string", "minLength": 1},
          "description": {"type": "string", "minLength": 1},
          "signal_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
          "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
          "trigger_condition": {"type": ["string", "null"]},
          "justification": {"type": ["string", "null"]}
        }
      }
    }
  }
}
```

**`dedup_cluster_review_response_schema.py`** — for Stage 4b (clustering):
```json
{
  "type": "object",
  "required": ["clusters", "ambiguous"],
  "properties": {
    "clusters": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["member_refs", "verdict", "representative_description", "rationale"],
        "properties": {
          "member_refs": {"type": "array", "items": {"type": "string"}, "minItems": 2},
          "verdict": {"type": "string", "enum": ["Duplicate"]},
          "representative_description": {"type": "string", "minLength": 1},
          "rationale": {"type": "string", "minLength": 1}
        }
      }
    },
    "ambiguous": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["member_refs", "rationale"],
        "properties": {
          "member_refs": {"type": "array", "items": {"type": "string"}, "minItems": 2},
          "rationale": {"type": "string", "minLength": 1}
        }
      }
    }
  }
}
```

### 5.4 Identifier conventions

- ZachmanCell: `ZC-R{row}-C-{column}` — constructed deterministically; no sequence allocation needed
- CellContentItem: `CCI-ROW{row}-C-{column}-{seq}` — `{seq}` is zero-padded 3-digit integer, scoped per ZachmanCell, continuous across re-runs
- AnalysisPass: `P###` — global sequence, same as all other mechanisms

---

## 6. Mode Discipline Realisation

Pass 3b uses the mode discipline decorator pattern established by Source Capture (Row 4 Applied §4.7). The orchestration entry point (`__init__.py`) applies the mode decorator to each step:

| **Step / Stage** | **Declared mode** | **Decorator behaviour** |
| --- | --- | --- |
| Step 1 | DM | Verifies no AI calls made; records DM on AnalysisPass |
| Step 2 | DM | Verifies no AI calls made; records DM |
| Stage 3a | IM | Records AI invocation fingerprint; LPM constraint on Signal text |
| Stage 3b | DM | Verifies entity production from AI output only; no new AI calls |
| Stage 3c | DM | Verifies schema validation only |
| Stage 4a | DM | Verifies no AI calls |
| Stage 4b | IM | Records AI invocation fingerprint |
| Stage 4c | DM | Verifies merge from AI verdicts only |
| Step 5 | DM | Verifies no AI calls; records ledger write |
| Step 6 | DM | Verifies no AI calls; AnalysisPass production |

Mode violations (an IM step making no AI calls, or a DM step making AI calls) are recorded in `AnalysisPass.outputs.mode_violations` and set execution_status = CompletedWithWarnings.

---

## 7. Audit Trail Population

See Row 3 Mechanism Spec §7 and Row 4 Understanding §12.5 for the full `outputs.cci_data` JSONB structure. The implementation MUST populate all fields in the `cci_data` sub-structure on every run, including zero-value counts (not null, not omitted). A missing field in `cci_data` is a schema conformance failure.

---

## 8. Verification Criteria

All verification criteria from Row 3 Mechanism Spec §8.1 (decidable) and §8.2 (plausibility) apply. The automated criteria (VER-3b-01 through VER-3b-10) are implemented as pytest tests in the test suite. See Row 4 Understanding §12.7 for the full test specification.

**Automated test module:** `tests/test_cci_construction.py`

Tests use the test fixtures in §9 as input data. Each test asserts one or more VER-3b-NN criteria. Tests run against the live Neon PostgreSQL test database using the same transactional pattern as production (transaction + rollback for test isolation).

---

## 9. Test Fixtures

### 9.1 Fixture 1 — Happy path: single batch, Signals spanning multiple columns

**Purpose:** Verify Step 1–6 end-to-end for a minimal case. Three Signals covering multiple columns, single batch (under batch_size threshold), CCIs produced across multiple cells.

**Pre-conditions in ledger:**
- `row_ref = 2`
- Signals present (row_target="2"):
  - SG001: description="The system tracks pocket money transactions for children", signal_type="Normative", confidence=0.85
  - SG002: description="Each child has a named account within the system", signal_type="Normative", confidence=0.90
  - SG003: description="Parents approve all transactions above a threshold amount", signal_type="Normative", confidence=0.80
- No other Signals for row 2.

**Expected outcomes:**
- VER-3b-01: 6 ZachmanCells exist for row 2
- VER-3b-09: AnalysisPass with mechanism="CellContentItemConstruction" exists for row 2
- CCIs produced across multiple columns — at minimum: What (Transaction entity, Account entity), Who (Child actor, Parent actor), Why (approval rule or threshold constraint)
- All CCIs have ci_id matching `^CCI-ROW2-C-(What|How|Where|Who|When|Why)-\d{3}$`
- All CCI.signal_refs entries resolve to SG001, SG002, or SG003
- All CCIs have classification_type within the permitted vocabulary for their column
- VER-3b-10: SG001, SG002, SG003 each appear in at least one CCI.signal_refs
- AnalysisPass.outputs.cci_data.batches_processed = 1, batches_failed = 0

### 9.2 Fixture 2 — Cross-batch deduplication: same content derived from two batches

**Purpose:** Verify that cross-batch duplicates are caught by Step 4 deduplication. Two batches each deriving the same Who-column Actor CCI from different Signals describing the same actor.

**Pre-conditions in ledger:**
- `row_ref = 2`, `ProjectProfile.cci_batch_size = 1` (forced single-Signal batches for test control)
- Signals (row_target="2"):
  - SG010: description="Parents manage the system on behalf of children", signal_type="Actor", confidence=0.88
  - SG011: description="Parents are responsible for approving pocket money requests", signal_type="Actor", confidence=0.82

**Expected outcomes:**
- Two batches processed (one Signal each)
- Both batches likely produce a "Parent" Actor CCI in the Who column
- Step 4 deduplication merges these into one CCI with signal_refs=[SG010, SG011]
- AnalysisPass.outputs.cci_data.merges is non-empty (at least one merge recorded)
- VER-3b-07: sequence numbers unique within Who cell (only one CCI survives for Parent Actor)
- VER-3b-10: both SG010 and SG011 appear in at least one CCI.signal_refs (the merged CCI)

### 9.3 Fixture 3 — Re-run: new Signal added after Phase 10 Concern resolution

**Purpose:** Verify re-run behaviour — existing CCIs preserved; new Signal produces new CCI or merges with existing.

**Pre-conditions in ledger:**
- Pass 3b has previously run for row_ref = 2
- Existing committed CCIs for ZC-R2-C-What: CCI-ROW2-C-What-001 (Entity, "Transaction", signal_refs=[SG001])
- New Signal added (Concern resolved): SG020: description="Transactions have a date, amount, and description", signal_type="Normative", confidence=0.87

**Expected outcomes:**
- CCI-ROW2-C-What-001 MUST still exist with ci_id unchanged (immutable)
- New CCI CCI-ROW2-C-What-002 (or higher seq) produced for the Attribute content from SG020 — OR SG020 merged into CCI-ROW2-C-What-001 if the AI determines it is the same content (unlikely given different content character)
- AnalysisPass.outputs.cci_data.ccis_created ≥ 0, ccis_merged ≥ 0
- VER-3b-04: SG020 appears in at least one CCI.signal_refs

### 9.4 Fixture 4 — Empty Signal set (all Concerns open)

**Purpose:** Verify graceful handling of zero eligible Signals.

**Pre-conditions in ledger:**
- `row_ref = 2`
- No Signals for row_target="2" (all blocked by Open Concerns)

**Expected outcomes:**
- VER-3b-01: 6 ZachmanCells upserted for row 2
- Zero CCIs produced
- AnalysisPass.outputs.cci_data.ccis_created = 0, cells_populated = 0, cells_empty = 6
- AnalysisPass.execution_status = "Completed" (not Failed — zero CCIs is valid)
- VER-3b-10: trivially satisfied (empty Signal set; no Signal needs grounding)

### 9.5 Fixture 5 — Multi-project isolation (VER-3b-ZC-01)

**Purpose:** Verify composite PK enforcement — two projects each get their own six ZachmanCells for the same row. The ON CONFLICT target is `(cell_id, project_id)`, not `cell_id` alone.

**Pre-conditions:**
- Two distinct project_ids: `project_A`, `project_B`
- Each has at least one Signal for `row_ref = 2` with the appropriate `project_id`

**Test sequence:**
1. Run Pass 3b for `project_A`, `row_ref = 2`
2. Run Pass 3b for `project_B`, `row_ref = 2`

**Expected outcomes (VER-3b-ZC-01):**
- `SELECT COUNT(*) FROM zachman_cell WHERE row_target='2' AND project_id='project_A'` = 6
- `SELECT COUNT(*) FROM zachman_cell WHERE row_target='2' AND project_id='project_B'` = 6
- Total ZachmanCell rows for row_target='2' = 12
- No row has `project_id` pointing at the wrong project

### 9.6 Fixture 6 — Cross-project FK integrity (VER-3b-ZC-02)

**Purpose:** Verify that the composite FK on CellContentItem prevents cross-project ZachmanCell references at the database level.

**Pre-conditions:**
- `project_A` and `project_B` both have ZachmanCells for `row_ref = 2` (from Fixture 5)
- `project_A` has committed CCIs

**Expected outcomes (VER-3b-ZC-02):**
- For all CCIs WHERE `project_id = 'project_A'`: the referenced `(cell_id, project_id)` pair resolves to a ZachmanCell WHERE `project_id = 'project_A'`
- Attempting to INSERT a CCI with `project_id='project_A'` referencing a `cell_id` that only exists under `project_B` raises a FK violation — the composite FK enforces this at the database level
- No workaround in the db_reader is required to scope ZachmanCells to the correct project

---

## 10. Edge Cases (Implementation-Level)

### 10.1 AI returns classification_type outside permitted vocabulary

Stage 3b vocabulary validation catches this. The item is added to `candidates_rejected`. The AI is not retried for vocabulary violations — the prompt template includes the permitted vocabulary explicitly. If this occurs frequently, the prompt template's vocabulary instruction should be strengthened. AnalysisPass records the rejection count; Practitioner can review in the `candidates_rejected` count.

### 10.2 AI returns signal_refs containing Signal ids not in the eligible working set

Stage 3c cross-field validation catches this. The candidate is rejected. This indicates the AI hallucinated a Signal id. Recorded in `candidates_rejected`. Not a mechanism failure — the AI boundary validation is working correctly.

### 10.3 Stage 4b deduplication produces all-Duplicate verdicts for a cell

All candidates for the cell collapse into one or a small number. Consolidation threshold check fires if ratio > 0.80. Recorded in consolidation_flags. All surviving CCIs are committed normally. Practitioner review surfaced via AnalysisPass consolidation_flags.

### 10.4 Existing committed CCIs for a cell and new candidates are all Distinct

Stage 4b produces only Distinct verdicts. No merges occur. All new candidates proceed to Step 5 as new inserts. Existing CCIs unchanged. This is the common case on a small re-run after a single Concern resolution.

### 10.5 Step 5 transaction rollback

If the Postgres transaction rolls back (constraint violation, connection failure): execution_status = Failed. AnalysisPass is produced outside the rolled-back transaction with failure detail. No CCI or ZachmanCell entity changes are committed. Mechanism may be re-run without data integrity concern — idempotent Step 2 (upsert) and re-run-aware Step 4 ensure no duplicates on re-run.

Note: ZachmanCell upserts in Step 2 are committed in their own short transaction before the main mechanism transaction opens (since they are idempotent and needed by downstream pass even if the CCI transaction fails). If Step 2 succeeds but Step 5 fails: ZachmanCells exist in ledger but no CCIs. Phase 5 will surface as coverage findings — not a data integrity problem.

### 10.6 ProjectProfile.cci_consolidation_threshold not configured

Default value 0.80 applies. This is the expected case at v1 — threshold is not yet empirically validated. Calibration of this parameter is a deferred item with no currently assigned tracker finding; it should be raised when sufficient production run data is available to make an evidence-based threshold decision.

---

## 11. Cross-Mechanism Interactions

### 11.1 Upstream

| **Mechanism** | **What this mechanism consumes** | **Dependency type** |
| --- | --- | --- |
| **Pass 3a — Row-Lens Source Re-Analysis** | Signal entities (row_target = current row); AnalysisPass(RowLensSourceReanalysis) for precondition check | Hard prerequisite — Pass 3a MUST be Completed or CompletedWithWarnings before Pass 3b begins |
| **Phase 2 completion** | ProjectProfile (cci_consolidation_threshold); Stakeholder entities | Soft prerequisite — Phase 2 MUST be complete |

### 11.2 Downstream

| **Mechanism** | **What this mechanism produces for it** | **Dependency type** |
| --- | --- | --- |
| **Pass 3c — Domain Derivation** | CellContentItem entities for the row — the complete CCI set is the sole input to Pass 3c | Hard dependency — Pass 3c cannot begin until Pass 3b completes with status ∈ {Completed, CompletedWithWarnings} |
| **Phase 5 — Cell Quality Analysis** | ZachmanCell entities (all six, including empties) + CellContentItem entities | Analytical dependency — empty cells are first-class inputs to Phase 5 coverage analysis |

### 11.3 Coordination via ledger

Per Row 4 Applied §13: mechanisms coordinate via ledger reads, not direct calls. This mechanism reads Signals and existing CCIs from the ledger; writes ZachmanCells, CCIs, and AnalysisPass in transactions at completion.

---

## 12. Build Notes

### 12.1 Findings and decisions

| **Reference** | **Status** | **Relevance** |
| --- | --- | --- |
| **F40** | Open | §8.12 boundary analysis deferred to Phase 5 Robustness. Pass 3b does NOT produce boundary candidate CCIs. Row 2/3 Understanding amendment required. |
| **F41** | Open | Safety/CyberSec evaluation deferred to designated phases. Pass 3b does NOT produce Risk entities. Row 2/3 Understanding amendment required. |
| **F42** | Open | ZachmanCellModel PK must be composite (cell_id, project_id). Surfaced by Replit Agent during Step 2a implementation. Resolved in this spec at §3.2 and §4.2. Migration and CCI FK cascading fix required. |

### 12.2 Open questions for Replit Agent build

| **OQ** | **Question** | **Recommended default** |
| --- | --- | --- |
| **RA-1** | RETIRED. Was: batch size for Stage 4b semantic review. Superseded by clustering design in v0.4 — there are no pairs to batch. The equivalent question for clustering is: what to do when a group exceeds 50 members? RESOLVED in v0.5: split into sub-groups of 50 and process as separate AI calls. Record `step4_sub_group_split` in `execution_warnings`. |
| **RA-2** | Stage 4a: process all pairs or stop on first structural duplicate per source Signal? | Process all pairs. The candidate set is small; exhaustive pairwise comparison is correct and cheap at expected sizes. |
| **RA-3** | Where to record Step 2 ZachmanCell upsert transaction boundary relative to main mechanism transaction? | Step 2 ZachmanCell upserts in their own short transaction (committed immediately). Main mechanism transaction (Step 5: CCI inserts/updates + register + AnalysisPass) committed at end. Rationale: ZachmanCells must exist for referential integrity on CCI insert; if main transaction rolls back, the ZachmanCells remain (idempotent anyway). |

### 12.3 Replit Agent task structure

The Replit Agent handoff should include:
- This Implementation Spec v0.6 (primary input)
- Row 3 Mechanism Spec v0.6 (architectural reference)
- Row 4 Understanding v0.4 §12 (implementation patterns)
- Row 4 Applied v0.2 (common foundations — technology stack, transactional discipline, mode decorator)
- Canonical Ledger v2.12 (entity schemas)
- Existing Row-Lens Source Re-Analysis implementation as reference for AI invocation pattern, Pydantic response schema, AnalysisPass population, transactional discipline

The Agent should implement `mechanisms/cci_construction/` following the established pattern of `mechanisms/row_lens_source_reanalysis/` with adaptations for:
- Per-batch AI invocation (Step 3a derivation) rather than per-chunk
- Cluster-based AI deduplication (Step 4b) rather than pairwise
- Re-run-aware deduplication (comparing new candidates to existing committed CCIs in Stage 4b)
- In-place update of existing CCIs (signal_refs, confidence, description) on merge

**Build task — file rename:** The deduplication prompt and schema files have been renamed from the v0.3 era names. The Agent must ensure the following renames are applied and the old files deleted:
- `prompts/dedup_semantic_review_prompt.py` → `prompts/dedup_cluster_review_prompt.py`
- `schemas/dedup_review_response_schema.py` → `schemas/dedup_cluster_review_response_schema.py`

---

## Document End

End of SysEngage Row 4 Mechanism: CellContentItem Construction v0.12.

Changes from v0.11: §3.5 added — concrete `column_interrogatives.py` update for Where column at rows 4 and 5, including named deployment target instruction and worked example; Row 3 spec reference updated to v0.11.

Companion artefact: SysEngage_Row_3_Mechanism_CCI_Construction_v0_14.md

---

*v0.13 replaces the above Document End. End of SysEngage Row 4 Mechanism: CellContentItem Construction v0.13.*

*Changes from v0.12: Stage 4b named-instance prompt variant changed from determination request to preservation directive — groups with `stage4a_routed=True` members receive "return ALL as Distinct" directive; Row 3 spec reference updated to v0.12.*

*Companion artefact: SysEngage_Row_3_Mechanism_CCI_Construction_v0_14.md*

---

*v0.14 replaces the above Document End. End of SysEngage Row 4 Mechanism: CellContentItem Construction v0.14.*

*Changes from v0.13: Stage 3a-pre named-item enumeration pre-processor added to §4.3; `named_entity_vocabulary.py` added to module structure §3.1; `enumeration_splits` added to AnalysisPass outputs §4.6; Row 3 spec reference updated to v0.13.*

*Companion artefact: SysEngage_Row_3_Mechanism_CCI_Construction_v0_14.md*

---

*v0.15 replaces the above Document End. End of SysEngage Row 4 Mechanism: CellContentItem Construction v0.15.*

*Changes from v0.14: Stage 3a-pre criteria 2 and 3 tightened in §4.3 — verbs, adjectives, and common nouns explicitly rejected; named_entity_vocabulary.py content guidance added; Stage 4b diagnostic logging requirement added with structured log format; Row 3 spec reference updated to v0.14.*

*Companion artefact: SysEngage_Row_3_Mechanism_CCI_Construction_v0_14.md*
