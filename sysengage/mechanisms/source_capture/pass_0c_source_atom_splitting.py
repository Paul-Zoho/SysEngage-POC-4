"""
Pass 0C — SourceAtom Splitting.

Per Implementation Spec §4.4 and Row 4 Applied §9.

Mode: LPM — mechanical splitting only; no semantic interpretation.

What this Pass does:
  1. Per Source: applies SourceAtom granularity rules (sentence boundaries
     for prose, line boundaries for structured text).
  2. Handles known false-positive abbreviation patterns (per §4.4.2):
     Mr., Dr., Inc., e.g., i.e., etc. do not trigger sentence splits.
  3. Decimal points within numbers do not trigger splits.
  4. Per atom: creates SourceAtom with verbatim subset of parent Source.source_text.

Default granularity rules (per Implementation Spec §4.4.1):
  - Prose: sentence-end punctuation (. ! ?) followed by whitespace + capital.
  - Structured (newline-delimited): line boundaries.
  - Enumerated: list-item boundaries.

Abbreviation handling strategy:
  Replace known abbreviation dots with a placeholder BEFORE splitting,
  split on remaining punctuation, then restore placeholders. This avoids
  Python re lookbehind fixed-width restrictions entirely.

Verification criteria per Implementation Spec §8.4:
  - atom_text bytes are subset of parent Source.source_text.
  - Position uniqueness: no two atoms share same position for one Source.
  - Determinism: same Source + same rules → identical atom content and positions.
  - Edge case: Source with no atom boundaries → zero atoms produced (not error).
"""

import re
from dataclasses import dataclass

from core.modes import pass_mode
from mechanisms.source_capture.pass_0b_source_capture import SourceSpec

ABBREVIATION_PATTERN = re.compile(
    r"\b(Mr|Dr|Prof|Sr|Jr|Mrs|Ms|St|vs|etc|Inc|Ltd|Corp|Co)\.",
    re.IGNORECASE,
)

EG_IE_PATTERN = re.compile(r"\b(e\.g|i\.e)\.", re.IGNORECASE)

NUMBER_DECIMAL = re.compile(r"(\d)\.(\d)")

SENTENCE_SPLIT = re.compile(r"([.!?])(\s+(?=[A-Z\"\'\(]))")

LIST_ITEM_PATTERN = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)

ABBR_PLACEHOLDER = "\x00ABBR\x00"
DECIMAL_PLACEHOLDER = "\x00DEC\x00"


@dataclass
class AtomSpec:
    """Intermediate SourceAtom specification from Pass 0C. No ID yet."""

    atom_text: str
    position: int
    source_spec_index: int


@pass_mode("LPM")
def run_pass_0c(
    source_specs: list[SourceSpec],
) -> list[AtomSpec]:
    """
    Execute Pass 0C SourceAtom Splitting.

    Args:
        source_specs: List of SourceSpec from Pass 0B.

    Returns:
        List of AtomSpec across all Sources. Empty list if no atom boundaries found.
    """
    all_atoms: list[AtomSpec] = []

    for src_idx, source_spec in enumerate(source_specs):
        atoms = _split_source(source_spec.source_text, src_idx)
        all_atoms.extend(atoms)

    return all_atoms


def _split_source(source_text: str, source_index: int) -> list[AtomSpec]:
    """
    Split one Source's text into atomic units.

    Zero-atom rule (Implementation Spec §9.2.2):
    If the text contains no sentence-ending punctuation (. ! ?) at all,
    it is a bare fragment — no sentence boundaries exist — return 0 atoms.
    "Hello" → 0 atoms; "Second paragraph." → 1 atom.

    Detection order:
    1. If text has no sentence-ending punctuation → 0 atoms.
    2. If text has list-item markers → split on list items.
    3. If text has multiple lines and no sentence punctuation inline → split on lines.
    4. Otherwise → split on sentence boundaries.
    """
    stripped = source_text.strip()
    if not stripped:
        return []

    if not re.search(r"[.!?]", stripped):
        return []

    if LIST_ITEM_PATTERN.search(stripped):
        raw_atoms = _split_list_items(stripped)
    elif "\n" in stripped and not re.search(r"[.!?]\s", stripped):
        raw_atoms = _split_lines(stripped)
    else:
        raw_atoms = _split_sentences(stripped)

    atoms = []
    position = 0
    for text in raw_atoms:
        if text and text.strip():
            atoms.append(
                AtomSpec(
                    atom_text=text,
                    position=position,
                    source_spec_index=source_index,
                )
            )
            position += 1

    return atoms


def _split_sentences(text: str) -> list[str]:
    """
    Split text on sentence boundaries using placeholder strategy.

    Abbreviation handling (Implementation Spec §4.4.2):
    1. Replace abbreviation dots with ABBR_PLACEHOLDER.
    2. Replace decimal dots with DECIMAL_PLACEHOLDER.
    3. Split on remaining [.!?] + whitespace + capital-letter boundary.
    4. Restore placeholders.

    Returns list of sentence strings. If no splits found, returns [text].
    """
    protected = ABBREVIATION_PATTERN.sub(
        lambda m: m.group(0).replace(".", ABBR_PLACEHOLDER), text
    )
    protected = EG_IE_PATTERN.sub(
        lambda m: m.group(0).replace(".", ABBR_PLACEHOLDER), protected
    )
    protected = NUMBER_DECIMAL.sub(
        lambda m: m.group(1) + DECIMAL_PLACEHOLDER + m.group(2), protected
    )

    parts: list[str] = []
    last = 0

    for m in SENTENCE_SPLIT.finditer(protected):
        end_of_punct = m.start(2)
        chunk = protected[last : m.end(1)]
        parts.append(chunk)
        last = m.start(2)

    remainder = protected[last:]
    if remainder.strip():
        parts.append(remainder)

    if len(parts) <= 1:
        return [text]

    restored = [
        p.replace(ABBR_PLACEHOLDER, ".").replace(DECIMAL_PLACEHOLDER, ".")
        for p in parts
    ]

    return restored


def _split_lines(text: str) -> list[str]:
    """Split on line boundaries for structured text."""
    return [line for line in text.splitlines() if line.strip()]


def _split_list_items(text: str) -> list[str]:
    """Split on list-item markers (-, *, •) for enumerated content."""
    items = LIST_ITEM_PATTERN.split(text)
    return [item.strip() for item in items if item and item.strip()]
