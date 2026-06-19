# RD v0.17 — Spec Review

**Against:** `SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_17.md`  
**Baseline review:** `RD_v0_16_Spec_Review.md`  
**Date:** 2026-06-09  
**Reviewer:** Replit Agent

---

## Summary

| Category | Count |
|---|---|
| v0.16 findings fully resolved | 2 of 2 |
| New findings in v0.17 | 1 |
| Code docstring debt (carried from v0.15 / v0.16 — still open) | 2 |
| **Code action required** | **2 (docstrings only)** |
| **Spec doc update required** | **1** |

---

## v0.16 Finding Status

| ID | Finding | v0.17 Status |
|---|---|---|
| SPEC-16-A | §4.4.2 "guaranteed under MD-1" had no Path-R carve-out | ✅ Fixed — line 217 now qualifies the assertion "for a CCI-bearing proposal" and appends the full Path-R fallback clause referencing MD-2 §3.2 |
| SPEC-16-B | §12.5 primary inputs still said "v0.5" | ✅ Fixed — line 1003 now reads "Row 4 Requirement Derivation v0.17" |

---

## Open Findings

### SPEC-17-A — Filename header still says v0_16 *(LOW — stale carry-over; same pattern as SPEC-D)*

**Location:** Line 5

**Current text:**
> `Filename: SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_16.md`

**Problem:** The filename header was correctly updated in v0.16 (from v0_5 to v0_16). v0.17 bumped the version note but did not update the filename line a second time. The pattern: this field is updated on major revisions but missed again when a revision is smaller in scope.

**Required update:** `v0_16.md` → `v0_17.md`

---

## Code Docstring Debt (carried from v0.15, v0.16 — still open)

The v0.17 version note explicitly re-flags these: *"Two stale code docstrings remain (stage1_preflight.py L12 'two-part hash'; stage2_ai_derivation.py L4 'Spec v0.13') — code-side, flagged for the agent, not resolved in this spec."*

| File | Current (stale) | Required |
|---|---|---|
| `stage1_preflight.py` line 12 | `"two-part SHA-256 hash (CCI-ids + active Domain-ids)"` | `"three-part SHA-256 hash for rows ≥ 2 (CCI\|DOM\|SEEDS); two-part for Row 1"` |
| `stage2_ai_derivation.py` line 4 | `"Per Requirement Derivation Mechanism Spec v0.13 §4.2"` | `"Per Requirement Derivation Mechanism Spec v0.17 §4.2"` |

These are one-line edits with no functional impact.

---

## Implementation Conformance Snapshot

Spec changes introduced across the v0.15–v0.17 cycle remain fully implemented:

| Item | Spec location | Impl status |
|---|---|---|
| Three-part hash for rows ≥ 2 (CCI\|DOM\|SEEDS) | MD-3 (§3.2), §4.1, OQ-3d-01 | ✅ stage1_preflight.py |
| Path R one combined batch | §4.2 | ✅ stage2_ai_derivation.py |
| `refines_refs` set at derivation for Path R | §4.4.3 | ✅ stage4_entity_production.py |
| MD-2 Path R `source_domain_id` fallback | MD-2 (§3.2), §4.4.2 | ✅ stage4_entity_production.py |
| VER-3d-21 provenance guard | §8.1 | ✅ stage2 + stage3 |
| `empty_seed_set_upstream_gap` warning | §4.2 | ✅ run_stage2 |
