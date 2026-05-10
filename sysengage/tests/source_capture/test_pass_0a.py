"""
Tests for Pass 0A — Segment Construction.

Per Implementation Spec §8.2 verification criteria and §9 test fixtures.

Tests:
  - Happy path: 0 Segments for plain text (no structure)
  - Happy path: 2 Segments for multi_section.md (H2 headings)
  - Determinism: same input + same policy → identical Segment count and descriptions
  - Error case: invalid policy → SegmentationPolicyError
  - Edge case: single-document input with no structure → empty list (not error)
"""

from pathlib import Path

import pytest

from mechanisms.source_capture.errors import SegmentationPolicyError
from mechanisms.source_capture.pass_0_read_witness import run_pass_0
from mechanisms.source_capture.pass_0a_segment_construction import run_pass_0a


class TestPass0AHappyPath:
    def test_plain_text_produces_zero_segments(self, simple_paragraph_path: Path):
        """Plain text has no structural markers → 0 Segments (not an error)."""
        _, decode_result = run_pass_0(simple_paragraph_path)
        segments = run_pass_0a(decode_result)
        assert segments == []

    def test_multi_section_md_produces_two_segments(self, multi_section_path: Path):
        """Two ## headings → 2 Segments per Implementation Spec §9.1.2."""
        _, decode_result = run_pass_0(multi_section_path)
        segments = run_pass_0a(decode_result)

        assert len(segments) == 2

    def test_segment_titles_match_headings(self, multi_section_path: Path):
        _, decode_result = run_pass_0(multi_section_path)
        segments = run_pass_0a(decode_result)

        titles = [s.title for s in segments]
        assert "Section One" in titles
        assert "Section Two" in titles

    def test_segments_have_description(self, multi_section_path: Path):
        _, decode_result = run_pass_0(multi_section_path)
        segments = run_pass_0a(decode_result)

        for seg in segments:
            assert seg.description is not None
            assert len(seg.description) > 0

    def test_single_short_statement_zero_segments(
        self, single_short_statement_path: Path
    ):
        _, decode_result = run_pass_0(single_short_statement_path)
        segments = run_pass_0a(decode_result)
        assert segments == []

    def test_docx_produces_segments_by_heading(
        self, simple_requirements_docx: Path
    ):
        """Docx with Heading styles → Segments per Implementation Spec §9.1.3."""
        _, decode_result = run_pass_0(simple_requirements_docx)
        segments = run_pass_0a(decode_result)
        # The generated docx has 2 H2 sections + 1 H1 title
        assert len(segments) >= 2


class TestPass0ADeterminism:
    """Determinism: same input + same policy → identical Segment count and descriptions."""

    def test_identical_segment_count_on_rerun(self, multi_section_path: Path):
        _, dr1 = run_pass_0(multi_section_path)
        segs1 = run_pass_0a(dr1)

        _, dr2 = run_pass_0(multi_section_path)
        segs2 = run_pass_0a(dr2)

        assert len(segs1) == len(segs2)

    def test_identical_titles_on_rerun(self, multi_section_path: Path):
        _, dr1 = run_pass_0(multi_section_path)
        segs1 = run_pass_0a(dr1)

        _, dr2 = run_pass_0(multi_section_path)
        segs2 = run_pass_0a(dr2)

        for s1, s2 in zip(segs1, segs2):
            assert s1.title == s2.title


class TestPass0AErrorCases:
    def test_invalid_policy_raises_segmentation_policy_error(
        self, simple_paragraph_path: Path
    ):
        _, decode_result = run_pass_0(simple_paragraph_path)
        with pytest.raises(SegmentationPolicyError):
            run_pass_0a(decode_result, policy="invalid_policy_xyz")
