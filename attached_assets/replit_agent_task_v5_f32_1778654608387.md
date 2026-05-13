# Replit Agent Task — Source Capture v0.7 Incremental Update (F32 Non-Loss Preservation)

## Why this is a small refinement task

The v0.6 implementation handled the stress test successfully (TST-007 Row 1 Understanding v1.2 — 272 Sources, 55 Segments, canonical-clean, generator="v0.6", classifier active). F23 / F24 / F25 / F27 / F29 / F30 / F31 all confirmed across 3 verification cycles on diverse real inputs.

However Practitioner ledger review of TST-007 revealed a Non-Loss Principle violation: concatenating all 272 `source_text` values gave 37,514 characters, but the Read Witness `character_count` was 39,785. The 2,271-character delta is entirely attributable to heading text being consumed for `Segment.title` without being preserved as any Source content. Per Row 1 v1.2 §8.1 (Non-Loss Principle), input content must be preserved verbatim in the canonical entity stream — Source.source_text is the canonical content carrier; Segment.title is reviewer convenience metadata.

This task fixes the violation by making Pass 0A produce a Source for each detected structural heading (in addition to the body Sources that follow).

## Document to read

**SysEngage_Row_4_Mechanism_Source_Capture_v0_7.docx** — supersedes v0.6. Key sections:

- **§4.2.2** — Pass 0A processing logic, now with explicit heading-as-Source rule (third bullet) and Non-Loss reconstruction invariant (fifth bullet)
- **§4.2.5** — classifier section, now with new priority-0 rule for headings; enumeration expanded from 5 to 6 values; new "heading" value added; existing rules renumbered (bullet=1, table=2, sentence=3, definition=4, multi-line=5; priority order among them unchanged)
- **§4.3.2** — Pass 0B processing logic, now with heading-Source-plus-Segment relationship clarification (new bullet at the end)
- **§8.2** — Pass 0A verification, now with new Non-Loss reconstruction invariant check
- **§11 build notes** — F32 / F33 / F34 entries

Canonical ledger spec v2.11 unchanged.

## The implementation changes

### Change 1 — Bump generator string (F30 convention)

Update `GENERATOR_VERSION` from `"sysengage_source_capture_v0.6"` to `"sysengage_source_capture_v0.7"`. Single constant change.

Verify by inspecting `generator` field at top of a freshly-produced ledger.

### Change 2 — Pass 0A: produce a Source for each detected structural heading

This is the substantive change. Per Row 4 v0.7 §4.2.2 heading-as-Source bullet and §4.2.5 rule 0:

When Pass 0 detects a structural heading marker (Word Heading style; Markdown #/##/###; PDF outline entry), Pass 0A produces a dedicated Source for the heading text in addition to the body Sources that follow. The heading Source's content is the heading text exactly as it appeared in the input, with these specifics:

- **Word .docx**: the heading paragraph's text content; the Heading style metadata itself is NOT in the content (it's structural metadata that's already being used by Pass 0 to mark this as a heading)
- **Markdown**: the heading line's text content WITHOUT the # / ## / ### syntax prefix (the # marker is structural syntax, not heading content — strip it). For example, `## Mission Statement` produces a Source with source_text `"Mission Statement"` (or `" Mission Statement"` if you want to preserve the leading space after ##; either is acceptable as long as it's deterministic)
- **PDF**: the outline / bookmark entry's text content

The heading Source's segmentation_context is `"heading"` (the new value).

The heading Source is produced *before* the body Sources of that section in the capture order, so concatenating all Sources in source_id order reproduces the input character stream in the right sequence: heading text first, then body text following.

### Change 3 — Classifier: add "heading" value and priority-0 rule

Update the classifier function in Pass 0A per Row 4 v0.7 §4.2.5:

**Enumeration**: now 6 values — "heading", "sentence in prose", "bullet item", "table row", "definition line", "multi-line block"

**Priority order** (first matching rule wins):

