# SysEngage Issues Tracker

**Version:** 0.50
**Date:** 26 May 2026
**Status:** Active

**Changes from v0.49:** PMT Run 11 and NQPS Run 4 reviewed. Nuanced "and"/"&" test implemented across all rows. Repair prompt naming enforcement added. Row 2 "retention" vocabulary note added. F78 and F79 added (both Resolved).

---

## Status Summary

| Status | Count | Finding IDs |
|---|---|---|
| Open | 21 | F1, F2, F4, F5, F6, F8, F9, F12, F13, F14, F15, F16, F17, F19, F20, F21, F22, F33, F34, F40, F41, F42 |
| Action-Required | 3 | F43, F53, F66 |
| Conditionally Resolved | 1 | F35 |
| Resolved | 45 | F3, F7, F10, F11, F18, F23–F32, F37, F44, F45–F79 |
| Noted | 1 | F74 |
| Deferred | 9 | F33, F34, F36, F38, F39, F62, F63, F64, F68 |
| Wont-Fix | 0 | — |

**Total findings:** 79 (F1–F79)

---

## Active Findings — New in v0.50

### F78 — Nuanced "and"/"&" Test Replaces Blunt Prohibition → Mechanism Spec v0.24

**Status:** Resolved (26 May 2026, v0.50 cycle)
**Surfaced by:** NQPS Run 4 D005 "Regulatory and Social Responsibility" — correct grouping, blunt prohibition would have forced an incorrect split
**Category:** Prompt Quality / Spec Design

**Description:** The blunt prohibition ("if you need 'and', create two domains") was challenged by NQPS R4 D005. The six underlying CCIs (regulatory compliance management, commitment to regulatory compliance, social responsibility, environmental responsibility, charitable responsibility, legislative compliance) represent a single enterprise concern — the enterprise's accountability to the external world. A better name is "Corporate Responsibility Governance": one concept, no "and". The blunt prohibition would have forced a split into two thin domains where one rich domain is analytically correct.

The distinction is between two failure modes:
- **Case A — Grouping failure:** "Task Entitlement and Accountability" — two distinct concerns (specification vs. completion) that fail differently. Correct response: split.
- **Case B — Naming precision failure:** "Regulatory and Social Responsibility" — one enterprise concern named via its two sub-themes. Correct response: find the single-concept name.

**Resolution:** Blunt prohibition replaced with a two-step "and" test in all row guidance blocks (Rows 1–5):
1. Is there a single concept that encompasses both sub-themes without 'and'? If yes, use it.
2. If no single concept exists, the domain has two distinct concerns — create two domains.

Row 1 previously had no "and" guidance at all. Added "and" test block to Row 1 prohibition rules. Evidence: PMT R11 D003 "Earnings Transparency and Stewardship"; NQPS R4 D005 "Regulatory and Social Responsibility".

---

### F79 — Repair Prompt Naming Prohibition + Row 2 "Retention" Vocabulary → Mechanism Spec v0.24

**Status:** Resolved (26 May 2026, v0.50 cycle)
**Surfaced by:** PMT Run 11 Row 3: D011 "Earnings Derivation and Aggregation Logic" and D013 "Task Availability and Persistence Model" — "and" names produced by CHK-3c-08 split repair; PMT Run 11 D009 "Historical Record Retention" — "retention" vocabulary at Row 2
**Category:** Spec Gap / Prompt Quality

**Finding 1 — Repair prompt naming gap:** CHK-3c-08 split and CHK-3c-07 absorption repair prompts received ROW_GUIDANCE as context but did not have the "and" test explicitly stated as a naming requirement for their outputs. The primary grouping prompt correctly applied the prohibition (Row 2 and Row 3 primary outputs had no "and" names). The repair prompts produced "and" names because their task framing (absorb / split CCIs) did not include an explicit naming constraint. ROW_GUIDANCE injection alone is insufficient when the repair task framing can override it.

**Resolution:** §4.3 CHK-3c-07 and CHK-3c-08 now specify that their respective repair prompt templates MUST include an explicit naming prohibition statement. For CHK-3c-07: "Any new domain names must not use 'and'/'&' without first confirming no single concept covers both sub-themes." For CHK-3c-08: "Each split domain name must not be compound — find the single concept that unifies the sub-theme's CCIs."

**Finding 2 — Row 2 "retention" vocabulary:** PMT R11 D009 "Historical Record Retention" — "retention" is data storage vocabulary (Row 3/4 level). At Row 2 the business concern is stewardship of historical records, not technical retention. "Retention" added to the Row 2 vocabulary avoid list alongside "retrieve", "store", etc. Recommended alternatives: "stewardship", "record", "accountability".

---

## v0.50 Cycle Summary

**Current Replit Agent handoff package (Phase 3c):**

| File | Role |
|---|---|
| `SysEngage_Row_3_Mechanism_Domain_Derivation_v0_1.md` | Architectural authority |
| `SysEngage_Row_4_Understanding_v0_24.md` | Structural framework (unchanged) |
| `SysEngage_Row_4_Mechanism_Domain_Derivation_v0_24.md` | Implementation spec |
| `SysEngage_Issues_Tracker_v0_50.md` | Finding disposition |

**Total findings after v0.50:** 79 (F1–F79)

**Implementation action required:** Update `domain_single_cci_repair_prompt.py` and `domain_split_repair_prompt.py` to include the explicit naming prohibition statement as specified in Mechanism Spec v0.24 §4.3.

**Next:** Run PMT and NQPS FullRerun with updated repair prompt templates; confirm no "and" in repair prompt output names.

---

## Document End

End of SysEngage Issues Tracker v0.50. Seventy-nine findings. "and"/"&" handling is now principled across all rows and all prompt contexts — two-step test distinguishes naming precision failures from grouping failures; repair prompts explicitly required to enforce naming discipline.
