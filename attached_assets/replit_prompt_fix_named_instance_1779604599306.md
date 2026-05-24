# Pass 3b — Named Instance Prompt Fix Brief

**Date:** 16 May 2026
**Issue:** Stage 3a AI not populating `is_named_instance` field — iOS/Android/Windows still collapsing
**Run evidence:** PMT_Ph03_3b_CCIConstruction_R5_Run5.json
**Spec version:** v0.9 (Row 3), v0.9 (Row 4)

---

## Issue Description

The v0.9 spec added `is_named_instance` as an optional boolean to the Stage 3a response schema and a corresponding bypass in Stage 4b. The intent: when one Signal contains multiple distinct named items of the same classification type (e.g. iOS, Android, Windows as three separate Node CCIs), the AI flags each with `is_named_instance: true`, and Stage 4b skips the cluster review for that group — preserving all three rather than merging them.

**The field is in the schema. The mechanism is in Stage 4b. But it is not being used.**

Run 5 confirms this. ZC-R5-C-Where has 2 CCIs instead of the expected 3. Both committed CCIs show `is_named_instance=NOT PRESENT` — the AI did not populate the field at all. The Stage 4b bypass never fired (zero `stage4b_named_instance_bypass` warnings across all passes).

---

## Root Cause Analysis

The problem is not in the schema, the bypass logic, or Stage 4b. **The problem is in the Stage 3a prompt.**

Adding a field to the response schema does not tell the AI when or how to use it. The AI needs explicit instruction in the prompt about:
1. What named instances are
2. When to set `is_named_instance: true`
3. What output shape to produce (one CCI per named item, not one aggregate CCI)

Without that instruction, the AI does one of two things:
- Ignores the field entirely (as in Run 5, where neither CCI carries `is_named_instance`)
- Aggregates the named items into one description and produces a single CCI (e.g. "Multi-platform deployment specification encompassing iOS, Android, and Windows")

Both failure modes are visible in Run 5:
- Where-001 is an aggregate CCI: "Multi-platform deployment specification encompassing iOS, Android, and Windows"
- Where-002 is a single-platform CCI: "iOS platform deployment node specification"

The AI decided at Stage 3a to partially consolidate — producing one aggregate and one specific rather than three specific. This happens before deduplication even runs.

**Evidence from the merge audit:**
```
Row 5 merges:
  refs=['SG545'] surviving=(pending)
  - iOS platform deployment node specification for mobile operational execution.
  - Android platform deployment node specification for mobile operational execution.

  refs=['SG545'] surviving=(pending)
  - iOS platform deployment node specification for mobile operational execution.
  - Windows platform deployment node specification for desktop operational execution.
```

Stage 4b then merged iOS+Android and iOS+Windows into one surviving CCI each — but since the aggregate Where-001 was already committed, the final state is 2 CCIs (the aggregate and the iOS survivor) rather than 3 distinct platform nodes.

The prompt is not instructing the AI to:
- Produce one CCI per distinct named item
- Set `is_named_instance: true` on each
- Avoid aggregating named items into a single description

---

## Fix Required

Update `prompts/cci_derivation_prompt.py` with:

1. An explicit named-instance instruction block
2. A worked example showing the correct output shape
3. A clear prohibition on aggregating named items into a single CCI

The fix is prompt-only. No schema changes, no mechanism changes. The schema already has `is_named_instance`. Stage 4b already has the bypass. The prompt just needs to activate the pattern.

---

## Updated Prompt Specification

The following replaces the current `cci_derivation_prompt.py` template content. The additions are clearly marked.

---

### `cci_derivation_prompt.py` — Updated Template

