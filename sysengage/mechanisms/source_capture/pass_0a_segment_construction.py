"""
Pass 0A — Segment Construction.

Per Implementation Spec §4.2 and Row 4 Applied §9.

Mode: LPM — structural marker detection only; no content interpretation.

What this Pass does:
  1. Scans decoded character stream for structural markers per Segmentation policy.
  2. Per detected boundary, decides whether bounded content warrants a Segment.
  3. Returns list of SegmentSpec dicts (intermediate; not yet assigned IDs).

Default policy markers (per Implementation Spec §4.2.2):
  - Markdown: # or ## headings
  - .docx: lines starting with # or ## (added by decoder for Heading styles)
  - .pdf: double-newline boundaries (no heading info available from pypdf)

Default policy edge case per Row 2 v1.1 §3.9.1:
  "When ambiguous, include a Segment."

Single-document input with no internal structure: zero Segments produced (not an error).

Verification criteria per Implementation Spec §8.2:
  - Zero or more Segments returned
  - Each Segment has description (structural marker text) and content range
  - Determinism: same input + same policy → identical Segment count and descriptions
"""

import re
from dataclasses import dataclass, field
from typing import Any

from core.modes import pass_mode
from mechanisms.source_capture.decoders import DecodeResult
from mechanisms.source_capture.errors import SegmentationPolicyError

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


@dataclass
class SegmentSpec:
    """
    Intermediate Segment specification produced by Pass 0A.
    Not yet a canonical Segment (no ID assigned). ID assigned at ledger write.
    """

    title: str
    description: str | None
    line_start: int
    line_end: int | None = None
    content_lines: list[str] = field(default_factory=list)


@pass_mode("LPM")
def run_pass_0a(
    decode_result: DecodeResult,
    *,
    policy: str = "default",
) -> list[SegmentSpec]:
    """
    Execute Pass 0A Segment Construction.

    Args:
        decode_result: DecodeResult from Pass 0.
        policy: Segmentation policy name. Only "default" supported for v1.

    Returns:
        List of SegmentSpec (may be empty for single-document with no structure).

    Raises:
        SegmentationPolicyError: if policy name is unrecognised.
    """
    if policy != "default":
        raise SegmentationPolicyError(
            f"Unrecognised segmentation policy: {policy!r}. "
            "Only 'default' is supported in v1."
        )

    text = decode_result.text
    fmt = decode_result.format_detected

    if fmt in ("txt", "txt-fallback", "txt-fallback-from-.xyz") or fmt.startswith("txt-fallback"):
        # Plain text: no structural markers → zero Segments
        return []

    lines = text.splitlines(keepends=False)

    if fmt in ("md", "docx"):
        return _segment_by_headings(lines)
    elif fmt == "pdf":
        return _segment_by_headings(lines)
    else:
        # Unknown format post-decode: apply heading detection as best-effort
        return _segment_by_headings(lines)


def _segment_by_headings(lines: list[str]) -> list[SegmentSpec]:
    """
    Segment a character stream by heading markers (# and ## prefix).

    For .docx: decoder converts Heading styles to # / ## prefixes.
    For .md: native # / ## headings.
    For plain text fallback: no headings → empty result.

    Per default policy edge case: when ambiguous, include Segment.
    """
    segments: list[SegmentSpec] = []
    current_segment: SegmentSpec | None = None

    for line_idx, line in enumerate(lines):
        m = HEADING_PATTERN.match(line)
        if m:
            # Finalise previous segment
            if current_segment is not None:
                current_segment.line_end = line_idx - 1
                segments.append(current_segment)

            heading_text = m.group(2).strip()
            current_segment = SegmentSpec(
                title=heading_text,
                description=f"Section: {heading_text}",
                line_start=line_idx,
                content_lines=[],
            )
        else:
            if current_segment is not None:
                current_segment.content_lines.append(line)

    if current_segment is not None:
        current_segment.line_end = len(lines) - 1
        segments.append(current_segment)

    return segments
