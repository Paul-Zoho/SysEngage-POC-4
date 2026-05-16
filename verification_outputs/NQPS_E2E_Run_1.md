---
sysengage_ledger_version: "2.12"
schema_id: "sysengage.ledger.instance.v2_11"
project_id: "NQPS_E2E"
project_name: "Project NQPS_E2E"
run_id: "5209c557-5df8-4206-8627-f2f56c9c8742"
created_utc: "2026-05-16T08:36:09.149877+00:00"
row_target: "1"
generator: "sysengage-ledger-export v1.0"
content_hash: "48d86f70c1967126..."
---

# SysEngage Canonical Ledger — Project NQPS_E2E

> **Spec version:** v2.12 | **Project:** `NQPS_E2E` | **Rows:** 1
>
> This document is a **Markdown projection** (human review view). The authoritative canonical artefact is the companion `.ledger.json` file.

## Summary

| Element Type | Count |
| --- | --- |
| Source | 11 |
| Segment | 0 |
| SourceAtom | 0 |
| Signal | 11 |
| Concern | 0 |
| AnalysisPass | 2 |
| Stakeholder | 1 |
| Domain | 0 |
| Requirement | 0 |

---

## Analysis Passes (2)

### P565 — SourceCapture

- **Pass Type:** Universal
- **Mechanism:** `SourceCapture`
- **Execution Status:** ✓ `Success`
- **Mode Active:** `LPM`
- **Declared Modes:** `LPM`
- **Evaluated Scope:** All input material in this project
- **Started:** `2026-05-16T08:35:11.077260+00:00`
- **Completed:** `2026-05-16T08:35:16.319796+00:00`
- **Elapsed:** 5,242 ms
- **Confidence:** `██████████` 1.00

**Read Witness:**

| Key | Value |
| --- | --- |
| `input_hash` | `236515dba508919355fff5da9a80b9b8f13ad8bbfe46707063ea2af68b8208ad` |
| `byte_count` | 1093980 |
| `character_count` | 1915 |
| `read_mode` | `Full` |
| `read_completion_status` | `True` |

**Mechanism Data:**

- `cross_source_ordering`: []
- `non_text_source_ids`: []
- `segment_count`: 0
- `source_atom_count`: 0
- `source_count`: 11
- `source_ids`: ['S2753', 'S2754', 'S2755', 'S2756', 'S2757', 'S2758', 'S2759', 'S2760', 'S2761', 'S2762', 'S2763']
- `source_with_decoding_issues_ids`: []

**Mode Violations:** _none_

### P566 — RowLensSourceReanalysis

- **Pass Type:** Per-row
- **Mechanism:** `RowLensSourceReanalysis`
- **Execution Status:** ✓ `Completed`
- **Mode Active:** `IM`
- **Declared Modes:** `DM`, `IM`, `LPM`
- **Evaluated Scope:** All Sources + Row 0 Requirements
- **Started:** `2026-05-16T08:35:33.339009+00:00`
- **Completed:** `2026-05-16T08:35:47.272935+00:00`
- **Elapsed:** 16,791 ms
- **Confidence:** `████████░░` 0.83

**Row Lens Data (v2.12):**

| Key | Value |
| --- | --- |
| `row_ref` | 1 |
| `stream1_source_count` | 11 |
| `stream2_requirement_count` | 0 |
| `signal_count_produced` | 11 |
| `concern_count_produced` | 0 |

**Mode Violations:** _none_

---

## Sources (11)

### S2753

- **Input Material:** /home/runner/workspace/verification_inputs/Novus Quality Policy Statement v1.docx
- **Segmentation Context:** multi-line block
- **Confidence:** `██████████` 1.00

> 
QUALITY POLICY STATEMENT
Novus Mechanical Services Limited has established a Quality Policy to be consistent with the purpose and context of our organisation.

### S2754

- **Input Material:** /home/runner/workspace/verification_inputs/Novus Quality Policy Statement v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  It provides a framework for the setting and review of objectives in addition to our commitment to satisfy applicable customers’, regulatory and legislative requirements as well as our commitment to continually improve our management system.

### S2755

- **Input Material:** /home/runner/workspace/verification_inputs/Novus Quality Policy Statement v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  

Customer focus: As an organisation we have made a commitment to understand our current and future customers’ needs; meet their requirements and strive to exceed their expectations.

### S2756

- **Input Material:** /home/runner/workspace/verification_inputs/Novus Quality Policy Statement v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  
Leadership: Our Top Management have committed to creating and maintaining a working environment in which people become fully involved in achieving our objectives.

### S2757

