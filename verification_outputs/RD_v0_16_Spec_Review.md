# RD v0.16 — Spec Review

**Against:** `SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_16.md`  
**Baseline review:** `RD_v0_15_Spec_Review.md`  
**Implementation baseline:** checkpoint `d0acc9a1` (v0.15 gaps reviewed)  
**Date:** 2026-06-09  
**Reviewer:** Replit Agent

---

## Summary

| Category | Count |
|---|---|
| v0.15 findings fully resolved | 5 of 6 |
| v0.15 findings partially resolved (residual) | 1 |
| New findings in v0.16 | 1 |
| Code docstring debt (carried from v0.15, still open) | 2 |
| **Code action required** | **2 (docstrings only)** |
| **Spec doc update required** | **2** |

---

## v0.15 Finding Status

| ID | Finding | v0.16 Status |
|---|---|---|
| SPEC-A | §12.2 OQ-3d-01 said "two-part hash" | ✅ Fixed — line 979 now correctly documents two-part at Row 1, three-part at rows ≥ 2 |
| SPEC-B | §12.5 deviation bullet said "two-part" | ✅ Fixed — line 1021 now matches MD-3 |
| SPEC-C | §4.4.3 `refines_refs=[]` contradicted §4.2 Path R | ✅ Fixed — line 217 now reads "set **at derivation** for a Path-R child … **empty** for a Path-N row-native proposal" |
| SPEC-D | Filename header said v0_5 | ✅ Fixed — line 5 now reads `v0_16.md` |
| SPEC-E | §4.4.2 MD-2 Path R fallback undocumented | ⚠️ Partially fixed — MD-2 (§3.2) updated; §4.4.2 prose still inconsistent (see SPEC-16-A below) |
| SPEC-F | §4.2 Path R batching spec/impl divergence | ✅ Fixed — line 156 now says "one combined batch"; per-Domain batching noted as deferred |

---

## Open Findings

### SPEC-16-A — §4.4.2 prose still says "guaranteed under MD-1" without Path R carve-out *(MEDIUM — internal inconsistency)*

**Location:** §4.4.2 domain_refs DM-derivation (line ~215)

**Current text:**
> `domain_refs = sorted(...)`. Assert `len(domain_refs) >= 1` (**guaranteed under MD-1 post-CHK-3d-03**) and every referenced Domain `row_target == str(current_row)`. Empty result → fail closed...

**Problem:** The fix for SPEC-E was correctly applied to MD-2 (§3.2, line 103), which now reads: *"empty result with empty `cci_refs` → fall back to `source_domain_id`; empty result with non-empty `cci_refs` → fail closed"*. However, the §4.4.2 implementation prose (the companion procedural section) was not updated. The assertion *"guaranteed under MD-1 post-CHK-3d-03"* is still written without a Path R carve-out — a reader following the §4.4.2 step-by-step will not see the fallback rule and will conclude that all empty `domain_refs` results fail closed. This contradicts MD-2 (§3.2) and the implementation.

**Required update — append to the §4.4.2 fail-closed clause:**
```
Empty result with non-empty cci_refs → fail closed (log MD-2 validation_failure;
re-run CHK-3d-05 on the reduced set). Exception — Path-R proposals with empty
cci_refs: the intersection is structurally empty (no row-n CCI references);
use source_domain_id as the sole domain_ref (see MD-2 §3.2 Path-R fallback).
The MD-1 "guaranteed" note applies to Path-N proposals only.
```

---

### SPEC-16-B — §12.5 primary inputs still references "v0.5" *(LOW — stale carry-over)*

**Location:** §12.5 "Replit Agent task structure", primary inputs list (line ~1001)

**Current text:**
> `- This spec (Row 4 Requirement Derivation v0.5) — implementation authority (DDL §5.1, schemas §5.2, guidance §5.4)`

**Problem:** This bullet carries the original v0.5 version label through all subsequent revisions. It has never been updated. As of v0.16 it should read v0.16.

**Required update:** `v0.5` → `v0.16`

---

## Code Docstring Debt (carried from v0.15 — still open)

The v0.16 version note correctly flags these as *"code change, not spec"*, but both remain unimplemented.

| File | Current (stale) | Required |
|---|---|---|
| `stage1_preflight.py` line 12 | `"two-part SHA-256 hash (CCI-ids + active Domain-ids)"` | `"three-part SHA-256 hash for rows ≥ 2 (CCI\|DOM\|SEEDS); two-part for Row 1"` |
| `stage2_ai_derivation.py` line 4 | `"Per Requirement Derivation Mechanism Spec v0.13 §4.2"` | `"Per Requirement Derivation Mechanism Spec v0.16 §4.2"` |

These are one-line edits with no functional impact.

---

## Implementation Conformance Snapshot

All v0.15/v0.16 spec changes confirmed matching the implementation:

| Item | Spec location | Impl status |
|---|---|---|
| Three-part hash for rows ≥ 2 (CCI\|DOM\|SEEDS) | MD-3 (§3.2), §4.1, OQ-3d-01 | ✅ stage1_preflight.py |
| Path R one combined batch; per-Domain deferred | §4.2 line 156 | ✅ stage2_ai_derivation.py `_run_path_r` |
| `refines_refs` set at derivation for Path R | §4.4.3 line 217 | ✅ stage4_entity_production.py line 754 |
| MD-2 Path R `source_domain_id` fallback | MD-2 (§3.2) | ✅ stage4_entity_production.py lines 619–624 |
| VER-3d-16 updated (Path-R children non-empty) | §8.1 VER-3d-16 | ✅ spec; impl commits refines_refs for Path R |
| VER-3d-21 provenance guard | §4.2, §8.1 | ✅ stage2 + stage3 |
| `empty_seed_set_upstream_gap` warning | §4.2 | ✅ run_stage2 |
| `chk3d10_seed_extinct` warning type | §4.3 CHK-3d-10 | ✅ stage3 |
| VER-3d-03 `cci_refs OR refines_refs` | §8.1 | ✅ spec + migration 025 |
| §5.1 DDL: `cci_refs` MAY be empty for Path R | §5.1 line 266 | ✅ spec + migration 025 |
