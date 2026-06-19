# RD v0.14 — Implementation Status Report

**For:** SW agent review  
**Date:** 2026-06-09  
**Scope:** PMT rows 1–4, Pass 3d (Requirement Derivation)

---

## Bugs Found and Fixed This Session (3)

### BUG-1 — Priority vocabulary mismatch (Row 2)

| Field | Detail |
|---|---|
| **Symptom** | Stage4 `CheckViolation` on `ck_requirement_priority` |
| **Root cause** | `requirement_refinement_prompt.py` and the refinement response schema used MoSCoW vocabulary (`Must`/`Should`/`Could`) for the `priority` field; DB constraint requires `High`/`Medium`/`Low` |
| **Fix** | `schemas/requirement_refinement_response_schema.py` — type changed to `Optional[Literal["High","Medium","Low"]]`; `prompts/requirement_refinement_prompt.py` — vocabulary corrected to `High`/`Medium`/`Low` |
| **Status** | ✅ CLOSED |

---

### BUG-2 — Path R proposals rejected at INSERT (rows 3+)

| Field | Detail |
|---|---|
| **Symptom** | Stage4 `CheckViolation` on `ck_requirement_cci_refs_nonempty` |
| **Root cause** | Path R proposals have `cci_refs=[]` at derivation by design (CHK-3d-02 relaxed in v0.13). The original constraint predated Path R and required `jsonb_array_length(cci_refs) >= 1` unconditionally. |
| **Fix** | Migration `025_relax_cci_refs_nonempty_for_path_r.py` — drops the old constraint and recreates it as: `jsonb_array_length(cci_refs) >= 1 OR jsonb_array_length(refines_refs) >= 1`. Applied automatically via the dispatch migration step on next run. |
| **Status** | ✅ CLOSED |

---

### BUG-3 — False `IdempotentRerun` at Row 4 (Path R produces 0)

| Field | Detail |
|---|---|
| **Symptom** | `path_r=0`, 30 CHK-3d-10 `elaboration_gaps` at Row 4 |
| **Root cause** | BUG-2 caused Row 3 to fail at stage4 in R4_Run3 → 0 Row 3 requirements committed → Row 4 ran Path N only and recorded `Completed` with hash `H(CCIs_4, DOMs_4)`. When BUG-2 was fixed, Row 3 succeeded → 30 Row 3 requirements written → Row 4 stage1 computed the same `H(CCIs_4, DOMs_4)` — the seed set from Row 3 was not in the hash → `IdempotentRerun` triggered → stage2 skipped entirely → `path_r=0` again. |
| **Fix** | `stage1_preflight.py` — for `row_ref >= 2`, the sorted `requirement_id`s of surviving row n−1 requirements are appended as a third hash segment: `"CCI:..\|\|DOM:..\|\|SEEDS:<sorted ids>"`. Any change in row n−1 requirements now invalidates row n's cached hash → `FullRerun` → stage2 runs → seeds loaded → Path R fires. |
| **Spec note** | This is a pragmatic fix; the spec (MD-3) still documents a two-part hash. MD-3 needs a spec update — see open items below. |
| **Status** | ✅ CLOSED |

---

## VER-3d-21 and Empty Seed Set Warning — Spec v0.14 Gaps (Implemented)

### GAP-1 — VER-3d-21 not implemented

| Field | Detail |
|---|---|
| **Spec requirement** | `len(seed_set) == count(surviving row n−1 requirements)`. Guards against a provenance filter (`cci_refs`/`refines_refs`) creeping into `_load_seeds` and silently excluding row-native Path-N seeds. The R4_Run4 defect was 24 seeds instead of 27. |
| **Fix** | `Stage2Result` gains `seed_set_surviving_count: int = 0`. `run_stage2` runs an independent `COUNT(*)` with the minimal predicate (`project_id + row_target + retired_at IS NULL` only) alongside `_load_seeds`. Stage3 compares `len(seed_set)` against `surviving_count`; a mismatch emits a `ver3d21_seed_set_size_mismatch` structured warning. |
| **Status** | ✅ IMPLEMENTED |

### GAP-2 — `empty_seed_set_upstream_gap` warning not emitted

| Field | Detail |
|---|---|
| **Spec requirement** | When seed_set is empty at `row >= 2`, emit structured warning `empty_seed_set_upstream_gap`. Previously only a plain `log.warning` on exception; nothing emitted when seeds were genuinely zero with no error. |
| **Fix** | `run_stage2` — after seed load, if `row_ref >= 2` and `seed_set` is empty, appends `{"type": "empty_seed_set_upstream_gap", "parent_row_ref": row_ref - 1}` to `execution_warnings`. |
| **Status** | ✅ IMPLEMENTED |

---

## Spec Errors in v0.14 — Doc Updates Required (not code changes)

### SPEC-1 — MD-3 hash formula (§3.2) still says "two-part"

