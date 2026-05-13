"""
Pass 0B — Segment Construction.

Per Implementation Spec v0.4 §4.3 and Row 4 Applied §9.

Mode: LPM — structural marker detection only; no content interpretation.

What this Pass does:
  1. Receives SourceSpecs (with section_index) from Pass 0A.
  2. Scans decoded character stream for structural markers (headings).
  3. For each heading section that contains Sources: creates one SegmentSpec
     with title (from heading text), description, and source_spec_indices
     (ordered indices into the source_specs list from Pass 0A).
  4. Returns list of SegmentSpec (zero if no structural markers found).

The canonical Segment → Source relation (v2.11):
  Segment.source_refs lists the source_ids of all Sources in that section.
  Source has NO back-reference to Segment (segment_id removed per F24).
  The orchestrator reads SegmentSpec.source_spec_indices, resolves them to
  the assigned Source IDs, and writes Segment.source_refs accordingly.

Non-Empty-Segment rule (Implementation Spec v0.4 §4.3.2):
  Only heading sections with at least one Source get a Segment. Empty heading
  sections (heading with no body content, or body that produced 0 Sources)
  do NOT produce a Segment.

Plain text inputs (fmt starts with "txt"): zero Segments always returned.

Visually-styled headings deliberately not detected per F27 / Row 4 v0.5 §4.3.5;
future evolution gated on Path A spec amendment. Only genuine structural markers
(Word Heading styles, Markdown #/##, PDF outline entries) produce Segments.

Verification criteria per Implementation Spec v0.4 §8.3:
  - Zero or more Segments returned.
  - Each Segment has non-empty title and description.
  - source_spec_indices non-empty (Non-Empty-Segment rule).
  - source_spec_indices reference valid indices in source_specs list.
  - simple_paragraph.txt: 0 Segments (plain text, no headings).
  - multi_section.md: 2 Segments (Section One, Section Two).
  - Determinism: same input + same Sources → identical Segment count and titles.
"""

import re
from dataclasses import dataclass, field

from core.modes import pass_mode
from mechanisms.source_capture.decoders import DecodeResult
from mechanisms.source_capture.errors import SegmentationPolicyError
from mechanisms.source_capture.pass_0a_source_capture import SourceSpec


@dataclass
class SegmentSpec:
    """
    Intermediate Segment specification produced by Pass 0B.
    Not yet a canonical Segment (no ID). ID assigned at ledger write.

    source_spec_indices: ordered indices into the source_specs list from Pass 0A.
    The orchestrator maps these to assigned Source IDs for Segment.source_refs.
    """

    title: str
    description: str | None
    source_spec_indices: list[int] = field(default_factory=list)


@pass_mode("LPM")
def run_pass_0b(
    decode_result: DecodeResult,
    source_specs: list[SourceSpec],
    *,
    policy: str = "default",
) -> list[SegmentSpec]:
    """
    Execute Pass 0B Segment Construction.

    Args:
        decode_result: DecodeResult from Pass 0. Used to scan for headings.
        source_specs: SourceSpecs from Pass 0A (with section_index populated).
        policy: Segmentation policy. Only "default" supported in v1.

    Returns:
        List of SegmentSpec (may be empty if no structural markers found,
        or all heading sections contain no Sources).

    Raises:
        SegmentationPolicyError: if policy name is unrecognised.
    """
    if policy != "default":
        raise SegmentationPolicyError(
            f"Unrecognised segmentation policy: {policy!r}. "
            "Only 'default' is supported in v1."
        )

    fmt = decode_result.format_detected

    if fmt.startswith("txt"):
        return []

    headings = _extract_headings(decode_result.text)

    if not headings:
        return []

    return _build_segment_specs(headings, source_specs)


def _extract_headings(text: str) -> list[tuple[int, str]]:
    """
    Extract heading titles from structured text in document order.

    Returns list of (section_index, title) tuples. section_index matches
    the 0-based index assigned by Pass 0A: first heading → 0, second → 1, etc.
    """
    headings: list[tuple[int, str]] = []
    section_index = 0

    for line in text.split("\n"):
        m = re.match(r"^#{1,6}\s+(.+)$", line)
        if m:
            heading_text = m.group(1).strip()
            headings.append((section_index, heading_text))
            section_index += 1

    return headings


def _build_segment_specs(
    headings: list[tuple[int, str]],
    source_specs: list[SourceSpec],
) -> list[SegmentSpec]:
    """
    Build SegmentSpec list by matching Sources to their heading section.

    For each heading, collects source_specs whose section_index matches.
    Only creates a Segment if at least one Source belongs to that section
    (Non-Empty-Segment rule per Implementation Spec v0.4 §4.3.2).

    Per v0.7 §4.3.2 (F32): the heading Source (is_heading=True) is placed at
    position 0 of source_spec_indices. Pass 0A already emits heading Sources
    before body Sources so this is guaranteed by list order; the explicit sort
    makes it contract-level and robust to future reordering.
    """
    section_to_source_indices: dict[int, list[int]] = {}
    for src_idx, src_spec in enumerate(source_specs):
        if src_spec.section_index is not None:
            section_to_source_indices.setdefault(src_spec.section_index, []).append(src_idx)

    segment_specs: list[SegmentSpec] = []

    for section_index, title in headings:
        indices = section_to_source_indices.get(section_index, [])
        if not indices:
            continue

        # Guarantee heading Source at position 0 per v0.7 §4.3.2.
        sorted_indices = sorted(
            indices,
            key=lambda i: (0 if source_specs[i].is_heading else 1, i),
        )

        segment_specs.append(SegmentSpec(
            title=title,
            description=f"Section: {title}",
            source_spec_indices=sorted_indices,
        ))

    return segment_specs
