# Replit Agent Task — Source Capture Re-Implementation (Updated)

## Why this task is a re-issue

This task supersedes the previous re-implementation task instruction. Your Plan Mode review caught two errors in the previous specs:

- Q3 (AnalysisPass) — previous spec listed operational attributes as if non-canonical, when the canonical spec was simply underdeveloped and didn't reflect F4 / F10 architectural commitments
- Q4 (SourceAtom) — previous spec listed only 3 canonical attributes; canonical schema already had 6 (segment_ref, parent_atom_ref, confidence were missing from the spec, not from canonical)

Both errors were resolved at the spec layer per Path A discipline (canonical-first, then mechanism specs, then implementation):

1. **Canonical ledger spec v2.10 → v2.11** — amended canonical AnalysisPass to canonicalise mechanism / execution_status / mode_active / declared_transformation_modes / outputs / pass_started_at / pass_completed_at / elapsed_ms per F4 / F10 architectural commitments. Strict JSON Schema validation now permits the operational attributes that the implementation needs.

2. **Row 4 Mechanism Source Capture v0.3 → v0.4** — §5.1 Pydantic model attribute lists corrected for AnalysisPass and SourceAtom; §5.6 non-canonical stripping lists corrected; §8 verification postconditions updated; §11 build notes record F25 + F26 resolutions.

3. **Row 3 Mechanism Source Capture v0.2 → v0.3** — version reference bumps; §7.1.4 Read Witness narrative updated to reflect that AnalysisPass.outputs is now canonically locked; §11 build notes record F10 / F25 / F26 status.

You can now proceed without the workarounds Q3 was asking about. Operational AnalysisPass attributes (mechanism, execution_status, mode_active, etc.) are CANONICAL per v2.11 — keep them at export. SourceAtom canonical attributes are 6 (atom_id, atom_text, source_ref, segment_ref OPTIONAL, parent_atom_ref OPTIONAL, confidence REQUIRED) — keep all of them at export.

## Document list to uploaded to attached_assets

I have attached the following three documents. They supersede whatever you previously had:

1. **SysEngage_Row_3_Mechanism_Source_Capture_v0_3.docx** (Row 3 mechanism spec — supersedes v0.2)
2. **SysEngage_Row_4_Mechanism_Source_Capture_v0_4.docx** (Row 4 mechanism spec — supersedes v0.3)
3. **sysengage_minimal_ledger_spec_v2_11.md** (canonical ledger spec — UTF-8 markdown; .md extension this time; supersedes v2.10)

If you had the previous v0.2 / v0.3 / v2.10 documents in context, please discard them and work from the new set.

## The four implementation changes (consolidated and definitive)

### Change 1 — Pass 0A becomes Source Capture (was Segment Construction)

Per Row 3 v0.3 §4.2 and Row 4 v0.4 §4.2:

**Pass 0A behaviour**: identifies substantive input units at canonical Source granularity per v2.11 § Element Type — Source — sentence-level statement, single bullet statement, single table-row assertion, definition / constraint line. For prose input, **one Source per sentence**.

Boundary detection rules for prose: sentence-end punctuation (. ! ?) followed by whitespace. Handle known false-positives: abbreviations (Mr., Dr., Inc., e.g., i.e., etc.), decimal points within numbers, URLs.

Byte preservation discipline: leading whitespace where it belongs to the unit is preserved on the subsequent Source. Concatenating all Sources in capture order reproduces the input byte stream.

### Change 2 — Pass 0B becomes Segment Construction (was Source Capture)

Per Row 3 v0.3 §4.3 and Row 4 v0.4 §4.3:

**Pass 0B behaviour**: receives the captured Sources from Pass 0A and constructs Segments grouping Sources that need contextual support to be intelligible (anaphora, heading-derived scope, table-row-group context).

Segments are **optional**. Produced only when individual Sources cannot stand alone. For prose Sources that are self-contained, zero Segments are produced.

Each Segment populates the canonical `source_refs` array with the `source_id` values of its constituent Sources. **Canonical relation: Segment-points-to-Sources, not the other way around.** No `segment_id` back-reference column on the source table.

Pass labels (0, 0A, 0B, 0C) stay stable — only the content of Pass 0A and Pass 0B is swapped from the original v0.2 implementation.

### Change 3 — Pydantic and SQLAlchemy models updated to canonical attribute names (canonical v2.11)

Per Row 4 v0.4 §5.1 / §5.2:

**Source canonical attributes** (canonical ledger spec v2.11 § Element Type — Source):
- source_id (REQUIRED, format ^S\d{3}$)
- source_text (REQUIRED, verbatim bytes)
- segmentation_context (REQUIRED, classification text)
- input_material_ref (REQUIRED, origin reference)
- confidence (REQUIRED, 0.0..1.0)
- parent_source_ref (OPTIONAL, format ^S\d{3}$ — null in v1)

