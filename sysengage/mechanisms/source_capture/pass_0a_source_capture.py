"""
Pass 0A — Source Capture (sentence-level).

Per Implementation Spec v0.6 §4.2 and Row 4 Applied §9.

Mode: LPM — byte-for-byte verbatim content capture at sentence granularity.

CRITICAL LPM INVARIANT: source_text bytes are byte-for-byte identical to the
corresponding portion of the decoded input stream. No normalisation, no encoding
transformation, no whitespace collapse. For plain-text inputs, concatenating
all produced source_text values reproduces the original decoded text verbatim.

What this Pass does:
  1. Scans decoded character stream for sentence boundaries.
  2. For each sentence (or fragment without terminal punctuation): creates
     one SourceSpec with verbatim source_text.
  3. For structured formats (md/docx): pre-splits by heading lines so that
     heading-section membership is tracked via section_index (used by Pass 0B).
  4. segmentation_context populated via deterministic classifier per §4.2.5
     (F29/F31 resolution v0.6): one of "sentence in prose" / "bullet item" /
     "table row" / "definition line" / "multi-line block".

Sentence boundary detection (per Implementation Spec v0.6 §4.2.2):
  - Sentence ends at [.!?] followed by whitespace + capital letter (or open quote).
  - TITLE_ABBRS (Mr., Dr., Prof., etc.) NEVER trigger sentence splits — they
    always precede a name, not a new sentence.
  - Other abbreviations (Inc., Corp., Ltd.) CAN end sentences when the period is
    followed by whitespace + capital (dual-role: abbreviation dot = sentence period).
    Example: "Acme Inc. He..." → sentence boundary after "Inc." (F23 fix).
  - e.g. / i.e. patterns: both dots fully protected.
  - Single letter before period (e.g., 'e' in 'e.g.'): treated as abbreviation.
  - Text with no terminal punctuation → one Source for the whole text.

section_index on SourceSpec:
  None = plain text (no headings), or content before first heading.
  0, 1, 2, ... = ordinal index of the heading section this Source belongs to.
  Pass 0B reads section_index to assign Sources to Segments.

segmentation_context classifier (v0.6 §4.2.5 / F29 + F31):
  classify_segmentation_context() applies five rules in priority order:
    1. bullet item   — Pass 0 bullet-list marker (v1 stub, always False)
    2. table row     — Pass 0 table-row marker (v1 stub, always False)
    3. sentence in prose — contains [.!?], no embedded \\n (F31: moved up from v0.5 pos 4)
    4. definition line   — label:value, no terminator, no \\n (F31: moved down from v0.5 pos 3)
    5. multi-line block  — fallback
  Rule 3 now fires before Rule 4 so prose sentences with categorical label
  prefixes (e.g. "Customer focus: ...commitment...") classify correctly as prose.

Verification criteria per Implementation Spec v0.6 §8.2:
  - At least one Source produced for non-empty, successfully-decoded input.
  - Source.source_text verbatim (byte-identical to decoded input portion).
  - segmentation_context is classifier-derived (non-empty string).
  - Prose Sources → "sentence in prose"; metadata-only lines → "definition line";
    signature/attribution blocks → "multi-line block".
  - Determinism: same input → identical Source content, count, segmentation_context.
  - simple_paragraph.txt: exactly 4 Sources (F23 fix: sentence-level, not paragraph).
  - abbreviation_handling.txt: exactly 3 Sources, no false split on Dr./Inc./Mr.
  - very_long_sentence.txt: exactly 1 Source.
"""

import re
from dataclasses import dataclass

from core.modes import pass_mode
from mechanisms.source_capture.decoders import DecodeResult
from mechanisms.source_capture.errors import SegmentationPolicyError

HEADING_LINE_PATTERN = re.compile(r"^#{1,6}\s+.+$")

TITLE_ABBRS = frozenset({
    "Mr", "Mrs", "Ms", "Dr", "Prof", "Sr", "Jr", "St", "Gov",
    "Dept", "No", "Fig", "Gen", "Sgt", "Rep", "Sen", "Lt",
    "Col", "Cpl", "Pvt", "Cdr", "Maj", "Brig", "Capt",
})

EG_IE_PATTERN = re.compile(r"\b(e\.g|i\.e)\.", re.IGNORECASE)

DEFINITION_LINE_PATTERN = re.compile(
    r"^\s*[A-Za-z][A-Za-z\s]*\s*:\s*.+$",
    re.DOTALL,
)


