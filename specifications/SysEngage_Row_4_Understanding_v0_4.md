# SysEngage Row 4 Understanding

**Builder-perspective framework for software-product Row 4 analysis**

Filename: SysEngage_Row_4_Understanding_v0_4.md

Version: 0.4 (Pass 3b — batch processing model; Signal column attribute dependency removed)

Date: 16 May 2026

**Purpose.** Specifies the Row 4 Builder-perspective framework for SysEngage analysis of software products. This version adds framework content for the CellContentItem Construction mechanism (Pass 3b). All prior content from v0.2 is inherited unchanged.

**Status.** v0.4 — fourth Row 4 Understanding artefact. v0.1 covered Source Capture (deterministic). v0.2 added AI-involving mechanism framework (Row-Lens Source Re-Analysis). v0.3 added Pass 3b framework (per-cell processing model — superseded by this version). v0.4 replaces the v0.3 §12 content with the corrected batch processing model: Signals are partitioned into fixed-size batches; each batch is presented to the AI with all six column interrogatives simultaneously; the AI assigns `column` as part of the CCI derivation act. No Signal.column attribute required; no Pass 3a amendment required.

**Changes from v0.3.** (1) §12 header: updated reference from Row 3 Mechanism Spec v0.1 to v0.2. (2) §12.1: per-cell processing pattern replaced with batch processing pattern; batch-iteration pseudocode replaces cell-iteration pseudocode. (3) §12.2: prompt construction updated — all six column interrogatives presented in every batch prompt; `column` added as required field in response schema; Stage 3b validation now checks both `column` and `classification_type`. (4) §12.3: deduplication grouping source updated — candidates grouped by AI-assigned `cell_id` (derived from `column`), not by pre-partitioned Signal group. (5) §12.5: AnalysisPass `outputs.cci_data` gains `batches_processed` and `batches_failed` fields. (6) §12.6: module comments updated to reflect per-batch derivation and per-cell deduplication. (7) §12.7: plausibility checklist adds AI column assignment spot-check.

**Precedence rule.** Where this artefact's content appears to differ from POC source documents, the SysEngage Row 1 v1.2 / Row 2 v1.2 / Row 3 v1.1 Understanding documents take precedence. Where any content appears to differ from canonical ledger spec v2.12, the canonical spec takes precedence.

**Scope note.** This document records only the v0.4 additions and corrections to §12. All §1–§11 content from v0.2 is authoritative and unchanged. The §12 content from v0.3 is superseded in full by this version. Implementers should read v0.2 alongside v0.4. A consolidated v1.0 will be produced when the Phase 3 pass suite (3b, 3c, 3d) is complete and verified.

---

## v0.4 Additions and Corrections

### §12 Pass 3b — CellContentItem Construction Implementation Framework

This section establishes the Row 4 implementation framework for Pass 3b. It complements the Row 3 Mechanism Spec (SysEngage_Row_3_Mechanism_CCI_Construction_v0_2.md), which is the architectural authority. This section supersedes the §12 content from v0.3 in full.

---

#### §12.1 Batch Processing Pattern

Pass 3b processes all Signals in fixed-size batches. The canonical implementation pattern is a batch-iteration loop:

```
# Step 2a — ZachmanCell upsert (unconditional)
upsert_all_six_zachman_cells(row_ref)

# Step 2b — batch partitioning
batches = partition(eligible_signals, batch_size=ProjectProfile.cci_batch_size)

# Step 3 — per-batch CCI derivation
all_candidates = []
for batch in batches:
    candidates = construct_candidates(batch)  # AI call with all 6 columns
    all_candidates.extend(candidates)

# Step 4 — per-cell deduplication (on the full candidate set)
for column in [What, How, Where, Who, When, Why]:
    cell_candidates = [c for c in all_candidates if c.column == column]
    existing = read_existing_ccis(cell_id=f"ZC-R{row_ref}-C-{column}")
    survivors = deduplicate(cell_candidates, existing)
    commit(survivors)  # Step 5
```

