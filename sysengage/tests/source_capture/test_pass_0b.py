"""
Tests for Pass 0B — Source Capture.

Per Implementation Spec §8.3 verification criteria and §9 test fixtures.

Tests:
  - Happy path: >=1 Source for non-empty input
  - Byte preservation: source_text is verbatim from decoded input
  - Immutability: Source.source_text cannot be modified (frozen=True)
  - Determinism: same input + same segments → identical Source content
  - source_ids match canonical format S###
  - multi_section: 3 Sources with segment association
"""

from pathlib import Path

import pytest

from mechanisms.source_capture.pass_0_read_witness import run_pass_0
from mechanisms.source_capture.pass_0a_segment_construction import run_pass_0a
from mechanisms.source_capture.pass_0b_source_capture import run_pass_0b
from schemas.source import Source


class TestPass0BHappyPath:
    def test_simple_paragraph_produces_sources(self, simple_paragraph_path: Path):
        """1 Source produced for simple_paragraph.txt per §9.1.1."""
        _, dr = run_pass_0(simple_paragraph_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(dr, segs, input_material_ref=str(simple_paragraph_path))

        assert len(sources) >= 1

    def test_source_text_is_verbatim(self, simple_paragraph_path: Path):
        """Source.source_text verbatim from decoded input — no normalisation."""
        _, dr = run_pass_0(simple_paragraph_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(dr, segs, input_material_ref=str(simple_paragraph_path))

        full_text = dr.text
        for src in sources:
            assert src.source_text in full_text, (
                f"Source text not found verbatim in decoded input: {src.source_text!r}"
            )

    def test_source_text_non_empty(self, simple_paragraph_path: Path):
        _, dr = run_pass_0(simple_paragraph_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(dr, segs, input_material_ref=str(simple_paragraph_path))

        for src in sources:
            assert src.source_text.strip()

    def test_multi_section_produces_three_sources(self, multi_section_path: Path):
        """3 Sources (one per paragraph) per Implementation Spec §9.1.2."""
        _, dr = run_pass_0(multi_section_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(dr, segs, input_material_ref=str(multi_section_path))

        assert len(sources) == 3

    def test_multi_section_sources_have_segment_index(self, multi_section_path: Path):
        """All Sources in multi_section.md belong to a Segment."""
        _, dr = run_pass_0(multi_section_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(dr, segs, input_material_ref=str(multi_section_path))

        assert all(src.segment_spec_index is not None for src in sources)

    def test_single_short_statement_produces_one_source(
        self, single_short_statement_path: Path
    ):
        _, dr = run_pass_0(single_short_statement_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(
            dr, segs, input_material_ref=str(single_short_statement_path)
        )
        assert len(sources) == 1
        assert sources[0].source_text == "Hello"


class TestPass0BImmutability:
    """Source.source_text is immutable per LPM frozen=True enforcement."""

    def test_source_pydantic_model_frozen(self, simple_paragraph_path: Path):
        """
        Verify that a Source Pydantic model cannot be mutated after construction.
        Attempted mutation raises ValidationError (Pydantic v2 frozen model).
        This is the primary LPM byte-preservation enforcement.
        """
        _, dr = run_pass_0(simple_paragraph_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(dr, segs, input_material_ref=str(simple_paragraph_path))

        src_spec = sources[0]
        source = Source(
            source_id="S001",
            source_text=src_spec.source_text,
            segmentation_context=src_spec.segmentation_context,
            input_material_ref=str(simple_paragraph_path),
            project_id="TEST",
        )

        from pydantic import ValidationError

        with pytest.raises((ValidationError, TypeError, ValueError)):
            source.source_text = "MUTATED"


class TestPass0BDeterminism:
    def test_identical_source_texts_on_rerun(self, simple_paragraph_path: Path):
        _, dr1 = run_pass_0(simple_paragraph_path)
        segs1 = run_pass_0a(dr1)
        srcs1 = run_pass_0b(dr1, segs1, input_material_ref=str(simple_paragraph_path))

        _, dr2 = run_pass_0(simple_paragraph_path)
        segs2 = run_pass_0a(dr2)
        srcs2 = run_pass_0b(dr2, segs2, input_material_ref=str(simple_paragraph_path))

        assert len(srcs1) == len(srcs2)
        for s1, s2 in zip(srcs1, srcs2):
            assert s1.source_text == s2.source_text
