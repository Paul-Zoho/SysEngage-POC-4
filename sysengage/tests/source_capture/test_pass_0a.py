"""
Tests for Pass 0A — Source Capture (sentence-level).

Per Implementation Spec v0.5 §8.2 verification criteria and §9 test fixtures.

Pass 0A is now Source Capture (sentence-level), replacing the old Pass 0A
(Segment Construction). The old Segment Construction is now Pass 0B.

Tests:
  - Happy path: 4 Sources for simple_paragraph.txt (3-line, 4-sentence fixture)
  - Happy path: 4 Sources for multi_section.md (3 in section 0, 1 in section 1)
  - Happy path: 3 Sources for abbreviation_handling.txt (no false split on Dr./Inc./Mr.)
  - Happy path: 1 Source for single_short_statement.txt (no sentence boundary)
  - section_index is None for plain text (.txt)
  - section_index is int for structured text (.md) — matches heading ordinal
  - segmentation_context == "sentence in prose" for prose Sources (F29: classifier-derived)
  - segmentation_context == "definition line" for single label:value Sources (F29)
  - segmentation_context == "multi-line block" for signature/attribution blocks (F29)
  - segmentation_context == "bullet item" / "table row" when marker flags are True (F29)
  - source_text verbatim (found in decoded text for structured inputs)
  - source_text non-empty for all produced Sources
  - Determinism: same input + same policy → identical Source count and content
  - Error case: invalid policy → SegmentationPolicyError
"""

from pathlib import Path

import pytest

from mechanisms.source_capture.errors import SegmentationPolicyError
from mechanisms.source_capture.pass_0_read_witness import run_pass_0
from mechanisms.source_capture.pass_0a_source_capture import (
    run_pass_0a,
    SourceSpec,
    classify_segmentation_context,
)


class TestPass0AHappyPath:
    def test_simple_paragraph_produces_four_sources(
        self, simple_paragraph_path: Path
    ):
        """
        4 Sources expected for simple_paragraph.txt per §9.1.1.
        3-line, 4-sentence file → sentence-level capture → 4 Sources.
        """
        _, dr = run_pass_0(simple_paragraph_path)
        sources = run_pass_0a(dr)

        assert len(sources) == 4

    def test_multi_section_produces_four_sources(self, multi_section_path: Path):
        """
        4 Sources expected for multi_section.md per §9.1.2.
        Section One: 3 sentences → 3 Sources.
        Section Two: 1 sentence → 1 Source.
        Total: 4 Sources.
        """
        _, dr = run_pass_0(multi_section_path)
        sources = run_pass_0a(dr)

        assert len(sources) == 4

    def test_abbreviation_produces_three_sources(self, abbreviation_path: Path):
        """
        3 Sources for abbreviation_handling.txt per §9.2.3.
        "Dr. Smith works at Acme Inc. He is a clinician. Mr. Jones is the patient."
        - "Dr." → TITLE_ABBR, no split
        - "Inc." → NOT title abbr, followed by " He" (space + capital) → SPLIT
        - "clinician." → followed by " Mr." (space + capital) → SPLIT
        - "Mr." → TITLE_ABBR, no split
        - "patient." → end of text, no split
        Result: 3 Sources ("Dr. Smith works at Acme Inc.", " He is a clinician.", " Mr. Jones...")
        """
        _, dr = run_pass_0(abbreviation_path)
        sources = run_pass_0a(dr)

        assert len(sources) == 3

    def test_single_short_statement_produces_one_source(
        self, single_short_statement_path: Path
    ):
        """
        1 Source for 'Hello' (single word, no sentence boundary).
        No terminal punctuation followed by whitespace + capital → 1 chunk.
        """
        _, dr = run_pass_0(single_short_statement_path)
        sources = run_pass_0a(dr)

        assert len(sources) == 1
        assert sources[0].source_text == "Hello"

    def test_docx_produces_sources_by_sentence(
        self, simple_requirements_docx: Path
    ):
        """
        Docx with 2 H2 sections and body paragraphs → sentence-level Sources.
        The generated docx has 3 body sentences in section 1 + 2 in section 2 = 5.
        """
        _, dr = run_pass_0(simple_requirements_docx)
        sources = run_pass_0a(dr)

        assert len(sources) >= 5