@dataclass
class SourceSpec:
    """
    Intermediate Source specification produced by Pass 0A.
    Not yet a canonical Source (no ID). IDs assigned at ledger write.

    section_index: ordinal index of the heading section this sentence belongs
    to (0-based). None for plain-text inputs (no heading structure). Pass 0B
    reads this to group Sources into Segments without re-scanning the text.
    """

    source_text: str
    segmentation_context: str = "sentence in prose"
    section_index: int | None = None
    is_non_text: bool = False
    has_decoding_issues: bool = False


def classify_segmentation_context(
    source_text: str,
    *,
    has_bullet_marker: bool = False,
    has_table_marker: bool = False,
) -> str:
    """
    Deterministic segmentation_context classifier per v0.6 §4.2.5 (F29/F31 resolution).

    Applies five rules in priority order; first matching rule wins.

    Rule 1 — bullet item:
        Pass 0 surfaced a bullet-list structural marker for this Source.
        In v1, has_bullet_marker is always False (decoders not yet extended).

    Rule 2 — table row:
        Pass 0 surfaced a table-row structural marker for this Source.
        In v1, has_table_marker is always False (decoders not yet extended).

    Rule 3 — sentence in prose (F31: moved up from position 4):
        source_text contains a sentence terminator (.!?) and no embedded
        newlines. This fires BEFORE the definition-line check so that prose
        sentences with categorical label prefixes (e.g. "Customer focus: As an
        organisation we have made a commitment to understand our current and
        future customers' needs...") are correctly classified as prose, not
        as definition lines.

    Rule 4 — definition line (F31: moved down from position 3):
        source_text is a SINGLE logical line (no embedded newlines) matching
        the pattern: alphabetic label + optional spaces + colon + value, AND
        has no sentence terminator (Rule 3 would have caught it otherwise).
        Example: "Date: 22/4/2025", "Owner : Damian Shacklock", "Title: Director".

    Rule 5 — multi-line block (fallback):
        Source spans multiple lines without sentence punctuation, or is a
        structured non-prose block (signature blocks, attribution blocks,
        address blocks). Conservative fallback per §4.2.5 bias guidance.

    Args:
        source_text: verbatim source_text of the captured Source.
        has_bullet_marker: True when Pass 0 flagged this Source as from a
            bulleted list. Always False in v1.
        has_table_marker: True when Pass 0 flagged this Source as from a
            table row. Always False in v1.

    Returns:
        One of: "bullet item", "table row", "sentence in prose",
                "definition line", "multi-line block".
    """
    if has_bullet_marker:
        return "bullet item"

    if has_table_marker:
        return "table row"

    # Strip leading/trailing whitespace (including leading \n from sentence splits)
    # before newline checks. An embedded \n — e.g. "Line one\nLine two" — survives
    # strip() and still triggers the multi-line block fallback. Only boundary
    # whitespace from the split algorithm is dropped; genuine block structure is kept.
    text_core = source_text.strip()

    if re.search(r"[.!?]", text_core) and "\n" not in text_core:
        return "sentence in prose"

    if "\n" not in text_core and DEFINITION_LINE_PATTERN.match(text_core):
        return "definition line"

    return "multi-line block"


