# SysEngage Row 4 Understanding

**Builder-perspective framework for software-product Row 4 analysis**

Filename: SysEngage_Row_4_Understanding_v0_3.md

Version: 0.3 (Pass 3b — CellContentItem Construction framework additions)

Date: 16 May 2026

**Purpose.** Specifies the Row 4 Builder-perspective framework for SysEngage analysis of software products. This version adds framework content for the CellContentItem Construction mechanism (Pass 3b). All prior content from v0.2 is inherited unchanged.

**Status.** v0.3 — third Row 4 Understanding artefact. v0.1 covered Source Capture (deterministic). v0.2 added AI-involving mechanism framework (Row-Lens Source Re-Analysis). v0.3 extends with: Pass 3b-specific implementation patterns (§12 new); per-cell processing pattern (§12.1 new); Signal-to-CCI derivation pattern (§12.2 new); deduplication pattern (§12.3 new); re-run-aware commit pattern (§12.4 new); verification criteria additions (§8 extended).

**Precedence rule.** Where this artefact's content appears to differ from POC source documents, the SysEngage Row 1 v1.2 / Row 2 v1.2 / Row 3 v1.1 Understanding documents take precedence. Where any content appears to differ from canonical ledger spec v2.12, the canonical spec takes precedence.

**Scope note.** This document records only the v0.3 additions. All §1–§11 content from v0.2 is authoritative and unchanged. Implementers should read v0.2 alongside v0.3. A consolidated v1.0 will be produced when the Phase 3 pass suite (3b, 3c, 3d) is complete and verified.

---

## v0.3 Additions

### §12 Pass 3b — CellContentItem Construction Implementation Framework

This section establishes the Row 4 implementation framework for Pass 3b. It complements the Row 3 Mechanism Spec (SysEngage_Row_3_Mechanism_CCI_Construction_v0_1.md), which is the architectural authority. This section specifies implementation-level patterns consistent with the established SysEngage Row 4 conventions.

---

#### §12.1 Per-Cell Processing Pattern

Pass 3b processes cells independently. The canonical implementation pattern is a cell-iteration loop:

```
for each ZachmanCell in [What, How, Where, Who, When, Why]:
    signal_group = signals grouped to this cell in Step 2
    if signal_group is empty:
        continue  # cell remains empty; ZachmanCell entity exists from Step 2
    candidates = construct_candidates(signal_group)  # Step 3
    survivors = deduplicate(candidates, existing_ccis_for_cell)  # Step 4
    commit(survivors)  # Step 5
```

This pattern ensures:
- ZachmanCell entity creation is unconditional (Step 2 runs before the loop)
- Empty cells are handled by `continue` — no error, no special state
- Each cell's AI invocations are independent — a failure in one cell does not propagate to others
- The deduplication sweep in Step 4 always receives the current committed CCI set for the cell, ensuring re-run awareness

**Cell order:** Cells are processed in a fixed order — What, How, Where, Who, When, Why — for determinism. The order does not affect analytical correctness.

---

#### §12.2 Signal-to-CCI Derivation Pattern (Stage 3a / 3b)

**Prompt construction.** The Stage 3a AI invocation uses a prompt template parameterised with:
- `row_ref` — integer, determines the row's abstraction lens description
- `column` — one of {What, How, Where, Who, When, Why}
- `column_interrogative` — the analytical question for this column at this row (see §12.2.1)
- `permitted_classification_types` — the column's vocabulary from Row 3 Mechanism Spec §5.1
- `signals` — list of `{signal_id, description, signal_type, confidence}` for the cell's Signal group

**Response schema.** The AI response must conform to the `cci_construction_response_schema`:

```json
{
  "items": [
    {
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
- Construct a candidate CCI struct with all attributes except `ci_id` (not yet allocated)
- Apply vocabulary validation: `classification_type` must be in the column's permitted set
- Apply confidence range check: 0.0 ≤ confidence ≤ 1.0
- Apply non-empty checks: `description` and `signal_refs` must be non-empty

Struct is held in memory until Step 5. No ledger write at this stage.

##### §12.2.1 Column Interrogative Framing by Row

The prompt must communicate what the AI is looking for in each column at each row's abstraction level. The following table provides the interrogative framing to include in the prompt template:

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

**Stage 4a — Structural pre-filter (DM).**

Implementation: for each pair of candidates in the cell's candidate set, compute:
- `classification_type` match: string equality
- `signal_refs` match: set equality (order-independent comparison)

Both must match for a structural duplicate verdict. Implementation uses Python set comparison: `set(cand_a.signal_refs) == set(cand_b.signal_refs)`.

Stage 4a processes only new candidates against each other. It does not compare new candidates to existing committed CCIs — that is Stage 4b's responsibility.

**Stage 4b — AI semantic review (IM).**

Grouping for AI presentation: group surviving candidates (post-Stage 4a) by `classification_type` within the cell. Present same-type groups to the AI for pairwise semantic equivalence review. Also include existing committed CCIs for the cell in the same grouping — the AI sees both new candidates and existing CCIs.

Prompt parameterisation:
- `cell_id` — the ZachmanCell being reviewed
- `column` — column interrogative context
- `pairs` — list of `{item_a: {source, ci_id_or_null, description, signal_refs}, item_b: {source, ci_id_or_null, description, signal_refs}}` where `source` is "new_candidate" or "existing_cci" and `ci_id_or_null` is null for new candidates

Response schema:
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

`merged_description` is populated by the AI when `verdict = "Duplicate"` and the lower-confidence item contains nuance worth preserving. If null on a Duplicate verdict, the higher-confidence description is used unchanged.

**Stage 4c — Merge execution (DM).**

For each Duplicate verdict:
- If both items are new candidates: produce one merged candidate struct, discarding the other
- If one item is an existing committed CCI and the other is a new candidate: update the existing CCI's `signal_refs` (union) and `confidence` (max); update `description` if `merged_description` is non-null; no new entity created
- Record merge in AnalysisPass `outputs.cci_data.merges`

For each Ambiguous verdict:
- Both items survive
- Reduce each item's `confidence` by 0.1 (floor at 0.0)
- Record in AnalysisPass `outputs.cci_data.consolidation_flags`

**Consolidation threshold check (DM).**

After Stage 4c: compute `reduction_ratio = (candidates_in - candidates_out) / candidates_in`. If ratio > `ProjectProfile.cci_consolidation_threshold` (default 0.80): record in `outputs.cci_data.consolidation_flags` with `{cell_id, candidates_in, candidates_out, ratio}`.

---

#### §12.4 Re-Run-Aware Commit Pattern (Step 5)

**Identifier allocation.** On first run: sequence starts at 001 per ZachmanCell. On re-run: read the current maximum sequence number for the cell from the ledger and continue from `max + 1`. Implementation:

```
current_max = SELECT MAX(sequence_from_ci_id) FROM cci WHERE cell_id = ? AND row_target = ?
next_seq = (current_max or 0) + 1
```

The sequence number is extracted from the `ci_id` by parsing the trailing numeric segment.

**Write pattern.** Two write operations per re-run:

1. INSERT new CCIs (those not merged with existing CCIs in Stage 4b): standard INSERT with newly allocated `ci_id`.
2. UPDATE existing CCIs that were merged: UPDATE `signal_refs`, `confidence`, `description` WHERE `ci_id = ?`. The `ci_id` is never changed.

Both operations participate in the same Postgres transaction. Per Row 4 Applied §5 transactional discipline: all ledger writes for Pass 3b are committed atomically. If any write fails, the entire transaction rolls back.

**CellContentItemRegister update.** After INSERT operations: UPDATE the CellContentItemRegister to add new `ci_id` values to `member_ids`. UPDATE operations (to existing CCIs) do not change the register — the ci_id is already a member.

---

#### §12.5 AnalysisPass Population for Pass 3b

The `outputs.cci_data` sub-structure (see Row 3 Mechanism Spec §7) is stored as JSONB in the canonical `AnalysisPass.outputs` field. Implementation:

```python
outputs = {
    "cci_data": {
        "row_ref": row_ref,
        "cells_populated": int,
        "cells_empty": int,
        "ccis_created": int,
        "ccis_merged": int,
        "candidates_rejected": int,
        "merges": [
            {
                "surviving_ci_id": str,
                "original_descriptions": [str, str],
                "merged_signal_refs": [str]
            }
        ],
        "consolidation_flags": [
            {
                "cell_id": str,
                "candidates_in": int,
                "ccis_out": int,
                "ratio": float
            }
        ],
        "integrity_violations": [
            {
                "signal_id": str,
                "concern_id": str
            }
        ]
    },
    "mode_violations": []
}
```

---

#### §12.6 Module Structure for Pass 3b

```
mechanisms/cci_construction/
  __init__.py                        # Orchestration entry point — Steps 1–6
  step1_signal_assembly.py           # DM: eligible Signal query
  step2_zachman_cell_upsert.py       # DM: ZachmanCell upsert + Signal grouping
  step3_cci_derivation.py            # IM+DM: per-cell AI derivation + entity production
  step4_deduplication.py             # DM+IM+DM: structural pre-filter + AI review + merge
  step5_commit.py                    # DM: identifier allocation + ledger write
  step6_analysis_pass.py             # DM: AnalysisPass record production
  prompts/
    cci_derivation_prompt.py         # Template: per-cell Signal-to-CCI derivation
    dedup_semantic_review_prompt.py  # Template: semantic equivalence review
    column_interrogatives.py         # Row × Column framing table (§12.2.1)
    column_vocabulary.py             # Permitted classification_type values per column (§5.1)
  schemas/
    cci_construction_response_schema.py  # Pydantic: AI derivation response validation
    dedup_review_response_schema.py      # Pydantic: AI deduplication response validation
