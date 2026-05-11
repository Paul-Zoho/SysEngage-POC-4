"""
Tests for Pass 0B — Segment Construction (heading-based).

Per Implementation Spec v0.4 §8.3 verification criteria and §9 test fixtures.

Pass 0B is now Segment Construction (heading-based), replacing the old Pass 0B
(Source Capture). Pass 0B receives SourceSpecs from Pass 0A and the DecodeResult,
then identifies structural heading markers to group Sources into Segments.

Tests:
  - Happy path: 0 Segments for plain text (no structural markers)
  - Happy path: 2 Segments for multi_section.md (2 H2 headings, each with Sources)
  - Segment titles match heading text exactly
  - source_spec_indices non-empty per Non-Empty-Segment rule
  - source_spec_indices reference valid indices in source_specs list
  - Docx produces >= 2 Segments from H2 headings
  - Determinism: same input → identical Segment count and titles
  - Error case: invalid policy → SegmentationPolicyError
  - Source Pydantic model immutability (frozen=True LPM enforcement)
"""

from pathlib import Path

import pytest

from mechanisms.source_capture.pass_0_read_witness import run_pass_0
from mechanisms.source_capture.pass_0a_source_capture import run_pass_0a
from mechanisms.source_capture.pass_0b_segment_construction import (
    run_pass_0b,
    SegmentSpec,
)
from mechanisms.source_capture.errors import SegmentationPolicyError
from schemas.source import Source


class TestPass0BHappyPath:
    def test_plain_text_produces_zero_segments(self, simple_paragraph_path: Path):
        """
        Plain text has no structural markers → 0 Segments (not an error).
        format_detected starts with 'txt' → early return.
        """
        _, dr = run_pass_0(simple_paragraph_path)
        source_specs = run_pass_0a(dr)
        segments = run_pass_0b(dr, source_specs)

        assert segments == []

    def test_multi_section_produces_two_segments(self, multi_section_path: Path):
        """
        Two ## headings → 2 Segments per Implementation Spec §9.1.2.
        Each heading section has at least 1 Source → Non-Empty-Segment rule satisfied.
        """
        _, dr = run_pass_0(multi_section_path)
        source_specs = run_pass_0a(dr)
        segments = run_pass_0b(dr, source_specs)

        assert len(segments) == 2

    def test_segment_titles_match_headings(self, multi_section_path: Path):
        """Segment titles must be identical to heading text (stripped of # markers)."""
        _, dr = run_pass_0(multi_section_path)
        source_specs = run_pass_0a(dr)
        segments = run_pass_0b(dr, source_specs)

        titles = [s.title for s in segments]
        assert "Section One" in titles
        assert "Section Two" in titles

    def test_segments_have_description(self, multi_section_path: Path):
        """Segments must have a non-empty description."""
        _, dr = run_pass_0(multi_section_path)
        source_specs = run_pass_0a(dr)
        segments = run_pass_0b(dr, source_specs)

        for seg in segments:
            assert seg.description is not None
            assert len(seg.description.strip()) > 0

    def test_single_short_statement_zero_segments(
        self, single_short_statement_path: Path
    ):
        """Single word plain text → 0 Segments."""
        _, dr = run_pass_0(single_short_statement_path)
        source_specs = run_pass_0a(dr)
        segments = run_pass_0b(dr, source_specs)

        assert segments == []

    def test_docx_produces_segments_by_heading(self, simple_requirements_docx: Path):
        """Docx with Heading styles → Segments per Implementation Spec §9.1.3."""
        _, dr = run_pass_0(simple_requirements_docx)
        source_specs = run_pass_0a(dr)
        segments = run_pass_0b(dr, source_specs)

        assert len(segments) >= 2


