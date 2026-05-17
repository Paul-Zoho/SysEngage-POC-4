# Pass 3b Feedback Brief — PMT E2E Row 1 Ledger Review

**Date:** 16 May 2026
**Ledger reviewed:** PMT_E2E_phase3b_row_1.json (updated)
**Passes executed:** 5 CCIConstruction passes (1 Failed, 2 Success, 2 PartialSuccess)
**CCIs committed:** 19
**VER-3b criteria status:** FAIL (VER-3b-01, VER-3b-10)

---

## Finding 1 — CRITICAL: Non-Loss Violation (VER-3b-10 FAIL)

**23 of 29 Signals produce no CCIs.**

Only SG049–SG054 (6 Signals) are referenced by any CCI. The remaining 23 Signals — SG289–SG297, SG457–SG462, SG530, SG539–SG545 — are completely absent from the CCI output despite being in the SignalRegister and having row_target values in the ledger.

**Root cause identified from ledger data:**

The Step 1 Signal query is filtering correctly by `row_target = '1'` — but the ledger contains only 6 Signals with `row_target = '1'`. The other 23 Signals belong to rows 2, 3, 4, and 5:

```
row=1:  6 signals  (SG049–SG054)           ← processed
row=2:  9 signals  (SG289–SG297)           ← not processed — wrong row
row=3:  6 signals  (SG457–SG462)           ← not processed — wrong row
row=4:  1 signal   (SG530)                 ← not processed — wrong row
row=5:  7 signals  (SG539–SG545)           ← not processed — wrong row
```

The Step 1 query is working correctly — it correctly excluded Signals for other rows. The real problem is upstream: **the Row-Lens Source Re-Analysis (Pass 3a) for Row 1 only produced 6 Signals with `row_target=1`.** The remaining 23 Signals were produced by Pass 3a runs for rows 2, 3, 4, and 5 and are correctly stored under their respective `row_target` values.

**This is not a Pass 3b bug.** Pass 3b Step 1 is working as specified — it queries `row_target = str(row_ref)` and correctly retrieves only the 6 Row 1 Signals. The 19 CCIs produced from those 6 Signals are correct.

**Action required:**

Verify that Pass 3a for Row 1 was run to completion and produced the expected Signal set for `row_target=1`. If the Row 1 Pass 3a run only produced 6 Signals from the source documents, that is a Pass 3a output question — not a Pass 3b defect. Run Pass 3b against Row 2 (9 Signals) and Row 3 (6 Signals) to verify the mechanism works correctly on their Signal sets.

**VER-3b-10 status for the 6 Row 1 Signals:** All 6 are referenced by at least one CCI. Non-Loss is satisfied for the actual in-scope Signal set.

---

## Finding 2 — BUG: ZachmanCell Upsert Incomplete (VER-3b-01 FAIL)

**Only 5 ZachmanCells exist. `ZC-R1-C-Where` is missing.**

The ledger contains:
```
ZC-R1-C-How   ✓
ZC-R1-C-What  ✓
ZC-R1-C-When  ✓
ZC-R1-C-Who   ✓
ZC-R1-C-Why   ✓
ZC-R1-C-Where ✗  MISSING
```

**Spec requirement (Row 3 Mechanism Spec §4, Step 2a):** All six ZachmanCells MUST be upserted for the current row unconditionally — regardless of Signal population, regardless of whether any CCI will be assigned to that cell. Step 2a is an unconditional structural operation.

**Root cause:** Step 2a is likely only creating ZachmanCells for columns where Signals exist, or where the AI returns candidates. The Where column produced no CCIs across any pass, and no `ZC-R1-C-Where` entity was created. This means the upsert is conditional — it should not be.

**Fix required:** Step 2a must iterate over a fixed list of all six columns `[What, How, Where, Who, When, Why]` and upsert each cell_id unconditionally before any batch processing begins. The loop must not be gated on Signal availability or AI output.

**VER-3b-01 test assertion:** `SELECT COUNT(*) FROM zachman_cell WHERE row_target = '1'` must equal exactly 6.

---

## Finding 3 — BUG: cells_populated Miscounting

**Passes 1 and 3 report `cells_populated=0` and `cells_empty=6` despite reporting `ccis_created=13`.**

This is internally inconsistent — if 13 CCIs were created and committed, at least some cells must be populated.

**Likely cause:** The `cells_populated` count in Step 6 AnalysisPass production is being computed before the Step 5 transaction commits, or it is querying the ledger for existing CCIs before the new CCIs are visible (reading outside the transaction). The count is reading the pre-commit state (zero CCIs) rather than the post-commit state (13 CCIs).