```

**Design decisions inherited from Row 4 Applied and v0.2 framework:**
- Single transactional ledger write (Row 4 Applied §5)
- AI invocations outside the Postgres transaction (Row 4 Applied §5)
- Pydantic validation at AI response boundary (§9.4.3)
- AI model fingerprinting on AnalysisPass (§9.5.3)
- ProjectProfile parameters read at invocation time (not hard-coded)

---

#### §12.7 Verification Criteria Additions (extending §8)

The following verification criteria extend the framework's §8 pattern for Pass 3b specifically. They map directly to the decidable and plausibility criteria in Row 3 Mechanism Spec §8.

**Automated verification additions for Pass 3b:**

| **ID** | **Criterion** | **Test type** |
| --- | --- | --- |
| **VER-3b-01** | 6 ZachmanCells exist for row after Pass 3b | pytest assertion: count ZachmanCell WHERE row_target = row_ref == 6 |
| **VER-3b-02** | All ci_id values match canonical regex | pytest assertion: all ci_ids pass `^CCI-ROW[1-6]-C-(What\|How\|Where\|Who\|When\|Why)-\d{3}$` |
| **VER-3b-03** | All CCI.cell_id values resolve to existing ZachmanCells | pytest: referential integrity check |
| **VER-3b-04** | All CCI.signal_refs entries resolve to existing Signals | pytest: referential integrity check |
| **VER-3b-05** | classification_type values within permitted vocabulary per column | pytest: enumeration check using column_vocabulary.py |
| **VER-3b-06** | All confidence values within [0.0, 1.0] | pytest: range assertion |
| **VER-3b-07** | Sequence numbers unique per cell | pytest: for each column, verify no duplicate sequence numbers among CCIs for that cell |
| **VER-3b-08** | CellContentItemRegister includes all ci_ids for row | pytest: register membership check |
| **VER-3b-09** | AnalysisPass with mechanism="CellContentItemConstruction" exists | pytest: query by mechanism string |
| **VER-3b-10** | Non-Loss: every Signal grounds at least one CCI or appears in integrity_violations | pytest: for each Signal in step 1 working set: signal_id in at least one CCI.signal_refs OR in AnalysisPass integrity_violations |

**Plausibility checklist for Practitioner review:**

After Replit Agent build and automated verification pass, Practitioner reviews:
1. Select one populated cell. Review all CCIs for that cell against the cell's Signals. Do the CCI descriptions express the Signals' classified meaning without being verbatim copies?
2. For each merge recorded in AnalysisPass.outputs.cci_data.merges: do the original descriptions describe the same thing? Does the surviving description capture both?
3. Are any consolidation flags present? If so, review the flagged cell's surviving CCIs and compare to the Signal count for that cell.

---

## Document End

End of SysEngage Row 4 Understanding v0.3.

v0.3 adds §12 (Pass 3b CellContentItem Construction implementation framework). All prior §1–§11 content from v0.2 is authoritative and unchanged.

Companion artefacts produced with this version:
- SysEngage_Row_3_Mechanism_CCI_Construction_v0_1.md — Row 3 architectural spec
- SysEngage_Row_4_Mechanism_CCI_Construction_v0_1.md — Row 4 implementation spec
- SysEngage_Issues_Tracker_v0_27.md — tracker (F40 recorded)