class TestPass0BSourceSpecIndices:
    def test_source_spec_indices_non_empty(self, multi_section_path: Path):
        """
        Non-Empty-Segment rule: every Segment must have at least one Source.
        source_spec_indices must be non-empty for all produced Segments.
        """
        _, dr = run_pass_0(multi_section_path)
        source_specs = run_pass_0a(dr)
        segments = run_pass_0b(dr, source_specs)

        for seg in segments:
            assert len(seg.source_spec_indices) > 0, (
                f"Segment '{seg.title}' has empty source_spec_indices (violates Non-Empty-Segment rule)"
            )

    def test_source_spec_indices_are_valid(self, multi_section_path: Path):
        """
        source_spec_indices must reference valid indices in the source_specs list.
        No out-of-bounds index allowed.
        """
        _, dr = run_pass_0(multi_section_path)
        source_specs = run_pass_0a(dr)
        segments = run_pass_0b(dr, source_specs)

        n_sources = len(source_specs)
        for seg in segments:
            for idx in seg.source_spec_indices:
                assert 0 <= idx < n_sources, (
                    f"Segment '{seg.title}' has out-of-bounds source_spec_index: "
                    f"{idx} (valid range: 0..{n_sources - 1})"
                )

    def test_section_one_has_three_source_indices(self, multi_section_path: Path):
        """
        Section One in multi_section.md has 3 sentences → 3 source_spec_indices.
        """
        _, dr = run_pass_0(multi_section_path)
        source_specs = run_pass_0a(dr)
        segments = run_pass_0b(dr, source_specs)

        section_one = next(s for s in segments if s.title == "Section One")
        assert len(section_one.source_spec_indices) == 3

    def test_section_two_has_one_source_index(self, multi_section_path: Path):
        """
        Section Two in multi_section.md has 1 sentence → 1 source_spec_index.
        """
        _, dr = run_pass_0(multi_section_path)
        source_specs = run_pass_0a(dr)
        segments = run_pass_0b(dr, source_specs)

        section_two = next(s for s in segments if s.title == "Section Two")
        assert len(section_two.source_spec_indices) == 1

    def test_all_source_indices_covered(self, multi_section_path: Path):
        """
        Every source_spec should belong to exactly one segment
        (all section_index values should be covered by some segment).
        """
        _, dr = run_pass_0(multi_section_path)
        source_specs = run_pass_0a(dr)
        segments = run_pass_0b(dr, source_specs)

        all_indices_in_segments: set[int] = set()
        for seg in segments:
            all_indices_in_segments.update(seg.source_spec_indices)

        expected_indices = {i for i, s in enumerate(source_specs) if s.section_index is not None}
        assert all_indices_in_segments == expected_indices, (
            "Mismatch between indices covered by segments and sources with section_index"
        )


class TestPass0BImmutability:
    """Source Pydantic model is frozen=True — LPM byte-preservation enforcement."""

    def test_source_pydantic_model_frozen(self, simple_paragraph_path: Path):
        """
        Verify that a Source Pydantic model cannot be mutated after construction.
        Attempted mutation raises ValidationError (Pydantic v2 frozen model).
        This is the primary LPM byte-preservation enforcement.
        """
        source = Source(
            source_id="S001",
            source_text="The system performs analysis.",
            segmentation_context="sentence in prose",
            input_material_ref="test.txt",
            project_id="TEST",
        )

        from pydantic import ValidationError

        with pytest.raises((ValidationError, TypeError, ValueError)):
            source.source_text = "MUTATED"


class TestPass0BDeterminism:
    def test_identical_segment_count_on_rerun(self, multi_section_path: Path):
        """Determinism: same input → identical Segment count across two runs."""
        _, dr1 = run_pass_0(multi_section_path)
        segs1 = run_pass_0b(dr1, run_pass_0a(dr1))

        _, dr2 = run_pass_0(multi_section_path)
        segs2 = run_pass_0b(dr2, run_pass_0a(dr2))

        assert len(segs1) == len(segs2)

    def test_identical_titles_on_rerun(self, multi_section_path: Path):
        """Determinism: same input → identical Segment titles across two runs."""
        _, dr1 = run_pass_0(multi_section_path)
        segs1 = run_pass_0b(dr1, run_pass_0a(dr1))

        _, dr2 = run_pass_0(multi_section_path)
        segs2 = run_pass_0b(dr2, run_pass_0a(dr2))

        for s1, s2 in zip(segs1, segs2):
            assert s1.title == s2.title


class TestPass0BErrorCases:
    def test_invalid_policy_raises_segmentation_policy_error(
        self, simple_paragraph_path: Path
    ):
        """Unrecognised policy name → SegmentationPolicyError (not silent fallback)."""
        _, decode_result = run_pass_0(simple_paragraph_path)
        source_specs = run_pass_0a(decode_result)
        with pytest.raises(SegmentationPolicyError):
            run_pass_0b(decode_result, source_specs, policy="invalid_policy_xyz")

    def test_default_policy_accepted(self, simple_paragraph_path: Path):
        """policy='default' → no error."""
        _, decode_result = run_pass_0(simple_paragraph_path)
        source_specs = run_pass_0a(decode_result)
        segments = run_pass_0b(decode_result, source_specs, policy="default")
        assert isinstance(segments, list)
