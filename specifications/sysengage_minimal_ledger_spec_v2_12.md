SysEngage Minimal Canonical Ledger Specification

Version: v2.12

Updates (v2.12):

- F35 resolved: Canonical ledger amended to support the Row-Lens Source Re-Analysis mechanism (Mechanism B, Phase 3). Three changes: (1) Concern element type added (CNNNN identifier prefix; nine attributes; source_refs list replacing source_type+source_id; forward-link attributes not held on Concern — downstream entities carry back-references); (2) CN added to Identifier Prefix Register; (3) prose note added to AnalysisPass.outputs documenting the row_lens_data conventional sub-key produced by mechanism="RowLensSourceReanalysis". Signal element type is unchanged — source_refs already correctly accepts Source.source_id and Requirement.requirement_id per v2.11. Typo fix: Signal Normative Rules "requirent_id" corrected to "requirement_id".

- Rationale for v2.12 amendment: F35 architectural resolution (May 2026) established that row-lens re-analysis of Sources and upstream Requirements occurs at Phase 3 Pass 3a, producing Concerns (ambiguous content) and Signals (clear content). The Concern entity did not previously exist in the canonical ledger spec (it was defined only in Row 2 Understanding v1.1 Appendix E). Canonical spec amendment required before Mechanism B specification authoring can proceed (Path A discipline). RSSF (RowScopedSourceFindings) is NOT added — it was retired in Row 2 Understanding v1.2 per R2-AMEND-8; evidence of dual-stream engagement is the Phase 3 AnalysisPass execution record.

Updates (v2.11):

- F25 closed: Canonical AnalysisPass amended to canonicalise the operational attributes required by F4 / F10 architectural commitments in SysEngage. Prose attributes section and JSON Schema AnalysisPassPayload both updated to add: `mechanism` (REQUIRED) — name of the mechanism that produced this pass; `execution_status` (REQUIRED, enum Success/Failed/PartialSuccess) — outcome of the pass execution; `mode_active` (REQUIRED, enum LPM/IM/HM/...) — the Transformation Mode the pass operated in; `declared_transformation_modes` (REQUIRED, array) — the modes the pass was declared to operate in; `outputs` (REQUIRED, object) — mechanism-specific output sub-structure typically containing read_witness, mechanism_data, and mode_violations; `pass_started_at` (REQUIRED, datetime); `pass_completed_at` (OPTIONAL, datetime — null while pass in progress); `elapsed_ms` (OPTIONAL, integer convenience derived from start/completion timestamps). Existing canonical attributes (pass_id, pass_type, evaluated_scope, confidence) retained. `pass_type` semantically refines as broader category (e.g., "Universal" / "Per-row" / "Practitioner") distinct from `mechanism` which names the specific mechanism. `confidence` retained for general analytical activities (may be 1.0 for purely-deterministic LPM mechanisms).

- Rationale for v2.11 amendment: First Practitioner verification cycle on Source Capture v1 build (May 2026) surfaced that v2.10 canonical AnalysisPass had only four attributes (pass_id, pass_type, evaluated_scope, confidence) and didn't reflect F4 architectural commitment (mechanism provenance) or F10 architectural commitment (Read Witness on AnalysisPass.outputs). Implementations producing operationally-correct output were forced to include non-canonical attributes that would be rejected by strict JSON Schema validation (AnalysisPassPayload had `additionalProperties: false`). Tracked as SysEngage finding F25 with Path A resolution (canonical spec amendment before implementation continues). Path A chosen over pragmatic workarounds to preserve disciplined layered conformance — implementation must conform to canonical ledger spec AND mechanism specification AND architectural commitments simultaneously.

Updates (v2.10 — preserved for traceability):

- Defect 4.5 closed: CellContentItem `ci_id` format locked to canonical structured form `^CCI-ROW[1-6]-C-(What|How|Where|Who|When|Why)-\\d{3}$` per JSON Schema (Appendix C). Prose at § Element Type — CellContentItem and § Identifier Prefix Register updated to match. "For v2.9 draft purposes" wording removed.

- Defect 6.9 closed: residual references to "Finding" element scrubbed from narrative (Signal description at element § Signal; Suggestion type description at element § Suggestion). Finding is not a defined element in this spec; references aligned to use Gap or observation/category as appropriate.

- Defect 6.10 alignment: short-form coverage type names ("Cell", "Domain", "Requirement") in CoverageItem.target_ref description aligned to long form ("CellCoverage", "DomainCoverage", "RequirementCoverage") to match enum and Normative Rules.

- Version bump: spec, schema $id, sysengage_ledger_version, schema_id constants, and schema description text all updated v2.9 → v2.10.

Updates (v2.9 — preserved for traceability):

- Refactored to updated Metamodel. Categories 1, 4, 5, most of 6, 7, and parts of 8 from the v2.8 defect list resolved.

# Permitted Element Types

The following is a list of permitted elements types within the ledger

- `Source`

- `Register`

- `SourceRegister`

- `AnalysisPass`

- `Gap`

- `GapRegister`

- `ZachmanCell`

- `ZachmanCellRegister`

- `CellContentItem`

- `Domain`

- `DomainRegister`

- `Requirement`

- `RequirementRegister`

- `Question`

- `QuestionRegister`

- `Answer`

- `AnswerRegister`

- `Suggestion`

- `SuggestionRegister`

- `CoverageItem`

- `CoverageRegister`

- `Segment`

- `SegmentRegister`

- `SourceAtom`

- `SourceAtomRegister`

- `Signal`

- `SignalRegister`

- `Risk`

- `RiskRegister`

- `Stakeholder`

- `StakeholderRegister`

- `Concern`

- `ConcernRegister`

# Identifier Conventions (NORMATIVE)

## Purpose

- Define, once, the canonical regex form used throughout this specification  so that narrative rules and the JSON Schema in Appendix C are unambiguous  and consistent.

## Canonical Regex Form (NORMATIVE)

All identifier regex patterns in this specification are given in **raw regex form**. Raw regex form is the form a regex engine (Python `re`,JavaScript `RegExp`, POSIX ERE, etc.) accepts directly as a pattern string, with single backslashes for character-class shortcuts.

For example, the Source element's identifier rule is written:

> `source_id` MUST match regex `^S\\d{3}$`.

This is the canonical form. It is what a reader would pass to a regex engine verbatim.

## JSON Schema Serialization (NORMATIVE)

When an identifier pattern is expressed inside the JSON Schema in Appendix C, backslashes MUST be doubled to survive JSON-string escaping. The canonical regex `^S\\d{3}$` becomes, inside a JSON Schema `"pattern"` value:

> `"pattern": "^S\\d{3}$"`

This is a JSON serialization concern only. The underlying regex is the same.

## Rule of Thumb

- In narrative prose (element definitions, normative rules, examples): use

  **single-backslash raw regex form**. Example: `^R\\d{3}$`.

- In JSON Schema blocks (Appendix C) or any JSON example: use

  **double-backslash JSON-escaped form**. Example: `"pattern": "^R\\d{3}$"`.

- Any generator producing a canonical ledger instance MUST write JSON  patterns using the double-backslash form because that is what JSON requires. Any validator compiling a pattern from the JSON Schema MUST

  parse one level of JSON-string unescaping before passing the result to

  a regex engine; this is automatic for any standard JSON parser.

## Identifier Prefix Register (INFORMATIVE)

The following table lists all identifier prefixes used in this specification. This is an informative summary; the authoritative definition remains in each element's definition.

| Prefix | Element Type | Canonical Regex |
| --- | --- | --- |
| S | Source | `^S\\d{3}$` |
| SEG | Segment | `^SEG\\d{3}$` |
| SA | SourceAtom | `^SA\\d{3}$` |
| ZC | ZachmanCell | `^ZC-R[1-6]-C-(What│How│Where│Who│When│Why)$` |
| CI | CellContentItem | `^CCI-ROW[1-6]-C-(What\|How\|Where\|Who\|When\|Why)-\\d{3}$` |
| D | Domain | `^D\\d{3}$` |
| R | Requirement | `^R\\d{3}$` |
| P | AnalysisPass | `^P\\d{3}$` |
| G | Gap | `^G\\d{3}$` |
| SG | Signal | `^SG\\d{3}$` |
| Q | Question | `^Q\\d{3}$` |
| A | Answer | `^A\\d{3}$` |
| SUG | Suggestion | `^SUG\\d{3}$` |
| CV | CoverageItem | `^CV\\d{3}$` |
| SH | Stakeholder | `^SH\\d{3}$` |
| K | Risk | `^K\\d{3}$` |
| CN | Concern | `^CN\\d{3}$` |

Register identifiers MAY use free-form strings, but SHOULD use the pattern

`^<TYPE>_REG\\d{3}$` where `<TYPE>` is the register's element type in

uppercase (e.g. `SOURCE_REG001`). This is a convention, not a rule.

# Ledger Scope and Row Semantics (NORMATIVE)

## Purpose

- Define the scope of a SysEngage canonical ledger instance and the semantics of row-level analysis within that scope.

- Establish deterministic rules for how row context attaches to each element, enabling unambiguous row-scoped queries and cross-row traceability.

## Ledger Scope (NORMATIVE)

A canonical ledger instance represents a single project, not a single Zachman row. All elements produced during the analysis of every Zachman row for that project coexist within one ledger file.

- A ledger MAY be ingested, edited, and extended iteratively as analysis proceeds row-by-row. Later rows append elements to the same ledger; earlier rows' elements are not removed or migrated.

- A ledger MUST NOT be split across multiple files for canonical storage. Projections (Markdown, CSV, per-row summaries) MAY be derived from the ledger but are not authoritative.

- A single project SHALL have exactly one canonical ledger instance at any given time. When the ledger is updated, the updated instance replaces the previous one; historical instances MAY be retained as versioned snapshots but are not the active ledger.

## Row Semantics (NORMATIVE)

The Zachman rows (1-6) are processed in sequence, but all rows' elements coexist in the ledger. Row context for each element is determined by one of two mechanisms:

- **Explicit row attribution** — the element carries a `row_target` attribute with a value in `"1".."6"`. Explicit attribution applies to: `Signal`, `Domain`, `Requirement`, and `ZachmanCell`.

- **Implicit row attribution** — the element's row is inferred by following its relationships to an element with explicit row attribution. Implicit attribution applies to: `CellContentItem`, `Gap`,

  `CoverageItem`, `Question`, `Answer`, `Suggestion`.

- `Source`, `SourceAtom`, and `Segment` have no row context. They are raw input artefacts, ingested once and referenced by row-scoped elements across multiple rows as needed.

## Row Inference Rules (NORMATIVE)

For elements using implicit row attribution, the row_target is computed as follows:

- ****CellContentItem**** — row_target equals the `row_target` value of the `ZachmanCell` referenced by `cell_id`.

- ****CoverageItem**** — row equals the row of the element referenced by `target_ref`:

  - If `target_ref` is a CellContentItem, row equals that CellContentItem's inferred row.

  - If `target_ref` is a Domain, row equals that Domain's `row_target`.

  - If `target_ref` is a Requirement, row equals that Requirement's `row_target`.

- ****Gap**** — row equals the row of any entry in `coverage_item`. All CoverageItems referenced by a single Gap MUST resolve to the same row; see Row Consistency Rules below.

- ****Question**** — row equals the row of any entry in `related_gap_ids`. All Gaps referenced by a single Question MUST resolve to the same row.

- ****Answer**** — row equals the row of the Question referenced by `question_id`.

- ****Suggestion**** — row equals the row of any entry in `produced_from_gap_ids`. All Gaps referenced by a single Suggestion MUST resolve to the same row.

## Row Consistency Rules (NORMATIVE)

For elements that reference other row-scoped elements, consistency between the reference chain is REQUIRED:

- An element's inferred row MUST be unique. If multiple reference paths are available (e.g., a Suggestion referencing multiple Gaps), all paths MUST resolve to the same row.

- A Requirement's `cci_refs` entries MUST all resolve to CellContentItems whose row equals the Requirement's `row_target`.

- A Domain's `cell_content_item_refs` entries MUST all resolve to CellContentItems whose row equals the Domain's `row_target`.

- A Signal's `source_refs` entries MAY reference Sources (no row constraint) or Requirements. Any referenced Requirement MUST have a `row_target` value strictly less than the Signal's `row_target` value. (A Row N signal is evidenced by Sources of any provenance or by Requirements produced from earlier rows.)

- Cross-row references via `Signal.source_refs` are the only permitted mechanism for row N analysis to depend on row N-1 outputs. Direct cross-row references between non-Signal elements are not permitted.

## row_target Attribute (NORMATIVE)

The `row_target` attribute is REQUIRED on `Signal`, `Domain`, and`Requirement`, with the following semantics:

- `row_target: string` — MUST be one of `"1"`, `"2"`, `"3"`, `"4"`, `"5"`, `"6"`.

- `row_target` on an element indicates the Zachman row in which the  element was produced or to which it primarily contributes.

- For `Signal`, `row_target` is the row whose analysis produced the Signal. (In v2.8 the attribute on Signal is named `row`; see Migration Notes below.)

- For `Domain` and `Requirement`, `row_target` is the row whose analysis produced the element.

- `ZachmanCell.row_target` serves the equivalent purpose for cells and retains its existing name.

## Ledger-Level row_target (NORMATIVE)

The ledger instance itself carries a `row_target` field (Appendix C, schema-level attribute) representing the set of rows act

# CanonicalLedger

## Purpose (NORMATIVE)

- Define the authoritative container representing a valid SysEngage ledger instance.

- Provide run context (row_target) and creation metadata for governance and audit.

A `CanonicalLedger` SHALL:

- Contain zero or more `Source` elements

- Contain exactly one `SourceRegister`

- Allow zero or more additional `Register` elements

- Allow zero or more `AnalysisPass` elements

- Allow zero or more `Gap` elements

- Contain exactly one `GapRegister`

- Allow zero or more `ZachmanCell` elements

- Contain exactly one `ZachmanCellRegister`

- Allow zero or more `CellContentItem` elements

- Allow zero or more `Domain` elements

- Contain exactly one `DomainRegister`

- Allow zero or more `Requirement` elements  

- Contain exactly one `RequirementRegister`

- Allow zero or more `Question` elements  

- Contain exactly one `QuestionRegister`

- Allow zero or more `Answer` elements  

- Contain exactly one `AnswerRegister`

- Allow zero or more `Suggestion` elements  

- Contain exactly one `SuggestionRegister`

- Allow zero or more `CoverageItem` elements  

- Contain exactly one `CoverageRegister`

- Allow zero or more `Segment` elements  

- Contain exactly one `SegmentRegister` IF `Segment` elements  exist

- Allow zero or more `SourceAtom` elements 

- Contain exactly one `SourceAtomRegister` IF `SourceAtom` elements  exist

- Allow zero or more `Signal` elements  

- Contain exactly one `SignalRegister`

- Allow zero or more `Risk` elements  

- Contain exactly one `RiskRegister` IF `Risk` elements  exist

- Allow zero or more additional `Stakeholder` elements beyond SH001

- Contain exactly one `StakeholderRegister`

- Contain the reserved `SH001` SysEngage Tool Stakeholder

# Element Type — Register (Generic)

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `(Generic)` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

## Attributes (with descriptions)

All Register element types (SourceRegister, SegmentRegister, etc.) share the attributes defined below. Individual Register element sections specify only the attributes and rules that are specific to that Register, referencing this section for common ones.

- `register_id: string` (REQUIRED)

Description: Stable identifier for this Register instance. Convention: uppercase prefix of the governed element type plus "_REG" plus a three-digit sequence, e.g., `SOURCE_REG001`, `GAP_REG001`. The convention is recommended but not enforced at schema level.

- `register_type: string` (REQUIRED)

Description: The element type governed by this Register. Constrains which `member_ids` are valid. See each Register's Normative Rules for the required constant value.

- `member_ids: string[]` (REQUIRED)

Description: The complete set of element identifiers governed by this Register. Every element of the governed type present in the ledger MUST appear in `member_ids`; no entry in `member_ids` MAY reference an element that does not exist in the ledger.

Notes: Order is not semantically significant and SHALL be sorted lexicographically per Appendix B.2.

- `completeness_rule: string` (REQUIRED)

Description: Declarative statement of the completeness semantics this Register enforces. Typically the canonical completeness rule from the Register's Normative Rules section, restated here for generator and reviewer clarity.

- `confidence: number` (REQUIRED, 0.0..1.0)