1. **NEW Rule 0**: If Pass 0 surfaced a structural heading marker for this Source → "heading". (Highest priority; fires before all others.)
2. Rule 1: bullet-list marker → "bullet item"
3. Rule 2: table-row marker → "table row"
4. Rule 3: sentence terminator present → "sentence in prose"
5. Rule 4: definition-line pattern (label-colon-short-value, no sentence terminator) → "definition line"
6. Rule 5: fallback → "multi-line block"

Implementation guidance: rule 0 fires based on structural marker context (the same context the classifier was already receiving for rules 1 and 2). It does NOT depend on the source_text content directly — a heading Source might or might not contain a sentence terminator (e.g., "1. What is SysEngage?" has a question mark), but rule 0 still fires because the structural marker says "this Source originated from a heading".

### Change 4 — Pass 0B: position heading Source as Segment.source_refs[0]

Per Row 4 v0.7 §4.3.2 heading-Source-plus-Segment bullet:

When Pass 0B produces a Segment from a structural heading marker, the corresponding heading Source's source_id is placed at position 0 of Segment.source_refs. Subsequent positions contain the body Sources within that section.

Segment.title remains the heading text (unchanged behaviour). So the heading text appears in two places in the ledger:

- In `Source.source_text` of the heading Source (canonical content per Non-Loss)
- In `Segment.title` of the corresponding Segment (reviewer convenience)

These two pieces should be identical (modulo any leading/trailing whitespace differences if those exist).

### What stays the same

- All other Pass 0A boundary detection logic (sentence boundaries, byte preservation for body content)
- Pass 0B's strict-structural detection scope (F27) — only Word Heading / Markdown # / PDF outline produce Segments; visually-styled paragraph text does NOT
- Pass 0C SourceAtom logic (unchanged; still dormant for prose by v1 default)
- Pydantic / SQLAlchemy models — Source.segmentation_context is REQUIRED non-empty string; no schema change (the new "heading" value is just a string)
- Canonical JSON export filtering (F24)
- Database schema; no recreate needed
- CLI verification harness

## Pre-implementation steps

### Step 1 — Read the spec

Open SysEngage_Row_4_Mechanism_Source_Capture_v0_7.docx. Focus on §4.2.2 (Non-Loss invariant + heading-as-Source rule), §4.2.5 (priority-0 rule), §4.3.2 (Segment.source_refs[0] = heading Source), §8.2 (Non-Loss reconstruction check).

### Step 2 — Plan Mode review

This is a more substantive change than v4 (which was just rule order swap + constant bump). Plan Mode review is worth doing carefully:

- Confirm you understand the heading-as-Source rule: Word Heading style / Markdown # / PDF outline = produce a Source for the heading text
- Confirm you've identified where in Pass 0A the existing heading detection happens (Pass 0 surfaces the structural marker; Pass 0A consumes it currently to inform Pass 0B's Segment creation; the new behaviour is that Pass 0A ALSO produces a Source for the heading)
- Confirm the heading Source's source_id appears at Segment.source_refs[0]
- Confirm the Markdown # syntax stripping behaviour (heading content excludes the # marker syntax)
- Confirm the new "heading" classifier value will work with existing Pydantic validation (segmentation_context is REQUIRED non-empty string with no enum enforced; new value is just a string, no schema change)
- Confirm test fixtures that have heading content will need expected-output updates

If anything is ambiguous, raise it. The spec is precise about WHAT to do but you decide HOW to do it.

### Step 3 — No database reset needed

Incremental change. Existing DB can stay.

## Implementation steps

