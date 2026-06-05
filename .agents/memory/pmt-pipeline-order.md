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

**Correct runner pattern — production stays empty:**
The runner must clone a disposable test branch from production BEFORE importing
any mechanism modules, then set `os.environ["NEON_DATABASE_URL"]` to the test
branch URL. `core/db.py` builds the engine at import time, so all mechanism
imports must happen AFTER the env var is set. After all passes complete, rename
the test branch to the snapshot name (rename = promotion, no extra clone needed).

**Observed PMT Row 1 results (20260605, test branch — clean run):**
- Input doc: `The Pocket Money Tracker System v1.docx`
- Sources: 10, Signals (Row 1): 6 eligible
- CCIs: 20 created, 0 merged (dedup ON)
- Domains: 6 (D001–D006)
- Requirements: 16 (8 Functional, 7 Constraint, 1 Structural)
- Snapshot: `snap_PMT_ph03_3d_R1_20260605` (br-wispy-rain-abw21rf3)
- Ledger: `PMT_Ph03_3d_RequirementDerivation_R1_Run9.json` (79 elements, 8 registers, hash 0d8ff25d790c0355)
- Production (main) branch: 0 rows in all tables throughout