This pattern ensures:
- ZachmanCell entity creation is unconditional (Step 2a runs before any batch processing)
- Every Signal is processed regardless of which column its derived CCIs will land in
- Cross-batch duplicates (same classified content derived from two different batches) are caught in Step 4 per-cell deduplication
- Empty cells are a natural outcome — no special handling; Phase 5 surfaces them as coverage findings

**Batch size:** `ProjectProfile.cci_batch_size` (default 20). Controls context window pressure only — has no effect on analytical correctness. Duplicates across batch boundaries are resolved in Step 4.

---

#### §12.2 Signal-to-CCI Derivation Pattern (Stage 3a / 3b)

**Prompt construction.** The Stage 3a AI invocation uses a prompt template parameterised with:
- `row_ref` — integer, determines the row's abstraction lens description
- `all_column_interrogatives` — the full set of six column interrogatives for this row (from `column_interrogatives.py[row_ref]`)
- `all_column_vocabularies` — the permitted `classification_type` values for all six columns (from `column_vocabulary.py`)
- `signals` — list of `{signal_id, description, signal_type, confidence}` for this batch

The prompt instructs the AI to derive CCIs across all six columns from the batch. The AI determines column placement as part of the derivation act — this is an interpretive judgment, not a mechanical partition from a Signal attribute.

**Response schema.** The AI response must conform to the `cci_construction_response_schema`. The schema includes `column` as a required field:

```json
{
  "items": [
    {
      "column": "What|How|Where|Who|When|Why",
      "classification_type": "string",
      "description": "string",
      "signal_refs": ["signal_id_string"],
      "confidence": 0.0,
      "trigger_condition": "string or null",
      "justification": "string or null"
    }
  ]
}
```

Pydantic validation is applied immediately on receipt. Items that fail validation are excluded and recorded in AnalysisPass failure detail. Valid items proceed to Stage 3b entity production.

**Entity production (Stage 3b).** For each valid AI response item:
- Validate `column` is one of {What, How, Where, Who, When, Why} — reject if not
- Validate `classification_type` is in `column_vocabulary.py[column]` — reject if not
- Validate `signal_refs` is non-empty — reject if empty
- Validate `confidence` ∈ [0.0, 1.0] — reject if outside range
- Validate `description` is non-empty — reject if empty
- Construct candidate CCI struct (no ci_id yet): `{cell_id=f"ZC-R{row_ref}-C-{column}", column, classification_type, description, signal_refs, confidence, trigger_condition, justification}`

Struct is held in memory. No ledger write at this stage.

##### §12.2.1 Column Interrogative Framing by Row

The prompt must communicate what the AI is looking for in each column at each row's abstraction level. The following table provides the interrogative framing to include in the prompt template. All six columns are presented in every batch prompt.

| **Row** | **What** | **How** | **Where** | **Who** | **When** | **Why** |
| --- | --- | --- | --- | --- | --- | --- |
| **1 (Planner)** | Things of strategic importance to the enterprise | Processes the enterprise performs | Locations where the enterprise operates | Stakeholders in the enterprise context | Events and cycles that matter strategically | Goals and drivers of the enterprise |
| **2 (Owner)** | Business entities and data objects | Business processes and workflows | Business locations and channels | Business roles and actors | Business events and timing constraints | Business rules and objectives |
| **3 (Designer)** | Logical data entities and relationships | Logical processes and functions | Logical locations and nodes | Logical actors and roles | Logical events and state transitions | Design constraints and principles |
| **4 (Builder)** | Physical data structures and schemas | Physical processes and components | Physical nodes and infrastructure | Technical actors and system components | Physical events and scheduling | Technical constraints and standards |
| **5 (Implementer)** | Detailed data definitions and formats | Detailed procedures and algorithms | Detailed network and deployment specs | Detailed user and system interfaces | Detailed timing and sequencing | Detailed rules and validation criteria |
| **6 (User)** | Operational data and content | Operational procedures and tasks | Operational locations and access points | Operational users and support roles | Operational schedules and triggers | Operational policies and compliance |