1. Update `GENERATOR_VERSION` constant from "v0.6" to "v0.7"
2. Update Pass 0A boundary detection to emit a Source for each detected structural heading (Word Heading style, Markdown #/##/###, PDF outline entry). The heading Source's source_text is the heading text without structural marker syntax
3. Update classifier: add new priority-0 rule for headings; new "heading" return value
4. Update Pass 0B to place heading Source's source_id at position 0 of Segment.source_refs
5. Update test fixtures with expected heading Sources:
   - `multi_section.md` — currently has heading content; expected output should now include heading Sources
   - Any other fixtures with structural headings need expected-output updates
6. Add a verification assertion in tests: sum of len(Source.source_text) across all Sources equals Read Witness character_count
7. Run pytest. Expect heading-related test failures until expected values are updated
8. Run CLI harness on existing inputs:
   - TST-001 v4 Pocket Money — expect heading Source for "High Level Description" → 10 Sources (was 9); 1 Segment with 10 source_refs (was 9)
   - TST-002 v4 Novus — expect unchanged (no Word Heading style; QUALITY POLICY STATEMENT is bold paragraph text not detected per F27 → still 11 Sources, 0 Segments)
   - TST-007 v2 Row 1 Understanding — expect 55 additional heading Sources → 272 + 55 = 327 Sources; 55 Segments each with heading Source at position 0 of source_refs; Source concatenation now matches Read Witness character_count exactly

## Verification

Practitioner will run the CLI harness on all three inputs:

```
python -m sysengage.tools.run_capture "verification_inputs/The Pocket Money Tracker System v1.docx" verification_outputs/TST-001-PocketMoney-v4.json
python -m sysengage.tools.run_capture "verification_inputs/Novus Quality Policy Statement v1.docx" verification_outputs/TST-002-Novus-v4.json
python -m sysengage.tools.run_capture "verification_inputs/SysEngage_Row_1_Understanding_v1_2.docx" verification_outputs/TST-007-Row1-v2.json
```

**Expected outcomes**:

- **All three ledgers**: `"generator": "sysengage_source_capture_v0.7"` at top of JSON
- **TST-001 v4 Pocket Money**: 10 Sources (1 heading "High Level Description" + 9 body prose); SEG###.source_refs has 10 entries with heading Source at position 0; sum of Source.source_text lengths = Read Witness character_count (902 chars exactly)
- **TST-002 v4 Novus**: unchanged from v3 (11 Sources, 0 Segments) since no Word Heading style detected; reconstruction match was already 1915=1915
- **TST-007 v2 Row 1 Understanding**: 327 Sources (55 heading + 272 body); 55 Segments each with heading at source_refs[0]; sum of Source.source_text lengths = 39,785 chars exactly (matching Read Witness character_count). This is the primary diagnostic for F32 closure.

If reconstruction sum matches Read Witness character_count on TST-007, F32 closure is confirmed at code layer.

## Constraints

- Do NOT change Pass 0B's strict-structural detection scope (F27 still holds — visually-styled paragraph text does NOT produce Segments OR heading Sources)
- Do NOT change Pass 0A's sentence boundary detection for body content (only ADD heading-Source production; don't modify the existing body-Source logic)
- Do NOT introduce new dependencies
- The new classifier rule MUST be deterministic — heading detection is based on Pass 0's structural markers, no heuristics
- Do NOT skip the generator string bump; that's the F30 convention from v0.6

## When you're done

Confirm completion with:

- Files modified
- Whether GENERATOR_VERSION is now "v0.7"
- Whether Pass 0A produces heading Sources
- Whether Segment.source_refs[0] is the heading Source
- Whether classifier emits "heading" value for heading Sources
- Test pass / fail counts after fixture updates
- Whether reconstruction sum matches Read Witness character_count on TST-007 (this is the key diagnostic)

## Note on cycle context

This is the fifth implementation cycle:

- v0.2 (cancelled): canonical-incorrect granularity
- v0.4: canonical-correct output; verified on TST-001 / TST-002 (8 May)
- v0.5: added classifier; verified on TST-001 v2 / TST-002 v2 (12 May)
- v0.6: classifier rule order swap + generator string bump; verified on TST-005 / TST-006 (13 May)
- v0.7 (this): heading-Source preservation for Non-Loss Principle; first cycle responding to F32 from large-document stress test

This cycle is larger than v0.6 (which was tiny — rule order swap + constant bump). v0.7 actually adds a new capability (heading-Source production). It's still smaller than v0.4 (which was a full re-implementation per corrected canonical spec). The Path A discipline continues — well-framed v0.7 spec + bounded scope should make implementation efficient.
