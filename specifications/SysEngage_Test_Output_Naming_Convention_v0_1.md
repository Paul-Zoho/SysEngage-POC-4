# SysEngage Test Output Document Naming Convention

**Version:** 0.1
**Date:** 16 May 2026
**Applies to:** All ledger export files and verification summary documents produced during SysEngage mechanism test runs

---

## Purpose

This document defines the naming convention for all test output files produced by the SysEngage Replit implementation. It applies to ledger export JSON files and verification summary markdown documents. The convention must be applied consistently by the implementation — filenames are generated programmatically, not chosen manually.

---

## Canonical Format

```
{ProjectID}_Ph{phase}_{pass}_{passLabel}_R{row}_Run{n}.{ext}
```

---

## Field Definitions

| Field | Format | Rules |
| --- | --- | --- |
| `{ProjectID}` | UPPERCASE short code | Client project identifier. Matches `project_id` in the ledger. Example: `PMT`, `ACME`. No spaces, no hyphens. |
| `Ph{phase}` | `Ph` + zero-padded 2-digit integer | SysEngage phase number. Zero-padded to 2 digits for lexicographic sort stability. Example: `Ph01`, `Ph03`, `Ph10`. |
| `{pass}` | Alphanumeric pass identifier | The sub-pass within the phase. Example: `0a`, `0b`, `3a`, `3b`, `3c`, `3d`. Omit this field entirely (including its trailing underscore) if the phase has no sub-passes. |
| `{passLabel}` | CamelCase mechanism name | Human-readable label for the pass. Must match the `mechanism` string on the AnalysisPass entity in the ledger. Example: `SourceCapture`, `RowLensReanalysis`, `CCIConstruction`, `DomainDerivation`, `RequirementDerivation`. |
| `R{row}` | `R` + single digit 1–6 | Zachman row number. No zero-padding. Example: `R1`, `R6`. |
| `Run{n}` | `Run` + positive integer | Run sequence for this pass/row combination. Starts at `1`. Increments by 1 on each re-run (e.g. after a Phase 10 Concern resolution). Not zero-padded. Example: `Run1`, `Run2`. |
| `{ext}` | File extension | `json` for ledger export files. `md` for verification summary documents. |

---

## Separator

All fields are separated by a single underscore `_`. No spaces, no hyphens, no dots within the name (only the final dot before the extension).

---

## Examples

### Ledger export files

| Scenario | Filename |
| --- | --- |
| PMT Phase 1 Source Capture, Row 1, first run | `PMT_Ph01_0a_SourceCapture_R1_Run1.json` |
| PMT Phase 1 Source Capture, Row 2, first run | `PMT_Ph01_0a_SourceCapture_R2_Run1.json` |
| PMT Phase 3 Row-Lens Re-Analysis, Row 1, first run | `PMT_Ph03_3a_RowLensReanalysis_R1_Run1.json` |
| PMT Phase 3 CCI Construction, Row 1, first run | `PMT_Ph03_3b_CCIConstruction_R1_Run1.json` |
| PMT Phase 3 CCI Construction, Row 1, second run (after Concern resolution) | `PMT_Ph03_3b_CCIConstruction_R1_Run2.json` |
| PMT Phase 3 CCI Construction, Row 2, first run | `PMT_Ph03_3b_CCIConstruction_R2_Run1.json` |
| PMT Phase 3 Domain Derivation, Row 1, first run | `PMT_Ph03_3c_DomainDerivation_R1_Run1.json` |
| PMT Phase 3 Requirement Derivation, Row 1, first run | `PMT_Ph03_3d_RequirementDerivation_R1_Run1.json` |
| ACME Phase 3 CCI Construction, Row 1, first run | `ACME_Ph03_3b_CCIConstruction_R1_Run1.json` |

### Verification summary documents

| Scenario | Filename |
| --- | --- |
| PMT Phase 3 CCI Construction, Row 1, first run — verification summary | `PMT_Ph03_3b_CCIConstruction_R1_Run1_VerificationSummary.md` |
| PMT Phase 3 CCI Construction, Row 1, second run — verification summary | `PMT_Ph03_3b_CCIConstruction_R1_Run2_VerificationSummary.md` |

The suffix `_VerificationSummary` is appended before the extension. The base name is otherwise identical to the corresponding ledger export file — the two files form a pair for the same run.

---

## Natural Sort Order

Files for a single project sort lexicographically by phase → pass → row → run when listed in a file explorer or directory listing:

```
PMT_Ph01_0a_SourceCapture_R1_Run1.json
PMT_Ph01_0a_SourceCapture_R2_Run1.json
PMT_Ph01_0b_SegmentCapture_R1_Run1.json
PMT_Ph03_3a_RowLensReanalysis_R1_Run1.json
PMT_Ph03_3a_RowLensReanalysis_R2_Run1.json
PMT_Ph03_3b_CCIConstruction_R1_Run1.json
PMT_Ph03_3b_CCIConstruction_R1_Run2.json
PMT_Ph03_3b_CCIConstruction_R2_Run1.json
PMT_Ph03_3c_DomainDerivation_R1_Run1.json
PMT_Ph03_3d_RequirementDerivation_R1_Run1.json
```

---

## Implementation Requirements

### Run number management

The implementation must track the current run number for each `(project_id, phase, pass, row)` combination. The run number is not stored in the ledger — it is derived at export time by counting existing output files matching the same base pattern in the output directory, then incrementing by 1.

If the output directory contains no prior files for the combination, `Run1` is used.

### Filename generation

Filename generation must be a deterministic function of the four inputs: `project_id`, `phase`, `pass`, `row`. It must not rely on timestamps, random values, or user input. Given the same inputs and the same prior file count, the generated filename must always be the same.

### Output directory

All test output files are written to a designated output directory (e.g. `test_outputs/` or `ledger_exports/`). The convention applies to all files in that directory. Subdirectory organisation by project or phase is optional and does not affect the naming convention.

### passLabel values (current mechanism set)

The following `passLabel` values are currently defined. Extend this table as new mechanisms are implemented:

| Phase | Pass | passLabel |
| --- | --- | --- |
| Ph01 | 0a | `SourceCapture` |
| Ph01 | 0b | `SegmentCapture` |
| Ph03 | 3a | `RowLensReanalysis` |
| Ph03 | 3b | `CCIConstruction` |
| Ph03 | 3c | `DomainDerivation` |
| Ph03 | 3d | `RequirementDerivation` |

The `passLabel` must match the `mechanism` field value on the `AnalysisPass` entity in the ledger export exactly. If the mechanism string changes, the passLabel in this table must be updated to match.

---

## Validation Rule

A correctly named file must satisfy this regex:

```
^[A-Z]{2,}_Ph\d{2}(_[0-9][a-z])?_[A-Z][A-Za-z]+_R[1-6]_Run\d+(_VerificationSummary)?\.(json|md)$
```

Any output file that does not satisfy this regex is incorrectly named.

---

## Document End

End of SysEngage Test Output Document Naming Convention v0.1.