class TestPass0ASectionIndex:
    def test_plain_text_section_index_is_none(self, simple_paragraph_path: Path):
        """
        Plain text (.txt) produces Sources with section_index=None.
        No heading structure detected → all Sources are unanchored.
        """
        _, dr = run_pass_0(simple_paragraph_path)
        sources = run_pass_0a(dr)

        for src in sources:
            assert src.section_index is None, (
                f"Expected section_index=None for plain text, got {src.section_index}"
            )

    def test_structured_text_section_index_is_int(self, multi_section_path: Path):
        """
        Structured text (.md) produces Sources with integer section_index.
        section_index tracks which heading section each Source belongs to.
        """
        _, dr = run_pass_0(multi_section_path)
        sources = run_pass_0a(dr)

        for src in sources:
            assert isinstance(src.section_index, int), (
                f"Expected int section_index for structured text, got {src.section_index!r}"
            )

    def test_multi_section_section_indices_cover_both_sections(
        self, multi_section_path: Path
    ):
        """
        multi_section.md has 2 heading sections (indices 0 and 1).
        Sources should be split across both section_index values.
        """
        _, dr = run_pass_0(multi_section_path)
        sources = run_pass_0a(dr)

        section_indices = {src.section_index for src in sources}
        assert 0 in section_indices, "section_index=0 expected for Section One"
        assert 1 in section_indices, "section_index=1 expected for Section Two"

    def test_section_one_has_three_sources(self, multi_section_path: Path):
        """
        Section One in multi_section.md has 3 sentences → 3 Sources with section_index=0.
        """
        _, dr = run_pass_0(multi_section_path)
        sources = run_pass_0a(dr)

        section_0_sources = [s for s in sources if s.section_index == 0]
        assert len(section_0_sources) == 3

    def test_section_two_has_one_source(self, multi_section_path: Path):
        """
        Section Two in multi_section.md has 1 sentence → 1 Source with section_index=1.
        """
        _, dr = run_pass_0(multi_section_path)
        sources = run_pass_0a(dr)

        section_1_sources = [s for s in sources if s.section_index == 1]
        assert len(section_1_sources) == 1


class TestPass0ASegmentationContext:
    def test_segmentation_context_is_sentence_in_prose(
        self, simple_paragraph_path: Path
    ):
        """All Sources have segmentation_context == 'sentence in prose'."""
        _, dr = run_pass_0(simple_paragraph_path)
        sources = run_pass_0a(dr)

        for src in sources:
            assert src.segmentation_context == "sentence in prose", (
                f"Expected 'sentence in prose', got {src.segmentation_context!r}"
            )

    def test_segmentation_context_for_structured_text(self, multi_section_path: Path):
        _, dr = run_pass_0(multi_section_path)
        sources = run_pass_0a(dr)

        for src in sources:
            assert src.segmentation_context == "sentence in prose"


class TestPass0ABytePreservation:
    def test_source_text_non_empty(self, simple_paragraph_path: Path):
        """All Sources have non-empty source_text."""
        _, dr = run_pass_0(simple_paragraph_path)
        sources = run_pass_0a(dr)

        for src in sources:
            assert src.source_text.strip(), (
                f"source_text must not be blank: {src.source_text!r}"
            )

    def test_plain_text_source_text_verbatim(self, simple_paragraph_path: Path):
        """
        For plain text, source_text bytes are verbatim from the decoded stream.
        Each source_text must be found inside the full decoded text.
        """
        _, dr = run_pass_0(simple_paragraph_path)
        sources = run_pass_0a(dr)

        full_text = dr.text
        for src in sources:
            assert src.source_text in full_text, (
                f"source_text not found verbatim in decoded input: {src.source_text!r}"
            )

    def test_structured_text_source_text_verbatim(self, multi_section_path: Path):
        """For structured text, stripped source_text must be a substring of decoded text."""
        _, dr = run_pass_0(multi_section_path)
        sources = run_pass_0a(dr)

        full_text = dr.text
        for src in sources:
            assert src.source_text.strip() in full_text, (
                f"source_text not found in decoded input: {src.source_text!r}"
            )

    def test_abbreviation_no_false_split_on_dr(self, abbreviation_path: Path):
        """
        'Dr.' must NOT trigger a sentence split before 'Smith'.
        Verified: 3 sources only (not 4), first source contains full "Dr. Smith works at Acme Inc."
        """
        _, dr = run_pass_0(abbreviation_path)
        sources = run_pass_0a(dr)

        assert len(sources) == 3

        first_text = sources[0].source_text.strip()
        assert "Dr. Smith" in first_text, (
            f"Dr. should not split from Smith. Got first source: {first_text!r}"
        )

    def test_abbreviation_no_false_split_on_mr(self, abbreviation_path: Path):
        """'Mr.' must NOT trigger a sentence split before 'Jones'."""
        _, dr = run_pass_0(abbreviation_path)
        sources = run_pass_0a(dr)

        last_text = sources[-1].source_text.strip()
        assert "Mr. Jones" in last_text, (
            f"Mr. should not split from Jones. Got last source: {last_text!r}"
        )

    def test_abbreviation_inc_does_split(self, abbreviation_path: Path):
        """
        'Inc.' followed by ' He' (space + capital) IS a sentence boundary.
        First source should end with 'Inc.' not continue into 'He is a clinician.'
        """
        _, dr = run_pass_0(abbreviation_path)
        sources = run_pass_0a(dr)

        first_text = sources[0].source_text.strip()
        assert first_text.endswith("Inc."), (
            f"First source should end after 'Inc.' Got: {first_text!r}"
        )