**Segment canonical attributes** (canonical ledger spec v2.11 § Element Type — Segment):
- segment_id (REQUIRED, format ^SEG\d{3}$)
- title (REQUIRED)
- description (OPTIONAL)
- source_refs (REQUIRED, ARRAY of source_id values — canonical Segment-to-Source relation)
- parent_segment_ref (OPTIONAL, format ^SEG\d{3}$ — for hierarchical Segmentation)
- confidence (REQUIRED, 0.0..1.0)

**SourceAtom canonical attributes** (canonical ledger spec v2.11 § Element Type — SourceAtom — 6 attributes, NOT 3 as previous task instruction said):
- atom_id (REQUIRED, format ^SA\d{3}$)
- atom_text (REQUIRED, verbatim subset of parent Source.source_text)
- source_ref (REQUIRED, format ^S\d{3}$ — parent Source)
- segment_ref (OPTIONAL, format ^SEG\d{3}$ — Segment within which atom is contextually scoped; populate when atom needs broader context than parent Source carries)
- parent_atom_ref (OPTIONAL, format ^SA\d{3}$ — broader atom this one refines; for atom hierarchies)
- confidence (REQUIRED, 0.0..1.0)

**AnalysisPass canonical attributes** (canonical ledger spec v2.11 § Element Type — AnalysisPass — substantial expansion from v2.10):
- pass_id (REQUIRED, format ^P\d{3}$)
- pass_type (REQUIRED — broad classification: "Universal" / "Per-row" / "Practitioner". For Source Capture: "Universal")
- mechanism (REQUIRED — mechanism implementation name. For this build: "SourceCapture")
- execution_status (REQUIRED, enum: "Success" / "Failed" / "PartialSuccess")
- mode_active (REQUIRED — active Transformation Mode. For Source Capture: "LPM")
- declared_transformation_modes (REQUIRED, array, non-empty. For Source Capture: ["LPM"])
- outputs (REQUIRED, JSONB object — conventional keys: read_witness, mechanism_data, mode_violations; failure_reason and failure_pass populated only on Failed/PartialSuccess)
- evaluated_scope (REQUIRED — statement describing what was analysed. For Source Capture: "All input material in this project" or similar)
- pass_started_at (REQUIRED, ISO 8601 datetime)
- pass_completed_at (OPTIONAL, ISO 8601 datetime — populated on terminal state)
- elapsed_ms (OPTIONAL, non-negative integer convenience)
- confidence (REQUIRED, 0.0..1.0 — typically 1.0 for deterministic LPM mechanisms)

Key structural changes for SQLAlchemy:

- **Remove the `segment_id` column from the source table** if present. Canonical Source has no parent-Segment back-reference.
- **Add `source_refs` as ARRAY of TEXT column to the segment table** if not already present. Populated by Pass 0B.
- **Add `parent_segment_ref` column to the segment table** (nullable, FK to segment.segment_id with SET NULL cascade).

DB field name preservation: if current DB columns are `pass_started_at` / `pass_completed_at` etc., **keep these names** — they match canonical. No rename needed. The export layer's job is filtering, not field renaming.

### Change 4 — Canonical JSON export filters non-canonical attributes only

Per Row 4 v0.4 §5.6:

Update `sysengage/tools/run_capture.py` export function to filter Pydantic model fields to canonical attributes per v2.11 before serialisation. The non-canonical-attribute lists below are now smaller than the previous task instruction said, because v2.11 canonicalises the operational AnalysisPass attributes that were previously thought non-canonical.

**Source.payload non-canonical (strip at export)**: phase_id, practitioner_id, project_id, is_non_text, has_decoding_issues, position. Keep: source_id, source_text, segmentation_context, input_material_ref, confidence, parent_source_ref.

**Segment.payload non-canonical (strip at export)**: phase_id, practitioner_id, project_id. Keep: segment_id, title, description, source_refs, parent_segment_ref, confidence.

**SourceAtom.payload non-canonical (strip at export)**: phase_id, practitioner_id, project_id, position, is_non_text, has_decoding_issues. Keep: atom_id, atom_text, source_ref, segment_ref (optional but canonical), parent_atom_ref (optional but canonical), confidence (REQUIRED — was previously incorrectly flagged for stripping).

**AnalysisPass.payload non-canonical (strip at export)**: phase_id, practitioner_id, project_id. Keep: pass_id, pass_type, mechanism, execution_status, mode_active, declared_transformation_modes, outputs (with conventional sub-keys), evaluated_scope, pass_started_at, pass_completed_at, elapsed_ms, confidence.

