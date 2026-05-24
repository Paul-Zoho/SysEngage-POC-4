# Pass 3b Analysis Report — PMT Named Instance Fix Review

**Date:** 16 May 2026
**Report covers:** Runs 2, 5, 7 — dedup-disabled baseline through named-instance prompt fix
**Agent task version:** v0.9 spec + named-instance prompt update
**Purpose:** Inform the Agent of current state, three prioritised fixes, and precise verification criteria

---

## Executive Summary

Run 7 is a mixed result. The mechanism infrastructure is working correctly — clean baseline, all VER-3b structural criteria passing, Stage 4b bypass logic activating. But three issues prevent sign-off:

1. **`is_named_instance` field is not persisted to the ledger** — the field exists in memory at Stage 4b (the bypass fired, proving it) but is absent from all 54 committed CCIs. Root cause: `CCICandidateModel` and the `cell_content_item` table are missing the column.

2. **The bypass fired for the wrong group** — ZC-R5-C-Who/Actor fired when it should not have. The named-instance rule must be tightened to single-Signal scope only.

3. **Row 3 regression** — 5 CCIs from 6 Signals (Run 7) vs 18 CCIs (Run 2 baseline). All 6 Row 3 Signals are referenced, so Non-Loss technically passes, but cell coverage collapsed from 4 cells to 3 cells, and ZC-R3-C-What is entirely empty. The updated prompt's stricter derivation rules are suppressing legitimate Row 3 content.

---

## Run Comparison

| Metric | Run 2 (no dedup) | Run 5 (dedup v0.9) | Run 7 (v0.9 + prompt fix) |
|---|---|---|---|
| Total CCIs | 69 | 62 | 54 |
| Cells populated | 19 | 20 | 17 |
| Row 1 CCIs | 15 | 12 | 17 |
| Row 2 CCIs | 25 | 25 | 23 |
| Row 3 CCIs | 18 | 14 | **5** |
| Row 4 CCIs | 2 | 2 | **1** |
| Row 5 CCIs | 9 | 9 | 8 |
| R5 Where CCIs | 3 | 2 | 2 |
| Named-instance bypass fires | n/a | 0 | 1 (wrong cell) |
| surviving_ci_id populated | n/a | No | No |
| R3 What column | Populated | Populated | **Empty** |

---

## Finding 1 — CRITICAL: `is_named_instance` Not Persisted to Ledger

### Evidence

Run 7 has zero CCIs with the `is_named_instance` field present:
```
Field present: 0 of 54 CCIs
is_named_instance=True: 0
is_named_instance=False: 0
Field absent: 54
```

Yet the Stage 4b bypass fired for ZC-R5-C-Who/Actor with `member_count: 2`. The bypass logic checks `candidate.is_named_instance == True` at Stage 4b. For it to have fired, the field **must have been present on the in-memory candidate structs** at the point Stage 4b ran.

### Diagnosis

The field is in the AI response, is parsed into the in-memory candidate struct at Stage 3b, and is read correctly by Stage 4b. But it is not written to the database at Step 5 because:

- `CCICandidateModel` (Pydantic) does not declare `is_named_instance` as an attribute → field is silently dropped during struct validation
- OR `cell_content_item` database table does not have an `is_named_instance` column → SQLAlchemy silently ignores it during INSERT

Both are likely present simultaneously. The field must be added to both.

### Fix Required

**1. Database migration** (new migration file, e.g. `008_cci_named_instance.py`):
```sql
ALTER TABLE cell_content_item
ADD COLUMN is_named_instance BOOLEAN NULL DEFAULT NULL;
```
Nullable with no default — existing CCIs have no value for this field and that is correct. Do not default to `false` — the absence of the field is semantically distinct from `false`.

**2. `CCICandidateModel` Pydantic update:**
Add `is_named_instance: Optional[bool] = None` to the model. This ensures the field is not stripped during Stage 3b entity production.

