---
name: PMT full pipeline pass order
description: Correct ordering for the full PMT E2E pipeline (Source Capture through Requirement Derivation) and the role of each pass.
---

## Correct pass order

```
SourceCapture  →  RLSRA (3a)  →  CCI (3b)  →  DD (3c)  →  RD (3d)
```

| Pass | Mechanism name | Writes to | Idempotency scope |
|------|---------------|-----------|-------------------|
| SC | `SourceCapture` | `source`, `segment`, `source_atom` | `"All input material in this project"` / status `"Success"` |
| RLSRA | `RowLensSourceReanalysis` | `signal`, `concern` | `"All Sources (Row N)"` |
| CCI | `CellContentItemConstruction` | `cell_content_item`, `zachman_cell` | `"All Row N Signals"` |
| DD | `DomainDerivation` | `domain` | `"All Row N CCIs"` |
| RD | `RequirementDerivation` | `requirement` | `"All Row N Domains"` |

**Why RLSRA is critical:** `CCI step1_signal_assembly.py` reads from the `signal` table filtered by `row_target`. If RLSRA hasn't run, `signal` is empty and CCI produces 0 CCIs (no error, no warning — silent zero output).

**Observed PMT Row 1 results (20260605, main branch — clean run):**
- Input doc: `The Pocket Money Tracker System v1.docx`
- Sources: 10
- Signals (Row 1): 5 eligible (RLSRA, 4 out-of-scope)
- CCIs: 15 created, 0 merged (dedup ON)
- Domains: 3 (D001 Child Participation, D002 Parental Governance, D003 Earnings Accountability)
- Requirements: 13 (9 Functional, 2 Constraint, 2 Structural)
- Snapshot: `snap_PMT_ph03_3d_R1_20260605` (br-holy-hill-ab7v6bmb)
- Ledger: `PMT_Ph03_3d_RequirementDerivation_R1_Run8.json` (69 elements, 9 registers, hash 79b0438eaed6b4de)