Note: the previous task instruction's Q3 framing — "keep operational attributes despite non-canonical" — is no longer applicable. Per v2.11, these attributes ARE canonical. The filtering rule is now simply: strip only the genuinely non-canonical implementation-internal attributes (phase_id / practitioner_id / project_id / position / is_non_text / has_decoding_issues — whichever appear on each entity).

## Confirmed answers to your previous Plan Mode questions

For convenience, the resolutions to your six Q1-Q6 questions are reproduced below — they remain valid for v0.4 / v0.3 / v2.11 work:

- **Q1 (simple_paragraph.txt content)** — update file to Row 4 v0.4 §9.1.1 verbatim content (4 sentences across 3 lines producing 4 Sources)
- **Q2 (very_long_sentence.txt)** — programmatically generate a genuine 10KB+ single sentence with no internal terminating punctuation; expect exactly 1 Source
- **Q3 (AnalysisPass field mapping)** — SUPERSEDED. v2.11 canonicalises the operational attributes. Keep mechanism / execution_status / mode_active / declared_transformation_modes / outputs / pass_started_at / pass_completed_at / elapsed_ms at export. Strip only phase_id / practitioner_id / project_id. DB field names need no renaming (they already match canonical).
- **Q4 (SourceAtom canonical set)** — SUPERSEDED. Canonical SourceAtom is 6 attributes (your reading of the JSON Schema was right). Keep segment_ref, parent_atom_ref, confidence at export.
- **Q5 (Pass 0C v1 default)** — confirmed. Pass 0C module stays in place; for v1 default with prose, returns empty list. Either stub implementation or configuration-gated full implementation is fine.
- **Q6 (Alembic vs schema recreate)** — confirmed. Drop + recreate via create_all is the right call. Verify sequences (s_id_seq, seg_id_seq, sa_id_seq, p_id_seq) restart from 1 after recreate.

## What stays the same (do not change)