Description: Confidence that this Register is complete and correctly enumerates all members of the governed type.

Notes: Typically 1.0 when produced by a deterministic generator that builds the Register from the actual `elements[]` array. Lower values may indicate known gaps (e.g., a partial run or an in-progress analysis).

## Normative Rules

- `member_ids` SHALL reference valid ledger element identifiers only and contain no duplicates.

# Element Type — Source

## Purpose (NORMATIVE) — Replace / Clarify

A `Source` element represents a **traceable excerpt** originating from an immutable input artefact, typically at a granularity suitable for deterministic traceability such as:

- a sentence-level statement,

- a single bullet statement,

- a single table-row assertion,

- a definition line or constraint-like statement.

A Source exists to:

- preserve the original wording used for downstream analysis,

- enable deterministic review of what source content was used.

## Non-Purpose (NORMATIVE)

- Store paraphrases, summaries, or inferred interpretations.

- Act as a document catalogue entry without excerpt text.

- Store derived outputs such as requirements or gaps.

## Attributes (with descriptions)

- `source_id: string` (REQUIRED, format `S###`)

  Description: Stable identifier for this Source element. Used by all derived elements (Signals, Segments, SourceAtoms, CellContentItems) to anchor provenance chains.

  Notes: null

- `source_text: string` (REQUIRED)

 Description: Verbatim excerpt from an immutable input artefact. This is the raw evidence that downstream analysis will interpret. MUST preserve the original wording without paraphrasing, summarising, or cleanup. 

Notes: Preserve whitespace, punctuation, and casing as they appear in the source. If the input is a structured format (table row, bullet), capture the text content only; structural context belongs in `segmentation_context`.

- `segmentation_context: string` (REQUIRED)

Description: Classification explaining why this excerpt exists at this granularity in the ledger's scope. Typically identifies the role the excerpt plays in the original artefact (e.g., "normative statement", "definition", "table row entry", "bullet in requirements section"). 

Notes: Free-text; no enumeration enforced. SHOULD be consistent across similar excerpts within a single ledger.

- `parent_source_ref: string` (OPTIONAL, format `S###`)

Description: Reference to a broader Source excerpt that this Source is a sub-excerpt of. Enables a Source hierarchy where a paragraph-level Source contains sentence-level Sources as children. 

Notes: Use SourceAtom for sub-sentence granularity. Use `parent_source_ref` when both parent and child are at sentence-or-coarser granularity.

- `input_material_ref: string` (REQUIRED)

Description: Free-text reference to the input artefact (document, file, conversation, or other material) from which this Source was extracted. Typically a filename, URL, document title, or short descriptive label. 

Notes: Input materials are not modelled as first-class ledger elements in this specification. Groupings of Sources by shared input material MAY be derived as a projection by filtering on this field.

- `confidence: number` (REQUIRED, 0.0..1.0)

Description: Confidence that this excerpt has been correctly extracted and classified. Typically 1.0 for direct verbatim extraction from a clean text input; lower when OCR, transcription, or interpretation introduces uncertainty. 

## Normative Rules

- `source_id` MUST be unique and match `^S\\d{3}$`.

- If `parent_source_ref` is present, it MUST reference an existing Source and MUST NOT self-reference.

- The ledger remains conformant if all provenance tracing is performed to `Source` elements and no `SourceAtom` elements are present.

# Element Type — SourceRegister

**Specialisation of:** `Register`

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `Source` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

## Non-Purpose (NORMATIVE)

- Store paraphrases, summaries, or inferred interpretations.

- Act as a document catalogue entry without excerpt text.

- Store derived outputs such as requirements or gaps.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE SourceRegister SHALL exist.

- `register_type` SHALL be `Source`.

- `member_ids` SHALL contain ALL `Source.source_id` values.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL Source elements present in the ledger.

# Element Type — Segment

## Purpose (NORMATIVE) 

A `Segment` element represents a **coarse-grained, contiguous block** of an immutable input artefact that is useful as a segmentation boundary for analysis, such as:

- a paragraph,

- a bullet block,

- a table row-group or section block.

A Segment exists to:

- provide stable, human-reviewable segmentation boundaries,

- group related `Source` excerpts under a common contextual boundary,

- support deterministic review of which input blocks were considered relevant.

## Non-Purpose (NORMATIVE) — Clarify

A Segment SHALL NOT be interpreted as a fine-grained provenance anchor intended for sentence-level traceability. Sentence/statement-level provenance anchors belong to `Source` (and optionally `SourceAtom` when used).

## Attributes (with descriptions)

- `segment_id: string` (REQUIRED, format `SEG###`)

Description: Stable identifier for this Segment element.

- `title: string` (REQUIRED)

  Description: Short human-readable label for this segment. Used for navigation in projections and reviews.

  Notes: Typical length 3-10 words. Not enforced; a generator SHOULD produce titles that are distinct within the ledger.

- `description: string` (OPTIONAL)

  Description: Optional longer-form description of what this segment contains or represents. Used when the title alone is insufficient to identify the segment in review.

- `source_refs: string[]` (REQUIRED; references `Source.source_id`)

  Description: The set of Source elements that together constitute this segment. A segment groups Sources that share a common contextual boundary (paragraph, bullet block, table section).

Notes: Order within `source_refs` is not semantically significant unless declared otherwise by generator convention.

- `parent_segment_ref: string` (OPTIONAL; references `Segment.segment_id`)

  Description: Reference to a broader Segment that this Segment is contained within. Enables hierarchical segmentation (e.g., a section segment containing paragraph segments).

- `confidence: number` (REQUIRED, 0.0..1.0)

  Description: Confidence that this segmentation correctly represents a meaningful boundary in the input material.

## Normative Rules

- `segment_id` MUST be unique.

- `segment_id` MUST match regex `^SEG\\d{3}$`.

- `title` MUST NOT be empty.

- `source_refs` MUST contain at least one entry and each entry MUST reference an existing `Source.source_id`.

- If `description` is present, it MUST NOT be empty.

- If `parent_segment_ref` is present:

  - MUST reference an existing `Segment.segment_id`

  - MUST NOT self-reference

- `confidence` MUST be within 0.0..1.0.

- A Segment MAY be represented either by its own descriptive metadata and references to `Source` elements (`source_refs`)

- A Segment is conformant even if it references **no SourceAtoms** directly (Segments do not enumerate atoms).

---

# Element Type — SegmentRegister

**Specialisation of:** `Register`  

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `Segment` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE SegmentRegister SHALL exist IF `Segment` elements  exist.

- `register_type` SHALL be `Segment`.

- `member_ids` SHALL contain ALL `Segment.segment_id` values.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL Segment elements present in the ledger.

---

# Element Type — SourceAtom

## Purpose (NORMATIVE) — Replace / Clarify

A `SourceAtom` element represents an **OPTIONAL, fine-grained** verbatim fragment derived from a `Source` excerpt, intended only where sub-source granularity is required.

SourceAtom exists to:

- enable sub-sentence (or sub-row) provenance anchors where necessary,

- support highly precise traceability in advanced use cases.

## Non-Purpose (NORMATIVE)

- Store paraphrases, summaries, or inferred interpretations.

- Act as a document catalogue entry without excerpt text.

- Store derived outputs such as requirements or gaps.

- A SourceAtom SHALL NOT be treated as mandatory for ledger conformance.

## Attributes (with descriptions)

- `atom_id: string` (REQUIRED, format `SA###`)

Description: Stable identifier for this SourceAtom element.

- `atom_text: string` (REQUIRED)

Description: Verbatim atomic fragment — typically a clause, phrase, or sub-sentence token that carries a distinct semantic signal within a larger Source. Preserved as-is for fine-grained provenance.

Notes: Use SourceAtom only when sub-sentence granularity is needed.  For sentence-level provenance, Source alone is sufficient.

- `source_ref: string` (REQUIRED; references `Source.source_id`)

Description: The parent Source from which this atomic fragment was extracted. Every SourceAtom MUST belong to a Source.

- `segment_ref: string` (OPTIONAL; references `Segment.segment_id`)

Description: The Segment within which this atom is contextually scoped. Use to attach broader segmentation context that the parent Source alone does not carry.

- `parent_atom_ref: string` (OPTIONAL; references `SourceAtom.atom_id`)

Description: Reference to a broader SourceAtom that this SourceAtom refines. Enables atom hierarchies where a clause-level atom contains token-level atoms.

- `confidence: number` (REQUIRED, 0.0..1.0)

Description: Confidence that this atomic fragment has been correctly extracted from its parent Source.

## Normative Rules

- `atom_id` MUST be unique.

- `atom_id` MUST match regex `^SA\\d{3}$`.

- `atom_text` MUST NOT be empty.

- `source_ref` MUST reference an existing `Source.source_id`.

- If `segment_ref` is present, it MUST reference an existing `Segment.segment_id`.

- If `parent_atom_ref` is present:

  - MUST reference an existing `SourceAtom.atom_id`

  - MUST NOT self-reference

- `confidence` MUST be within 0.0..1.0.

---

# Element Type — SourceAtomRegister

**Specialisation of:** `Register`  

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `SourceAtom` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

- A `SourceAtomRegister` is OPTIONAL.

- If no SourceAtom elements exist in a ledger instance, a SourceAtomRegister MAY be omitted.

- If one or more SourceAtom elements exist, a SourceAtomRegister MUST exist and enumerate all SourceAtom identifiers.

## Non-Purpose (NORMATIVE)

- Store paraphrases, summaries, or inferred interpretations.

- Act as a document catalogue entry without excerpt text.

- Store derived outputs such as requirements or gaps.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE SourceAtomRegister SHALL exist IF `SourceAtom` elements  exist.

- `register_type` SHALL be `SourceAtom`.

- `member_ids` SHALL contain ALL `SourceAtom.atom_id` values.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL SourceAtom elements present in the ledger.

---

# Element Type — Signal

## Purpose (NORMATIVE)

- Represent a discrete, typed **evidence cue** detected in a Source (or SourceAtom) during analysis at the correct level for the row under development.

- Provide an auditable intermediate layer between verbatim provenance (Source/SourceAtom) and derived artefacts (e.g., CellContentItem, Requirement, Gap, Question).

- Enable deterministic re-use of detected cues across later passes without re-interpreting raw text differently per run.

## Non-Purpose (NORMATIVE)

- Replace `Source` as the primary verbatim provenance anchor.

- Represent deficiencies requiring closure (use `Gap` / `Question`).

- Store rewritten/paraphrased text not evidenced by Source/SourceAtom anchors.

- Act as free-form commentary without explicit type and provenance.

## Attributes (with descriptions)

- `signal_id: string` (REQUIRED, format `SG###`)

  Description: Stable identifier for this Signal element.

- `signal_type: string` (REQUIRED)

Description: Classification of the signal cue. Enumerated values: Normative, Intent, Actor, Concern, Ambiguity, Quality.

Notes:

    - Normative: an explicit obligation or constraint statement.

    - Intent: a goal, purpose, or desired outcome.

    - Actor: an identified stakeholder, role, or participant.

    - Concern: a risk, issue, or point requiring attention.

    - Ambiguity: a statement that is unclear, contradictory, or

      under-specified.

    - Quality: a non-functional property (performance, security,

      reliability, etc.) appearing in the source material.

- `row_target: string` (REQUIRED; one of "1", "2", "3", "4", "5", "6")

Description: The Zachman row whose analysis produced this Signal. See § Ledger Scope and Row Semantics for the full row-value table and row attribution rules.

- `description: string` (REQUIRED)

Description: Human-readable statement describing what cue was detected and how it should be interpreted as evidence. Describes an observation, not an outcome; Gap or evaluation semantics belong on their respective elements.

- `source_refs: string[]` (REQUIRED; references `Source.source_id` or `Requirement.requirement_id`)

Description: Provenance anchors for this Signal. Each entry MUST be either a `Source.source_id` (the Signal is evidenced directly from input material) or a `Requirement.requirement_id` from an earlier row (the Signal is evidenced by upstream analysis output).

Notes: Typically one entry per Signal. Multiple entries are permitted when evidence spans multiple Sources, multiple Requirements, or a combination. Any referenced Requirement MUST have `row_target`strictly less than this Signal's `row_target`.

- `sourceatom_refs: string[]` (OPTIONAL; references `SourceAtom.atom_id`)

  Description: Finer-grained provenance anchors when SourceAtom elements are in use. Provides sub-sentence precision beyond what `source_refs` alone can express.

- `confidence: number` (REQUIRED, 0.0..1.0)

Description: Confidence that this signal has been correctly detected and classified.

- `derived_from_concern_id: string` (OPTIONAL) [NEW v2.12]

  Description: Reference to the Concern (CNNNN) from which this Signal was created, when the Signal was produced via the Concern resolution lifecycle (Phase 10 Practitioner Answer with outcome=Resolved). Null for Signals produced directly from Source or Requirement content without a prior Concern phase.

  Notes: When populated, the referenced CNNNN MUST exist in the ledger and MUST have `state=Resolved`. The Concern's `produced_in_row` MUST equal this Signal's `row_target`.

## Normative Rules

- `signal_id` MUST be unique.

- `signal_id` MUST match regex `^SG\\d{3}$`.

- `signal_type` MUST NOT be empty.

-  `row_target` MUST NOT be empty.

-  `row_target` MUST be one of: "1", "2", "3", "4", "5", "6".

- `description` MUST NOT be empty.

- `source_refs` MUST contain at least one entry.

- Each entry in `source_refs` MUST reference an existing `Source.source_id` or `Requirement.requirement_id`.

- Any Requirement referenced in `source_refs` MUST have `row_target`strictly less than this Signal's row_target.

- If `sourceatom_refs` is present:

  - MUST contain at least one entry

  - Each entry MUST reference an existing `SourceAtom.atom_id`.

- `confidence` MUST be within 0.0..1.0.

- If `derived_from_concern_id` is present, it MUST reference an existing `Concern.concern_id` in the ledger. [NEW v2.12]

- If `derived_from_concern_id` is present, the referenced Concern MUST have `state` = "Resolved". [NEW v2.12]

- If `derived_from_concern_id` is present, the referenced Concern's `produced_in_row` MUST equal this Signal's `row_target`. [NEW v2.12]

## Dual-Stream Provenance Note (INFORMATIVE) [NEW v2.12]

`source_refs` carries the provenance of the Signal's input stream. The schema already accepts both `Source.source_id` and `Requirement.requirement_id` entries (see JSON Schema `SignalPayload` — `source_refs` items use `oneOf` accepting `id_S` or `id_R`). This is documented here explicitly for cross-mechanism clarity:

- **Stream 1 Signal** (derived from original Sources): `source_refs` contains `Source.source_id` entries (`S###` format).

- **Stream 2 Signal** (derived from upstream Requirements): `source_refs` contains `Requirement.requirement_id` entries (`R###` format).

- **Mixed Signal** (synthesises content from both streams): `source_refs` contains entries of both formats.

Any Requirement referenced in `source_refs` MUST have `row_target` strictly less than this Signal's `row_target` (existing normative rule — upstream row constraint).

When a Signal is created from a resolved Concern, `derived_from_concern_id` (nullable attribute on Signal) references the originating Concern (CNNNN). This attribute is populated only when the Signal was produced via the Concern resolution lifecycle (Phase 10 Answer with outcome=Resolved).

---

# Element Type — SignalRegister

**Specialisation of:** `Register`

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `Signal` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE SignalRegister SHALL exist.

- `register_type` SHALL be `Signal`.

- `member_ids` SHALL contain ALL `Signal.signal_id` values.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL Signal elements present in the ledger.

- `confidence` MUST be within 0.0..1.0.

---

# Element Type — CellContentItem

## Purpose (NORMATIVE)

- Represent a single piece of row-and-column-scoped content derived from one or more Signals during the analysis of a Zachman cell.

- Act as the unit of content that Domains group and Requirements derive from — the bridge between raw Signals (evidence cues) and the formal  outputs of a row (Domains, Requirements).

- Preserve attribution from the Signals that triggered the classification so that derived Requirements can be traced back to the originating input material.

## Non-Purpose (NORMATIVE)

- Restate the content of the Signals that produced it. A CellContentItem expresses the classified meaning for cell-level analysis; the raw evidence remains on the Signals.

- Carry row coordinate directly. Row is inferred via `cell_id` from the referenced ZachmanCell (see § Row Inference Rules).

- Act as a Requirement, a Gap, or a Coverage outcome. Those semantics belong on their respective element types.