**3. `CellContentItemModel` SQLAlchemy update:**
Add `is_named_instance: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)` to the model.

**4. Ledger export / db_reader:**
Ensure `is_named_instance` is included in the CCI JSON export so it appears in the output document for verification.

### Verification

After fix: query any Run 7 re-run for CCIs where `is_named_instance IS NOT NULL`. The iOS, Android, Windows CCIs from SG545 should each carry `is_named_instance=True`. The `stage4b_named_instance_bypass` warning for ZC-R5-C-Where should appear in execution_warnings.

---

## Finding 2 — BUG: Bypass Firing for Wrong Group

### Evidence

Run 7 execution_warnings for Row 5:
```python
{
  'warning_type': 'stage4b_named_instance_bypass',
  'detail': {
    'cell_id': 'ZC-R5-C-Who',
    'classification_type': 'Actor',
    'member_count': 2
  }
}
```

The two Who/Actor CCIs that triggered the bypass:
- `CCI-ROW5-C-Who-001`: Child user actor — grounded in **SG539**
- `CCI-ROW5-C-Who-002`: Parent user actor — grounded in **SG540**

These come from **two different Signals** (SG539 and SG540). They are not named instances from a single Signal — they are independent CCIs that happen to share the same `classification_type`. The bypass should not have fired. The fact it did means the AI set `is_named_instance=True` on both, which is incorrect under the spec rule.

### Root Cause

The prompt's Rule 5 says "when a Signal describes multiple distinct named items of the same classification type" but does not explicitly state that all instances must share **the same single Signal**. The AI interpreted Child (SG539) and Parent (SG540) as two named actors worth preserving — correct intuition, wrong mechanism.

### Fix Required

**Prompt update — tighten Rule 5:**

Add to the rule, after the definition of named instances:

```
IMPORTANT CONSTRAINT: is_named_instance: true ONLY applies when ALL instances
in the group share THE SAME SINGLE Signal in signal_refs. If two CCIs of the
same classification type come from DIFFERENT Signals, they are independent CCIs —
do NOT set is_named_instance: true. Stage 4b will adjudicate them via the normal
cluster review.

CORRECT — same single Signal producing 3 named nodes:
  signal_refs: ["SG545"] → iOS Node (is_named_instance: true)
  signal_refs: ["SG545"] → Android Node (is_named_instance: true)
  signal_refs: ["SG545"] → Windows Node (is_named_instance: true)

INCORRECT — different Signals, NOT named instances:
  signal_refs: ["SG539"] → Child Actor (is_named_instance: false)
  signal_refs: ["SG540"] → Parent Actor (is_named_instance: false)
  These come from different Signals — they are independent CCIs, not named instances.
```

**Stage 4b bypass logic update:**

Add a second condition to the bypass check. The bypass should only fire when:
1. All new candidates in the group carry `is_named_instance=True` AND
2. All new candidates in the group share identical `signal_refs` (same single Signal)

If condition 2 is not met — candidates carry `is_named_instance=True` but from different Signals — proceed to the AI cluster review normally. The AI's flag was incorrectly set and should not be trusted for bypass.

In `step4_deduplication.py`, update the bypass condition:
```python
# Current (incorrect):
all_named = all(c.is_named_instance for c in new_candidates_in_group)
if all_named:
    bypass  # WRONG - doesn't check signal_refs

# Correct:
all_named = all(c.is_named_instance for c in new_candidates_in_group)
all_same_signal = len(set(frozenset(c.signal_refs) for c in new_candidates_in_group)) == 1
if all_named and all_same_signal:
    bypass  # Correct - named instances from same single Signal
```

### Verification

After fix: run against clean snapshot. ZC-R5-C-Who should NOT produce a bypass warning. ZC-R5-C-Where SHOULD produce a bypass warning with `member_count: 3`.

---

## Finding 3 — REGRESSION: Row 3 Coverage Collapsed

