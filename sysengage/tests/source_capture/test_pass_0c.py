"""
Tests for Pass 0C — SourceAtom Splitting.

Per Implementation Spec v0.4 §8.4 verification criteria and §9 test fixtures.

v1 default behaviour (produce_atoms_for_prose=False):
  Pass 0C is a no-op in v1. Default call always returns 0 atoms regardless of input.
  This is the canonical v1 behaviour per Implementation Spec v0.4 §4.4.3.

Non-default behaviour (produce_atoms_for_prose=True):
  Full splitting logic applied. Abbreviation handling still enforced.
  Reserved for future downstream mechanisms requiring sub-sentence anchors.

Tests (default, produce_atoms_for_prose=False):
  - Any input → 0 atoms always

Tests (non-default, produce_atoms_for_prose=True):
  - abbreviation_handling.txt: 3 atoms ("Dr. Smith works at Acme Inc." is atom 1,
    then "He is a clinician." is atom 2, then "Mr. Jones is the patient." is atom 3)
    Wait — abbreviation_handling.txt (NEW content) is now sentence-level Sources from Pass 0A:
    Source 1: "Dr. Smith works at Acme Inc."
    Source 2: " He is a clinician."
    Source 3: " Mr. Jones is the patient."
    With produce_atoms_for_prose=True, Pass 0C tries to sub-split each Source.
    "Dr. Smith works at Acme Inc." has no sub-sentence boundary → 0 atoms (zero-atom rule: no period
    followed by whitespace+capital within the source_text itself, since Inc. is the last word).
    Wait: "Dr. Smith works at Acme Inc." — the "." in "Dr." is protected (TITLE_ABBR). The "." at "Inc."
    → followed by end of string → no boundary. So 0 atoms from source 1.
    "He is a clinician." → no internal boundary → 0 atoms.
    "Mr. Jones is the patient." → "Mr." protected, "patient." at end → 0 atoms.
    Hmm, actually with the zero-atom rule: source_text must have terminal punctuation for atoms.
    "Dr. Smith works at Acme Inc." → has "." → check: any sentence boundary? No (Inc. is end) → 0 atoms.
    So with produce_atoms_for_prose=True and the new sentence-level fixture, 0 atoms total.
    This is correct — each Source IS already a sentence, so no sub-splitting occurs.
  - simple_paragraph: with old 3-sentence paragraph → 1 Source → 0 atoms (single sentence, no boundaries)
    Actually with the NEW simple_paragraph.txt (4 sentences → 4 Sources), each Source is a sentence.
    Sub-splitting each sentence: no internal boundaries → 0 atoms per Source → 0 total.
  - single_short_statement: "Hello" → no terminal punctuation → zero-atom rule → 0 atoms
  - Position uniqueness: no two atoms share same position for one Source (when atoms exist)
  - Determinism
"""

from pathlib import Path

import pytest

from mechanisms.source_capture.pass_0_read_witness import run_pass_0
from mechanisms.source_capture.pass_0a_source_capture import run_pass_0a
from mechanisms.source_capture.pass_0c_source_atom_splitting import run_pass_0c


class TestPass0CDefaultNoOp:
    """
    Default behaviour (produce_atoms_for_prose=False): always 0 atoms.
    This is the canonical v1 default per Implementation Spec v0.4 §4.4.3.
    """

    def test_simple_paragraph_default_produces_zero_atoms(
        self, simple_paragraph_path: Path
    ):
        """Default call on simple_paragraph.txt → 0 atoms."""
        _, dr = run_pass_0(simple_paragraph_path)
        source_specs = run_pass_0a(dr)
        atoms = run_pass_0c(source_specs)

        assert len(atoms) == 0

    def test_multi_section_default_produces_zero_atoms(
        self, multi_section_path: Path
    ):
        """Default call on multi_section.md → 0 atoms."""
        _, dr = run_pass_0(multi_section_path)
        source_specs = run_pass_0a(dr)
        atoms = run_pass_0c(source_specs)

        assert len(atoms) == 0

    def test_abbreviation_default_produces_zero_atoms(
        self, abbreviation_path: Path
    ):
        """Default call on abbreviation_handling.txt → 0 atoms."""
        _, dr = run_pass_0(abbreviation_path)
        source_specs = run_pass_0a(dr)
        atoms = run_pass_0c(source_specs)

        assert len(atoms) == 0

    def test_single_short_statement_default_produces_zero_atoms(
        self, single_short_statement_path: Path
    ):
        """Default call on single_short_statement.txt → 0 atoms."""
        _, dr = run_pass_0(single_short_statement_path)
        source_specs = run_pass_0a(dr)
        atoms = run_pass_0c(source_specs)

        assert len(atoms) == 0

    def test_empty_source_specs_produces_zero_atoms(self):
        """Empty source_specs → 0 atoms (no-op, no error)."""
        atoms = run_pass_0c([])

        assert len(atoms) == 0


