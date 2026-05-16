# SysEngage Replit Agent Task — Pass 3b: CellContentItem Construction

**Task version:** v0.1
**Date:** 16 May 2026
**Mechanism:** CellContentItem Construction (MECH-R3-004)
**Phase / Pass:** Phase 3, Pass 3b
**Tracker reference:** F40 (boundary analysis deferred), F41 (Safety/CyberSec deferred)

---

## Context

You are implementing Pass 3b of the SysEngage analytical pipeline — CellContentItem (CCI) Construction. This pass runs after Pass 3a (Row-Lens Source Re-Analysis) completes and produces the first structured analytical output from the Signal set: CellContentItem entities, one per distinct classified content item per ZachmanCell.

This is an AI-involving mechanism. Two steps use the Claude Sonnet API (Stage 3a: CCI derivation; Stage 4b: semantic deduplication). All other steps are fully deterministic.

---

## Specification artefacts to read before writing any code

Read all four artefacts in this order. Do not begin implementation until you have read all of them.

1. **`SysEngage_Row_4_Mechanism_CCI_Construction_v0_1.md`** — primary implementation spec. This is your primary reference for everything you build. Read it completely.

2. **`SysEngage_Row_3_Mechanism_CCI_Construction_v0_1.md`** — architectural authority. When the Row 4 spec references "per Row 3 Mechanism Spec §X", read that section here.

3. **`SysEngage_Row_4_Understanding_v0_3.md`** — §12 only. Implementation patterns for Pass 3b: per-cell processing pattern, prompt construction, deduplication pattern, re-run commit pattern, module structure.

4. **`SysEngage_Row_4_Applied_to_SysEngage_v0_2.docx`** — common foundations. Technology stack, transactional discipline, mode decorator pattern, Pydantic discipline. These apply to every mechanism including this one.

Reference these for established patterns already in the codebase:
- **`mechanisms/row_lens_source_reanalysis/`** — the AI invocation pattern, Pydantic response schema approach, AnalysisPass production, transactional discipline, and mode decorator are all established here. Follow the same patterns.
- **`mechanisms/source_capture/`** — identifier allocation and sequence conventions.
- **`sysengage_minimal_ledger_spec_v2_12.md`** — canonical entity schemas. ZachmanCell and CellContentItem schemas are authoritative here.

---

## What to build

### New module

Create `mechanisms/cci_construction/` with this file structure:

```
mechanisms/cci_construction/
  __init__.py                            # Orchestration entry point — Steps 1–6
  step1_signal_assembly.py               # DM: eligible Signal query
  step2_zachman_cell_upsert.py           # DM: ZachmanCell upsert + Signal grouping
  step3_cci_derivation.py                # IM+DM: per-cell AI derivation + entity production
  step4_deduplication.py                 # DM+IM+DM: structural pre-filter + AI review + merge
  step5_commit.py                        # DM: identifier allocation + ledger write
  step6_analysis_pass.py                 # DM: AnalysisPass record production
  prompts/
    cci_derivation_prompt.py             # Template: per-cell Signal-to-CCI derivation
    dedup_semantic_review_prompt.py      # Template: semantic equivalence review
    column_interrogatives.py             # Row × Column framing table
    column_vocabulary.py                 # Permitted classification_type values per column
  schemas/
    cci_construction_response_schema.py  # Pydantic: AI derivation response validation
    dedup_review_response_schema.py      # Pydantic: AI deduplication response validation
```

### New database entities

Two new entity types require database tables and Pydantic models:

**ZachmanCell** — `cell_id` (PK, format `ZC-R{row}-C-{column}`), `row_target` (string), `column` (string). Upsert-safe (ON CONFLICT DO NOTHING).