class TestPass0ADeterminism:
    def test_identical_source_count_on_rerun(self, multi_section_path: Path):
        """Determinism: same input → identical Source count across two runs."""
        _, dr1 = run_pass_0(multi_section_path)
        srcs1 = run_pass_0a(dr1)

        _, dr2 = run_pass_0(multi_section_path)
        srcs2 = run_pass_0a(dr2)

        assert len(srcs1) == len(srcs2)

    def test_identical_source_texts_on_rerun(self, simple_paragraph_path: Path):
        """Determinism: same input → identical source_text values across two runs."""
        _, dr1 = run_pass_0(simple_paragraph_path)
        srcs1 = run_pass_0a(dr1)

        _, dr2 = run_pass_0(simple_paragraph_path)
        srcs2 = run_pass_0a(dr2)

        for s1, s2 in zip(srcs1, srcs2):
            assert s1.source_text == s2.source_text, (
                "source_text differs across runs (determinism violation)"
            )

    def test_identical_section_indices_on_rerun(self, multi_section_path: Path):
        """Determinism: same input → identical section_index values across two runs."""
        _, dr1 = run_pass_0(multi_section_path)
        srcs1 = run_pass_0a(dr1)

        _, dr2 = run_pass_0(multi_section_path)
        srcs2 = run_pass_0a(dr2)

        for s1, s2 in zip(srcs1, srcs2):
            assert s1.section_index == s2.section_index


class TestPass0AErrorCases:
    def test_invalid_policy_raises_segmentation_policy_error(
        self, simple_paragraph_path: Path
    ):
        """Unrecognised policy name → SegmentationPolicyError (not silent fallback)."""
        _, decode_result = run_pass_0(simple_paragraph_path)
        with pytest.raises(SegmentationPolicyError):
            run_pass_0a(decode_result, policy="invalid_policy_xyz")

    def test_default_policy_accepted(self, simple_paragraph_path: Path):
        """policy='default' → no error."""
        _, decode_result = run_pass_0(simple_paragraph_path)
        sources = run_pass_0a(decode_result, policy="default")
        assert len(sources) >= 1