## Attributes (with descriptions)

- `ci_id: string` (REQUIRED, format `^CCI-ROW[1-6]-C-(What|How|Where|Who|When|Why)-\\d{3}$`)

 Description: Stable identifier for this CellContentItem element. The structured form encodes the row (1-6) and column (one of the six Zachman interrogatives) of the parent ZachmanCell, plus a sequence number scoped to that (row, column) cell.

Notes: Identifier sequence allocation is per (row, column) pair — one sequence per ZachmanCell instance, not one global CCI sequence. Implementations must allocate sequence numbers within the scope of the CCI's parent ZachmanCell. Defect 4.5 in the v2.8 defect list closed in v2.10 by locking this canonical format.

- `cell_id: string` (REQUIRED; references `ZachmanCell.cell_id`)

Description: The ZachmanCell this CellContentItem belongs to. Anchors the item to a specific (row, column) position in the Zachman grid and, by inference, establishes this CellContentItem's row scope.

- `classification_type: string` (REQUIRED)

Description: The classification assigned to this piece of cell content, reflecting what kind of content-item it is within the cell's interrogative (What/How/Where/Who/When/Why).

Notes: Free-text; no enumeration enforced at ledger level. Example values by column: for a "What" cell — "Entity", "Attribute", "Relationship"; for a "How" cell — "Process", "Function", "Rule"; for a "Who" cell — "Actor", "Role", "Organisation". Generators SHOULD use a stable vocabulary within a single ledger.

- `signal_refs: string[]` (REQUIRED; references `Signal.signal_id`)

Description: The Signals whose detected evidence led to the creation of this CellContentItem. Every CellContentItem MUST be grounded in at least one Signal.

Notes: A single CellContentItem MAY aggregate evidence from multiple Signals when they point to the same cell content. Signals MAY be referenced by multiple CellContentItems when the same evidence legitimately supports multiple classifications.

- `description: string` (REQUIRED)

  Description: Human-readable statement describing the specific piece of cell content this item represents. Expresses the classified meaning (e.g., "Customer entity with attributes name, email, and status") in a form suitable for review.

- `trigger_condition: string` (OPTIONAL)

Description: Optional condition under which this content item is active, relevant, or applies. Used for content that is conditional rather than unconditionally present (e.g., "applies only during maintenance mode", "active when user role is Administrator").

- `justification: string` (OPTIONAL)

Description: Optional explanation of why this content item was classified as it was, captured for audit and review. Complements `signal_refs` by providing the reasoning, not just the evidence.

- `confidence: number` (REQUIRED, 0.0..1.0)

Description: Confidence that this CellContentItem has been correctly classified and that the referenced Signals genuinely support the classification.

## Normative Rules

- `ci_id` MUST be unique.

- `cell_id` MUST reference an existing `ZachmanCell.cell_id`.

- `signal_id` MUST contain at least one entry and each entry MUST reference a valid ledger element identifier.

- `signal_refs` MUST contain at least one entry; each entry MUST reference an existing Signal.

- Entries in `signal_refs` MUST NOT be duplicated.

- The `cell_id` referenced MUST resolve to a ZachmanCell whose row equals the `row_target` of every Signal in `signal_refs`.

---

# Element Type — ZachmanCell

## Purpose (NORMATIVE)

- Represent a Zachman framework cell within a defined row/column scope.

- Provide a structural anchor for cell-scoped content and completeness checks.

- Encode both Zachman coordinates (row via `row`, interrogative/column via `column`) in a single element type. The six interrogatives (What, How,  Where, Who, When, Why) are represented as enumerated values of `column`rather than as separate ledger elements.

## Attributes (with descriptions)

- `cell_id: string` (REQUIRED, format `ZC-R{row}-C-{column}`)

  Description: Stable identifier encoding both the row and column coordinates of this cell. Canonical form is `ZC-R{row}-C-{column}` where `{row}` is "1" through "6" and `{column}` is one of the six interrogatives.

Notes: Example: `ZC-R1-C-What`, `ZC-R3-C-How`, `ZC-R6-C-Why`. See § Identifier Conventions for the full regex.

- `row_target: string` (REQUIRED; one of "1", "2", "3", "4", "5", "6")

Description: The Zachman row this cell belongs to. Forms a coordinate pair with `column`. Together they uniquely position the cell in the Zachman grid.

Notes: See § Ledger Scope and Row Semantics for canonical row-value meanings and row-attribution rules. ZachmanCell.row_target is the ground-truth anchor from which other elements infer their row.

- `column: string` (REQUIRED; one of "What", "How", "Where", "Who", "When", "Why")

  Description: The Zachman interrogative this cell represents. Forms a coordinate pair with `row_target`.

Notes: Interrogative meanings: What (Data/Information), How (Function/Process), Where (Network/Location), Who (People/Organisation), When (Time/Schedule), Why (Motivation/Goal). These are the six  interrogatives of the Zachman Framework and are not modelled as separate ledger elements (see defect 8.10 resolution).

## Normative Rules

- `cell_id` MUST be unique within the ledger. 

- `cell_id` MUST match regex `^ZC-R[1-6]-C-(What|How|Where|Who|When|Why)$`.- `row_target` MUST NOT be empty.

- `row_target` MUST NOT be empty.

- `row_target` MUST be one of: "1", "2”, “3”, “4”, “5”, “6”

- The digit immediately following `-R` in `cell_id` MUST equal the value of the `row_target` field. 

- The column interrogative appearing after `-C-` in `cell_id` MUST equal the value of the `column` field.

- `column` MUST NOT be empty.

- `column` MUST be one of: "What", "How", "Where", "Who", "When", "Why".

- `cell_id`, `row_target`, and `column` MUST be mutually consistent: for a ZachmanCell with `row_target = "N"` and `column = "X"`, the `cell_id` MUST equal `ZC-RN-C-X`.

- No two `ZachmanCell` elements within the same ledger MAY share the same (`row_target`, `column`) coordinate pair. At most one `ZachmanCell` SHALL exist per grid position.

# Element Type — ZachmanCellRegister

**Specialisation of:** `Register`  

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `ZachmanCell` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE ZachmanCellRegister SHALL exist.

- `register_type` SHALL be `ZachmanCell`.

- `member_ids` SHALL contain ALL `ZachmanCell.cell_id` values.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL ZachmanCell elements present in the ledger.

---

# Element Type — Domain

## Purpose (NORMATIVE)

- Represent a classification domain used to organise and contextualise ledger elements.

- Support domain coverage analysis and structured viewpoints.

## Attributes (with descriptions)

- `domain_id: string` (REQUIRED, format `D###`)

Description: Stable identifier for this Domain element.

- `name: string` (REQUIRED)

Description: Short label for this Domain, used in projections, reviews, and requirement attribution. SHOULD be distinct and descriptive within the ledger.

Notes: Typical length 2-5 words. Examples: "User Identity Management", "Order Fulfilment Workflow", "Data Retention Constraints".

- `description: string` (REQUIRED)

Description: Human-readable explanation of what this Domain represents, what content it groups, and why that grouping is meaningful for the row's analysis.

- `classification_type: string` (OPTIONAL)

Description: Optional classification describing the nature of the Domain itself (e.g., "Functional", "Structural", "Behavioural", "Regulatory"). Provides metadata about the kind of grouping the Domain represents, not its content.

Notes: Free-text; no enumeration enforced. A generator SHOULD use a stable vocabulary across Domains within a single ledger to enable filtering.

- `row_target: string` (REQUIRED; one of "1", "2", "3", "4", "5", "6")

Description: The Zachman row this Domain primarily targets. Enables first-class row-scoped queries and coverage analysis without traversing linked CellContentItem elements.

Notes: See § Ledger Scope and Row Semantics for row-value meanings. MUST equal the row of every CellContentItem referenced by `cell_content_item_refs`.

- `cell_content_item_refs: string[]` (REQUIRED; references `CellContentItem.ci_id`)

Description: The CellContentItems that together constitute this Domain. A Domain groups CellContentItems into a logical unit for Requirement derivation and coverage analysis.

Notes: MUST contain at least one entry. Entries MUST reference CellContentItems whose cell row equals this Domain's `row_target`.

## Normative Rules

- `domain_id` MUST be unique.

- `domain_id` MUST match regex `^D\\d{3}$`.

- `name` MUST NOT be empty.

- `description` MUST NOT be empty.

- If `row_target` is present:

  - MUST be one of: "1", "2", "3", "4", "5", "6"

  - SHOULD correspond to a `ZachmanCell.row_target` value that exists in the same ledger