### Evidence

| Row 3 metric | Run 2 (no dedup) | Run 5 (v0.9) | Run 7 (prompt fix) |
|---|---|---|---|
| CCIs total | 18 | 14 | **5** |
| Cells populated | 4 | 4 | **3** |
| What column | 6 CCIs | 7 CCIs | **0 CCIs** |
| How column | 6 CCIs | 5 CCIs | 3 CCIs |
| When column | 3 CCIs | 2 CCIs | 1 CCI |
| Why column | 3 CCIs | — | 1 CCI |

All 6 Row 3 Signals ARE referenced by at least one CCI (Non-Loss passes). But the coverage has dramatically thinned. The Row 3 Signals are:

```
SG457 [Normative] conf=0.70 — Logical association rule: task completion → child entity links
SG458 [Normative] conf=0.68 — Data visibility: child access to task collections
SG459 [Normative] conf=0.72 — Temporal aggregation: weekly earned amount computation
SG460 [Normative] conf=0.71 — Reporting interface: parent view of earnings/completion
SG461 [Normative] conf=0.75 — Periodic reset: weekly task availability cycle
SG462 [Normative] conf=0.66 — Data retention: historical record persistence
```

Prior runs derived 14–18 CCIs from these 6 Signals across What, How, When, Why columns. Run 7 derives only 5 CCIs, all in How/When/Why, with ZC-R3-C-What entirely empty. Yet SG457–SG462 clearly contain entity content (logical task records, child entities, earnings records) that should populate the What column.

### Diagnosis

The updated prompt's Rule 1 (atomic content — "one clause, not a list") and Rule 2 (derived statements — "do not copy Signal text verbatim") are causing the AI to apply stricter filtering, particularly on Signals with lower confidence (SG458 at 0.68, SG462 at 0.66). At Row 3's Designer abstraction level, these Signals are more abstract and indirect — the AI appears to be rejecting derivations it is uncertain about rather than producing lower-confidence CCIs.

The Row 3 What column contains entities like "Task", "TaskRecord", "EarningsRecord" — these are implied by the Signal content but not explicitly named as entities. The updated prompt's stricter Rules 1 and 2 may be suppressing these implied-but-valid derivations.

### Fix Required

Add a "prefer coverage over precision" instruction to the prompt for lower-confidence situations:

```
7. COVERAGE PREFERENCE
   When Signal content suggests a classified item but you are uncertain about
   the exact formulation, prefer producing the CCI with a lower confidence value
   over not producing it at all. A CCI with confidence 0.65 that may need
   Practitioner review is better than no CCI and lost content.
   
   This is especially important for:
   - What column entity derivation from process-oriented Signals
   - Higher abstraction rows (Row 3+) where entities are implied rather than named
   - Signals with confidence below 0.70
   
   The minimum confidence for a producible CCI is 0.50. Below that, use
   trigger_condition or justification to explain the uncertainty, but still
   produce the CCI.
```

### Verification

After fix: Row 3 should produce CCIs in the What column from SG457 (task entity), SG458 (task collection entity), SG459 (earnings aggregation entity), SG460 (reporting interface entity). The What column should have at minimum 3–4 Entity CCIs. Total Row 3 CCIs should return to 10+ range (may be lower than the 18 no-dedup baseline after legitimate dedup merges, but should not be 5).

---

## Finding 4 — PERSISTENT: `surviving_ci_id` Still `(pending)`

All 4 merge records in Run 7 show `surviving_ci_id=(pending)`. This has been present since Run 3 across 4 consecutive runs. The merge audit trail is incomplete — the surviving CCI's identifier is never recorded.

### Root Cause

The merge record is constructed and added to the `merges` buffer before Step 5 runs. Step 5 is where `ci_id` is allocated. The identifier does not exist at the time the merge record is written.

### Fix Required

Two-step fix:

