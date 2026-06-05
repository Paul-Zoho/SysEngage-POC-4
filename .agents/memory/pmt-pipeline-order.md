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

**Observed PMT Row 1 results (20260605, main branch):**
- Input doc: `The Pocket Money Tracker System v1.docx`
- Sources: 10 (3 duplicate SC runs → 30 total in DB at snapshot time)
- Signals (Row 1): 12 eligible (RLSRA produced some, 8 out-of-scope)
- CCIs: 17 created, 0 merged (dedup ON)
- Domains: 5 (D001–D005)
- Requirements: 12 (4 Functional, 5 Constraint, 3 Structural)
- Snapshot: `snap_PMT_ph03_3d_R1_20260605` (br-gentle-recipe-abqm801y)
- Ledger: `PMT_Ph03_3d_RequirementDerivation_R1_Run7.json`