- **Input Material:** /home/runner/workspace/verification_inputs/Novus Quality Policy Statement v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  
Engagement of people: As an organisation we recognise that people are the essence of any good business and that their full involvement enables their abilities to be used for our benefit.

### S2758

- **Input Material:** /home/runner/workspace/verification_inputs/Novus Quality Policy Statement v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  
Process approach: As an organisation we understand that a desired result is achieved more efficiently when activities and related resources are managed as a process or series of interconnected processes.

### S2759

- **Input Material:** /home/runner/workspace/verification_inputs/Novus Quality Policy Statement v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  
Improvement: We have committed to achieving continual improvement across all aspects of our quality management system; it is one of our main annual objectives.

### S2760

- **Input Material:** /home/runner/workspace/verification_inputs/Novus Quality Policy Statement v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  
Evidence-based decision making: As an organisation we have committed to only make decisions relating to our QMS following an analysis of relevant data and information.

### S2761

- **Input Material:** /home/runner/workspace/verification_inputs/Novus Quality Policy Statement v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  
Relationship management: We recognises that an organisation and the relationship it has with its external providers are interdependent and a mutually beneficial relationship enhances the ability of both to create value.

### S2762

- **Input Material:** /home/runner/workspace/verification_inputs/Novus Quality Policy Statement v1.docx
- **Segmentation Context:** sentence in prose
- **Confidence:** `██████████` 1.00

>  
Our policy is also to meet the requirements of our social, environmental, charitable and legislative responsibilities.

### S2763

- **Input Material:** /home/runner/workspace/verification_inputs/Novus Quality Policy Statement v1.docx
- **Segmentation Context:** multi-line block
- **Confidence:** `██████████` 1.00

> 

Signed : 							Date: 22/4/2025
           	
Damian Shacklock
Director
NOVUS MECHANICAL SERVICES LTD.


---

## Signals (11)

### Row 1 Signals (11)

#### SG278 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2753`
- **Confidence:** `████████░░` 0.85

> Establishes organizational quality policy aligned with business purpose and context as foundational governance framework.

#### SG279 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2754`
- **Confidence:** `████████░░` 0.80

> Defines quality policy framework purpose for objective-setting and commitment to regulatory compliance and continuous improvement.

#### SG280 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2755`
- **Confidence:** `█████████░` 0.90

> Articulates strategic commitment to understanding customer needs and exceeding expectations as organizational driver.

#### SG281 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2756`
- **Confidence:** `████████░░` 0.75

> Expresses leadership commitment to creating enabling work environment for achieving organizational objectives.

#### SG282 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2757`
- **Confidence:** `████████░░` 0.85

> Recognizes people engagement as essential organizational value and strategic enabler for business benefit.

#### SG283 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2758`
- **Confidence:** `███████░░░` 0.70

> Declares process approach as organizational efficiency principle for achieving desired results.

#### SG284 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2759`
- **Confidence:** `█████████░` 0.88

> Establishes continual improvement across quality management as core annual organizational objective.

#### SG285 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2760`
- **Confidence:** `████████░░` 0.82

> Commits organization to evidence-based decision making principle for quality management governance.

#### SG286 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2761`
- **Confidence:** `████████░░` 0.78

> Recognizes mutually beneficial external provider relationships as strategic driver for value creation.

#### SG287 — `Intent`

- **Row Target:** 1
- **Signal Type:** `Intent`
- **Source Refs:** `S2762`
- **Confidence:** `█████████░` 0.87

> Declares policy commitment to social, environmental, charitable, and legislative responsibilities as organizational obligations.

#### SG288 — `Normative`

- **Row Target:** 1
- **Signal Type:** `Normative`
- **Source Refs:** `S2763`
- **Confidence:** `██████████` 0.95

> Provides formal policy authorization by organizational director establishing governance authority and accountability.

---

## Stakeholders (1)

| ID | Name | Role / Kind |
| --- | --- | --- |
| `SH_NQPS` | Practitioner SH_NQPS | practitioner (Human) |

---

## Registers

| Register | Type | Member Count |
| --- | --- | --- |
| `SOURCE_REG001` | Source | 11 |
| `SIGNAL_REG001` | Signal | 11 |
| `STAKEHOLDER_REG001` | Stakeholder | 1 |

---

## Ledger Provenance

| Field | Value |
| --- | --- |
| Spec Version | v2.12 |
| Run ID | `5209c557-5df8-4206-8627-f2f56c9c8742` |
| Created UTC | `2026-05-16T08:36:09.149877+00:00` |
| Content Hash (sha256) | `48d86f70c1967126fe5ab9790a74fc7af23eca130b3ed1771ac75ca5ef4ea2d7` |

_Generated by SysEngage Ledger Export — spec conformant Markdown projection_
