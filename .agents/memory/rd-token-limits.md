---
name: RD mechanism AI token limits
description: stage2 Path R and stage3 CHK-3d-10 repair had max_tokens too low for higher rows; caused parse failures on Row 5.
---

## Rule

`max_tokens` must accommodate the full output for the largest plausible seed set. At ~300 tokens per proposal, 26 seeds × 1–2 proposals = 8K+ tokens minimum.

| Call site | Old limit | Fixed limit | Why it mattered |
|---|---|---|---|
| `stage2_ai_derivation._call_ai` default | 4096 | **8192** | Path R for all rows; 26 seeds hit ceiling |
| `stage3_structural_validation._call_repair_ai` default | 2048 | **4096** | CHK-3d-09 orphan repair |
| `stage3` CHK-3d-10 inline repair call | 2048 | **8192** | Repair receives ALL unrefined seeds at once |

**Why:** Rows 1–4 squeaked under the old limits (fewer seeds, shorter physical-level statements). Row 5 (26 seeds, implementer-level elaboration) reliably truncated mid-JSON → `json.loads()` threw → `path_r_parse_failure` warning, zero proposals returned. Both initial attempt AND retry failed, then repair also failed (same 2048 limit on all unrefined seeds).

**How to apply:** Whenever adding a new AI call that processes a variable-length seed set, budget at least `max(seeds) × 400` tokens for output. For full-row calls (all seeds at once) with claude-sonnet-4-5 (64K output cap), 8192 is the safe floor; raise to 16384 if seeds regularly exceed 40.

**Diagnostic signal:** `path_r_parse_failure` warning with no `detail` field = truncation (response cut mid-JSON). After this fix, the warning also captures `response_preview` (first 200 chars) to distinguish truncation from hallucinated non-JSON responses.
