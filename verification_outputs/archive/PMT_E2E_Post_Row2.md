---
sysengage_ledger_version: "2.12"
schema_id: "sysengage.ledger.instance.v2_11"
project_id: "PMT_E2E"
project_name: "Project PMT_E2E"
run_id: "4ebd0f92-2632-420c-b39b-18f5fb1cac6b"
created_utc: "2026-05-16T08:59:02.091787+00:00"
row_target: "1, 2"
generator: "sysengage-ledger-export v1.0"
content_hash: "22866048b9c1f4e2..."
---

# SysEngage Canonical Ledger — Project PMT_E2E

> **Spec version:** v2.12 | **Project:** `PMT_E2E` | **Rows:** 1, 2
>
> This document is a **Markdown projection** (human review view). The authoritative canonical artefact is the companion `.ledger.json` file.

## Summary

| Element Type | Count |
| --- | --- |
| Source | 10 |
| Segment | 1 |
| SourceAtom | 0 |
| Signal | 15 |
| Concern | 0 |
| AnalysisPass | 3 |
| Stakeholder | 1 |
| Domain | 0 |
| Requirement | 0 |

---

## Analysis Passes (3)

### P529 — SourceCapture

- **Pass Type:** Universal
- **Mechanism:** `SourceCapture`
- **Execution Status:** ✓ `Success`
- **Mode Active:** `LPM`
- **Declared Modes:** `LPM`
- **Evaluated Scope:** All input material in this project
- **Started:** `2026-05-16T06:56:51.769563+00:00`
- **Completed:** `2026-05-16T06:56:55.242212+00:00`
- **Elapsed:** 3,472 ms
- **Confidence:** `██████████` 1.00

**Read Witness:**

| Key | Value |
| --- | --- |
| `input_hash` | `5d66954e4d33dda146d247e09c75a371789b83e04396eb7f4d9b69f6996e35a0` |
| `byte_count` | 13803 |
| `character_count` | 902 |
| `read_mode` | `Full` |
| `read_completion_status` | `True` |

**Mechanism Data:**

- `cross_source_ordering`: []
- `non_text_source_ids`: []
- `segment_count`: 1
- `source_atom_count`: 0
- `source_count`: 10
- `source_ids`: ['S2295', 'S2296', 'S2297', 'S2298', 'S2299', 'S2300', 'S2301', 'S2302', 'S2303', 'S2304']
- `source_with_decoding_issues_ids`: []

**Mode Violations:** _none_

### P530 — RowLensSourceReanalysis

- **Pass Type:** Per-row
- **Mechanism:** `RowLensSourceReanalysis`
- **Execution Status:** ✓ `Completed`
- **Mode Active:** `IM`
- **Declared Modes:** `DM`, `IM`, `LPM`
- **Evaluated Scope:** All Sources + Row 0 Requirements
- **Started:** `2026-05-16T06:57:19.535781+00:00`
- **Completed:** `2026-05-16T06:57:33.557430+00:00`
- **Elapsed:** 16,954 ms
- **Confidence:** `████░░░░░░` 0.44

**Row Lens Data (v2.12):**

| Key | Value |
| --- | --- |
| `row_ref` | 1 |
| `stream1_source_count` | 10 |
| `stream2_requirement_count` | 0 |
| `signal_count_produced` | 6 |
| `concern_count_produced` | 0 |

**Mode Violations:** _none_

### P567 — RowLensSourceReanalysis

- **Pass Type:** Per-row
- **Mechanism:** `RowLensSourceReanalysis`
- **Execution Status:** ✓ `Completed`
- **Mode Active:** `IM`
- **Declared Modes:** `DM`, `IM`, `LPM`
- **Evaluated Scope:** All Sources + Row 1 Requirements
- **Started:** `2026-05-16T08:58:31.430615+00:00`
- **Completed:** `2026-05-16T08:58:45.663681+00:00`
- **Elapsed:** 17,141 ms
- **Confidence:** `█████████░` 0.88

**Row Lens Data (v2.12):**

| Key | Value |
| --- | --- |
| `row_ref` | 2 |
| `stream1_source_count` | 10 |
| `stream2_requirement_count` | 0 |
| `signal_count_produced` | 9 |
| `concern_count_produced` | 0 |

**Mode Violations:** _none_

---

## Sources (10)

### S2295

- **Input Material:** /home/runner/workspace/verification_inputs/The Pocket Money Tracker System v1.docx
- **Segmentation Context:** heading
- **Confidence:** `██████████` 1.00

> High Level Description

### S2296

- **Input Material:** /home/runner/workspace/verification_inputs/The Pocket Money Tracker System v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

> The pocket money tracker system allows children to claim pocket money tasks as they are completed throughout the week.

### S2297

- **Input Material:** /home/runner/workspace/verification_inputs/The Pocket Money Tracker System v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  Parents can detail tasks that should be completed and the monetary amount earned for that task.

### S2298

- **Input Material:** /home/runner/workspace/verification_inputs/The Pocket Money Tracker System v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  As a task is completed it is linked to the child that completed it.

### S2299

- **Input Material:** /home/runner/workspace/verification_inputs/The Pocket Money Tracker System v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  The children should be able to see the available tasks and the tasks they have completed that week.

### S2300

- **Input Material:** /home/runner/workspace/verification_inputs/The Pocket Money Tracker System v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  At the end of each week the children can see the total amount they have earned that week.