class TestPass0AClassifier:
    """
    Unit tests for classify_segmentation_context() per v0.5 §4.2.5 (F29).

    Tests cover all five classifier values and the priority-order rules.
    Rules 1-2 (bullet item / table row) are tested via marker flags.
    Rules 3-5 (definition line / sentence in prose / multi-line block) are
    content-based and tested via source_text content.

    Integration tests via fixture files verify that Pass 0A wires the
    classifier correctly for real inputs.
    """

    def test_bullet_marker_returns_bullet_item(self):
        """Rule 1: has_bullet_marker=True → 'bullet item' regardless of text."""
        assert classify_segmentation_context(
            "any text", has_bullet_marker=True
        ) == "bullet item"

    def test_bullet_marker_takes_priority_over_definition_line(self):
        """Rule 1 has highest priority — even a definition-line text yields 'bullet item'."""
        assert classify_segmentation_context(
            "Owner: Damian Shacklock", has_bullet_marker=True
        ) == "bullet item"

    def test_table_marker_returns_table_row(self):
        """Rule 2: has_table_marker=True → 'table row'."""
        assert classify_segmentation_context(
            "any text", has_table_marker=True
        ) == "table row"

    def test_table_marker_priority_over_sentence_in_prose(self):
        """Rule 2 takes priority over prose detection."""
        assert classify_segmentation_context(
            "He is a clinician.", has_table_marker=True
        ) == "table row"

    def test_definition_line_single_line(self):
        """Rule 3: single-line label:value → 'definition line'."""
        assert classify_segmentation_context("Owner: Damian Shacklock") == "definition line"

    def test_definition_line_date(self):
        """Rule 3: 'Date: 22/4/2025' → 'definition line'."""
        assert classify_segmentation_context("Date: 22/4/2025") == "definition line"

    def test_definition_line_with_space_before_colon(self):
        """Rule 3: label with space before colon → 'definition line'."""
        assert classify_segmentation_context("Owner : Damian Shacklock") == "definition line"

    def test_definition_line_with_leading_spaces(self):
        """Rule 3: leading whitespace does not prevent definition-line match."""
        assert classify_segmentation_context("   Title: Director") == "definition line"

    def test_multiline_block_is_not_definition_line(self):
        """
        Rule 3 requires no embedded newlines.
        Multi-line text containing definition-like lines falls through to Rule 5.
        """
        multiline = "Signed by\nDamian Shacklock\nDirector\nDate: 12 May 2026"
        assert classify_segmentation_context(multiline) == "multi-line block"

    def test_sentence_in_prose_simple(self):
        """Rule 4: single sentence with terminal punctuation → 'sentence in prose'."""
        assert classify_segmentation_context("He is a clinician.") == "sentence in prose"

    def test_sentence_in_prose_with_question(self):
        """Rule 4: question mark counts as terminal punctuation."""
        assert classify_segmentation_context("Is this the system?") == "sentence in prose"

    def test_sentence_in_prose_with_exclamation(self):
        """Rule 4: exclamation mark counts as terminal punctuation."""
        assert classify_segmentation_context("The system shall comply!") == "sentence in prose"

    def test_sentence_in_prose_does_not_fire_for_multiline(self):
        """Rule 4 requires no embedded newline — multi-line text falls to Rule 5."""
        assert classify_segmentation_context("Line one.\nLine two.") == "multi-line block"

    def test_multi_line_block_fallback_no_punctuation(self):
        """Rule 5: no terminal punctuation, no newline → 'multi-line block'."""
        assert classify_segmentation_context("Damian Shacklock") == "multi-line block"

    def test_multi_line_block_signature_block(self):
        """Rule 5: multi-line attribution block → 'multi-line block'."""
        sig = "Signed by\nDamian Shacklock\nDirector\nDate: 12 May 2026"
        assert classify_segmentation_context(sig) == "multi-line block"

    def test_multi_line_block_no_sentence_terminator_multiline(self):
        """Rule 5: multiple lines without sentence-end punctuation → 'multi-line block'."""
        assert classify_segmentation_context("Line one\nLine two") == "multi-line block"

    def test_prose_fixture_all_sentence_in_prose(
        self, simple_paragraph_path: Path
    ):
        """
        Integration: simple_paragraph.txt is all prose sentences.
        All Sources must have segmentation_context == 'sentence in prose' (F29).
        """
        _, dr = run_pass_0(simple_paragraph_path)
        sources = run_pass_0a(dr)

        assert len(sources) == 4
        for src in sources:
            assert src.segmentation_context == "sentence in prose", (
                f"Expected 'sentence in prose' for prose fixture, "
                f"got {src.segmentation_context!r} for: {src.source_text!r}"
            )

    def test_definition_line_fixture(self, definition_line_path: Path):
        """
        Integration: definition_line.txt contains a single 'Owner: ...' line.
        The one Source produced must have segmentation_context == 'definition line'.
        """
        _, dr = run_pass_0(definition_line_path)
        sources = run_pass_0a(dr)

        assert len(sources) == 1
        assert sources[0].segmentation_context == "definition line", (
            f"Expected 'definition line', got {sources[0].segmentation_context!r}"
        )

    def test_signature_block_fixture(self, signature_block_path: Path):
        """
        Integration: signature_block.txt is a 4-line attribution block with no
        sentence-ending punctuation. The single Source produced (the whole block,
        since there are no sentence boundaries) must be 'multi-line block'.
        """
        _, dr = run_pass_0(signature_block_path)
        sources = run_pass_0a(dr)

        assert len(sources) >= 1
        for src in sources:
            assert src.segmentation_context == "multi-line block", (
                f"Expected 'multi-line block' for signature fixture, "
                f"got {src.segmentation_context!r} for: {src.source_text!r}"
            )

    def test_classifier_determinism(self):
        """Same source_text always yields the same segmentation_context."""
        text = "The system shall comply with all applicable standards."
        result1 = classify_segmentation_context(text)
        result2 = classify_segmentation_context(text)
        assert result1 == result2

    def test_all_five_values_reachable(self):
        """Every classifier value is reachable via the appropriate input."""
        assert classify_segmentation_context("x", has_bullet_marker=True) == "bullet item"
        assert classify_segmentation_context("x", has_table_marker=True) == "table row"
        assert classify_segmentation_context("Owner: Alice") == "definition line"
        assert classify_segmentation_context("This is prose.") == "sentence in prose"
        assert classify_segmentation_context("No punctuation here") == "multi-line block"