**Fix required:** `cells_populated` must be computed from the in-memory data structures at the end of Step 5, not from a post-commit ledger query. Specifically: count the number of distinct `cell_id` values among the CCIs that were successfully INSERTed in Step 5. This is available in memory without any database read.

**PartialSuccess passes (4 and 5) do not show this bug** — they correctly report `cells_populated=4` and `cells_populated=5` respectively, suggesting the fix was partially applied but only works on re-runs where existing CCIs are already in the ledger and the query returns non-zero results.

---

## Finding 4 — OBSERVATION: Consolidation Flags at ratio=1.0

Passes 4 and 5 show consolidation flags for multiple cells with `ratio=1.0` — every new candidate was merged into an existing CCI, producing zero net new entities for those cells.

This is **correct behaviour**, not a bug. It confirms the re-run deduplication model is working: Passes 4 and 5 are re-runs against the same 6 Signals, so all candidates produced by Stage 3a are semantic equivalents of existing committed CCIs. The AI semantic review correctly identifies them as duplicates and the merge rule applies.

The `ratio=1.0` flag fires because the threshold (default 0.80) is exceeded. This is the intended safety signal — it is telling the Practitioner that nothing new was added in this re-run. No action required; the flag is informational.

---

## Finding 5 — OBSERVATION: Where Column Coverage

The Where column (geography/location) has zero CCIs across all passes. This is analytically plausible for Row 1 of a pocket money tracking application — the 6 Row 1 Signals are intent and goal statements that do not reference locations or platforms. No action required for Pass 3b.

Note: once Finding 2 is fixed, `ZC-R1-C-Where` will exist as an empty cell, which Phase 5 Cell Quality Analysis will surface as a coverage question at the appropriate time.

---

## Finding 6 — OBSERVATION: Deduplication Performance

The current run uses 6 Signals in 1 batch, making the deduplication performance question moot at this scale. The 223-Signal concern raised before this run was hypothetical. **Defer performance investigation until a larger Signal set is available** — specifically, run Pass 3b against a row with 30+ Signals and measure actual Step 4 elapsed time before deciding whether to restructure the AI semantic review from pairwise to clustering.

The AnalysisPass records `elapsed_ms` — confirm this field is being populated and report its value for the Row 2 and Row 3 runs when available.

---

## Summary of Actions Required

| # | Priority | Finding | Action |
|---|---|---|---|
| 1 | Clarification | Non-Loss — 23 Signals excluded | Verify Pass 3a Row 1 output is complete. Not a Pass 3b bug — Step 1 query is correct. Run Pass 3b for rows 2–5 to confirm full coverage. |
| 2 | **Fix** | ZachmanCell upsert — Where missing | Step 2a must unconditionally upsert all 6 cells. Remove any conditional logic from the upsert loop. |
| 3 | **Fix** | cells_populated miscounting | Compute cells_populated from in-memory post-commit data, not from a pre-commit ledger query. |
| 4 | Informational | ratio=1.0 consolidation flags | Correct behaviour. No action. |
| 5 | Informational | Where column empty | Correct behaviour. Will surface in Phase 5. |
| 6 | Deferred | Deduplication performance | Measure on larger Signal set before redesigning. |

---

## VER-3b Status After This Run

| Criterion | Status | Notes |
|---|---|---|
| VER-3b-01 | **FAIL** | 5 cells, not 6. ZC-R1-C-Where missing. |
| VER-3b-02 | PASS | All ci_ids match `^CCI-ROW1-C-...-\d{3}$` |
| VER-3b-03 | PASS | All CCI.cell_id values resolve to existing ZachmanCells |
| VER-3b-04 | PASS | All signal_refs resolve to existing Signals |
| VER-3b-05 | PASS | All classification_types within column vocabulary |
| VER-3b-06 | PASS | All confidence values within [0.0, 1.0] |
| VER-3b-07 | PASS | Sequence numbers unique per cell |
| VER-3b-08 | PASS | CellContentItemRegister present (not verified member count) |
| VER-3b-09 | PASS | AnalysisPass with mechanism="CCIConstruction" exists |
| VER-3b-10 | PASS* | All 6 in-scope Row 1 Signals referenced. *23 excluded Signals belong to other rows — not a Pass 3b failure. |

**Fix Findings 2 and 3, re-run, and confirm VER-3b-01 passes before proceeding to Pass 3c design.**