- `row_target` MUST equal the row of every CellContentItem referenced by `cell_content_item_refs` (each CellContentItem's row is inferred from its cell_id via ZachmanCell.row).

- `cell_content_item_refs` MUST NOT be empty.

---

# Element Type — DomainRegister

**Specialisation of:** `Register`  

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `Domain` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE DomainRegister SHALL exist.

- `register_type` SHALL be `Domain`.

- `member_ids` SHALL contain ALL `Domain.domain_id` values.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL Domain elements present in the ledger.

---

# Element Type — Requirement

## Purpose (NORMATIVE)

- Represent a normative obligation/constraint within the ledger scope.

- Support verification, traceability, and cross-row elaboration.

- Preserve requirement statements independent of source document layout.

## Non-Purpose (NORMATIVE)

- Store gaps or suggestions (use their dedicated element types).

- Encode implementation decisions unless explicitly a constraint.

## Attributes (with descriptions)

- `requirement_id: string` (REQUIRED, format `R###`)

  Description: Stable identifier for the Requirement element.

  Notes: null

- `statement: string` (REQUIRED)

  Description: Normative requirement statement captured for this ledger scope.

  Notes: null

- `requirement_type: string` (REQUIRED; Functional|Constraint|Performance|Suitability|Non-Functional)

  Description: Classification of the requirement (e.g., Functional, Constraint).

  Notes: null

- `row_target: string` (REQUIRED; one of "1", "2", "3", "4", "5", "6")

  Description: The Zachman row whose analysis produced this Requirement. Enables direct row-scoped queries and cross-row integrity checks without traversing cci_refs.

  Notes: MUST match the row of all CellContentItems referenced by

  `cci_refs` and the row of all Domains referenced by `domain_refs`.

- `rationale: string` (OPTIONAL)

  Description: Optional justification explaining why the requirement exists.

  Notes: null

- `cci_refs: string[]` (REQUIRED; references `CellContentItem.ci_id`)

  Description: Provenance anchors supporting this element via CellContentItem identifiers.

  Notes: null

- `answer_refs: string[]` (OPTIONAL; references `Answer.answer_id`)

  Description: Provenance anchors supporting that this element was created  by the gap, question, answer mechanism via Answer identifiers.

  Notes: null

- `domain_refs: string[]` (REQUIRED; references `Domain.domain_id`)

  Description: Optional domain classification references relevant to this element.

  Notes: null

- `fit_criteria: string` (OPTIONAL)

  Description: Optional acceptance/satisfaction criteria defining how compliance is judged.

  Notes: null

- `verification_method: string` (OPTIONAL; Test|Analysis|Inspection|Demonstration)

  Description: Optional description of how satisfaction is verified.

  Notes: null

- `priority: string` (OPTIONAL; High|Medium|Low)

  Description: Optional importance/criticality indicator.

  Notes: null

- `confidence: number` (REQUIRED, 0.0..1.0)

  Description: Confidence that this element’s content/classification is correct (0.0..1.0).

  Notes: null

## Normative Rules

- `requirement_id` MUST be unique.

- `requirement_id` MUST match regex `^R\\d{3}$`.

- `statement` MUST NOT be empty.

- `cci_refs` MUST NOT be empty.

- If `fit_criteria` is present, it MUST NOT be empty.

- `requirement_type` MUST be one of the defined enumeration values.

- If `requirement_type == Performance`, `fit_criteria` SHOULD be present.

- `domain_refs` MUST contain at least one entry referencing an existing `Domain.domain_id`.

- `row_target` MUST be one of: "1", "2", "3", "4", "5", "6".

- `row_target` MUST equal the row of every CellContentItem referenced

  by `cci_refs` (each CellContentItem's row is inferred from its

  cell_id via ZachmanCell.row_target).

- `row_target` MUST equal the `row_target` of every Domain referenced

  by `domain_refs`.

- `confidence` MUST be within 0.0..1.0.

---

# Element Type — RequirementRegister

**Specialisation of:** `Register`  

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `Requirement` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE RequirementRegister SHALL exist.

- `register_type` SHALL be `Requirement`.

- `member_ids` SHALL contain ALL `Requirement.requirement_id` values.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL Requirement elements present in the ledger.

---

# Element Type — AnalysisPass

## Purpose (NORMATIVE)

- Record a discrete analytical activity executed within the SysEngage process.

- Enable attribution of analytical outputs (Gaps, Suggestions, Coverage, Sources, Segments, SourceAtoms) to the mechanism execution that produced them.

- Support auditability and run reconstruction including mode discipline tracking, read provenance, and execution timing.

- Provide the canonical anchor for Read Witness data (per architectural commitment F10) and mechanism provenance (per architectural commitment F4) without embedding process logic.

## Attributes (with descriptions)

- `pass_id: string` (REQUIRED, format `P###`)

  Description: Stable identifier for the AnalysisPass element.

  Notes: null

- `pass_type: string` (REQUIRED)

  Description: Broad classification of analysis activity. Typical values include "Universal" (mechanism runs once per project, e.g., Source Capture), "Per-row" (mechanism runs per Zachman row), "Practitioner" (Practitioner-initiated analysis activity). Distinct from `mechanism` (which names the specific mechanism implementation).

  Notes: Free-text classification; no enumeration enforced by schema.

- `mechanism: string` (REQUIRED)

  Description: Name of the mechanism implementation that produced this pass. Typical values include canonical mechanism names such as "SourceCapture", "RowLensSourceReAnalysis", "ActorSignalIdentification". Provides mechanism provenance per architectural commitment F4.

  Notes: SHOULD be consistent across passes from the same mechanism. Format follows mechanism naming convention (PascalCase identifier).

- `execution_status: string` (REQUIRED, enum)

  Description: Outcome of the pass execution. Enum: "Success" (mechanism completed without error and produced all expected outputs), "Failed" (mechanism aborted due to error; AnalysisPass.outputs.failure_reason and failure_pass populated), "PartialSuccess" (mechanism completed but with partial-failure conditions such as decoder errors mid-stream; AnalysisPass.outputs records the partial-failure detail).

  Notes: Failed and PartialSuccess passes are still recorded for audit trail.

- `mode_active: string` (REQUIRED, enum)

  Description: The Transformation Mode the pass actually operated in. Enum: "LPM" (Literal Persistence Mode — byte-preserving, deterministic, no AI semantic interpretation), "IM" (Interpretation Mode — AI-assisted semantic interpretation permitted), additional modes per Row 1 Understanding §8.3 / Row 2 Understanding §3.3.4 if defined. Provides mode discipline audit trail.

  Notes: Single value (the active mode); `declared_transformation_modes` lists permitted modes.

- `declared_transformation_modes: array of string` (REQUIRED)

  Description: The set of Transformation Modes the pass was declared to operate in (typically size 1 for purely-deterministic passes; may have multiple values for passes that switch modes). Used at audit time to verify the active mode was one of the declared permitted modes.

  Notes: Non-empty array; each element MUST be a valid mode identifier.

- `outputs: object` (REQUIRED)

  Description: Mechanism-specific output sub-structure. Conventional top-level keys: `read_witness` (proof of complete read for mechanisms that read input material — provides input_hash, byte_count, character_count, read_mode, read_completion_status per architectural commitment F10), `mechanism_data` (mechanism-specific accumulator state — e.g., entity counts, cross-source ordering metadata, ids of produced entities), `mode_violations` (array, populated if any mode-discipline violation occurred during pass; empty array on clean execution), `failure_reason` (populated only when execution_status is Failed or PartialSuccess), `failure_pass` (populated only on failure, identifies which sub-Pass within the mechanism failed).

  Notes: Specific structure within `outputs` varies per mechanism — defined by the mechanism's specification, not enumerated in this schema. JSON Schema validates the outer `outputs` field as an object; mechanism-specific sub-structure validation is the responsibility of the mechanism's Pydantic model or equivalent.

  Conventional sub-keys (documented here for cross-mechanism consistency; not schema-enforced):

  - `read_witness`: proof of complete input read for mechanisms that ingest input material. Sub-fields: `input_hash`, `byte_count`, `character_count`, `read_mode`, `read_completion_status`. Per architectural commitment F10.

  - `mechanism_data`: mechanism-specific accumulator state — entity counts, cross-source ordering metadata, ids of produced entities.

  - `mode_violations`: array of mode-discipline violation records; empty array on clean execution.

  - `row_lens_data` [NEW v2.12]: present when `mechanism` is `RowLensSourceReanalysis`. Records dual-stream engagement evidence. Sub-fields: `row_ref` (integer 1–6 — which row's lens was applied), `stream1_source_count` (integer — Sources analysed from stream 1), `stream2_requirement_count` (integer — Requirements analysed from stream 2; 0 at Row 1), `signal_count_produced` (integer — total Signals produced across both streams), `concern_count_produced` (integer — total Concerns produced across both streams). Invariant: `stream1_source_count + stream2_requirement_count = signal_count_produced + concern_count_produced`.

- `pass_started_at: string` (REQUIRED, format datetime)

  Description: ISO 8601 timestamp recording when the pass execution began.

  Notes: Must precede or equal `pass_completed_at` if both present.

- `pass_completed_at: string` (OPTIONAL, format datetime)

  Description: ISO 8601 timestamp recording when the pass execution completed. Null while pass in progress; populated on completion regardless of execution_status (Success, Failed, or PartialSuccess all set this on terminal pass state).

  Notes: Implementation MAY persist intermediate AnalysisPass records with completed_at null for long-running passes; conformant final state has completed_at populated.

- `elapsed_ms: integer` (OPTIONAL)

  Description: Convenience field — elapsed milliseconds between pass_started_at and pass_completed_at. May be derived by readers from the timestamps; including it explicitly simplifies queries.

  Notes: When populated, MUST be consistent with pass_completed_at − pass_started_at.

- `confidence: number` (REQUIRED, 0.0..1.0)

  Description: Confidence that this AnalysisPass's recorded content (the produced entities, the witness data, the audit trail) is correctly attributed to the mechanism execution. Typically 1.0 for deterministic LPM mechanisms; lower values reserved for AI-assisted analytical passes where attribution may be uncertain.

  Notes: Distinct from confidence of produced entities (each entity carries its own confidence). This is the confidence of the AnalysisPass record itself.

## Normative Rules

- `pass_id` MUST be unique within the ledger.

- `pass_id` MUST match regex `^P\\d{3}$`.

- `pass_type` MUST NOT be empty.

- `mechanism` MUST NOT be empty.

- `execution_status` MUST be one of: "Success", "Failed", "PartialSuccess".

- `mode_active` MUST NOT be empty. Implementations SHOULD restrict to declared Transformation Modes; the canonical schema does not enforce a specific enum to remain extensible.

- `declared_transformation_modes` MUST contain at least one entry.

- `mode_active` MUST appear in `declared_transformation_modes` (the active mode must be among the declared permitted modes).

- `outputs` MUST be an object.

- If `execution_status` is "Success", `outputs.mode_violations` (if present) MUST be an empty array.

- If `execution_status` is "Failed" or "PartialSuccess", `outputs.failure_reason` MUST be populated with a non-empty string.

- `evaluated_scope` MUST NOT be empty.

- `pass_started_at` MUST be a valid ISO 8601 datetime.

- If `pass_completed_at` is present, it MUST be a valid ISO 8601 datetime and MUST be greater than or equal to `pass_started_at`.

- `elapsed_ms` (if present) MUST be a non-negative integer consistent with the timestamps.

- `confidence` MUST be within 0.0..1.0.

---

# Element Type — CoverageItem

## Purpose (NORMATIVE)

- Record an assessment of completeness/alignment/sufficiency for a defined scope.

- Support robustness tracking and gap discovery.

- Preserve coverage outcomes independently of Gaps.

## Attributes (with descriptions)

- `coverage_id: string` (REQUIRED, format `CV###`)

Description: Stable identifier for this CoverageItem element.

- `coverage_type: string` (REQUIRED; one of CellCoverage, DomainCoverage, RequirementCoverage)

Description: The kind of ledger element whose coverage is being assessed. Determines how `target_ref` is interpreted.

 Notes:

- CellCoverage: assesses coverage of a CellContentItem (i.e., whether the cell content has the evidence, domain membership, and derived requirements needed to be considered complete).

- DomainCoverage: assesses coverage of a Domain (i.e., whether the Domain's grouped CellContentItems have collectively produced sufficient Requirements).

- RequirementCoverage: assesses coverage of a Requirement (i.e., whether the Requirement has the supporting cells, fit criteria, and verification method needed to be considered complete).

- `target_ref: string` (REQUIRED; references a valid ledger element identifier)

Description: The specific element being assessed. Its type MUST match `coverage_type`: CellContentItem for `CellCoverage`, Domain for `DomainCoverage`, Requirement for `RequirementCoverage`.

Notes: See Normative Rules for the target-typing constraint.

- `coverage_state: string` (REQUIRED; one of Covered, PartiallyCovered, NotCovered, Unknown)

Description: The assessed coverage state for the target element.

Notes:

- Covered: the target element is considered complete for the purposes of the current row's analysis.

- PartiallyCovered: the target element has some but not all of the expected supporting content; a Gap SHOULD exist describing the deficiency.

- NotCovered: the target element is identified as missing expected supporting content; a Gap MUST exist describing what is absent.

- Unknown: coverage could not be determined in this pass, typically because prerequisite analysis has not yet occurred.

- `produced_by_pass_id: string` (REQUIRED; references `AnalysisPass.pass_id`)

Description: The AnalysisPass that produced this CoverageItem. Enables attribution of coverage outcomes to specific analysis activities.

- `notes: string` (OPTIONAL)

Description: Optional free-text commentary on the coverage assessment. Use to record rationale for Partial or Unknown states, edge cases, or caveats that cannot be captured by the enumerated `coverage_state`.

- `confidence: number` (REQUIRED, 0.0..1.0)

Description: Confidence that this coverage assessment is correct. Typically high for mechanical checks (e.g., "does a Requirement have a fit_criteria?"); lower for subjective assessments.

## Normative Rules

- `coverage_id` MUST be unique.

- `coverage_id` MUST match regex `^CV\\d{3}$`.

- `coverage_type` MUST be one of: CellCoverage, DomainCoverage, RequirementCoverage.

- `target_id` MUST reference an existing ledger element identifier.

- `coverage_state` MUST be one of:

  Covered | PartiallyCovered | NotCovered | Unknown

- If `coverage_state == NotCovered`, a Gap MUST exist referencing this CoverageItem's `coverage_id` in its `coverage_item` array.

- If `coverage_state == PartiallyCovered`, a Gap SHOULD exist

  referencing this CoverageItem.

- `produced_by_pass_id` MUST reference an existing `AnalysisPass.pass_id`.

- If `notes` is present, it MUST NOT be empty.

- `confidence` MUST be within 0.0..1.0.

- Target typing constraint:

  - If `coverage_type == CellCoverage`, `target_id` MUST reference `CellContentItem.ci_id`.

  - If `coverage_type == DomainCoverage`, `target_id` MUST reference `Domain.domain_id`.

  - If `coverage_type == RequirementCoverage`, `target_id` MUST reference `Requirement.requirement_id`.

---

# Element Type — CoverageRegister

**Specialisation of:** `Register`  

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `Coverage` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE CoverageRegister SHALL exist.

- `register_type` SHALL be `CoverageItem`.

- `member_ids` SHALL contain ALL `CoverageItem.coverage_id` values.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL CoverageItem elements present in the ledger.

---

# Element Type — Gap (Aligned)

## Purpose (NORMATIVE)

- Record a missing, incomplete, inconsistent, or unresolved condition in scope.

- Support closure tracking and mitigation workflows.

- Enable traceability to impacted elements and (where applicable) Zachman cells.

## Non-Purpose (NORMATIVE)

- Store proposed solutions (use Suggestion).

## Attributes (with descriptions)

- `gap_id: string` (REQUIRED, format `G###`)

  Description: Stable identifier for the Gap element.

  Notes: null

- `description: string` (REQUIRED)

  Description: Human-readable statement describing the element’s content/meaning.

  Notes: null

- `impact: string` (REQUIRED)

  Description: Indicator of consequence/severity.

  Notes: null

- `coverage_item: string[]`(REQUIRED; references `CoverageItem.coverage_id` values)

  Description: List of coverage item identifiers that the gap describes.

  Notes: null

- `proposed_resolution: string` (REQUIRED)

  Description: See element definition for semantic meaning of `proposed_resolution`.

  Notes: null

- `resolution_state: string` (REQUIRED; Open|Accepted|Mitigated|Closed)

  Description: Lifecycle state of this Gap. Tracks progression through the gap-closure workflow from identification to resolution.

  Notes: 

**1. Open**

**Description:**
The gap has been identified but **not yet addressed**. This is the default state for all new gaps.
**When to Use:**

		- When a gap is first created.

		- When a gap is still under analysis or awaiting stakeholder input.

**2. Accepted**

**Description:**
The gap has been **reviewed and acknowledged**, but **no action will be taken** to address it at this time. This state is used when stakeholders decide the gap is not critical or relevant to the current scope.
**When to Use:**

		- When stakeholders respond "No" to a suggestion or question related to the gap.

		- When the gap is deemed "Not Applicable" or "Deferred" with a documented rationale.

**3. Mitigated**

**Description:**
The gap has been **partially addressed**, but **further action may be required** in future steps or iterations. This state is used when the gap cannot be fully closed at the current stage but has been improved (e.g., requirements updated, partial links added).
**When to Use:**

		- When a gap is partially resolved (e.g., requirements updated but traceability not fully restored).

		- When the gap is dependent on future work or external factors.

**4. Closed**

**Description:**
The gap has been **fully addressed** and resolved. All required actions (e.g., creating/updating requirements) have been completed, and the gap no longer exists.
**When to Use:**

		- When all proposed resolutions for the gap have been implemented.

		- When the gap is verified as resolved through stakeholder review or validation.

## Normative Rules

- `gap_id` MUST be unique within the ledger.

- `gap_id` MUST match regex `^G\\d{3}$`.

- `description` MUST NOT be empty.

- `impact` MUST be one of: High, Medium, Low.

- `coverage_item` MUST contain at least one entry.

- Each entry in `coverage_item` MUST reference an existing

  `CoverageItem.coverage_id`.

- Entries in `coverage_item` MUST NOT be duplicated within the array.

- `proposed_resolution` MUST NOT be empty.

- `resolution_state` MUST be one of: Open, Accepted, Mitigated, Closed.

- `confidence` MUST be within 0.0..1.0.

## State Transition Rules (NORMATIVE)

- A newly created Gap SHALL have `resolution_state = "Open"`.

- Permitted state transitions:

  - Open → Accepted (stakeholder decides no action will be taken)

  - Open → Mitigated (partial resolution applied)

  - Open → Closed (full resolution applied)

  - Mitigated → Closed (remaining work completed)

  - Mitigated → Accepted (remaining work abandoned with documented rationale)

- Transitions from Accepted and Closed SHALL NOT occur. Once a Gap is Accepted

  or Closed, a new Gap element MUST be created if the condition re-emerges.

- If `resolution_state == Closed`:

  - At least one `Requirement` in the ledger SHOULD reference a related

    `Answer` in its `answer_refs` whose `question_id` is linked to this Gap

    via `Question.related_gap_ids`. This evidences that the closure

    proceeded through the proper Gap → Question → Answer → Requirement

    workflow rather than being marked closed without action.

- If `resolution_state == Accepted`:

  - The Gap's `proposed_resolution` MUST state the rationale for acceptance.

- If `resolution_state == Mitigated`:

  - At least one `Suggestion` SHOULD exist with `produced_from_gap_ids`

    including this Gap's `gap_id`, documenting the partial resolution

    applied and any remaining work.---

# Element Type — GapRegister

**Specialisation of:** `Register`  

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `Gap` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE GapRegister SHALL exist.

- `register_type` SHALL be `Gap`.

- `member_ids` SHALL contain ALL `Gap.gap_id` values.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL Gap elements present in the ledger.

---

# Element Type — Suggestion

## Purpose (NORMATIVE)

- Record a proposed improvement or corrective action derived from analysis.

- Support mitigation and refinement workflows without asserting obligations.

- Preserve advisory outputs separately from Requirements.

## Attributes (with descriptions)

- `suggestion_id: string` (REQUIRED, format `SUG###`)

  Description: Stable identifier for the Suggestion element.

  Notes: null

- `type: string` (REQUIRED)

  Description: Classification of the observation category.

  Notes: null

- `description: string` (REQUIRED)

  Description: Human-readable statement describing the element’s content/meaning.

  Notes: null

- `priority: string` (REQUIRED; High|Medium|Low)

  Description: Optional importance/criticality indicator.

  Notes: null

- `target_element_ids: string[]` (REQUIRED; references any ledger element_id) 

Description: The ledger elements that this Suggestion proposes to improve, correct, add, or modify. Each entry is an element_id as defined in Appendix B.3. The type of the referenced element is inferred from its ID prefix. 

Notes: null 

- `rationale: string` (OPTIONAL)

  Description: Optional justification explaining why the requirement exists.

  Notes: null

- `produced_from_gap_ids: string[]` (REQUIRED; references `Gap.gap_id`)

  Description: See element definition for semantic meaning of `produced_from_gap_ids`.

  Notes: null

- `confidence: number` (REQUIRED, 0.0..1.0)

  Description: Confidence that this element’s content/classification is correct (0.0..1.0).

  Notes: null

## Normative Rules

- `suggestion_id` MUST be unique.

- `suggestion_id` MUST match regex `^SUG\\d{3}$`.

- `type` MUST NOT be empty.

- `description` MUST NOT be empty.

- `priority` MUST be one of: High, Medium, Low.

- `target_element_ids` MUST contain at least one entry. 

- Each entry in `target_element_ids` MUST be a non-empty string. 

- Each entry MUST reference an existing `element_id` within the same ledger. 

- Each entry MUST NOT be duplicated within `target_element_ids`. 

- If `rationale` is present, it MUST NOT be empty.

- Each entry in `target_element_ids` SHOULD reference an element whose type is one of: Requirement, CellContentItem, Domain, Gap, Question. If a Suggestion targets an element outside this set, `rationale` SHOULD be present and explain why. 

- the ‘produced_from_gap_ids` MUST contain at least one entry and each entry MUST reference an existing `Gap.gap_id`.

---

# Element Type — SuggestionRegister

**Specialisation of:** `Register`  

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `Suggestion` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE SuggestionRegister SHALL exist.

- `register_type` SHALL be `Suggestion`.

- `member_ids` SHALL contain ALL `Suggestion.suggestion_id` values.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL Suggestion elements present in the ledger.

---

# Element Type — Question

## Purpose (NORMATIVE)

- Represent an explicit question raised in response to an identified Gap, requiring an Answer to enable Gap closure or mitigation. 

- Capture both the question itself and the rationale for asking it, so that stakeholders (human or tool-as-stakeholder SH001) can provide informed Answers. 

- Serve as the intermediate element linking a Gap to its closure pathway: Gap → Question → Answer → (new or updated) Requirement → Gap closure.

## Non-Purpose (NORMATIVE)

- Record a Gap itself. Gaps describe conditions; Questions are actions taken in response to Gaps.

- Store the Answer. Answers are separate Answer elements referencing this Question via `Answer.question_id`.

- Act as an informal or conversational prompt. A Question is a formal ledger element that, when Answered, MAY drive normative change to the ledger's Requirements.

## Attributes (with descriptions)

- `question_id: string` (REQUIRED, format `Q###`)

Description: Stable identifier for this Question element.

- `question_text: string` (REQUIRED)

Description: The question being asked, in plain language. SHOULD be phrased so that the set of valid Answers is bounded (yes/no, a choice from an enumeration, or a specific constrained value).

Notes: Vague or open-ended question text typically produces Answers that cannot close a Gap. Example: instead of "Should we think about retention?", prefer "Should customer records be retained beyond account closure? If yes, for how long?".

- `expected_answer_format: string` (OPTIONAL)

Description: Optional description of the expected shape or constraints of a valid Answer. Guides the Answerer (human stakeholder or SysEngage tool) toward providing a response that can close the Gap.

Notes: Free-text. Examples: "yes/no", "one of: Active, Inactive, Archived", "a duration in days", "a list of applicable roles".

- `why_it_matters: string` (REQUIRED)

Description: Explanation of why this Question needs an Answer — what downstream Requirement or Gap closure depends on it. Captures the motivation for asking at ledger review time.

- `priority: string` (REQUIRED; one of High, Medium, Low)

Description: Importance of receiving an Answer. Used by generators and reviewers to triage which Questions to address first.

Notes:

- High: Gap closure blocked; downstream analysis cannot proceed.

- Medium: Gap closure desired but not blocking; workarounds exist.

- Low: Answer would improve quality but analysis can proceed without it.

- `status: string` (REQUIRED; one of Open, Answered, Closed)

Description: Lifecycle state of this Question.

Notes:

- Open: Question raised, no Answer yet exists.

- Answered: At least one Answer element references this Question via `question_id`.

- Closed: Question is resolved; either its Gap has been closed as a consequence of the Answer, or the Question has been withdrawn (with rationale recorded by a Stakeholder Answer or Suggestion).

- `related_gap_ids: string[]` (REQUIRED; references `Gap.gap_id`)

Description: The Gaps this Question was raised to help resolve. Every Question MUST be tied to at least one Gap; Questions without an underlying Gap are not within this ledger's scope.

Notes: All referenced Gaps MUST resolve to the same row (see § Row Inference Rules). Questions do not span rows.

- `confidence: number` (REQUIRED, 0.0..1.0)

Description: Confidence that this Question is correctly scoped to its referenced Gaps and that an Answer to it would meaningfully advance Gap closure.

## Normative Rules

- `question_id` MUST be unique.

- `question_id` MUST match regex `^Q\\d{3}$`.

- `question_text` MUST NOT be empty.

- `why_it_matters` MUST NOT be empty.

- `priority` MUST be one of: High, Medium, Low.

- `status` MUST NOT be empty and it MUST be one of: Open, Answered, Closed.

- `related_gap_ids` MUST contain at least one entry and each entry MUST reference an existing `Gap.gap_id`.

- If `status == Answered`, then at least one `Answer` MUST exist referencing this `Question.question_id`.

- If `expected_answer_format` is present, it MUST NOT be empty.

- All entries in `related_gap_ids` MUST resolve to the same inferred row (i.e., this Question MUST NOT span rows).

---

# Element Type — QuestionRegister

**Specialisation of:** `Register`  

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `Question` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE QuestionRegister SHALL exist.

- `register_type` SHALL be `Question`.

- `member_ids` SHALL contain ALL `Question.question_id` values.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL Question elements present in the ledger.

---

# Element Type — Answer

## Purpose (NORMATIVE)

- Record a Stakeholder's response to a Question, providing the information needed to close or mitigate the Gap that triggered the Question.

- Preserve attribution: the `provided_by` field identifies the Stakeholder who supplied the Answer, distinguishing human responses from responses produced by the SysEngage tool itself (SH001).

- Serve as the bridge between Question and downstream ledger change: an accepted Answer typically drives the creation or amendment of a Requirement, which in turn enables Gap closure.

## Non-Purpose (NORMATIVE)

- Record the Gap itself, the Question itself, or any derived Requirement. Those are separate elements; the Answer connects them.

- Act as a discussion or conversation thread. An Answer is a single, attributable response; iterative dialogue is modelled as multiple Answer elements referencing the same Question, not as conversational threading within one element.

## Attributes (with descriptions)

- `answer_id: string` (REQUIRED, format `A###`)

Description: Stable identifier for this Answer element.

- `question_id: string` (REQUIRED; references `Question.question_id`)

Description: The Question this Answer responds to. Every Answer MUST be tied to exactly one Question.

Notes: A single Question MAY have multiple Answers — for example, an initial Answer from SysEngage (SH001) followed by a reviewing human Stakeholder's Answer that confirms, revises, or overrides.

- `response_text: string` (REQUIRED)

Description: The content of the Answer in plain language. SHOULD directly address the form specified by `Question.expected_answer_format` if present.

Notes: For tool-provided Answers (`provided_by == SH001`), the response text SHOULD be phrased deterministically and avoid speculative language, so that a reviewing human Stakeholder can readily confirm or override.

- `provided_by: string` (REQUIRED, format `SH###`; references `Stakeholder.stakeholder_id`)

Description: The Stakeholder who provided this Answer. Identifies whether the Answer originated from a human, an organisational body, or the SysEngage tool itself (SH001).

  Notes: Consumers MAY filter Answers by `provided_by == SH001` to identify tool-generated responses requiring human review. See § SysEngage Tool Stakeholder in the Stakeholder element definition.

- `provided_utc: string` (OPTIONAL, RFC 3339 / ISO 8601 date-time)

Description: UTC timestamp at which this Answer was provided. Enables ordering of multiple Answers to the same Question and audit-trail reconstruction.

Notes: When multiple Answers exist for a single Question, the most recent Answer (by `provided_utc`) is typically treated as the currently-authoritative one, with earlier Answers retained for audit only.

- `confidence: number` (REQUIRED, 0.0..1.0)

Description: Confidence that this Answer correctly addresses the referenced Question. For human-provided Answers, typically set by the answering Stakeholder. For SH001-provided Answers, reflects the tool's confidence in its own inference.

## Normative Rules

- `answer_id` MUST be unique.

- `answer_id` MUST match regex `^A\\d{3}$`.

- `question_id` MUST reference an existing `Question.question_id`.

- `response_text` MUST NOT be empty.

- `provided_by` MUST match regex `^SH\\d{3}$`.

- `provided_by` MUST reference an existing `Stakeholder.stakeholder_id` within the same ledger.

- If `provided_utc` is present, it MUST be a valid RFC 3339 /  ISO 8601 UTC date-time string.

- `confidence` MUST be within 0.0..1.0.

---

# Element Type — AnswerRegister

**Specialisation of:** `Register`  

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `Answer` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE AnswerRegister SHALL exist.

- `register_type` SHALL be `Answer`.

- `member_ids` SHALL contain ALL `Answer.answer_id` values.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL Answer elements present in the ledger.

---

# Element Type — Stakeholder

## Purpose (NORMATIVE)

- Represent a stakeholder participating in the design, review, or analysis of the system described by this ledger. Stakeholders are the source of `Answer` elements that close `Gap` workflows.

- Preserve attribution of answers, decisions, and approvals to a named identity (human or non-human) for audit and review.

- Reserve `SH001` as the canonical identity of the SysEngage tool itself, acting as a non-human stakeholder (see § SysEngage Tool Stakeholder below).

## Non-Purpose (NORMATIVE)

- Represent roles or responsibility assignments abstractly. A Stakeholder is a concrete identity; role assignments are represented via element references (e.g., `Risk.owner`, `Answer.provided_by`).

- Record authentication, authorisation, or access-control information. Stakeholders identify who* acted; they do not encode *what they are permitted to do*.

## SysEngage Tool Stakeholder (NORMATIVE)

The SysEngage tool acts as a stakeholder in its own right when it provides Answers to Questions generated during Gap closure. This non-human stakeholder is reserved at the identifier `SH001`.

### Canonical SH001 record

Every ledger SHALL contain a Stakeholder element with the following fixed values:

- `stakeholder_id`: `SH001`

- `name`: `SysEngage`

- `role`: `AutomatedAnalysisAgent`

- `description`: `The SysEngage tool itself, acting as a stakeholder to provide deterministic or inferable answers during Gap closure. Answers attributed to SH001 SHOULD be reviewable by a human stakeholder before being treated as authoritative.`

### When the tool acts as stakeholder

The SysEngage tool MAY provide an `Answer` (with `provided_by = SH001`) when all of the following hold:

- The associated `Question` has a deterministic or narrowly-inferable answer derivable from the ledger content, structured domain knowledge, or standard engineering completeness rules.

- The answer does not involve subjective judgement, stakeholder preference, or business decisions reserved to human stakeholders.

- The Answer, if accepted, produces a Requirement or amendment that could equally have been proposed by a human stakeholder.

Example: A Requirement specifies an attribute with an enumerated value set containing only `open`. The tool recognises that `open` without a paired state is likely incomplete. It generates a Question ("Should the attribute also support a `closed` value?"), provides an Answer with `provided_by = SH001`proposing `{open, closed}`, and derives a corresponding Requirement amendment. The Gap that triggered this chain is then marked `Mitigated` or `Closed` depending on whether human review is pending.

### When the tool MUST NOT act as stakeholder

The SysEngage tool MUST NOT provide an Answer with `provided_by = SH001`when:

- The Question involves a value judgement, a business priority, or a trade-off that is not deterministically resolvable from the ledger content.

- The answer would commit the project to a specific course of action (e.g., accepting a Risk, deferring a Requirement, selecting between competing architectural approaches).

- Providing the answer would circumvent a Stakeholder approval step required by the governing process.

### Distinguishing tool answers from human answers

Consumers of the ledger MAY filter, flag, or require re-review of any Answer whose `provided_by == SH001`. The ledger makes no implicit distinction between tool-provided and human-provided Answers at the data level; the distinction is carried entirely by the `provided_by` field.

Tool-provided answers are first-class Answers with full provenance and traceability, and are not implicitly less trustworthy — but they are explicitly attributable.

## Attributes (with descriptions)

- `stakeholder_id: string` (REQUIRED, format `SH###`)

  Description: Stable identifier for the Stakeholder element.

  Notes: `SH001` is reserved for the SysEngage tool itself (see § SysEngage Tool Stakeholder).

- `name: string` (REQUIRED)

  Description: Human-readable name or label for this stakeholder. For individual human stakeholders, typically a personal name or a role title (e.g., "Alice Chen", "Lead Architect"). For organisational or automated stakeholders, a team or system name (e.g., "Safety Review Board",

  "SysEngage").

  Notes: null

- `role: string` (OPTIONAL)

  Description: The functional role this stakeholder plays in the project context. Free-form string; recommended controlled values include: Sponsor, Architect, Engineer, Reviewer, DomainExpert, RegulatoryAuthority, AutomatedAnalysisAgent, Other.

Notes: The role `AutomatedAnalysisAgent` is reserved for non-human stakeholders such as the SysEngage tool itself.

- `description: string` (OPTIONAL)

  Description: Optional free-text description of this stakeholder's responsibilities, interests, or context within the project.

  Notes: null

- `stakeholder_kind: string` (OPTIONAL; Human|Automated|Organisational)

  Description: Classification of whether this stakeholder is an individual person, an automated system, or an organisational body. Enables filtering of Answers by stakeholder type (e.g., "show me only human-approved Answers").

  Notes: SH001 MUST have `stakeholder_kind = "Automated"`. Other stakeholders default to `Human` if unspecified.

## Normative Rules

- `stakeholder_id` MUST be unique within the ledger.

- `stakeholder_id` MUST match regex `^SH\\d{3}$`.

- `name` MUST NOT be empty.

- If `role` is present, it MUST NOT be empty.

- If `description` is present, it MUST NOT be empty.

- If `stakeholder_kind` is present, it MUST be one of: Human, Automated,

  Organisational.

## SysEngage Tool Stakeholder Rules (NORMATIVE)

- Every ledger MUST contain exactly one Stakeholder element with `stakeholder_id = SH001`.

- The SH001 Stakeholder MUST have `name = "SysEngage"`.

- The SH001 Stakeholder MUST have `role = "AutomatedAnalysisAgent"`.

- If `stakeholder_kind` is present on the SH001 Stakeholder, it MUST equal `Automated`.

- No Stakeholder other than SH001 MAY have `role = "AutomatedAnalysisAgent"`unless explicitly declared to represent a separate automated agent with a stated function distinct from SysEngage itself.

- If a Stakeholder other than SH001 has `role = "AutomatedAnalysisAgent"`, its `description` MUST state the specific automated function it represents.---

# Element Type — StakeholderRegister

**Specialisation of:** `Register`  

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `Stakeholder` elements.

- Enable completeness validation and prevent orphaned elements of this type.

- Support deterministic projections/views by providing a stable grouping boundary.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE StakeholderRegister SHALL exist.

- `register_type` SHALL be `Stakeholder`.

- `member_ids` SHALL contain ALL `Stakeholder.stakeholder_id` values.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL Stakeholder elements present in the ledger.

---

# Element Type — Risk

## Purpose (NORMATIVE)

- Represent a potential adverse condition or uncertainty affecting objectives.

- Support mitigation, monitoring, and governance workflows.

## Non-Purpose (NORMATIVE) 

- Record gaps or deficiencies in the current design (use `Gap`).

- Record proposed corrective actions (use `Suggestion`). 

- Record open questions awaiting stakeholder input (use `Question`). 

- Record derived requirements that emerge from risk mitigation (use `Requirement`; the Risk element records the uncertainty itself, not the mitigation obligation).

## Attributes (with descriptions)

- `risk_id: string` (REQUIRED, format `K###`)

  Description: Stable identifier for the Risk element.

  Notes: null

- `title: string` (REQUIRED)

  Description: Short title/label.

  Notes: null

- `description: string` (REQUIRED)

  Description: Free-text classification label grouping related Risks (e.g. "Technical", "Schedule", "External Dependency", "Regulatory"). Not enumerated; each ledger instance may define its own category vocabulary.

  Notes: null

- `category: string` (OPTIONAL)

  Description: See element definition for semantic meaning of `category`.

  Notes: null

- `likelihood: string` (REQUIRED; High|Medium|Low)

  Description: Indicator of probability/likelihood.

  Notes: null

- `impact: string` (REQUIRED; High|Medium|Low)

  Description: Indicator of consequence/severity.

  Notes: null

- `exposure: string` (OPTIONAL; High|Medium|Low)

  Description: Composite indicator of overall risk exposure, typically derived from likelihood and impact. Provided as a separate field to allow custom scoring schemes rather than fixing a likelihood/impact multiplication rule.

  Notes: null

- `mitigation: string` (OPTIONAL)

  Description: Description of the mitigation action planned, in progress, or completed to reduce this Risk's exposure. For richer structured mitigation, link a Requirement via `related_element_ids`.

  Notes: null

- `owner: string` (OPTIONAL; references `Stakeholder.stakeholder_id`) 

Description: The Stakeholder accountable for monitoring and mitigating this Risk. Referenced by stakeholder_id (format SH###).

  Notes: null

- `status: string` (REQUIRED; Active|Mitigated|Accepted|Closed)

  Description: Lifecycle state of this Risk. 

Notes: 

- Active: Risk is identified and requires monitoring or mitigation. 

- Mitigated: Mitigation action has reduced exposure to an acceptable level. 

- Accepted: Risk is acknowledged but no mitigation will be taken (rationale should be recorded in `mitigation` or via a linked Question/Answer). 

- Closed: Risk condition is no longer relevant (e.g., the uncertainty has resolved, or the affected scope has been removed).

- `related_element_ids: string[]` (OPTIONAL; references any ledger element_id) 

Description: Optional references to other ledger elements impacted by, or relevant to, this Risk. Each entry is an element_id as defined in Appendix B.3. The type of the referenced element is inferred from its ID prefix. 

Notes: null

- `source_refs: string[]` (OPTIONAL; references `Source.source_id`)

  Description: Provenance anchors supporting this element via Source identifiers.

  Notes: null

- `domain_refs: string[]` (OPTIONAL; references `Domain.domain_id`)

  Description: Optional domain classification references relevant to this element.

  Notes: null

- `confidence: number` (REQUIRED, 0.0..1.0)

  Description: Confidence that this element’s content/classification is correct (0.0..1.0).

  Notes: null

## Normative Rules

- `risk_id` MUST be unique.

- `risk_id` MUST match regex `^K\\d{3}$`.

- `title` MUST NOT be empty.

- `description` MUST NOT be empty.

- `likelihood` MUST be one of: High, Medium, Low.

- `impact` MUST be one of: High, Medium, Low.

- If `exposure` is present, it MUST be one of: High, Medium, Low.

- `status` MUST be one of: Active, Mitigated, Accepted, Closed.

- If `related_element_ids` is present: 

- MUST contain at least one entry. 

- Each entry MUST be a non-empty string. 

- Each entry MUST reference an existing `element_id` within the same ledger. 

- Each entry MUST NOT reference this Risk's own `risk_id` (no self-reference). 

- If `source_refs` is present, each entry MUST reference an existing `Source.source_id`.

- If `domain_refs` is present, each entry MUST reference an existing `Domain.domain_id`.

- `confidence` MUST be within 0.0..1.0.

- If `owner` is present, it MUST match regex `^SH\\d{3}$` and MUST reference an existing `Stakeholder.stakeholder_id`.

---

# Element Type — RiskRegister

**Specialisation of:** `Register`

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `Risk` elements.

- Enable completeness validation and prevent orphaned Risk elements.

- Support deterministic projections/views by providing a stable grouping boundary

  across all Risks regardless of status.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

- Filter Risks by status. All Risk elements are members regardless of their status value. Status-based filtering is a projection concern, not a register concern.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). This section notes any Register-specific constraints or notes.

[any Register-specific attribute discussion here, or "No Register-specific attributes." if none]

## Normative Rules

- Exactly ONE RiskRegister SHALL exist.

- `register_type` SHALL be `Risk`.

- `member_ids` SHALL contain ALL `Risk.risk_id` values present in the ledger, regardless of their `status` value.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL Risk elements present

  > in the ledger, regardless of status.

- `confidence` MUST be within 0.0..1.0. 

---

# Element Type — Concern [NEW v2.12]

## Purpose (NORMATIVE)

- Represent a discrete, row-scoped ambiguity detected during Phase 3 row-lens classification that cannot be resolved into a Signal without Practitioner clarification.

- Provide an auditable record of content that was ambiguous from the current row's analytical lens — whether from original Sources (stream 1) or upstream Requirements (stream 2).

- Enable the Concern lifecycle (Open → Resolved / Dispositioned) to proceed through Phase 9 Question generation and Phase 10 Practitioner Answer.

- Support multi-source ambiguity (e.g., two Sources that contradict each other) via a `source_refs` list.

## Non-Purpose (NORMATIVE)

- Replace `Signal` as the primary classification output. Signal and Concern are mutually exclusive per classification act — a given Source or Requirement produces exactly one of the two.

- Hold forward-links to downstream artefacts. Signal, Question, and Risk carry back-references to the originating Concern (via `derived_from_concern_id`, `triggered_by_concern_id` respectively). Concern itself holds no forward pointers.

- Represent deficiencies in coverage or quality (use `Gap`).

- Persist across rows. Concerns are strictly row-scoped — Row N Concerns close with Row N; Row N+1 generates fresh Concerns from its own Phase 3 classification.

## Attributes (with descriptions)

- `concern_id: string` (REQUIRED, format `CN###`)

  Description: Stable identifier for this Concern element. Project-scoped unique.

  Notes: MUST match regex `^CN\d{3}$`.

- `source_refs: string[]` (REQUIRED, minItems 1)

  Description: References to the Source(s), Segment(s), SourceAtom(s), or Requirement(s) from which this Concern was raised. The type of each referenced element is derivable from its identifier prefix: `S###` = Source, `SEG###` = Segment, `SA###` = SourceAtom, `R###` = Requirement. Multiple entries are permitted to cover multi-source ambiguity and cross-source contradiction cases.

  Notes: Each entry MUST reference an existing element in the ledger. Any Requirement referenced MUST have `row_target` strictly less than this Concern's `produced_in_row` (upstream row constraint — a Concern at Row N is raised from Row N-1 Requirements, not same-row Requirements).

- `description: string` (REQUIRED)

  Description: Free-text description of the ambiguity that prevents this content from being classified as a Signal, stated from the producing row's analytical lens.

  Notes: MUST NOT be empty. MUST describe the specific ambiguity — not a generic statement. AI-generated descriptions are expected to vary between runs on identical input; structural conformance (not content equivalence) is the verification criterion.

- `state: string` (REQUIRED, enum)

  Description: Lifecycle state of this Concern. Enum: `Open` (raised, not yet resolved — blocks row close via Phase 9 Concern Resolution Check), `Resolved` (Practitioner Answer with outcome=Resolved; Signal produced; Signal.derived_from_concern_id back-references this Concern), `Dispositioned` (Practitioner Answer with outcome=NotApplicable or Indeterminate; Indeterminate triggers Risk generation with Risk.triggered_by_concern_id back-reference).

  Notes: Default at production time is `Open`. State transitions are Practitioner-driven via Phase 10 Answer. No automated state transitions.

- `produced_in_row: string` (REQUIRED, enum)

  Description: The Zachman row in which this Concern was raised. String enum matching row_target convention. Concerns are strictly row-scoped.

  Notes: MUST be one of `"1"`, `"2"`, `"3"`, `"4"`, `"5"`, `"6"`. Row 1 Concerns reference only stream 1 Sources (no upstream Requirements exist at Row 1).

- `practitioner_id: string` (REQUIRED)

  Description: Reference to the Practitioner under whose authority this Concern was produced.

  Notes: MUST NOT be empty. In v1 single-Practitioner deployments, this is a constant across all Concerns in the project.

- `dispositioned_with_outcome: string` (OPTIONAL, enum)

  Description: How the Concern was dispositioned when `state=Dispositioned`. Enum: `NotApplicable` (source content is out-of-scope for this row's analysis), `Indeterminate` (ambiguity is genuinely unresolvable with available information; auto-generates a Risk).

  Notes: MUST be present when `state=Dispositioned`. MUST be absent (null) when `state` is `Open` or `Resolved`.

- `disposition_rationale: string` (OPTIONAL)

  Description: Practitioner narrative explaining why the Concern was dispositioned with the recorded outcome.

  Notes: SHOULD be present when `state=Dispositioned`. MAY be absent for `NotApplicable` dispositions where the rationale is self-evident from the Concern description.

- `confidence: number` (REQUIRED, 0.0..1.0)

  Description: Confidence that this Concern has been correctly identified and described. Reflects the producing mechanism's certainty that the content is genuinely ambiguous from the row's analytical lens.

  Notes: AI-generated Concerns will typically carry values below 1.0. Deterministic Concerns (Practitioner-raised) may carry 1.0.

## Normative Rules

- `concern_id` MUST be unique within the ledger.

- `concern_id` MUST match regex `^CN\d{3}$`.

- `source_refs` MUST contain at least one entry.

- Each entry in `source_refs` MUST reference an existing `Source.source_id`, `Segment.segment_id`, `SourceAtom.atom_id`, or `Requirement.requirement_id` in the ledger.

- Any Requirement referenced in `source_refs` MUST have `row_target` strictly less than this Concern's `produced_in_row`.

- `description` MUST NOT be empty.

- `state` MUST be one of: `"Open"`, `"Resolved"`, `"Dispositioned"`.

- `produced_in_row` MUST be one of: `"1"`, `"2"`, `"3"`, `"4"`, `"5"`, `"6"`.

- `practitioner_id` MUST NOT be empty.

- `dispositioned_with_outcome` MUST be present when `state` = `"Dispositioned"`.

- `dispositioned_with_outcome` MUST be absent (null or omitted) when `state` ∈ {`"Open"`, `"Resolved"`}.

- `dispositioned_with_outcome` (when present) MUST be one of: `"NotApplicable"`, `"Indeterminate"`.

- `confidence` MUST be within 0.0..1.0.

- A Concern with `state=Resolved` MUST have exactly one Signal in the ledger where `Signal.derived_from_concern_id` = this `concern_id`.

- A Concern with `state=Resolved` MUST NOT have `dispositioned_with_outcome` populated.

- A Concern with `dispositioned_with_outcome=Indeterminate` MUST have exactly one Risk in the ledger where `Risk.triggered_by_concern_id` = this `concern_id`.

---

# Element Type — ConcernRegister [NEW v2.12]

**Specialisation of:** `Register`

## Purpose (NORMATIVE)

- Declare the authoritative membership set for `Concern` elements.

- Enable completeness validation and prevent orphaned Concern elements.

- Support Phase 9 Concern Resolution Check by providing a complete enumeration of all Concerns at the relevant row scope.

## Non-Purpose (NORMATIVE)

- Duplicate member element content.

- Contain inferred/implicit members not listed in member_ids.

- Filter Concerns by state. All Concern elements are members regardless of their state value. State-based filtering is a projection concern, not a register concern.

## Attributes (with descriptions)

See § Common Register Attributes for the shared attributes (`register_id`, `register_type`, `member_ids`, `completeness_rule`, `confidence`). No Register-specific attributes beyond those common attributes.

## Normative Rules

- Exactly ONE ConcernRegister SHALL exist when any Concern elements are present in the ledger.

- `register_type` SHALL be `"Concern"`.

- `member_ids` SHALL contain ALL `Concern.concern_id` values present in the ledger, regardless of their `state` value.

- Canonical completeness rule:

  > This register SHALL contain the identifiers of ALL Concern elements present

  > in the ledger, regardless of state.

- `confidence` MUST be within 0.0..1.0.

---


# JSON CanonicalLedger constraints (NORMATIVE)

The JSON CanonicalLedger instance MUST satisfy all of the following:

- The ledger instance MUST be a single JSON object conforming to the Ledger Instance JSON Schema (Appendix C).

- `sysengage_ledger_version` MUST equal the specification version of this ledger model (e.g., "2.12").

- `schema_id` MUST identify the exact schema version used to validate this ledger instance.

- `created_utc` MUST be present and MUST be an RFC 3339 / ISO 8601 date-time.

- `elements` MUST be present and MUST be a JSON array.

- Every entry in `elements` MUST conform to the `element_envelope` schema (Appendix C).

- Every `elements[*].element_id` MUST be globally unique within the ledger.

- Every `elements[*].element_type` MUST be one of the permitted element types defined in this specification.

- For every element, `elements[*].payload` MUST contain the primary identifier that matches `elements[*].element_id` (per Appendix B.3).

- A `SourceRegister` element MUST exist (exactly 1).

- If `Concern` elements are present, a `ConcernRegister` element MUST exist (exactly 1) and MUST list all Concern element identifiers. [NEW v2.12]

- If `Segment` elements are present, a `SegmentRegister` SHOULD exist and MUST be complete (lists all Segment).

- If `SourceAtom` elements are present, a `SourceAtomRegister` SHOULD exist and MUST be complete (lists all SourceAtom).

- A `DomainRegister` element MUST exist (exactly 1).

- A `ZachmanCellRegister` element MUST exist (exactly 1).

- A `RequirementRegister` element MUST exist (exactly 1).

- A `SignalRegister` element MUST exist (exactly 1).

- A `GapRegister` element MUST exist (exactly 1).

- Registers MUST list all element IDs of their governed element type in `member_ids` (completeness rule), unless the register definition explicitly allows partial membership.

- No `member_ids` entry may reference an element_id that does not exist in `elements`.

- Where an element has `source_refs`, each referenced Source ID MUST exist and MUST correspond to an element of type `Source`.

- Where an element has `domain_refs`, each referenced Domain ID MUST exist and MUST correspond to an element of type `Domain`.

- If `Question` elements are present, a `QuestionRegister` SHOULD exist and MUST be complete (lists all Questions).

- If `Answer` elements are present, an `AnswerRegister` SHOULD exist and MUST be complete (lists all Answers).

- The ledger MUST NOT include element types that are not permitted by this specification.

- If `Risk` elements are present, the `RiskRegister` MUST list all `Risk.risk_id` values as members, regardless of status..

# Appendices

## Purpose

This appendix hardens the ledger output by defining a **single canonical ledger instance file format** and the **rules** that MUST be followed to generate deterministic, parser-friendly outputs across multiple runs.

This appendix is intended to be pasted directly into the ledger specification.

# Appendix A

## A. Canonical output artefact (NORMATIVE)

### A.1 Required canonical file type

- A SysEngage ledger instance **MUST** be emitted as **JSON**.

- The canonical ledger file **MUST** use the extension: `*.ledger.json`

- Any Markdown outputs (if produced) **MUST** be treated as **projections/views** and **MUST NOT** be used as the canonical machine-readable ledger.

### A.2 JSON Schema version

- The canonical ledger instance **MUST** validate against the JSON Schema in section **B**.

- The JSON Schema herein conforms to **JSON Schema 2020-12**.

---

# Appendix B

## B. Output generation rules (NORMATIVE)

These rules MUST be followed by any generator (human or AI) producing a canonical ledger instance.

### B.1 Canonical file emission rules

1. Output MUST be **UTF-8** encoded.

2. Output MUST use **LF** newlines.

3. Output MUST be valid JSON (RFC 8259); trailing commas are forbidden.

4. Output MUST be a **single JSON object** that validates against the schema in section C.

### B.2 Canonicalization and determinism rules

To ensure two runs producing identical content yield identical diffs and hashes:

1. **No prose/view sections**  

   The canonical JSON MUST NOT contain Markdown headings, narrative “sections”, or view wrappers. Human views must be separate artefacts.

2. **Stable key naming**  

   All keys in `payload` MUST be **snake_case** and MUST match the attribute names defined for that element in the ledger spec.

3. **Deterministic ordering**

   - `elements[]` MUST be sorted deterministically:

     1) by `element_type` using the exact order listed in the schema enum; then  

     2) by `element_id` in lexicographic order.

   - `register_index[]` MUST be sorted by (`register_type`, `register_id`) lexicographically.

4. **Deterministic ordering inside payload**

   - For any `payload` arrays whose order is not semantically meaningful (e.g., `member_ids`, `linked_*_ids`), the generator MUST sort them lexicographically.

   - If an array’s order **is** semantically meaningful, the ledger spec MUST explicitly declare it as ordered; otherwise it SHALL be treated as unordered and sorted.

5. **Uniqueness constraints**

   - Every `element_id` MUST be globally unique across `elements[]`.

   - Every register referenced in `register_index[]` MUST correspond to exactly one element with `element_type` equal to that register’s type (e.g., `SourceRegister`) and matching `element_id`.

### B.3 Required ID mapping rules (bridging to existing per-element IDs)

Because the underlying ledger spec defines per-element identifiers (e.g., `source_id`, `segment_id`, etc.), the canonical JSON serialization SHALL follow these mapping rules:

1. `element_id` MUST equal the element’s primary identifier from its payload, using the following precedence:

   - If payload contains `<type>_id` (e.g., `source_id`, `segment_id`, `requirement_id`), then `element_id` MUST equal that value.

   - If the element is a register and contains `register_id`, then `element_id` MUST equal `register_id`.

2. The payload MUST still retain the original identifier field (e.g., `source_id`), unchanged.

This ensures parsers can rely on a single field (`element_id`) for cross-element references while preserving the ledger spec’s element-native IDs.

### B.4 Allowed fields and forward-compatibility rules

1. `payload` MAY include additional fields beyond those currently specified **ONLY IF** the ledger spec version explicitly permits extensions for that element type.

2. If extensions are permitted:

   - They MUST be namespaced using a stable prefix, e.g., `ext_*` or `x_*`.

3. If extensions are not permitted, generators MUST NOT emit extra keys.

### B.5 Content hashing rules

1. `content_hash.hash` MUST be computed over a canonicalized form of the ledger instance:

   - Remove `content_hash` from the object.

   - Ensure deterministic ordering (per B.2).

   - Serialize the resulting object using:

     - UTF-8

     - LF

     - 2-space indentation

     - No trailing whitespace

2. Apply SHA-256 to the resulting byte stream and hex-encode the digest.

### B.6 Strictness rules for multi-format outputs

1. A run MAY emit additional files (Markdown projections, CSV exports, etc.).

2. If additional files are emitted, the run MUST still emit the canonical JSON ledger, and all other files MUST be derivable from it.

3. If any non-JSON artefact contradicts the JSON ledger, the JSON ledger is authoritative.

---

# Appendix C

## C. Ledger instance JSON Schema (NORMATIVE)

{

   "$schema":"https://json-schema.org/draft/2020-12/schema",

   "$id":"sysengage.ledger.instance.v2_11.schema.json",

   "title":"SysEngage Ledger Instance (v2.12) — Canonical Serialization",

   "type":"object",

   "additionalProperties":false,

   "required":[

      "sysengage_ledger_version",

      "schema_id",

      "row_target",

      "run_id",

      "created_utc",

      "generator",

      "elements",

      "register_index",

      "content_hash"

   ],

   "properties":{

      "sysengage_ledger_version":{

         "type":"string",

         "const":"2.12",

         "description":"Ledger specification version that this instance claims conformance to."

      },

      "schema_id":{

         "type":"string",

         "const":"sysengage.ledger.instance.v2_11",

         "description":"Stable schema identifier for parser routing and validation selection."

      },

      "row_target":{

         "oneOf": [

         { "type": "string", "enum": ["1","2","3","4","5","6"] },

         { "type": "array", "items": { "type": "string", "enum": ["1","2","3","4","5","6"] }, "minItems": 1 }

         ]   

      },

      "run_id":{

         "type":"string",

         "minLength":1,

         "description":"Stable run identifier (deterministic if randomness controls are deterministic)."

      },

      "created_utc":{

         "type":"string",

         "format":"date-time",

         "description":"UTC timestamp when this canonical ledger instance was generated."

      },

      "generator":{

         "type":"object",

         "additionalProperties":false,

         "required":[

            "name",

            "version"

         ],

         "properties":{

            "name":{

               "type":"string",

               "minLength":1

            },

            "version":{

               "type":"string",

               "minLength":1

            },

            "build":{

               "type":"string"

            },

            "execution_model":{

               "type":"string",

               "description":"Operational specification / execution model identifier used for the run."

            }

         }

      },

      "elements":{

         "type":"array",

         "minItems":1,

         "description":"All ledger elements as a single deterministic list (canonical).",

         "items":{

            "$ref":"#/$defs/element_envelope"

         }

      },

      "register_index":{

         "type":"array",

         "minItems":1,

         "description":"Deterministic index of registers for fast parser lookup (type → register_id).",

         "items":{

            "type":"object",

            "additionalProperties":false,

            "required":[

               "register_type",

               "register_id"

            ],

            "properties":{

               "register_type":{

                  "$ref":"#/$defs/element_type"

               },

               "register_id":{

                  "type":"string",

                  "minLength":1,

                  "description":"The element_id of the register element within elements[]."

               }

            }

         }

      },

      "content_hash":{

         "$ref":"#/$defs/content_hash"

      },

      "warnings":{

         "type":"array",

         "description":"Optional non-fatal warnings emitted by the generator (not required for conformance).",

         "items":{

            "$ref":"#/$defs/message"

         }

      },

      "errors":{

         "type":"array",

         "description":"Optional fatal errors encountered (if present, the file is still valid JSON but the run is non-conformant).",

         "items":{

            "$ref":"#/$defs/message"

         }

      }

   },

   "$defs":{

      "message":{

         "type":"object",

         "additionalProperties":false,

         "required":[

            "code",

            "message"

         ],

         "properties":{

            "code":{

               "type":"string",

               "minLength":1

            },

            "message":{

               "type":"string",

               "minLength":1

            },

            "severity":{

               "type":"string",

               "enum":[

                  "info",

                  "warning",

                  "error"

               ]

            },

            "related_element_ids":{

               "type":"array",

               "items":{

                  "type":"string",

                  "minLength":1

               }

            }

         }

      },

      "content_hash":{

         "type":"object",

         "additionalProperties":false,

         "required":[

            "hash_alg",

            "hash"

         ],

         "properties":{

            "hash_alg":{

               "type":"string",

               "enum":[

                  "sha256"

               ],

               "description":"Hash algorithm used for deterministic ledger payload hashing."

            },

            "hash":{

               "type":"string",

               "pattern":"^[A-Fa-f0-9]{64}$",

               "description":"Hex-encoded hash over the canonicalized ledger payload (rules in section C)."

            }

         }

      },

      "element_type":{

         "type":"string",

         "enum":[

            "Source",

            "Register",

            "SourceRegister",

            "AnalysisPass",

            "Gap",

            "GapRegister",

            "ZachmanCell",

            "ZachmanCellRegister",

            "CellContentItem",

            "Domain",

            "DomainRegister",

            "Requirement",

            "RequirementRegister",

            "Question",

            "QuestionRegister",

            "Answer",

            "AnswerRegister",

            "Suggestion",

            "SuggestionRegister",

            "CoverageItem",

            "CoverageRegister",

            "Segment",

            "SegmentRegister",

            "SourceAtom",

            "SourceAtomRegister",

            "Signal",

            "SignalRegister",

            "Risk",

            "RiskRegister",

"Stakeholder",

            "StakeholderRegister",

            "Concern",

            "ConcernRegister"

         ],

         "description":"Permitted element types (ledger spec v2.12)."

      },

      "id_S":{

         "type":"string",

         "pattern":"^S\\d{3}$"

       },

      "id_SEG":{

         "type":"string",

         "pattern":"^SEG\\d{3}$"

       },

      "id_SA":{

         "type":"string",

         "pattern":"^SA\\d{3}$"

       },

       "id_ZC":{

          "type":"string",

          "pattern": "^ZC-R[1-6]-C-(What|How|Where|Who|When|Why)$"

       },

       "id_CI":{

          "type":"string",

          "pattern": "^CCI-ROW[1-6]-C-(What|How|Where|Who|When|Why)-\\d{3}$"

       },

       "id_R":{

          "type":"string",

          "pattern":"^R\\d{3}$"

       },

       "id_P":{

          "type":"string",

          "pattern":"^P\\d{3}$"

       },

       "id_G":{

          "type":"string",

          "pattern":"^G\\d{3}$"

       },

       "id_D":{

          "type":"string",

          "pattern":"^D\\d{3}$"

       },

       "id_SG":{

          "type":"string",

          "pattern":"^SG\\d{3}$"

       },

       "id_Q":{

          "type":"string",

          "pattern":"^Q\\d{3}$"

       },

       "id_A":{

          "type":"string",

          "pattern":"^A\\d{3}$"

       },

       "id_SUG":{

          "type":"string",

          "pattern":"^SUG\\d{3}$"

       },

       "id_CV":{

          "type":"string",

          "pattern":"^CV\\d{3}$"

       },

       "id_K": { 

          "type": "string", 

          "pattern": "^K\\d{3}$" 

       },

       "id_SH": {

 "type": "string", 

"pattern": "^SH\\d{3}$" 

          },

       "id_CN": {

          "type": "string",

          "pattern": "^CN\\d{3}$"

       },

         "GenericRegisterPayload":{

            "type":"object",

            "additionalProperties":false,

            "required":[

               "register_id",

               "register_type",

               "member_ids",

               "completeness_rule",

               "confidence"

            ],

            "properties":{

               "register_id":{

                  "type":"string",

                  "minLength":1

               },

               "register_type":{

                  "$ref":"#/$defs/element_type"

               },

               "member_ids":{

                  "type":"array",

                  "items":{

                     "type":"string",

                     "minLength":1

                  }

               },

               "completeness_rule":{

                  "type":"string",

                  "minLength":1

               },

               "confidence":{

                  "$ref":"#/$defs/confidence"

               }

            },

            "description":"Generic register payload for element_type == 'Register'. Prefer specialised register types where available."

         },

"StakeholderPayload": {

"type": "object",

"additionalProperties": false,

"required": ["stakeholder_id", "name"],

"properties": {

"stakeholder_id": {"$ref": "#/$defs/id_SH"},

"name": {"type": "string", "minLength": 1},

"role":{"type": "string", "minLength": 1},

"description":{"type": "string", "minLength": 1},

"stakeholder_kind": {"type": "string", "enum": ["Human", "Automated", "Organisational"]}

  }

},

"StakeholderRegisterPayload": {

  "allOf": [

    { "$ref": "#/$defs/RegisterPayload" },

    {

      "type": "object",

      "properties": {

        "register_type": { "const": "Stakeholder" },

        "member_ids": {

          "type": "array",

          "items": { "$ref": "#/$defs/id_SH" },

          "uniqueItems": true

        }

      }

    }

  ]

}

"QuestionPayload":{

"type":"object",

"additionalProperties":false,

 "required":[

"question_id",

"question_text",

"why_it_matters",

"priority",

"related_gap_ids",

"confidence"],

"properties":{

"question_id":{"$ref":"#/$defs/id_Q"},

"question_text":{"type":"string", "minLength":1},

"expected_answer_format":{"type":"string", "minLength":1},

"why_it_matters":{"type":"string", "minLength":1},

"priority":{"type":"string", "enum":[

"High",

"Medium",

"Low"]},

"status":{"type":"string", "enum":[

"Open",

"Answered",

"Closed"]},

"related_gap_ids":{"type":"array", "items":{"$ref":"#/$defs/id_G"}},

"confidence":{"$ref":"#/$defs/confidence"}}

},

"QuestionRegisterPayload":{

"allOf":[{"$ref":"#/$defs/RegisterPayload"},

{

"type":"object",

"properties":{

"register_type":{"const":"Question"},

"member_ids":{"type":"array", "items":{"$ref":"#/$defs/id_Q"}}}

}

]

 },

"AnswerPayload":{

"type":"object",

"additionalProperties":false,

"required":[

"answer_id",

"question_id",

"response_text",

"provided_by",

"confidence"],

"properties":{

"answer_id":{"$ref":"#/$defs/id_A"},

"question_id":{"$ref":"#/$defs/id_Q"},

"response_text":{"type":"string", "minLength":1},

"provided_by":{"$ref":"#/$defs/id_SH"},

"provided_utc":{"type":"string", "format":"date-time", "minLength":1},

"confidence":{"$ref":"#/$defs/confidence"}}

},

"AnswerRegisterPayload":{

"allOf":[{"$ref":"#/$defs/RegisterPayload"},

{

"type":"object",

"properties":{

"register_type":{"const":"Answer"},

"member_ids":{"type":"array", "items":{"$ref":"#/$defs/id_A"}}}

}

]

},

"SuggestionPayload":{

"type":"object",

"additionalProperties":false,

 "required":[

"suggestion_id",

"type",

"description",

"priority",

		"target_element_ids",

"produced_from_gap_ids",

 "confidence"],

"properties":{

"suggestion_id":{"$ref":"#/$defs/id_SUG"},

"type":{"type":"string", "enum":[

"ImproveCoverage",

"RefineRequirement",

"AddDomain",

"Process"]},

"description":{"type":"string", "minLength":1},

"priority":{"type":"string", "enum":[

"High",

"Medium",

"Low"]},

"target_element_ids": { 

"type": "array", 

"minItems": 1, 

"items": { "type": "string", "minLength": 1, 

"description": "References an element_id. Must resolve to an existing element in the same ledger; validated at ledger-level, not schema-level." },

"uniqueItems": true

 } 

"rationale":{"type":"string", "minLength":1},

"produced_from_gap_ids":{"type":"array", "items":{"$ref":"#/$defs/id_G"}},

"confidence":{"$ref":"#/$defs/confidence"}}

},

"SuggestionRegisterPayload":{

"allOf":[{"$ref":"#/$defs/RegisterPayload"},

{

"type":"object",

"properties":{

"register_type":{"const":"Suggestion"},

"member_ids":{"type":"array", "items":{"$ref":"#/$defs/id_SUG"}}

}

               }

            ]

         },

"CoverageItemPayload":{

"type":"object",

"additionalProperties":false,

 "required":[

"coverage_id",

"coverage_type",

"target_ref",

"coverage_state",

"confidence"],

"properties":{

"coverage_id":{"$ref":"#/$defs/id_CV"},

"coverage_type":{"type":"string", "enum":[

"DomainCoverage",

"CellCoverage",

"RequirementCoverage"]},

"target_ref":{"type": "string", "oneOf": [ 

{ "$ref": "#/$defs/id_D" }, 

 { "$ref": "#/$defs/id_R" }, 

 { "$ref": "#/$defs/id_CI" }]},

"coverage_state":{"type":"string", "enum":[

"Covered",

"PartiallyCovered",

"NotCovered",

"Unknown"]},

"produced_by_pass_id":{"$ref":"#/$defs/id_P"},

"confidence":{"$ref":"#/$defs/confidence"}

            }

         },

"CoverageRegisterPayload":{

"allOf":[{"$ref":"#/$defs/RegisterPayload"},

{

"type":"object",

"properties":{

"register_type":{"const":"CoverageItem"},

"member_ids":{"type":"array", "items":{"$ref":"#/$defs/id_CV"}}

                  }

               }

            ]

         },

         "confidence":{

            "type":"number",

            "minimum":0.0,

            "maximum":1.0

         },

         "ref_SourceIds":{

            "type":"array",

            "minItems":1,

            "items":{

               "$ref":"#/$defs/id_S"

            }

         },

         "ref_DomainIds":{

            "type":"array",

            "minItems":1,

            "items":{

               "$ref":"#/$defs/id_D"

            }

         },

         "RegisterPayload":{

            "type":"object",

            "additionalProperties":false,

            "required":[

               "register_id",

               "register_type",

               "member_ids",

               "completeness_rule",

               "confidence"

            ],

            "properties":{

               "register_id":{

                  "type":"string",

                  "minLength":1

               },

               "register_type":{

                  "type":"string",

                  "minLength":1

               },

               "member_ids":{

                  "type":"array",

                  "items":{

                     "type":"string",

                     "minLength":1

                  }

               },

               "completeness_rule":{

                  "type":"string",

                  "minLength":1

               },

               "confidence":{

                  "$ref":"#/$defs/confidence"

               }

            }

         },

         "SourcePayload":{

            "type":"object",

            "additionalProperties":false,

            "required":[

               "source_id",

               "source_text",

               "segmentation_context",

	"input_material_ref",

"confidence"

            ],

            "properties":{

"source_id":{"$ref":"#/$defs/id_S"},

"source_text":{"type":"string", "minLength":1},

"segmentation_context":{"type":"string", "minLength":1},

"input_material_ref":{"type":"string", "minLength":1},

"parent_source_ref":{"$ref":"#/$defs/id_S"},

"confidence":{"$ref":"#/$defs/confidence"}

            }

         },

         "SourceRegisterPayload":{

            "allOf":[

               {

                  "$ref":"#/$defs/RegisterPayload"

               },

               {

"type":"object",

"properties":{

"register_type":{"const":"Source"},

"member_ids":{"type":"array", "items":{"$ref":"#/$defs/id_S"}

                     }

                  }

               }

            ]

         },

         "SegmentPayload":{

            "type":"object",

            "additionalProperties":false,

            "required":[

               "segment_id",

               "title",

               "source_refs",

               "confidence"

            ],

            "properties":{

               "segment_id":{

                  "$ref":"#/$defs/id_SEG"

               },

               "title":{

                  "type":"string",

                  "minLength":1

               },

               "description":{

                  "type":"string",

                  "minLength":1

               },

               "source_refs":{

                  "$ref":"#/$defs/ref_SourceIds"

               },

               "parent_segment_ref":{

                  "$ref":"#/$defs/id_SEG"

               },

               "confidence":{

                  "$ref":"#/$defs/confidence"

               }

            }

         },

         "SegmentRegisterPayload":{

            "allOf":[

               {

                  "$ref":"#/$defs/RegisterPayload"

               },

               {

                  "type":"object",

                  "properties":{

                     "register_type":{

                        "const":"Segment"

                     },

                     "member_ids":{

                        "type":"array",

                        "items":{

                           "$ref":"#/$defs/id_SEG"

                        }

                     }

                  }

               }

            ]

         },

         "SourceAtomPayload":{

            "type":"object",

            "additionalProperties":false,

            "required":[

               "atom_id",

               "atom_text",

               "source_ref",

               "confidence"

            ],

            "properties":{

               "atom_id":{

                  "$ref":"#/$defs/id_SA"

               },

               "atom_text":{

                  "type":"string",

                  "minLength":1

               },

               "source_ref":{

                  "$ref":"#/$defs/id_S"

               },

               "segment_ref":{

                  "$ref":"#/$defs/id_SEG"

               },

               "parent_atom_ref":{

                  "$ref":"#/$defs/id_SA"

               },

               "confidence":{

                  "$ref":"#/$defs/confidence"

               }

            }

         },

         "SourceAtomRegisterPayload":{

            "allOf":[

               {

                  "$ref":"#/$defs/RegisterPayload"

               },

               {

                  "type":"object",

                  "properties":{

                     "register_type":{

                        "const":"SourceAtom"

                     },

                     "member_ids":{

                        "type":"array",

                        "items":{

                           "$ref":"#/$defs/id_SA"

                        }

                     }

                  }

               }

            ]

         },

         "ZachmanCellPayload":{

            "type":"object",

            "additionalProperties":false,

            "required":[

               "cell_id",

               "row_target",

               "column"],

            "properties":{

               "cell_id":{

                  "$ref":"#/$defs/id_ZC"

               },

               "row_target":{

                  "type": "string",

                  "enum": ["1", "2", "3", "4", "5", "6"]

               },

               "column":{

                  "type":"string",

                  "enum": ["What", "How", "Where", "Who", "When", "Why"]

               }

            }

         },

         "ZachmanCellRegisterPayload":{

            "allOf":[

               {

                  "$ref":"#/$defs/RegisterPayload"

               },

               {

                  "type":"object",

                  "properties":{

                     "register_type":{

                        "const":"ZachmanCell"

                     }

                  }

               }

            ]

         },

"CellContentItemPayload":{

"type":"object",

"additionalProperties":false,

"required":[

"ci_id",

"cell_id",

 "signal_refs",

"classification_type",

"description",

"confidence"],

"properties":{

"ci_id":{"$ref":"#/$defs/id_CI"},

"cell_id":{"$ref":"#/$defs/id_ZC"},

"signal_refs":{ "type":"array","items":{"$ref":"#/$defs/id_SG"}},

"classification_type":{"type":"string", "minLength":1},

"description":{"type":"string", "minLength":1},

"trigger_condition":{"type":"string", "minLength":1},

"justification":{"type":"string", "minLength":1},

"confidence":{"$ref":"#/$defs/confidence"}

}

},

"DomainPayload": {

"type": "object",

"additionalProperties": true,

"required": [

"domain_id",

"name",

"description",

"row_target",

"cell_content_item_refs"],

"properties": {

"domain_id": {"$ref": "#/$defs/id_D" },

"name": {"type": "string", "minLength":1},

"description": {"type": "string", "minLength":1},

"classification_type": {"type": "string", "minLength":1},

"row_target": {"type": "string", "enum": ["1","2","3","4","5","6"]},

"cell_content_item_refs":{"type":"array", "items":{"$ref":"#/$defs/id_CI"}

}

},

         "DomainRegisterPayload":{

            "allOf":[

               {

                  "$ref":"#/$defs/RegisterPayload"

               },

               {

                  "type":"object",

                  "properties":{

                     "register_type":{

                        "const":"Domain"

                     },

                     "member_ids":{

                        "type":"array",

                        "items":{

                           "$ref":"#/$defs/id_D"

                        }

                     }

                  }

               }

            ]

         },

"RequirementPayload":{

"type":"object",

"additionalProperties":false,

 "required":[

"requirement_id",

"statement",

"requirement_type",

"row_target",

"domain_refs",

"cci_refs",

"confidence"],

"properties":{

"requirement_id":{"$ref":"#/$defs/id_R"},

"statement":{"type":"string", "minLength":1},

"requirement_type":{"type":"string","enum":[

"Functional",

"Non-Functional",

"Constraint",

"Performance",

"Suitability"]},

"row_target": { "type": "string", "enum": ["1", "2", "3", "4", "5", "6"]},

"rationale":{"type":"string", "minLength":1},

"cci_refs":{"type":"array", "items":{"$ref":"#/$defs/id_CI"}},

"answer_refs":{"type":"array", "items":{"$ref":"#/$defs/id_A"}},

"domain_refs":{"$ref":"#/$defs/ref_DomainIds"},

"fit_criteria":{"type":"string", "minLength":1},

"verification_method":{"type":"string", "enum":[

"Test",

"Analysis",

"Inspection",

"Demonstration"]},

"priority":{"type":"string", "enum":[

"High",

"Medium",

"Low"]},

"confidence":{"$ref":"#/$defs/confidence"}

}

},

"RequirementRegisterPayload":{

            "allOf":[

               {

                  "$ref":"#/$defs/RegisterPayload"

               },

               {

                  "type":"object",

                  "properties":{

                     "register_type":{

                        "const":"Requirement"

                     },

                     "member_ids":{

                        "type":"array",

                        "items":{

                           "$ref":"#/$defs/id_R"

                        }

                     }

                  }

               }

            ]

         },

"AnalysisPassPayload":{

"type":"object",

"additionalProperties":false,

 "required":[

"pass_id",

"pass_type",

"mechanism",

"execution_status",

"mode_active",

"declared_transformation_modes",

"outputs",

"evaluated_scope",

"pass_started_at",

"confidence"],

"properties":{

"pass_id":{"$ref":"#/$defs/id_P"},

"pass_type":{"type":"string", "minLength":1},

"mechanism":{"type":"string", "minLength":1},

"execution_status":{"type":"string", "enum":["Success", "Failed", "PartialSuccess"]},

"mode_active":{"type":"string", "minLength":1},

"declared_transformation_modes":{"type":"array", "minItems":1, "items":{"type":"string", "minLength":1}},

"outputs":{"type":"object"},

"evaluated_scope":{"type":"string", "minLength":1},

"pass_started_at":{"type":"string", "format":"date-time"},

"pass_completed_at":{"type":"string", "format":"date-time"},

"elapsed_ms":{"type":"integer", "minimum":0},

"confidence":{"$ref":"#/$defs/confidence"}

            }

         },

"GapPayload":{

"type":"object",

"additionalProperties":false,

 "required":[

"gap_id",

"description",

"impact",

"coverage_item",

"proposed_resolution",

"resolution_state",

"confidence"],

"properties":{

"gap_id":{"$ref":"#/$defs/id_G"},

"description":{"type":"string", "minLength":1},

"impact": { "type": "string", "enum": ["High", "Medium", "Low"] },

"coverage_item": {

  "type": "array",

  "minItems": 1,

  "uniqueItems": true,

  "items": { "$ref": "#/$defs/id_CV" }},

"proposed_resolution":{"type":"string", "minLength":1},

"resolution_state":{"type":"string", "enum":[

"Open",

"Accepted",

"Mitigated",

"Closed"]},

"confidence": { "$ref": "#/$defs/confidence" }	

            }

         },

"GapRegisterPayload":{

"allOf":[{"$ref":"#/$defs/RegisterPayload"},

{

"type":"object",

"properties":{

"register_type":{"const":"Gap"}}

               }

            ]

         },

"SignalPayload":{

"type":"object",

"additionalProperties":false,

 "required":[

"signal_id",

"signal_type",

 "row_target",

"description",

"source_refs",

"confidence"],

"properties":{

"signal_id":{"$ref":"#/$defs/id_SG"},

"signal_type":{"type":"string", "enum": ["Normative", "Intent", "Actor", "Concern", "Ambiguity", "Quality"]},

"row_target":{"type": "string", "enum": ["1", "2", "3", "4", "5", "6"]},

"description":{"type":"string", "minLength":1},

"source_refs":{"type": "array", "minItems": 1,

"uniqueItems": true,

"items":{"oneOf": [

{"$ref": "#/$defs/id_S" },

{"$ref": "#/$defs/id_R" }]}},

"sourceatom_refs":{"type":"array", "items":{"$ref":"#/$defs/id_SA"}},

"derived_from_concern_id":{"type":"string", "pattern":"^CN\\d{3}$"},

"confidence":{"$ref":"#/$defs/confidence"}

}

},

"SignalRegisterPayload":{

"allOf":[

{"$ref":"#/$defs/RegisterPayload"},

{"type":"object", "properties":{"register_type":{"const":"Signal"}}}

]

},

 "RiskPayload": {

  	"type": "object",

 	 "additionalProperties": false,

 	"required": [

    		"risk_id",

   		"title",

    		"description",

    		"likelihood",

    		"impact",

    		"status",

    		"confidence"],

  	"properties": {

    		"risk_id":{ "$ref": "#/$defs/id_K" },

    		"title":{ "type": "string", "minLength": 1 },

   		"description": { "type": "string", "minLength": 1 },

    		"category": { "type": "string", "minLength": 1 },

    		"likelihood": { "type": "string", "enum": ["High", "Medium", "Low"] },

    		"impact": { "type": "string", "enum": ["High", "Medium", "Low"] },

    		"exposure": { "type": "string", "enum": ["High", "Medium", "Low"] },

    		"mitigation": { "type": "string", "minLength": 1 },

    		"owner": { "$ref": "#/$defs/id_SH" },

    		"status": { "type": "string", "enum": ["Active", "Mitigated", "Accepted", "Closed"]},

    		"related_element_ids": {

      			"type": "array",

     			"minItems": 1,

      			"items": {

       				"type": "string",

        				"minLength": 1,

    "description": "An element_id referencing any element in the same ledger."},

      			"uniqueItems": true},

    		"source_refs": { "type": "array", "items": { "$ref": "#/$defs/id_S" }, "minItems": 1, "uniqueItems": true },

    		"domain_refs": { "type": "array", "items": { "$ref": "#/$defs/id_D" }, "minItems": 1, "uniqueItems": true },

    		"confidence":  { "$ref": "#/$defs/confidence" }

 		 }

},

 "RiskRegisterPayload": {

"allOf": [{ "$ref": "#/$defs/RegisterPayload" },

{

"type": "object",

"properties": {

"register_type": { "const": "Risk" },

"member_ids": {

"type": "array",

"items": { "$ref": "#/$defs/id_K" },

"uniqueItems": true}}

}

]

},

"ConcernPayload": {

"type": "object",

"additionalProperties": false,

"required": [

"concern_id",

"source_refs",

"description",

"state",

"produced_in_row",

"practitioner_id",

"confidence"],

"properties": {

"concern_id": { "type": "string", "pattern": "^CN\\d{3}$" },

"source_refs": {

"type": "array",

"minItems": 1,

"uniqueItems": true,

"items": {

"oneOf": [

{ "$ref": "#/$defs/id_S" },

{ "$ref": "#/$defs/id_SEG" },

{ "$ref": "#/$defs/id_SA" },

{ "$ref": "#/$defs/id_R" }

]}},

"description": { "type": "string", "minLength": 1 },

"state": { "type": "string", "enum": ["Open", "Resolved", "Dispositioned"] },

"produced_in_row": { "type": "string", "enum": ["1", "2", "3", "4", "5", "6"] },

"practitioner_id": { "type": "string", "minLength": 1 },

"dispositioned_with_outcome": { "type": "string", "enum": ["NotApplicable", "Indeterminate"] },

"disposition_rationale": { "type": "string" },

"confidence": { "$ref": "#/$defs/confidence" }

}

},

"ConcernRegisterPayload": {

"allOf": [{ "$ref": "#/$defs/RegisterPayload" },

{

"type": "object",

"properties": {

"register_type": { "const": "Concern" },

"member_ids": {

"type": "array",

"items": { "type": "string", "pattern": "^CN\\d{3}$" },

"uniqueItems": true }}

}

]

},


"UnspecifiedPayload":{

            "type":"object",

            "description":"Temporary fallback until full per-element payload schemas are added. Remove once complete coverage is achieved.",

            "additionalProperties":true

         },

         "element_envelope":{

            "type":"object",

            "additionalProperties":false,

            "required":[

               "element_type",

               "element_id",

               "payload"

            ],

            "properties":{

               "element_type":{

                  "$ref":"#/$defs/element_type"

               },

               "element_id":{

                  "type":"string",

                  "minLength":1

               },

               "payload":{

                  "type":"object"

               }

            },

            "allOf":[

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"Source"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/SourcePayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_S"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"SourceRegister"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/SourceRegisterPayload"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"Segment"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/SegmentPayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_SEG"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"SegmentRegister"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/SegmentRegisterPayload"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"SourceAtom"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/SourceAtomPayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_SA"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"SourceAtomRegister"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/SourceAtomRegisterPayload"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"ZachmanCell"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/ZachmanCellPayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_ZC"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"ZachmanCellRegister"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/ZachmanCellRegisterPayload"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"CellContentItem"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/CellContentItemPayload"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"Domain"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/DomainPayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_D"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"DomainRegister"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/DomainRegisterPayload"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"Requirement"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/RequirementPayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_R"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"RequirementRegister"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/RequirementRegisterPayload"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"AnalysisPass"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/AnalysisPassPayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_P"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"Gap"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/GapPayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_G"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"GapRegister"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/GapRegisterPayload"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"Signal"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/SignalPayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_SG"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"SignalRegister"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/SignalRegisterPayload"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"Question"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/QuestionPayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_Q"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"QuestionRegister"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/QuestionRegisterPayload"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"Answer"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/AnswerPayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_A"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"AnswerRegister"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/AnswerRegisterPayload"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"Suggestion"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/SuggestionPayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_SUG"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"SuggestionRegister"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/SuggestionRegisterPayload"

                        }

                     }

                  }

              },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"CoverageItem"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/CoverageItemPayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_CV"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"CoverageRegister"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/CoverageRegisterPayload"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"Stakeholder"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/StakeholderPayload"

                        },

                        "element_id":{

                           "$ref":"#/$defs/id_SH"

                        }

                     }

                  }

               },

               {

                  "if":{

                     "properties":{

                        "element_type":{

                           "const":"StakeholderRegister"

                        }

                     },

                     "required":[

                        "element_type"

                     ]

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/StakeholderRegisterPayload"

                        }

                     }

                  }

               },