class TestPass0CWithAtomSplitting:
    """
    Non-default behaviour (produce_atoms_for_prose=True).
    Full splitting logic; reserved for future downstream mechanisms.
    """

    def test_single_short_statement_zero_atoms_with_splitting(
        self, single_short_statement_path: Path
    ):
        """
        'Hello' has no terminal punctuation → zero-atom rule → 0 atoms
        even with produce_atoms_for_prose=True.
        """
        _, dr = run_pass_0(single_short_statement_path)
        source_specs = run_pass_0a(dr)
        atoms = run_pass_0c(source_specs, produce_atoms_for_prose=True)

        assert len(atoms) == 0

    def test_sentence_level_sources_produce_zero_atoms(
        self, simple_paragraph_path: Path
    ):
        """
        When Sources are already sentence-level (from Pass 0A), sub-splitting
        them with produce_atoms_for_prose=True yields 0 atoms — each Source
        has no internal sentence boundary.
        """
        _, dr = run_pass_0(simple_paragraph_path)
        source_specs = run_pass_0a(dr)
        atoms = run_pass_0c(source_specs, produce_atoms_for_prose=True)

        assert len(atoms) == 0

    def test_atom_text_is_subset_of_source_text(
        self, multi_section_path: Path
    ):
        """
        If atoms are produced: atom_text bytes are verbatim subset of
        parent Source spec's source_text per LPM invariant.
        """
        _, dr = run_pass_0(multi_section_path)
        source_specs = run_pass_0a(dr)
        atoms = run_pass_0c(source_specs, produce_atoms_for_prose=True)

        for atom in atoms:
            parent_text = source_specs[atom.source_spec_index].source_text
            assert atom.atom_text.strip() in parent_text, (
                f"Atom text {atom.atom_text!r} not found in parent source text {parent_text!r}"
            )

    def test_source_spec_index_is_valid(self, simple_paragraph_path: Path):
        """
        source_spec_index on each AtomSpec references a valid index in source_specs.
        """
        _, dr = run_pass_0(simple_paragraph_path)
        source_specs = run_pass_0a(dr)
        atoms = run_pass_0c(source_specs, produce_atoms_for_prose=True)

        n = len(source_specs)
        for atom in atoms:
            assert 0 <= atom.source_spec_index < n, (
                f"source_spec_index {atom.source_spec_index} out of range [0, {n})"
            )


class TestPass0CPositionUniqueness:
    def test_no_duplicate_positions_per_source(self, multi_section_path: Path):
        """Position uniqueness: no two atoms share same position for one Source."""
        _, dr = run_pass_0(multi_section_path)
        source_specs = run_pass_0a(dr)
        atoms = run_pass_0c(source_specs, produce_atoms_for_prose=True)

        from collections import defaultdict
        positions_by_source: dict[int, list[int]] = defaultdict(list)
        for atom in atoms:
            positions_by_source[atom.source_spec_index].append(atom.position)

        for src_idx, positions in positions_by_source.items():
            assert len(positions) == len(set(positions)), (
                f"Duplicate positions for source_spec_index {src_idx}: {positions}"
            )


class TestPass0CDeterminism:
    def test_default_always_returns_empty(self, simple_paragraph_path: Path):
        """Default mode is deterministically 0 atoms on any run."""
        _, dr = run_pass_0(simple_paragraph_path)
        source_specs = run_pass_0a(dr)

        atoms1 = run_pass_0c(source_specs)
        atoms2 = run_pass_0c(source_specs)

        assert len(atoms1) == 0
        assert len(atoms2) == 0

    def test_identical_atom_content_on_rerun_with_splitting(
        self, multi_section_path: Path
    ):
        """
        With produce_atoms_for_prose=True: same input → identical atom content.
        """
        _, dr1 = run_pass_0(multi_section_path)
        specs1 = run_pass_0a(dr1)
        atoms1 = run_pass_0c(specs1, produce_atoms_for_prose=True)

        _, dr2 = run_pass_0(multi_section_path)
        specs2 = run_pass_0a(dr2)
        atoms2 = run_pass_0c(specs2, produce_atoms_for_prose=True)

        assert len(atoms1) == len(atoms2)
        for a1, a2 in zip(atoms1, atoms2):
            assert a1.atom_text == a2.atom_text
            assert a1.position == a2.position