BUG-3's fix adds a third `||SEEDS:` segment for `row_ref >= 2`. MD-3 as written describes a formula the code no longer implements.

**Required update:**
```
MD-3 — Three-part input hash for rows >= 2 (rows = 1: two-part, unchanged)

requirement_input_hash = SHA-256(
  "CCI:" + "|".join(sorted(ci_ids))
  + "||DOM:" + "|".join(sorted(active_domain_ids))
  + "||SEEDS:" + "|".join(sorted(surviving_row_n-1_requirement_ids))   # rows >= 2 only
)
```

The sorted active Domain-id list is still stored separately in `mechanism_data.domain_id_set` for the Domain-set-change comparison. Row 1 hash remains two-part (no seeds).

---

### SPEC-2 — VER-3d-21 table entry missing from §8.1

VER-3d-21 is described inline in §4.2 but does not appear in the §8.1 decidable criteria table, and has no pytest fixture mapping.

**Required update:** Add to §8.1 table:

| ID | Criterion | pytest assertion |
|---|---|---|
| **VER-3d-21** | Seed-set size equals surviving row n−1 requirement count (provenance-blind guard): `len(seed_set) == count(retired_at IS NULL AND row_target = str(row−1))` | Assert `ver3d21_seed_set_size_mismatch` absent from `execution_warnings` in all producing runs; fixture seeds stage2 with a filtered list and asserts the mismatch warning fires |

---

### SPEC-3 — VER-3d-03 contradicts Path R (§8.1)

VER-3d-03 currently asserts: *"Non-empty `statement`; ≥1 `cci_refs`"*.

Path R requirements have `cci_refs=[]` at derivation by design (migration 025; CHK-3d-02 relaxed). VER-3d-03 as written would falsely fail every Path R requirement if automated.

**Required update:**
```
VER-3d-03 | Non-empty statement; ≥1 cci_refs OR ≥1 refines_refs
           | len(statement) > 0
           | AND (jsonb_array_length(cci_refs) >= 1
           |      OR jsonb_array_length(refines_refs) >= 1)
```

This matches the migration 025 constraint and CHK-3d-02 as relaxed in v0.13.

---

### SPEC-4 — §3.1 module listing missing Path R files

The following files are live and load-bearing but absent from the §3.1 module structure table:

```
prompts/requirement_refinement_prompt.py           # Path R prompt (stage2 + stage3 CHK-3d-10 repair)
schemas/requirement_refinement_response_schema.py  # Pydantic: Path R refinement response
```

Both are imported by `stage2_ai_derivation.py` and `stage3_structural_validation.py`.

**Required update:** Add both lines to §3.1.

---

## Cascade Pattern — For Future Reference

The three bugs form a cascade. Each upstream stage4 failure causes the downstream row to pass with `path_r=0` and record a `Completed` hash. When the upstream fix lands, the downstream row finds an unchanged `H(CCIs_n, DOMs_n)` → `IdempotentRerun` → same gap repeats one row lower.

```
R4_Run3:  Row 3 → stage4 ck_cci_refs FAIL → 0 reqs committed
          Row 4 → seeds empty → Path N only → Completed, hash=H4
                                                            ↓
BUG-2 fixed (migration 025):
          Row 3 → stage4 OK → 30 reqs committed
          Row 4 → H(CCIs_4,DOMs_4) == stored H4 → IdempotentRerun → path_r=0
                                                            ↓
BUG-3 fixed (||SEEDS: in hash):
          Row 4 → hash now H(CCIs_4,DOMs_4,SEEDS_4) ≠ stored H4 → FullRerun → Path R fires ✓
```

The `||SEEDS:` fix breaks this cascade permanently. Without it, each constraint fix would silently reproduce the wiring-gap symptom at the next row down.

---

## Files Changed

| File | Change |
|---|---|
| `alembic/versions/025_relax_cci_refs_nonempty_for_path_r.py` | NEW — relaxes `ck_requirement_cci_refs_nonempty` for Path R |
| `mechanisms/requirement_derivation/prompts/requirement_refinement_prompt.py` | EDITED — priority vocabulary `High`/`Medium`/`Low` |
| `mechanisms/requirement_derivation/schemas/requirement_refinement_response_schema.py` | EDITED — `priority` type corrected |
| `mechanisms/requirement_derivation/stage1_preflight.py` | EDITED — adds `_load_seed_ids()`, extends hash with `\|\|SEEDS:` for `row_ref >= 2` |
| `mechanisms/requirement_derivation/stage2_ai_derivation.py` | EDITED — adds `seed_set_surviving_count`, `_count_surviving_requirements()`, `empty_seed_set_upstream_gap` warning |
| `mechanisms/requirement_derivation/stage3_structural_validation.py` | EDITED — adds VER-3d-21 check before CHK-3d-10 |