{

"if":{

"properties":{"element_type":{"const":"Risk"}},

"required":["element_type"]},

"then":{

"properties":{

"payload":{"$ref":"#/$defs/RiskPayload"},

"element_id":{"$ref":"#/$defs/id_K"}}

}

               },

{

  "if": {

    "properties": { "element_type": { "const": "RiskRegister" } },

    "required": ["element_type"]

  },

  "then": {

    "properties": {

      "payload": { "$ref": "#/$defs/RiskRegisterPayload" }

    }

  }

},              

{

                  "if":{

                     "properties":{"element_type":{"const":"Concern"}},

                     "required":["element_type"]

                  },

                  "then":{

                     "properties":{

                        "payload":{"$ref":"#/$defs/ConcernPayload"},

                        "element_id":{"type":"string","pattern":"^CN\\d{3}$"}

                     }

                  }

},

{

                  "if":{

                     "properties":{"element_type":{"const":"ConcernRegister"}},

                     "required":["element_type"]

                  },

                  "then":{

                     "properties":{

                        "payload":{"$ref":"#/$defs/ConcernRegisterPayload"}

                     }

                  }

},

{

                  "if":{

                     "properties":{"element_type":{"const":"Register"}},

                     "required":["element_type"]

                  },

                  "then":{

                     "properties":{

                        "payload":{"$ref":"#/$defs/GenericRegisterPayload"}

                     }

                  }


               },

               {

                  "if":{

                     "not":{

                        "properties":{

                           "element_type":{

                              "enum":[

                                 "Source",

                                 "SourceRegister",

                                 "Segment",

                                 "SegmentRegister",

                                 "SourceAtom",

                                 "SourceAtomRegister",

                                 "ZachmanCell",

                                 "ZachmanCellRegister",

                                 "CellContentItem",

                                 "Domain",

                                 "DomainRegister",

                                 "Requirement",

                                 "RequirementRegister",

                                 "AnalysisPass",

                                 "Gap",

                                 "GapRegister",

                                 "Signal",

                                 "SignalRegister",

                                 "Question",

                                 "QuestionRegister",

                                 "Answer",

                                 "AnswerRegister",

                                 "Suggestion",

                                 "SuggestionRegister",

                                 "CoverageItem",

                                 "CoverageRegister",

"Stakeholder",

                                 "StakeholderRegister",

"Risk", 

"RiskRegister",

"Concern",

"ConcernRegister"

                              ]

                           }

                        },

                        "required":["element_type"]

                     }

                  },

                  "then":{

                     "properties":{

                        "payload":{

                           "$ref":"#/$defs/UnspecifiedPayload"

                          }

                       }

                    }

               }

            ]

         }

   }

}