- Pass 0 (Read Witness) logic — unchanged
- Pass 0C (SourceAtom Splitting) — concept unchanged; for v1 default with prose, returns empty list
- File-format decoders (.txt, .md, .docx, .pdf) — unchanged
- Database scaffolding except as Change 3 requires
- AnalysisPass record creation discipline (mode tracking, atomic transaction)
- CLI verification harness `sysengage/tools/run_capture.py` — modified only as Change 4 requires
- Identifier sequencing patterns (S### / SEG### / SA### / P###)
- pytest framework and test infrastructure
- Transaction discipline (atomic ledger writes)

## Pre-implementation steps

### Step 1 — Read the specs

Open and read the three documents listed above. Pay particular attention to:

- Canonical ledger spec v2.11 § Element Type — AnalysisPass (substantially amended from v2.10 — read carefully)
- Canonical ledger spec v2.11 § Element Type — SourceAtom (unchanged from v2.10 but worth verifying — 6 attributes)
- Row 4 v0.4 §5.1 / §5.6 (corrected canonical attribute lists)
- Row 4 v0.4 §8 verification postconditions (updated to reference correct canonical sets)
- Row 4 v0.4 §9 test fixtures (expected outputs revised per F23 in v0.3 cycle)
- Row 3 v0.3 §4.2 / §4.3 / §4.4 (Pass content as in Row 3 v0.2 — granularity-correct from F23 cycle)
- Row 3 v0.3 §7.1.4 (Read Witness narrative reflects v2.11 canonical AnalysisPass.outputs)

### Step 2 — Plan Mode review

Before writing any code, do a Plan Mode review. Confirm:

- You understand the four changes per the consolidated spec set
- The canonical AnalysisPass attribute set per v2.11 is now clear (operational attributes ARE canonical)
- The canonical SourceAtom set per v2.11 is 6 attributes (was previously mis-stated as 3)
- Which existing code paths are affected
- Which fixtures need expected-output revision

Raise any further ambiguities or questions before starting implementation. The previous Plan Mode review caught real spec errors — please apply the same rigour here. We've already had two iterations to get the specs right; if anything still looks off, flag it before coding.

### Step 3 — Database reset

Same as previous task instruction. Drop and recreate all tables. Verify sequences restart from 1. The database must be empty before re-implementation runs so that re-verification produces clean S001 / SEG001 / SA001 / P001 starting state.

## Implementation steps (after Plan Mode review approved)

1. Update SQLAlchemy models per Change 3 — remove non-canonical Source-to-Segment back-reference; add Segment.source_refs and Segment.parent_segment_ref columns
2. Update Pydantic models per Change 3 — canonical attribute names and field counts per v2.11 (substantial AnalysisPass expansion; SourceAtom adds segment_ref / parent_atom_ref / confidence)
3. Update Pass 0A implementation per Change 1 — sentence-level Source extraction
4. Update Pass 0B implementation per Change 2 — Segment Construction; populate source_refs
5. Update Pass 0C implementation per Change 5 / Q5 — v1 default returns empty list for prose
6. Update canonical JSON export in `sysengage/tools/run_capture.py` per Change 4 — strip only the genuinely non-canonical attributes
7. Update test fixtures per Row 4 v0.4 §9 — concrete expected outputs revised per F23 cycle:
   - simple_paragraph.txt → 4 Sources / 0 SourceAtoms (was 1 Source / 3 SourceAtoms)
   - multi_section.md → 4 Sources + 2 Segments with source_refs populated / 0 SourceAtoms
   - abbreviation_handling.txt → 3 Sources / 0 SourceAtoms
   - Rename `very_large_paragraph.txt` → `very_long_sentence.txt`; expected output is 1 Source (single 10KB+ sentence with no internal terminating punctuation)
8. Run pytest — expect most tests to pass; fix any that don't
9. Run the CLI verification harness with the database empty — confirm it produces a valid (empty) canonical ledger output

## Verification

After implementation complete, Practitioner will:

1. Upload The Pocket Money Tracker System v1.docx (already in verification_inputs/)
2. Run: `python -m sysengage.tools.run_capture "verification_inputs/The Pocket Money Tracker System v1.docx" verification_outputs/my_test_ledger_v2.json`
3. Download my_test_ledger_v2.json
4. Open in existing ledger viewer

**Expected output**: approximately 9 Sources (one per sentence in the Pocket Money body paragraph), 1 Segment titled "High Level Description" with source_refs containing all 9 Source identifiers, 0 SourceAtoms, 1 AnalysisPass conforming to v2.11 canonical schema. AnalysisPass.payload should include: pass_id, pass_type=Universal, mechanism=SourceCapture, execution_status=Success, mode_active=LPM, declared_transformation_modes=[LPM], outputs (with read_witness sub-structure plus mechanism_data plus mode_violations=[]), evaluated_scope, pass_started_at, pass_completed_at, elapsed_ms, confidence=1.0. No phase_id, practitioner_id, or project_id in the payload (those are stripped at export).

If verification succeeds, F23 / F24 / F25 / F26 are confirmed resolved at the implementation level. If anything else surfaces, it will be captured as new tracker findings.

## Constraints

- Do NOT introduce new dependencies (no new pip packages).
- Do NOT change the Read Witness implementation, decoder logic, or any code not directly affected by the four changes above.
- Do NOT re-introduce a `Source.segment_id` back-reference column out of implementation convenience — this is canonically incorrect.
- Do NOT modify the canonical ledger spec or the Row 3 / Row 4 specs. They are authoritative for this work.
- Do NOT change the CLI invocation interface — `python -m sysengage.tools.run_capture <input> <output>` stays the same.
- Do NOT strip canonical operational attributes from AnalysisPass at export. Per v2.11, mechanism / execution_status / mode_active / declared_transformation_modes / outputs / timestamps ARE canonical. The previous task instruction's framing was based on outdated canonical spec.
- Do NOT strip canonical optional attributes from SourceAtom at export. segment_ref / parent_atom_ref are canonical (optional); confidence is canonical (required).

## When you're done

Confirm completion with a summary:

- Which files were modified (list paths)
- Which fixtures were updated (filenames + old-expected → new-expected counts)
- Which tests pass / fail counts
- Whether the CLI verification harness runs cleanly with empty database
- Schema validation result: does the exported ledger JSON validate against canonical ledger spec v2.11 JSON Schema (Appendix C)? If you can run a JSON Schema validator against the empty-database export, do so and report.
- Any further ambiguities, questions, or findings surfaced during the work — capture them so they can be added to the SysEngage tracker

The Practitioner will then run verification on the Pocket Money input and report results back.

## Note on canonical conformance discipline

This task is the third iteration of the re-implementation work (v1 → re-implementation per v0.3+v0.2+v2.10 → re-implementation per v0.4+v0.3+v2.11). Each iteration tightened canonical conformance:

- v1: implementation followed v0.2 spec faithfully but produced canonical-incorrect output (paragraph-level Source / sentence-level SourceAtom)
- First re-implementation (cancelled): per v0.3+v0.2+v2.10 — would have required pragmatic workarounds at JSON export for operational AnalysisPass attributes, breaking layered conformance
- Second re-implementation (this task): per v0.4+v0.3+v2.11 — canonical spec amended so operational attributes are properly canonical; implementation can conform to all three layers simultaneously without workarounds

Path A (canonical-first, then mechanism specs, then implementation) was chosen specifically to preserve disciplined layered conformance. This task is the implementation step in Path A. After re-verification confirms canonical-correct output, the entire cycle closes cleanly: implementation conforms to mechanism spec; mechanism spec conforms to canonical spec; canonical spec accurately reflects architectural commitments. No "we'll fix it later" debt.
