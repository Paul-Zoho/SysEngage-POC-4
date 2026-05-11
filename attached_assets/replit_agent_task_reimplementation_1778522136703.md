# Replit Agent Task — Source Capture Re-Implementation per Row 3 v0.2 + Row 4 v0.3

## Context

The Source Capture mechanism you built earlier is functionally complete and the CLI verification harness works. However, first verification on real input (The Pocket Money Tracker System v1.docx) surfaced two findings that require re-implementation:

1. **F23 — Source / SourceAtom granularity misframed**: the v0.2 specs you implemented from defined Source at paragraph-level and SourceAtom at sentence-level. The canonical ledger spec defines Source at sentence-level and SourceAtom at sub-sentence-level. Your implementation followed the v0.2 specs faithfully (no defect on your part) but the specs themselves were canonical-incorrect.

2. **F24 — Non-canonical attributes leaking into canonical JSON export**: the canonical JSON ledger produced by `sysengage/tools/run_capture.py` includes implementation-internal attributes (phase_id, practitioner_id, project_id, position, is_non_text, has_decoding_issues) that are not part of the canonical schema and must be stripped during export.

Both findings have been resolved at the spec level. Two revised specs are provided:

- **SysEngage_Row_3_Mechanism_Source_Capture_v0_2.docx** (Row 3 — supersedes v0.1)
- **SysEngage_Row_4_Mechanism_Source_Capture_v0_3.docx** (Row 4 — supersedes v0.2)

Plus the canonical ledger spec, also bumped:

- **sysengage_minimal_ledger_spec_v2_10.docx** (canonical — supersedes v2.9; UTF-8 markdown content despite .docx extension; can be read as plain text)

Read all three before starting. They describe what needs to change and what stays the same.

## Document list uploaded to attached_assets

1. `SysEngage_Row_3_Mechanism_Source_Capture_v0_2.docx`
2. `SysEngage_Row_4_Mechanism_Source_Capture_v0_3.docx`
3. `sysengage_minimal_ledger_spec_v2_10.docx` (note: this is UTF-8 markdown text content with .docx extension — open as text)

## What changes (the four implementation changes)

### Change 1 — Pass 0A becomes Source Capture (was Segment Construction)

Per Row 3 v0.2 §4.2 and Row 4 v0.3 §4.2:

**New Pass 0A behaviour**: identifies substantive input units at canonical Source granularity — sentence-level statement, single bullet statement, single table-row assertion, definition / constraint line. For prose input, **one Source per sentence**, not per paragraph.

Boundary detection rules for prose: sentence-end punctuation (. ! ?) followed by whitespace. Handle known false-positives: abbreviations (Mr., Dr., Inc., e.g., i.e., etc.), decimal points within numbers, URLs.