### S2301

- **Input Material:** /home/runner/workspace/verification_inputs/The Pocket Money Tracker System v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  The Parents can also see a report of how much each child has earned and the tasks they completed so that they can provide the pocket money earned to each child.

### S2302

- **Input Material:** /home/runner/workspace/verification_inputs/The Pocket Money Tracker System v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  At the start of the next week all tasks become available again to be claimed.

### S2303

- **Input Material:** /home/runner/workspace/verification_inputs/The Pocket Money Tracker System v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  Historical task data shall be available.

### S2304

- **Input Material:** /home/runner/workspace/verification_inputs/The Pocket Money Tracker System v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  The resulting system shall be able to operate on iOS 16, Android 9 and Windows 11 or later.

---

## Segments (1)

### SEG301 — High Level Description

- **Source Refs:** `S2295`, `S2296`, `S2297`, `S2298`, `S2299`, `S2300`, `S2301`, `S2302`, `S2303`, `S2304`
- **Confidence:** `██████████` 1.00

Section: High Level Description

---

## Signals (15)

### Row 1 Signals (6)

#### SG049 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2296`
- **Confidence:** `████████░░` 0.75

> Expresses the fundamental purpose of enabling children to claim and track completed pocket money tasks weekly.

#### SG050 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2297`
- **Confidence:** `███████░░░` 0.72

> Articulates parental motivation to define compensated task assignments with associated monetary values.

#### SG051 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2299`
- **Confidence:** `███████░░░` 0.70

> Captures the purpose of providing children visibility into available and completed task inventory.

#### SG052 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2300`
- **Confidence:** `███████░░░` 0.73

> Identifies the motivational goal of enabling children to view their weekly earnings summary.

#### SG053 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2301`
- **Confidence:** `████████░░` 0.78

> Establishes parental need to access child performance reporting for accurate compensation distribution purposes.

#### SG054 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2303`
- **Confidence:** `███████░░░` 0.68

> Indicates stakeholder requirement for longitudinal task history access supporting accountability or trend analysis.

### Row 2 Signals (9)

#### SG289 — `Intent`

- **Row Target:** 2
- **Signal Type:** `Intent`
- **Source Refs:** `S2295`
- **Confidence:** `████████░░` 0.75

> Section header indicating the commencement of conceptual system description.

#### SG290 — `Intent`

- **Row Target:** 2
- **Signal Type:** `Intent`
- **Source Refs:** `S2296`
- **Confidence:** `████████░░` 0.85

> Establishes the core business concept of children claiming completed tasks for monetary reward tracking.

#### SG291 — `Normative`

- **Row Target:** 2
- **Signal Type:** `Normative`
- **Source Refs:** `S2297`
- **Confidence:** `█████████░` 0.90

> Defines the parent capability to specify task entities with associated monetary value attributes.

#### SG292 — `Normative`

- **Row Target:** 2
- **Signal Type:** `Normative`
- **Source Refs:** `S2298`
- **Confidence:** `█████████░` 0.92

> Specifies the relationship between completed task entities and child entities through linkage.

#### SG293 — `Normative`

- **Row Target:** 2
- **Signal Type:** `Normative`
- **Source Refs:** `S2299`
- **Confidence:** `█████████░` 0.88

> Defines child actor visibility requirements for both available and completed task entities within temporal scope.

#### SG294 — `Normative`

- **Row Target:** 2
- **Signal Type:** `Normative`
- **Source Refs:** `S2300`
- **Confidence:** `█████████░` 0.90

> Establishes weekly aggregation capability for earned monetary totals visible to child actors.

#### SG295 — `Normative`

- **Row Target:** 2
- **Signal Type:** `Normative`
- **Source Refs:** `S2301`
- **Confidence:** `█████████░` 0.92

> Defines parent reporting capability displaying child-task-earnings relationships to support payment fulfillment.

#### SG296 — `Normative`

- **Row Target:** 2
- **Signal Type:** `Normative`
- **Source Refs:** `S2302`
- **Confidence:** `█████████░` 0.87

> Specifies the cyclical business rule for task availability reset at weekly temporal boundaries.

#### SG297 — `Normative`

- **Row Target:** 2
- **Signal Type:** `Normative`
- **Source Refs:** `S2303`
- **Confidence:** `████████░░` 0.85

> Mandates retention and accessibility of historical task data entities across temporal periods.

---

## Stakeholders (1)

| ID | Name | Role / Kind |
| --- | --- | --- |
| `SH_PMT` | Practitioner SH_PMT | practitioner (Human) |

---

## Registers

| Register | Type | Member Count |
| --- | --- | --- |
| `SOURCE_REG001` | Source | 10 |
| `SIGNAL_REG001` | Signal | 15 |
| `STAKEHOLDER_REG001` | Stakeholder | 1 |
| `SEGMENT_REG001` | Segment | 1 |

---

## Ledger Provenance

| Field | Value |
| --- | --- |
| Spec Version | v2.12 |
| Run ID | `4ebd0f92-2632-420c-b39b-18f5fb1cac6b` |
| Created UTC | `2026-05-16T08:59:02.091787+00:00` |
| Content Hash (sha256) | `22866048b9c1f4e213d271db27708dbaf25aaf407ebe16fc27109356ca7ffc53` |

_Generated by SysEngage Ledger Export — spec conformant Markdown projection_