@pass_mode("LPM")
def run_pass_0a(
    decode_result: DecodeResult,
    *,
    policy: str = "default",
) -> list[SourceSpec]:
    """
    Execute Pass 0A Source Capture (sentence-level).

    Args:
        decode_result: DecodeResult from Pass 0.
        policy: Segmentation policy. Only "default" supported in v1.

    Returns:
        List of SourceSpec — one per sentence-level unit.

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
    has_decoding_issues = not decode_result.read_completion_status

    if not text.strip():
        return []

    if fmt.startswith("txt"):
        return _split_plain_text(text, has_decoding_issues)

    sources = _split_structured_text(text, has_decoding_issues)
    if not sources:
        return _split_plain_text(text, has_decoding_issues)
    return sources


def _split_plain_text(text: str, has_decoding_issues: bool) -> list[SourceSpec]:
    """
    Split plain text into sentence-level Sources preserving all whitespace.

    Byte-preservation invariant: concatenating all source_text values
    reproduces the original decoded text verbatim (no stripping).
    """
    boundaries = _find_sentence_boundaries(text)
    chunks = _split_at_boundaries(text, boundaries)

    sources: list[SourceSpec] = []
    for chunk in chunks:
        if chunk.strip():
            sources.append(SourceSpec(
                source_text=chunk,
                segmentation_context=classify_segmentation_context(chunk),
                section_index=None,
                has_decoding_issues=has_decoding_issues,
            ))

    return sources


def _split_structured_text(text: str, has_decoding_issues: bool) -> list[SourceSpec]:
    """
    Split structured text (md/docx/pdf) into sentence-level Sources.

    Headings are NOT captured as Sources — they become Segment titles in Pass 0B.
    Each Source carries section_index indicating which heading section it belongs to.
    Structural whitespace (blank lines between heading and content) is stripped.
    """
    lines = text.split("\n")
    sources: list[SourceSpec] = []
    section_index = -1
    current_section_lines: list[str] = []
    found_heading = False

    for line in lines:
        if HEADING_LINE_PATTERN.match(line):
            if found_heading and current_section_lines:
                section_text = "\n".join(current_section_lines)
                section_sources = _split_section_content(
                    section_text, section_index, has_decoding_issues
                )
                sources.extend(section_sources)
            section_index += 1
            found_heading = True
            current_section_lines = []
        else:
            if found_heading:
                current_section_lines.append(line)

    if found_heading and current_section_lines:
        section_text = "\n".join(current_section_lines)
        section_sources = _split_section_content(
            section_text, section_index, has_decoding_issues
        )
        sources.extend(section_sources)

    if not found_heading:
        return []

    return sources


def _split_section_content(
    section_text: str,
    section_index: int,
    has_decoding_issues: bool,
) -> list[SourceSpec]:
    """
    Sentence-split one heading section's content.

    For structured documents: strip leading newlines (paragraph separators)
    and trailing whitespace from each sentence-chunk so Sources contain
    only prose. Leading space within a sentence (from ". " separator) is kept.
    """
    boundaries = _find_sentence_boundaries(section_text)
    chunks = _split_at_boundaries(section_text, boundaries)

    sources: list[SourceSpec] = []
    for chunk in chunks:
        stripped = chunk.lstrip("\n").rstrip()
        if stripped:
            sources.append(SourceSpec(
                source_text=stripped,
                segmentation_context=classify_segmentation_context(stripped),
                section_index=section_index,
                has_decoding_issues=has_decoding_issues,
            ))

    return sources


def _find_sentence_boundaries(text: str) -> list[int]:
    """
    Return list of character positions immediately AFTER each sentence-ending
    punctuation mark. Each position is where the next sentence starts.

    Title abbreviation handling:
      Words in TITLE_ABBRS (Dr, Mr, Prof, ...) before a period are NEVER sentence
      boundaries — they always precede a proper name, not a new sentence.

    End-of-sentence for other abbreviations:
      Words NOT in TITLE_ABBRS before a period CAN be sentence-ending even if
      the word is also used as an abbreviation (e.g., "Inc." at end of sentence).
      This dual-role is intentional: abbreviation dot = sentence dot.

    Single-letter word protection:
      A period after a single letter (e.g., 'e' in 'e.g.') is not a boundary.
      e.g./i.e. patterns have ALL dots protected via EG_IE_PATTERN.

    Boundary condition: the period must be followed by whitespace + uppercase
    letter or open-quote/bracket for the boundary to be recognised.
    """
    n = len(text)

    protected_dot_positions: set[int] = set()
    for m in EG_IE_PATTERN.finditer(text):
        for i in range(m.start(), m.end()):
            if text[i] == ".":
                protected_dot_positions.add(i)

    boundaries: list[int] = []

    for i in range(n):
        ch = text[i]
        if ch not in ".!?":
            continue

        if ch == "." and i in protected_dot_positions:
            continue

        if ch == ".":
            word_start = i - 1
            while word_start >= 0 and text[word_start].isalpha():
                word_start -= 1
            word_start += 1
            word_before = text[word_start:i]

            if word_before in TITLE_ABBRS:
                continue

            if len(word_before) == 1:
                continue

        j = i + 1
        while j < n and text[j] in " \t\r\n":
            j += 1

        if j < n and (text[j].isupper() or text[j] in "\"'(["):
            boundaries.append(i + 1)

    return boundaries


def _split_at_boundaries(text: str, boundaries: list[int]) -> list[str]:
    """
    Split text at boundary positions into verbatim chunks.

    Each boundary is the index where the next sentence begins (just after
    the terminal punctuation). No modification of the original text bytes.
    Concatenating all returned chunks reproduces the input exactly.
    """
    if not boundaries:
        return [text]

    chunks: list[str] = []
    prev = 0
    for b in boundaries:
        chunk = text[prev:b]
        chunks.append(chunk)
        prev = b

    remaining = text[prev:]
    if remaining.strip():
        chunks.append(remaining)

    return chunks