---

#### §12.3 Deduplication Pattern (Stage 4a / 4b / 4c)

Deduplication operates per cell across the full candidate set from all batches. After all batches have been processed in Step 3, candidates are grouped by `cell_id` (derived from their AI-assigned `column`) and deduplication runs per cell.

**Stage 4a — Structural pre-filter (DM).**

For each pair of candidates within the same cell's candidate set:
- `classification_type` match: string equality
- `signal_refs` match: set equality (order-independent): `set(cand_a.signal_refs) == set(cand_b.signal_refs)`

Both must match for a structural duplicate verdict. This catches the case where two batches produced the same classified content from the same Signal(s).

Stage 4a processes only new candidates against each other. Comparison against existing committed CCIs is Stage 4b's responsibility.

**Stage 4b — AI semantic review (IM).**

Read existing committed CCIs for the cell from ledger. Group surviving candidates (post-Stage 4a) + existing CCIs by `classification_type`. For groups with >1 member: call Claude Sonnet API with `dedup_semantic_review_prompt`.

Prompt parameterisation:
- `cell_id` — the ZachmanCell being reviewed
- `column` — column interrogative context
- `pairs` — list of `{item_a: {source, ref, description, signal_refs}, item_b: {source, ref, description, signal_refs}}` where `source ∈ {"new_candidate", "existing_cci"}`

Response schema (unchanged from v0.1):
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

**Stage 4c — Merge execution (DM).**

For each Duplicate verdict:
- If both items are new candidates: produce one merged candidate struct, discarding the other. Record merge in AnalysisPass `outputs.cci_data.merges`.
- If one item is an existing committed CCI and the other is a new candidate: update the existing CCI's `signal_refs` (union) and `confidence` (max); update `description` if `merged_description` is non-null; no new entity created. Record merge.

For each Ambiguous verdict:
- Both items survive; reduce each confidence by 0.1 (floor at 0.0); record in consolidation_flags.

**Consolidation threshold check (DM).**

After Stage 4c per cell: compute `reduction_ratio = (candidates_in - surviving_new) / candidates_in`. If ratio > `ProjectProfile.cci_consolidation_threshold` (default 0.80): record in `outputs.cci_data.consolidation_flags`.

---

#### §12.4 Re-Run-Aware Commit Pattern (Step 5)

**Identifier allocation.** On first run: sequence starts at 001 per ZachmanCell. On re-run: read the current maximum sequence number for the cell from the ledger and continue from `max + 1`.

```
current_max = SELECT MAX(sequence_from_ci_id) FROM cci WHERE cell_id = ?
next_seq = (current_max or 0) + 1
```

**Write pattern.** Two write operations per re-run:
1. INSERT new CCIs: standard INSERT with newly allocated `ci_id`.
2. UPDATE existing CCIs that were merged: UPDATE `signal_refs`, `confidence`, `description` WHERE `ci_id = ?`. The `ci_id` is never changed.

Both operations participate in the same Postgres transaction. Per Row 4 Applied §5 transactional discipline.

**CellContentItemRegister update.** After INSERT operations: add new `ci_id` values to `member_ids`. UPDATE operations on existing CCIs do not change the register.

---

#### §12.5 AnalysisPass Population for Pass 3b

The `outputs.cci_data` sub-structure is stored as JSONB in `AnalysisPass.outputs`. All fields must be populated (zero-value counts, not null):

```python
outputs = {
    "cci_data": {
        "row_ref": row_ref,
        "batches_processed": int,
        "batches_failed": int,
        "cells_populated": int,
        "cells_empty": int,
        "ccis_created": int,
        "ccis_merged": int,
        "candidates_rejected": int,
        "merges": [...],
        "consolidation_flags": [...],
        "integrity_violations": [...]
    },
    "mode_violations": []
}
```

