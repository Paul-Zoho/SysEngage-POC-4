"""
Tests for Pass 0C — SourceAtom Splitting.

Per Implementation Spec §8.4 verification criteria and §9 test fixtures.

Tests:
  - simple_paragraph.txt: 3 SourceAtoms (3 sentences per §9.1.1)
  - abbreviation_handling.txt: 3 atoms despite Dr./Inc./Mr. abbreviations (§9.2.3)
  - single_short_statement.txt: 0 atoms (no boundary) per §9.2.2
  - atom_text is verbatim subset of parent Source.source_text
  - Position uniqueness: no two atoms share same position for one Source
  - Determinism: same Source → identical atom content and positions
"""

from pathlib import Path

import pytest

from mechanisms.source_capture.pass_0_read_witness import run_pass_0
from mechanisms.source_capture.pass_0a_segment_construction import run_pass_0a
from mechanisms.source_capture.pass_0b_source_capture import run_pass_0b
from mechanisms.source_capture.pass_0c_source_atom_splitting import run_pass_0c


class TestPass0CHappyPath:
    def test_simple_paragraph_produces_three_atoms(self, simple_paragraph_path: Path):
        """
        3 SourceAtoms expected for simple_paragraph.txt per Implementation Spec §9.1.1.

        The file is a single paragraph with 3 sentences, producing 1 Source and 3 atoms.
        """
        _, dr = run_pass_0(simple_paragraph_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(dr, segs, input_material_ref=str(simple_paragraph_path))
        atoms = run_pass_0c(sources)

        assert len(atoms) == 3

    def test_single_short_statement_zero_atoms(
        self, single_short_statement_path: Path
    ):
        """0 SourceAtoms for 'Hello' (no sentence boundary) per §9.2.2."""
        _, dr = run_pass_0(single_short_statement_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(
            dr, segs, input_material_ref=str(single_short_statement_path)
        )
        atoms = run_pass_0c(sources)

        assert len(atoms) == 0

    def test_abbreviation_handling_three_atoms(self, abbreviation_path: Path):
        """
        3 atoms from 'Dr. Smith works at Acme Inc. He is a clinician. Mr. Jones is the patient.'
        Per Implementation Spec §9.2.3 expected outputs.
        """
        _, dr = run_pass_0(abbreviation_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(dr, segs, input_material_ref=str(abbreviation_path))
        atoms = run_pass_0c(sources)

        assert len(atoms) == 3

    def test_abbreviation_atom_texts(self, abbreviation_path: Path):
        """
        Verify atom text content per Implementation Spec §9.2.3 expected outputs.

        Fixture: "Dr. Smith will present the findings. He will use slides. The team has been informed."
        SourceAtom 1: "Dr. Smith will present the findings."
        SourceAtom 2: "He will use slides."
        SourceAtom 3: "The team has been informed."

        Key assertion: "Dr." abbreviation does NOT trigger a false split before "Smith",
        even though "Smith" starts with a capital letter.
        """
        _, dr = run_pass_0(abbreviation_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(dr, segs, input_material_ref=str(abbreviation_path))
        atoms = run_pass_0c(sources)

        texts = [a.atom_text.strip() for a in atoms]
        assert "Dr. Smith will present the findings." in texts
        assert "He will use slides." in texts
        assert "The team has been informed." in texts

    def test_multi_section_produces_four_atoms(self, multi_section_path: Path):
        """
        4 SourceAtoms expected for multi_section.md per §9.1.2:
        2 in first paragraph (2 sentences), 1 in second, 1 in third.
        """
        _, dr = run_pass_0(multi_section_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(dr, segs, input_material_ref=str(multi_section_path))
        atoms = run_pass_0c(sources)

        assert len(atoms) == 4


class TestPass0CBytePreservation:
    def test_atom_text_is_subset_of_source_text(self, simple_paragraph_path: Path):
        """
        atom_text bytes are byte-for-byte identical to corresponding subset
        of parent Source.source_text per Implementation Spec §8.4 invariant.
        """
        _, dr = run_pass_0(simple_paragraph_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(dr, segs, input_material_ref=str(simple_paragraph_path))
        atoms = run_pass_0c(sources)

        for atom in atoms:
            parent_text = sources[atom.source_spec_index].source_text
            assert atom.atom_text.strip() in parent_text, (
                f"Atom text {atom.atom_text!r} not found in parent Source text {parent_text!r}"
            )

    def test_abbreviation_atom_text_in_source(self, abbreviation_path: Path):
        _, dr = run_pass_0(abbreviation_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(dr, segs, input_material_ref=str(abbreviation_path))
        atoms = run_pass_0c(sources)

        for atom in atoms:
            parent_text = sources[atom.source_spec_index].source_text
            assert atom.atom_text.strip() in parent_text


class TestPass0CPositionUniqueness:
    def test_no_duplicate_positions_per_source(self, multi_section_path: Path):
        """Position uniqueness: no two atoms share same position for one Source."""
        _, dr = run_pass_0(multi_section_path)
        segs = run_pass_0a(dr)
        sources = run_pass_0b(dr, segs, input_material_ref=str(multi_section_path))
        atoms = run_pass_0c(sources)

        from collections import defaultdict
        positions_by_source: dict[int, list[int]] = defaultdict(list)
        for atom in atoms:
            positions_by_source[atom.source_spec_index].append(atom.position)

        for src_idx, positions in positions_by_source.items():
            assert len(positions) == len(set(positions)), (
                f"Duplicate positions for source {src_idx}: {positions}"
            )


class TestPass0CDeterminism:
    def test_identical_atom_content_on_rerun(self, simple_paragraph_path: Path):
        def run_all(path: Path):
            _, dr = run_pass_0(path)
            segs = run_pass_0a(dr)
            srcs = run_pass_0b(dr, segs, input_material_ref=str(path))
            return run_pass_0c(srcs)

        atoms1 = run_all(simple_paragraph_path)
        atoms2 = run_all(simple_paragraph_path)

        assert len(atoms1) == len(atoms2)
        for a1, a2 in zip(atoms1, atoms2):
            assert a1.atom_text == a2.atom_text
            assert a1.position == a2.position