**Step 1 — Write a placeholder during Stage 4c:**
When a merge is executed, if the surviving entity is a new candidate (no ci_id yet), record a temporary internal reference (e.g. the Python object id or a UUID) in the merge record.

**Step 2 — Update after Step 5 commit:**
After Step 5 allocates and commits identifiers, iterate through the `merges` buffer and replace any temporary references with the actual committed `ci_id`. Then write the AnalysisPass with the updated merges buffer.

This ensures `surviving_ci_id` always contains the committed ledger identifier.

### Verification

After fix: all merge records in the AnalysisPass should have `surviving_ci_id` matching a valid `ci_id` in the CCI set (format `CCI-ROW{n}-C-{col}-{seq}`). Zero `(pending)` values should appear.

---

## Summary of Actions for Agent

| # | Priority | Finding | Files to change |
|---|---|---|---|
| 1 | **Critical** | `is_named_instance` not persisted | Migration `008_cci_named_instance.py`; `CCICandidateModel`; `CellContentItemModel`; `db_reader` / ledger export |
| 2 | **Fix** | Bypass firing for wrong group | `prompts/cci_derivation_prompt.py` Rule 5 — add single-Signal constraint and counterexample; `step4_deduplication.py` — add `all_same_signal` condition to bypass check |
| 3 | **Fix** | Row 3 regression | `prompts/cci_derivation_prompt.py` — add Rule 7 coverage preference; lower confidence floor (0.50); add guidance for implied entities at higher abstraction rows |
| 4 | **Fix** | `surviving_ci_id` still pending | `step4_deduplication.py` / merge buffer construction; `step6_analysis_pass.py` — update merge records post-Step-5 commit |

---

## Verification Sequence

Run these checks in order after all four fixes are applied. Use a clean snapshot branch (`snap_PMT_ph03_3a_R5` or equivalent with zero CCIs).

**Check 1 — `is_named_instance` persistence:**
```sql
SELECT ci_id, is_named_instance, signal_refs
FROM cell_content_item
WHERE cell_id = 'ZC-R5-C-Where'
ORDER BY ci_id;
```
Expected: 3 rows, all with `is_named_instance = true`, all with `signal_refs = ['SG545']`.

**Check 2 — Correct bypass activation:**
```python
# In AnalysisPass.outputs.cci_data.execution_warnings
# Expect: one entry for ZC-R5-C-Where, NOT for ZC-R5-C-Who
assert any(
    w['warning_type'] == 'stage4b_named_instance_bypass'
    and w['detail']['cell_id'] == 'ZC-R5-C-Where'
    for w in execution_warnings
)
assert not any(
    w['warning_type'] == 'stage4b_named_instance_bypass'
    and w['detail']['cell_id'] == 'ZC-R5-C-Who'
    for w in execution_warnings
)
```

**Check 3 — Row 3 coverage recovery:**
```sql
SELECT cell_id, COUNT(*) as cci_count
FROM cell_content_item
WHERE cell_id LIKE 'ZC-R3-%'
GROUP BY cell_id
ORDER BY cell_id;
```
Expected: ZC-R3-C-What populated (≥3 CCIs). Total Row 3 CCIs ≥ 10.

**Check 4 — `surviving_ci_id` populated:**
```python
# In all AnalysisPass.outputs.cci_data.merges
for merge in merges:
    assert merge['surviving_ci_id'] != '(pending)'
    assert re.match(r'^CCI-ROW[1-6]-C-(What|How|Where|Who|When|Why)-\d{3}$',
                    merge['surviving_ci_id'])
```

**Check 5 — Full VER-3b suite:**
Run the standard `tests/test_cci_construction.py` suite. All 10 VER-3b criteria must pass (VER-3b-10 will still show SG289 as non-productive — this is the known open item, not a blocker).

---

## Document End

End of Pass 3b Analysis Report — Run 7.
Next run should be Run 8 on a clean snapshot branch after all four fixes applied.