``

# Appendix D — Version Migration Notes [NEW v2.12]

## v2.11 → v2.12 Migration

**Additive changes only. No existing element types or attributes have been removed or renamed.**

New element types: `Concern` (CNNNN), `ConcernRegister`. Absent in pre-v2.12 ledger instances — tools reading v2.11 instances treat absence as "Concern mechanism was not yet in use" rather than as an error.

New attribute on `Signal`: `derived_from_concern_id` (optional). Absent in pre-v2.12 Signal elements — treat as null (Signal was not produced via Concern resolution).

New conventional sub-key on `AnalysisPass.outputs`: `row_lens_data`. Absent in pre-v2.12 AnalysisPass records for `RowLensSourceReanalysis` mechanism — treat as mechanism not yet executed or legacy pass record.

**RSSF not added:** RowScopedSourceFindings (RSSF-NNN) is NOT defined in this specification. It was proposed in Row 2 Understanding v1.1 but retired in v1.2 per F35 architectural resolution. Ledger instances that contain RSSF-prefixed elements from prototype work should treat them as unrecognised legacy elements.

**Concern identifier prefix:** CNNNN (not CON-NNN). Ledger instances from Row 2 Understanding v1.1 prototype work that use CON-NNN identifiers should be treated as legacy — remap CON-NNN → CNNNN for v2.12 conformance. The schema does not validate legacy instances.