Byte preservation discipline: leading whitespace where it belongs to the unit (e.g., the space after the previous sentence's terminating period) is preserved on the subsequent Source. Concatenating all Sources in capture order reproduces the input byte stream.

The previous Pass 0A logic (structural-marker detection for Segments) **moves to Pass 0B**, not deleted.

### Change 2 — Pass 0B becomes Segment Construction (was Source Capture)

Per Row 3 v0.2 §4.3 and Row 4 v0.3 §4.3:

**New Pass 0B behaviour**: Pass 0B receives the captured Sources from Pass 0A and constructs Segments grouping Sources that need contextual support to be intelligible (anaphora, heading-derived scope, table-row-group context).

Segments are **optional**. Produced only when individual Sources cannot stand alone. For prose Sources that are self-contained, zero Segments are produced.

Each Segment populates the canonical `source_refs` array with the `source_id` values of its constituent Sources. **This is the canonical Segment-to-Source relation** — Segment points to Sources, not the other way around.

The default Segmentation policy: produce one Segment per top-level structural boundary (Markdown # / ## heading, Word Heading 1 / 2 style, .pdf bookmark / outline entry, document boundary in multi-document inputs). Nested Segments enabled when policy enables (e.g., section Segment containing paragraph Segments).

Pass labels (0, 0A, 0B, 0C) **stay stable** — only the content of Pass 0A and Pass 0B is being swapped. Mechanism orchestration order changes from Pass 0 → 0A → 0B → 0C to the same Pass-label sequence but with the swapped content.

### Change 3 — Pydantic and SQLAlchemy models updated to canonical attribute names

Per Row 4 v0.3 §5.1 / §5.2:

**Source canonical attributes**: source_id, source_text, segmentation_context, input_material_ref, confidence, parent_source_ref

**Segment canonical attributes**: segment_id, title, description, source_refs (ARRAY of TEXT), parent_segment_ref, confidence

**SourceAtom canonical attributes**: atom_id, atom_text, source_ref

**AnalysisPass canonical attributes**: pass_id, mechanism, execution_status, mode_active, declared_transformation_modes, outputs (JSONB), timestamps (created_at, completed_at, elapsed_ms)

Key structural changes:

- **Remove the `segment_id` column from the source table** (if present). The canonical Source has no parent-Segment back-reference. Segment-to-Source relation is via Segment.source_refs only.
- **Add `source_refs` as ARRAY of TEXT column to the segment table** if not already present. Populated by Pass 0B with constituent Source identifiers.
- **Add `parent_segment_ref` column to the segment table** (nullable, FK to segment.segment_id with SET NULL cascade) for hierarchical Segmentation support. Currently unused for v1 default policy but the column should exist for forward compatibility.

Implementation-internal attributes (phase_id, practitioner_id, project_id, is_non_text, has_decoding_issues, position) may remain on Pydantic and SQLAlchemy models for operational purposes. They must be stripped at canonical JSON export per Change 4. Note: `confidence` IS canonical on Source and Segment — do not strip it.

### Change 4 — Canonical JSON export filters to canonical attributes only

Per Row 4 v0.3 §5.6:

Update `sysengage/tools/run_capture.py` `export_ledger()` function (or wherever the Pydantic-to-JSON serialisation happens) to filter each entity to its canonical attribute set before serialisation.

**Source.payload non-canonical attributes to strip**: phase_id, practitioner_id, project_id, is_non_text, has_decoding_issues, position. Keep: source_id, source_text, segmentation_context, input_material_ref, confidence, parent_source_ref.

**Segment.payload non-canonical attributes to strip**: phase_id, practitioner_id, project_id. Keep: segment_id, title, description, source_refs, parent_segment_ref, confidence.

**SourceAtom.payload non-canonical attributes to strip**: phase_id, practitioner_id, project_id, position. Keep: atom_id, atom_text, source_ref.

**AnalysisPass.payload non-canonical attributes to strip**: phase_id, practitioner_id, project_id. Keep: pass_id, mechanism, execution_status, mode_active, declared_transformation_modes, outputs, created_at, completed_at, elapsed_ms.

The list of canonical attributes can be a hardcoded dict in run_capture.py for v1 — no need for a fancy abstraction. Future refactor may introduce `canonical_attributes()` class methods on Pydantic models.

## What stays the same (do not change)

Most of the existing implementation is correct and should remain:

- Pass 0 (Read Witness) logic — unchanged
- Pass 0C (SourceAtom Splitting) — concept unchanged but rarely invoked (sub-sentence splitting is optional; v1 default for prose produces zero SourceAtoms; activates for structured inputs like table rows splitting into cells)
- File-format decoders (.txt, .md, .docx, .pdf) — unchanged
- Database scaffolding (Postgres schema, sequences, indices) — modified only as Change 3 requires
- AnalysisPass record creation and mode discipline (LPM enforcement, mode_violations tracking) — unchanged
- CLI verification harness `sysengage/tools/run_capture.py` — modified only as Change 4 requires
- Identifier sequencing (S### / SEG### / SA### / P###) — unchanged
- pytest framework and test infrastructure — unchanged
- Transaction discipline (atomic ledger writes) — unchanged

## Pre-implementation steps

### Step 1 — Read the specs

Open and read the three documents listed above. Pay particular attention to:

- Row 3 v0.2 §4.2 / §4.3 / §4.4 / §7.1.1 / §7.1.2 / §7.1.3 / §9.3 / §9.4
- Row 4 v0.3 §4.2 / §4.3 / §4.4 / §5.1 / §5.2 / §5.5 / §5.6 / §8.2 / §8.3 / §8.4 / §9 test fixtures
- Canonical ledger spec v2.10 § Element Type — Source / Element Type — Segment / Element Type — SourceAtom / Element Type — AnalysisPass

### Step 2 — Plan Mode review

Before writing any code, do a Plan Mode review:

- Confirm you understand the four changes
- Identify which existing code paths are affected (Pass orchestrator, Pass 0A function, Pass 0B function, Pydantic models, SQLAlchemy models, JSON export function, test fixtures)
- Confirm which existing tests will need their expected outputs revised (most of the source_capture happy-path tests and abbreviation_handling test)
- Flag any ambiguities or questions before starting

If anything in the spec seems unclear, ambiguous, or contradictory with what you've already built, raise it as a question in Plan Mode before proceeding.

### Step 3 — Database reset

The existing database contains Sources, Segments, SourceAtoms produced by the previous (canonical-incorrect) implementation. Do NOT accumulate canonical-correct data alongside the existing canonical-incorrect data — that produces a confusing mixed state.

Run a database reset to clear all Sources, Segments, SourceAtoms, and AnalysisPass records. The schema itself (sequences, foreign keys, etc.) should be dropped and recreated to ensure the schema changes from Change 3 are applied cleanly.

A truncate + sequence reset is sufficient if the schema changes are limited; if Change 3 requires structural modifications to existing tables (adding source_refs column to segment, removing segment_id column from source), use a fresh schema recreate.

## Implementation steps (after Plan Mode review approved)

1. Update SQLAlchemy models per Change 3 — remove non-canonical Source-to-Segment back-reference; add Segment.source_refs and Segment.parent_segment_ref columns
2. Update Pydantic models per Change 3 — canonical attribute names
3. Update Pass 0A implementation per Change 1 — sentence-level Source extraction
4. Update Pass 0B implementation per Change 2 — Segment Construction from captured Sources; populate source_refs
5. Update mechanism orchestrator if Pass dependencies are wired in code — Pass 0A → Pass 0B (was Pass 0A → Pass 0B previously but with content swapped, the orchestrator may or may not need changes depending on how it's structured)
6. Update canonical JSON export in `sysengage/tools/run_capture.py` per Change 4 — attribute filtering
7. Update test fixtures per Row 4 v0.3 §9 — concrete expected outputs revised. Most affected: simple_paragraph.txt (was 1 Source + 3 SourceAtoms → now 4 Sources + 0 SourceAtoms), multi_section.md (was 3 Sources + 2 Segments + 4 SourceAtoms → now 4 Sources + 2 Segments with source_refs populated + 0 SourceAtoms), abbreviation_handling.txt (was 1 Source + 3 SourceAtoms → now 3 Sources + 0 SourceAtoms)
8. Rename fixture file `very_large_paragraph.txt` → `very_long_sentence.txt` per Row 4 v0.3 §9.2.4 (paragraph framing was canonical-incorrect)
9. Run pytest — expect most tests to pass on first run; fix any that don't (likely test expected-output assertions, not core logic)
10. Run the CLI verification harness with the database empty — confirm it produces output (no Sources to export yet, but the harness should not crash)

## Verification

After implementation complete, the Practitioner will:

1. Upload The Pocket Money Tracker System v1.docx (already in verification_inputs/)
2. Run: `python -m sysengage.tools.run_capture "verification_inputs/The Pocket Money Tracker System v1.docx" verification_outputs/my_test_ledger_v2.json`
3. Download my_test_ledger_v2.json
4. Open in existing ledger viewer

**Expected output**: approximately 9 Sources (one per sentence in the Pocket Money body paragraph), 1 Segment titled "High Level Description" with source_refs containing all 9 Source identifiers, 0 SourceAtoms, 1 AnalysisPass with execution_status=Success. No non-canonical attributes in any payload.

If the verification succeeds, F23 and F24 are confirmed resolved at the implementation level. If anything else surfaces during verification, it will be captured as new tracker findings.

## Constraints

- Do NOT introduce new dependencies (no new pip packages, no new environment requirements). Use what's already in `pyproject.toml`.
- Do NOT change the Read Witness implementation, decoder logic, or any code not directly affected by the four changes above.
- Do NOT re-introduce a `Source.segment_id` back-reference column out of implementation convenience — this is canonically incorrect (Segment.source_refs is the canonical relation).
- Do NOT modify the canonical ledger spec or the Row 3 / Row 4 specs. They are authoritative for this work.
- Do NOT change the CLI invocation interface — `python -m sysengage.tools.run_capture <input> <output>` stays the same.

## Plan Mode questions worth raising up front

Before starting implementation, please consider and raise as Plan Mode questions any of the following if they apply:

- Are there other places in the existing implementation (beyond Pass 0A / Pass 0B / models / JSON export) that reference non-canonical attribute names like `Source.content`, `Source.source_uri`, or `Source.context_id` that need updating?
- Is the existing fixture file naming convention consistent with what Row 4 v0.3 §9 describes?
- Are there integration tests or end-to-end tests that depend on the v0.2 expected outputs and need updating beyond the unit-test fixtures?
- Is there anything in `replit.md` (the entry-point documentation) that needs updating?

## When you're done

Confirm completion with a summary:

- Which files were modified (list paths)
- Which fixtures were updated (list filenames and old-expected → new-expected counts)
- Which tests now pass
- Whether the CLI verification harness runs cleanly
- Any ambiguities, questions, or findings surfaced during the work that should be captured in the SysEngage tracker

The Practitioner will then run verification on the Pocket Money input and report results back. If verification confirms canonical-correct output, F23 and F24 will be marked resolved in the tracker.