Note: `batches_processed` and `batches_failed` are new in v0.4 (batch model). These replace the cell-level failure tracking from the per-cell model in v0.3.

---

#### §12.6 Module Structure for Pass 3b

```
mechanisms/cci_construction/
  __init__.py                            # Orchestration entry point — Steps 1–6
  step1_signal_assembly.py               # DM: eligible Signal query
  step2_zachman_cell_upsert.py           # DM: ZachmanCell upsert + batch partitioning
  step3_cci_derivation.py                # IM+DM: per-batch AI derivation + entity production
  step4_deduplication.py                 # DM+IM+DM: per-cell structural pre-filter + AI review + merge
  step5_commit.py                        # DM: identifier allocation + ledger write
  step6_analysis_pass.py                 # DM: AnalysisPass record production
  prompts/
    cci_derivation_prompt.py             # Template: per-batch Signal-to-CCI derivation (all 6 columns)
    dedup_semantic_review_prompt.py      # Template: per-cell semantic equivalence review
    column_interrogatives.py             # Row × Column framing table (§12.2.1)
    column_vocabulary.py                 # Permitted classification_type values per column
  schemas/
    cci_construction_response_schema.py  # Pydantic: AI derivation response (includes column field)
    dedup_review_response_schema.py      # Pydantic: AI deduplication response
```

---

#### §12.7 Verification Criteria Additions (extending §8)

**Automated verification for Pass 3b:**

| **ID** | **Criterion** | **Test type** |
| --- | --- | --- |
| **VER-3b-01** | 6 ZachmanCells exist for row after Pass 3b | pytest: count ZachmanCell WHERE row_target = row_ref == 6 |
| **VER-3b-02** | All ci_id values match canonical regex | pytest: all ci_ids pass `^CCI-ROW[1-6]-C-(What\|How\|Where\|Who\|When\|Why)-\d{3}$` |
| **VER-3b-03** | All CCI.cell_id values resolve to existing ZachmanCells | pytest: referential integrity check |
| **VER-3b-04** | All CCI.signal_refs entries resolve to existing Signals | pytest: referential integrity check |
| **VER-3b-05** | classification_type values within permitted vocabulary per column | pytest: enumeration check using column_vocabulary.py |
| **VER-3b-06** | All confidence values within [0.0, 1.0] | pytest: range assertion |
| **VER-3b-07** | Sequence numbers unique per cell | pytest: no duplicate sequence numbers among CCIs per cell |
| **VER-3b-08** | CellContentItemRegister includes all ci_ids for row | pytest: register membership check |
| **VER-3b-09** | AnalysisPass with mechanism="CellContentItemConstruction" exists | pytest: query by mechanism string |
| **VER-3b-10** | Non-Loss: every Signal grounds at least one CCI or appears in integrity_violations | pytest: for each Signal in step 1 working set: signal_id in at least one CCI.signal_refs OR in AnalysisPass integrity_violations |

**Plausibility checklist for Practitioner review:**
1. Select one populated cell. Review all CCIs against the full Signal set. Do CCI descriptions express classified meaning without verbatim copying Signal text?
2. Are CCIs placed in the expected columns for their content? Column placement is AI-determined — spot-check that the AI's column assignments are analytically reasonable.
3. For each merge in AnalysisPass.outputs.cci_data.merges: do both original descriptions describe the same thing?
4. Are consolidation flags present? If so, review the flagged cell's surviving CCIs.

---

## Document End

End of SysEngage Row 4 Understanding v0.4.

v0.4 replaces §12 from v0.3 with the corrected batch processing model. §12 content from v0.3 is superseded in full. All §1–§11 content from v0.2 unchanged.

Companion artefacts:
- SysEngage_Row_3_Mechanism_CCI_Construction_v0_2.md — Row 3 architectural spec
- SysEngage_Row_4_Mechanism_CCI_Construction_v0_2.md — Row 4 implementation spec
- SysEngage_Issues_Tracker_v0_27.md — tracker current state