**CellContentItem** — `ci_id` (PK, format `CCI-ROW{row}-C-{column}-{seq}`), `cell_id` (FK → ZachmanCell), `classification_type` (string), `signal_refs` (JSON array of SG### strings), `description` (string), `trigger_condition` (string, nullable), `justification` (string, nullable), `confidence` (float). Identifier sequence scoped per ZachmanCell.

Add Alembic migration for both tables. Migration must be additive — no changes to existing tables.

**CellContentItemRegister** — if a generic Register table already exists in the codebase, add entries for CCI entities following the established pattern. If not, create a simple register table: `register_id`, `entity_type`, `member_ids` (JSON array).

### New Pydantic schemas (in `schemas/`)

Mirror the pattern from `mechanisms/row_lens_source_reanalysis/schemas/`. Two schemas:

1. **`cci_construction_response_schema.py`** — validates AI response for Stage 3a:
```json
{
  "items": [
    {
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

2. **`dedup_review_response_schema.py`** — validates AI response for Stage 4b:
```json
{
  "verdicts": [
    {
      "item_a_ref": "string",
      "item_b_ref": "string",
      "verdict": "Duplicate|Distinct|Ambiguous",
      "rationale": "string",
      "merged_description": "string or null"
    }
  ]
}
```

### Prompt templates (in `prompts/`)

**`column_vocabulary.py`** — a dict keyed by column name with the permitted `classification_type` values:
```python
COLUMN_VOCABULARY = {
    "What":  ["Entity", "Attribute", "Relationship"],
    "How":   ["Process", "Function", "Rule"],
    "Where": ["Location", "Node", "Network"],
    "Who":   ["Actor", "Role", "Organisation"],
    "When":  ["Event", "Cycle", "Trigger"],
    "Why":   ["Goal", "Principle", "Constraint"],
}
```

**`column_interrogatives.py`** — a nested dict `{row_ref: {column: interrogative_framing}}`. Use the full Row × Column table from Row 4 Understanding v0.3 §12.2.1.

**`cci_derivation_prompt.py`** — parameterised template for Stage 3a. Must:
- Identify itself as operating at the row's abstraction level using the column_interrogatives framing
- State the permitted classification_type values explicitly
- Instruct the AI to produce one item per distinct classified content item (not per Signal)
- Instruct the AI that descriptions are derived statements, not verbatim copies of Signal text
- Instruct the AI that signal_refs must reference only Signal ids from the provided list
- Instruct the AI to respond in JSON conforming to the `cci_construction_response_schema`

**`dedup_semantic_review_prompt.py`** — parameterised template for Stage 4b. Must:
- Present pairs of CCI candidates (and/or existing CCIs) for semantic equivalence review
- Distinguish between `new_candidate` and `existing_cci` items in the pair presentation
- Instruct the AI to return one of three verdicts: Duplicate, Distinct, Ambiguous
- Instruct the AI that `merged_description` should be populated when merging and the lower-confidence item contains useful nuance not in the higher-confidence description
- Instruct the AI to respond in JSON conforming to the `dedup_review_response_schema`

---

## Step-by-step implementation requirements

### Step 1 — Assemble eligible Signal set
- Query: SELECT Signal WHERE `row_target = str(row_ref)` ORDER BY `signal_id` ASC
- For each Signal WHERE `derived_from_concern_id IS NOT NULL`: verify Concern.state = 'Resolved'. If not: exclude Signal; add to `integrity_violations` buffer
- No ledger write. Result is in-memory only.

### Step 2 — Upsert ZachmanCells and group Signals
- UPSERT all six ZachmanCells for the row (ON CONFLICT DO NOTHING). Columns in order: What, How, Where, Who, When, Why
- Commit ZachmanCell upserts in their own short transaction before the main mechanism transaction opens (see Row 4 Mechanism Spec §10.5 and open question RA-3)
- Partition Signal working set by column → dict `{column: [Signal]}`

### Step 3 — Per-cell CCI derivation (loop over populated cells)
- For each column where Signal group is non-empty:
  - Stage 3a: call Claude Sonnet API with `cci_derivation_prompt`. Retry up to 3× with 1s/2s/4s backoff on failure
  - Parse response against `cci_construction_response_schema` (Pydantic). Record malformed items in `candidates_rejected`
  - Stage 3b: for each valid item, validate `classification_type` against column vocabulary; validate `signal_refs` non-empty; validate `confidence` in [0.0, 1.0]; validate `description` non-empty. Record failures in `candidates_rejected`
  - Stage 3c: validate that each `signal_refs` entry resolves to a Signal in the current working set. Reject and record if not
  - Hold valid candidate structs in memory per cell

### Step 4 — Per-cell deduplication (loop over populated cells)
- Stage 4a: for each pair of candidates in the cell's buffer: if `classification_type` matches AND `set(signal_refs)` matches → structural duplicate. Apply merge rule. Remove lower-confidence candidate
- Stage 4b: read existing committed CCIs for the cell from ledger. Group surviving candidates + existing CCIs by `classification_type`. For groups with >1 member: call Claude Sonnet API with `dedup_semantic_review_prompt`. Parse response against `dedup_review_response_schema`
  - Duplicate verdict: apply merge rule. If merging into existing CCI → add to "update-existing" buffer (NOT a new candidate)
  - Distinct verdict: both items survive as-is
  - Ambiguous verdict: both survive; reduce each confidence by 0.1 (floor 0.0); record in consolidation_flags
- Stage 4c: apply consolidation threshold check. If `(candidates_in - surviving_new) / candidates_in > ProjectProfile.cci_consolidation_threshold` (default 0.80): record in consolidation_flags

**Merge rule** (apply in both Stage 4a and 4c):
- `signal_refs`: `sorted(list(set(a.signal_refs) | set(b.signal_refs)))` (sorted by signal_id for determinism)
- `confidence`: `max(a.confidence, b.confidence)`
- `description`: AI's `merged_description` if non-null; else the higher-confidence item's description
- `trigger_condition`: higher-confidence item's value; whichever has it if only one does
- `justification`: concatenate with `" | "` if both non-null; whichever is non-null if only one

### Step 5 — Assign identifiers and commit (main transaction)
**Open Postgres transaction.**

For each column with surviving new candidate CCIs:
- `SELECT MAX(seq) FROM cci WHERE cell_id = 'ZC-R{row}-C-{column}'` where seq is parsed from the ci_id trailing digits. If no existing CCIs: max = 0
- For each candidate in column: allocate `ci_id = f"CCI-ROW{row_ref}-C-{column}-{str(next_seq).zfill(3)}"`, increment next_seq
- Validate candidate struct against CCI Pydantic model. On failure: record in `candidates_rejected`, skip INSERT
- INSERT new CCIs

For each existing CCI in the "update-existing" buffer:
- UPDATE `signal_refs`, `confidence`, `description` WHERE `ci_id = ?`. Do NOT change `ci_id`

UPDATE CellContentItemRegister: add all newly INSERTed ci_ids to member_ids.

**Commit transaction.** On rollback: set execution_status = Failed; proceed to Step 6 with failure detail.

### Step 6 — AnalysisPass record
Construct and INSERT AnalysisPass following the established pattern from `mechanisms/row_lens_source_reanalysis/analysis_pass_production.py`. Key fields:

```python
mechanism = "CellContentItemConstruction"
pass_type = "Per-row"
mode_active = "DM"
declared_transformation_modes = ["IM", "DM"]
outputs = {
    "cci_data": {
        "row_ref": row_ref,
        "cells_populated": <count>,
        "cells_empty": 6 - cells_populated,
        "ccis_created": <count of new INSERTs>,
        "ccis_merged": <count of existing CCI UPDATEs>,
        "candidates_rejected": <count>,
        "merges": [...],              # see Row 3 Mechanism Spec §7
        "consolidation_flags": [...],
        "integrity_violations": [...]
    },
    "mode_violations": []
}
```

`execution_status`:
- `"Completed"`: all cells processed, no AI failures, no schema rejections
- `"CompletedWithWarnings"`: at least one cell succeeded; some had AI failures, schema rejections, integrity violations, or consolidation flags
- `"Failed"`: Step 5 transaction rolled back; OR all populated cells had AI failures

Record `ai_model_fingerprints` (list of model version strings from every AI invocation in Steps 3a and 4b). Record `confidence` as mean of all AI invocation confidence scores.

---

## What NOT to build

- **No Risk entities** — Safety/CyberSec evaluation is deferred to designated analysis phases (F41). Pass 3b produces no Risk entities under any condition.
- **No boundary candidate CCIs** — behavioural-structural boundary analysis is deferred to Phase 5 Robustness mechanism (F40). A CCI is placed in one cell. Pass 3b does not produce multi-cell candidates.
- **No changes to existing tables** — this is an additive build. The Signal, Concern, Source, Segment, SourceAtom, AnalysisPass, Stakeholder tables are read-only for this task.
- **No changes to existing mechanisms** — Source Capture and Row-Lens Source Re-Analysis modules are reference only. Do not modify them.

---

## Open questions — resolve during build, record decisions

Three open questions from Row 4 Mechanism Spec §12.2. Resolve them during implementation and note your decision in a brief comment in the relevant file:

**RA-1 — Stage 4b batch size for semantic review.** The spec recommends: present all same-classification_type pairs for a cell in one call; if >30 same-type pairs, split into batches of 20. Follow this recommendation; adjust if context pressure observed.

**RA-2 — Stage 4a exhaustive vs early-exit.** The spec recommends exhaustive pairwise comparison. Follow this recommendation; cell CCI counts are expected to be small (5–20 per cell).

**RA-3 — ZachmanCell upsert transaction boundary.** Commit ZachmanCell upserts in their own short transaction before the main mechanism transaction (Step 5). Rationale: ZachmanCells must exist for referential integrity on CCI INSERT; if the main transaction rolls back, ZachmanCells remain (idempotent, correct). Follow this recommendation.

---

## Verification requirements

After implementation, run the automated verification suite and confirm all 10 decidable criteria pass.

Run tests using pytest against the test database. Create `tests/test_cci_construction.py` implementing the four fixtures from Row 4 Mechanism Spec §9:

- **Fixture 1** — Happy path: single populated cell (What column), 3 Signals, verify CCI production, ZachmanCell creation, AnalysisPass
- **Fixture 2** — Deduplication: two Who-column Signals, verify Stage 4a/4b fires and merge audit appears in AnalysisPass
- **Fixture 3** — Re-run: existing CCI in ledger, new Signal added, verify existing ci_id preserved and new Signal grounded in CCI
- **Fixture 4** — Empty Signal set: zero Signals, verify 6 ZachmanCells upserted, zero CCIs, AnalysisPass Completed status

Each test must assert the relevant VER-3b-NN criteria from Row 3 Mechanism Spec §8.1. Specifically:

| **Test** | **Criteria to assert** |
| --- | --- |
| Fixture 1 | VER-3b-01, VER-3b-02, VER-3b-03, VER-3b-04, VER-3b-05, VER-3b-06, VER-3b-08, VER-3b-09, VER-3b-10 |
| Fixture 2 | VER-3b-07 (sequence uniqueness), VER-3b-10 (both Signals grounded) |
| Fixture 3 | VER-3b-03, VER-3b-04, VER-3b-10; PLUS: existing ci_id unchanged assertion |
| Fixture 4 | VER-3b-01, VER-3b-09; PLUS: ccis_created = 0, cells_empty = 6 assertions |

---

## Generator string

Set the generator string for this mechanism to `"sysengage_cci_construction_v0.1"`. Include this string in the AnalysisPass `mechanism` field output metadata. Follow the generator string convention from Row 4 Mechanism Source Capture §7.6 — bump this string when the mechanism spec version changes.

---

## Plan Mode requirement

Before writing any code, enter Plan Mode. In Plan Mode:

1. Confirm you have read all four specification artefacts listed above.
2. State the module structure you will create.
3. Confirm your understanding of the two transaction boundaries (Step 2 ZachmanCell upsert in own transaction; Step 5 main CCI commit transaction).
4. Confirm your understanding of re-run semantics — existing CCIs are never deleted; new candidates are checked against existing CCIs in Stage 4b; existing CCIs may be updated in-place (signal_refs, confidence, description) but ci_id is immutable.
5. Identify any spec ambiguity you need to resolve before proceeding. If you have a question that the spec does not answer, state it explicitly before beginning implementation. Do not make silent assumptions.
6. State how you will implement the mode discipline for Stage 3a (IM) and Stage 4b (IM) — specifically, how the mode decorator pattern will record AI invocations on the AnalysisPass.

Only proceed to implementation after Plan Mode is complete and any ambiguities are resolved.

---

## Deliverables

1. `mechanisms/cci_construction/` — complete module as specified
2. `tests/test_cci_construction.py` — four fixtures, all VER-3b-NN assertions
3. Alembic migration — ZachmanCell and CellContentItem tables
4. Updated `replit.md` or equivalent — note this task's completion and the mechanism ID (MECH-R3-004)
5. Brief implementation notes — record your RA-1/RA-2/RA-3 decisions and any other decisions made during build

---

## Success criteria

The build is complete when:
- All 10 automated VER-3b-NN criteria pass in the pytest suite
- All four test fixtures execute without error
- The AnalysisPass for a test run contains a valid `cci_data` sub-structure with all required fields populated (no null counts)
- The generator string `"sysengage_cci_construction_v0.1"` appears in AnalysisPass mechanism field output
- No existing tests are broken
