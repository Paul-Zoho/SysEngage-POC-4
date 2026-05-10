"""
Pass 0B — Source Capture.

Per Implementation Spec §4.3 and Row 4 Applied §9.

Mode: LPM — byte-for-byte verbatim content capture.

CRITICAL LPM INVARIANT: source_text bytes are byte-for-byte identical to
the corresponding portion of the decoded input stream. No normalisation,
no encoding transformation, no whitespace collapse beyond what the decoder
already performed. Implemented via Source Pydantic model with frozen=True —
any mutation attempt raises ValidationError (LPM violation).

What this Pass does:
  1. For each Segment (or the whole document if no Segments): identifies
     substantive content blocks (paragraphs or coherent text blocks).
  2. Per identified block: creates Source Pydantic record with verbatim content.
  3. Assigns segment_id (context_id) when Source belongs to a Segment.

Source identification heuristic (per Implementation Spec §4.3.2):
  - Input split by double-newline (paragraph boundary) as primary unit.
  - Empty blocks (whitespace only) are skipped.
  - Each non-empty block → one Source.

Verification criteria per Implementation Spec §8.3:
  - At least one Source produced for non-empty, successfully-decoded input.
  - Source.source_text is verbatim (byte-identical to decoded input portion).
  - Source.source_text cannot be modified post-creation (frozen=True).
  - Determinism: same input + same Segments → identical Source content.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from core.modes import pass_mode
from mechanisms.source_capture.decoders import DecodeResult
from mechanisms.source_capture.pass_0a_segment_construction import SegmentSpec

PARAGRAPH_BOUNDARY = re.compile(r"\n\n+")
HEADING_LINE = re.compile(r"^#{1,6}\s+.+$")


@dataclass
class SourceSpec:
    """
    Intermediate Source specification from Pass 0B.
    Not yet a canonical Source (no ID). IDs assigned at ledger write.
    """

    source_text: str
    segmentation_context: str
    segment_spec_index: int | None = None
    is_non_text: bool = False
    has_decoding_issues: bool = False


@pass_mode("LPM")
def run_pass_0b(
    decode_result: DecodeResult,
    segment_specs: list[SegmentSpec],
    *,
    input_material_ref: str,
) -> list[SourceSpec]:
    """
    Execute Pass 0B Source Capture.

    Args:
        decode_result: DecodeResult from Pass 0.
        segment_specs: Segment specifications from Pass 0A (may be empty).
        input_material_ref: file path / URI for the input artefact.

    Returns:
        List of SourceSpec (at least one for non-empty, successfully-decoded input).
    """
    text = decode_result.text
    has_decoding_issues = not decode_result.read_completion_status

    if segment_specs:
        return _capture_with_segments(text, segment_specs, has_decoding_issues)
    else:
        return _capture_without_segments(text, has_decoding_issues)


def _capture_without_segments(
    text: str,
    has_decoding_issues: bool,
) -> list[SourceSpec]:
    """
    Capture Sources from a document with no Segment structure.
    Split on paragraph boundaries (double newline).
    """
    blocks = PARAGRAPH_BOUNDARY.split(text)
    sources: list[SourceSpec] = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if HEADING_LINE.match(block):
            # Skip standalone heading lines with no content
            continue
        sources.append(
            SourceSpec(
                source_text=block,
                segmentation_context="paragraph",
                segment_spec_index=None,
                has_decoding_issues=has_decoding_issues,
            )
        )

    return sources


def _capture_with_segments(
    text: str,
    segment_specs: list[SegmentSpec],
    has_decoding_issues: bool,
) -> list[SourceSpec]:
    """
    Capture Sources within each Segment's content range.
    Each Segment's content lines are split on double-newline for paragraph Sources.
    """
    all_lines = text.splitlines(keepends=False)
    sources: list[SourceSpec] = []

    for seg_idx, seg in enumerate(segment_specs):
        # Join with double-newline so each content_line (one decoder paragraph) becomes
        # its own paragraph-separated block. Works for both docx (single \n between paras
        # from the decoder) and .md (already has blank lines as empty content_lines).
        content_text = "\n\n".join(seg.content_lines)
        blocks = PARAGRAPH_BOUNDARY.split(content_text)

        for block in blocks:
            block = block.strip()
            if not block:
                continue
            if HEADING_LINE.match(block):
                continue
            sources.append(
                SourceSpec(
                    source_text=block,
                    segmentation_context="section-content",
                    segment_spec_index=seg_idx,
                    has_decoding_issues=has_decoding_issues,
                )
            )

    # If no Sources produced within segments (all headings, no body),
    # fall back to whole-document capture per Non-Loss Principle.
    if not sources:
        sources = _capture_without_segments(text, has_decoding_issues)

    return sources