```
You are performing CellContentItem (CCI) derivation for a SysEngage analysis pass.

CONTEXT
=======
Row: {row_ref} — {row_lens_description}
Signals to analyse: {signal_count} signals (batch {batch_number} of {batch_total})

ZACHMAN COLUMN FRAMEWORK
========================
Analyse the signals against all six Zachman columns simultaneously. For each column,
identify content in the signals that belongs to that column's interrogative at the
Row {row_ref} abstraction level:

{column_interrogatives_block}

PERMITTED CLASSIFICATION TYPES PER COLUMN
==========================================
{column_vocabulary_block}

SIGNALS
=======
{signals_block}

DERIVATION RULES
================

1. ATOMIC CONTENT ITEMS
   Each CCI must express one single, atomic piece of classified content.
   Do not combine multiple distinct concepts into one CCI description.
   A CCI description should be concise — one clause, not a list.

2. DERIVED STATEMENTS
   CCI descriptions are derived statements of classified meaning.
   Do not copy Signal text verbatim. Re-express the content in terms of
   the Zachman column's interrogative at this row's abstraction level.

3. SIGNAL GROUNDING
   Every CCI must be grounded in at least one Signal via signal_refs.
   Do not produce CCIs that cannot be traced to a Signal in the batch.
   signal_refs must only contain Signal IDs from the list above.

4. COLUMN ASSIGNMENT
   Assign each CCI to the most appropriate column.
   A single Signal may produce CCIs in multiple columns if the Signal
   contains content relevant to multiple interrogatives.

5. NAMED INSTANCES — CRITICAL RULE
   When a Signal describes multiple DISTINCT NAMED ITEMS of the same
   classification type, you MUST produce ONE SEPARATE CCI PER NAMED ITEM.
   Do NOT aggregate named items into a single CCI description.
   Set is_named_instance: true on EACH CCI in the named-instance group.

   Named instances are distinct, individually nameable things — such as:
   - Named platforms or operating systems (iOS, Android, Windows)
   - Named locations or deployment sites (London, New York, Singapore)
   - Named actors or roles (Child user, Parent user, Administrator)
   - Named events or triggers (WeeklyReset, MonthlyReview, OnLogin)
   - Named entities or data objects (Transaction, Account, Category)

   CORRECT — Three separate CCIs, each with is_named_instance: true:
   Signal: "The platform supports iOS, Android, and Windows deployment"
   Output:
     { "column": "Where", "classification_type": "Node",
       "description": "iOS mobile platform deployment node",
       "signal_refs": ["SG545"], "confidence": 0.90,
       "is_named_instance": true }
     { "column": "Where", "classification_type": "Node",
       "description": "Android mobile platform deployment node",
       "signal_refs": ["SG545"], "confidence": 0.90,
       "is_named_instance": true }
     { "column": "Where", "classification_type": "Node",
       "description": "Windows desktop platform deployment node",
       "signal_refs": ["SG545"], "confidence": 0.90,
       "is_named_instance": true }

   INCORRECT — Single aggregated CCI (never do this for named instances):
   Signal: "The platform supports iOS, Android, and Windows deployment"
   Output:
     { "column": "Where", "classification_type": "Node",
       "description": "Multi-platform deployment supporting iOS, Android, and Windows",
       "signal_refs": ["SG545"], "confidence": 0.90,
       "is_named_instance": false }

   The INCORRECT form loses the individual named deployment targets.
   The CORRECT form preserves each named target as a distinct analytical entity.

   Note: is_named_instance: true ONLY applies when a single Signal produces
   MULTIPLE CCIs of the SAME classification_type that are distinct named instances
   of that type. It does NOT apply to CCIs that are simply similar in nature
   but derived from different Signals, or CCIs of different classification types.

6. CONFIDENCE
   Assign confidence 0.0–1.0 reflecting how clearly the Signal supports
   the CCI's classification. 0.9+ for unambiguous content; 0.6–0.8 for
   content requiring inference; below 0.6 for speculative derivation.

OUTPUT FORMAT
=============
Respond ONLY with a valid JSON object. No preamble, no explanation, no markdown.

{
  "items": [
    {
      "column": "What|How|Where|Who|When|Why",
      "classification_type": "<type from permitted vocabulary for column>",
      "description": "<derived statement of classified meaning>",
      "signal_refs": ["<signal_id>"],
      "confidence": 0.0,
      "is_named_instance": false,
      "trigger_condition": null,
      "justification": null
    }
  ]
}

is_named_instance defaults to false. Only set to true per Rule 5 above.
trigger_condition: populate if the CCI applies only under a specific condition.
justification: populate if the classification requires explanation.
```

---

## Implementation Notes

**Template parameterisation:** The prompt template uses the same parameterisation pattern as the existing `cci_derivation_prompt.py`. The new content slots into the DERIVATION RULES section. Parameters `{row_ref}`, `{row_lens_description}`, `{column_interrogatives_block}`, `{column_vocabulary_block}`, `{signals_block}`, `{batch_number}`, `{batch_total}`, `{signal_count}` are all existing or trivially added.

**The worked example is load-bearing.** Without it the AI tends to ignore the named-instance rule on novel inputs. The iOS/Android/Windows example must be included verbatim — it is the concrete anchor that makes the rule actionable.

**`is_named_instance` in the response schema:** Already present in `cci_construction_response_schema.py` from v0.9. No schema changes needed.

**Stage 4b bypass:** Already implemented from v0.9. No mechanism changes needed. Once the prompt correctly populates `is_named_instance`, the bypass will activate and `stage4b_named_instance_bypass` entries will appear in `execution_warnings`.

**Test to verify fix:** After applying the prompt update, run Pass 3b against `snap_PMT_ph03_3a_R5` (or equivalent clean snapshot) with dedup enabled. ZC-R5-C-Where should produce exactly 3 CCIs, all with `is_named_instance=true`, and the AnalysisPass `execution_warnings` should contain one `stage4b_named_instance_bypass` entry for `{cell_id: "ZC-R5-C-Where", classification_type: "Node", member_count: 3}`.

---

## Open Items Not Addressed by This Fix

**`surviving_ci_id = "(pending)"` in merge records** — this has persisted across Runs 3, 4, and 5. The merge audit records are being written before Step 5 allocates identifiers. Fix: populate `surviving_ci_id` after the Step 5 transaction commits, updating the in-memory merge record before it is written to the AnalysisPass. This is a separate fix, not part of this brief.

**`non_productive_signals`** — SG289 still unreferenced. Separate fix.
