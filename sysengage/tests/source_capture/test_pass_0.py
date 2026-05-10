"""
Tests for Pass 0 — Read Witness.

Per Implementation Spec §8.1 verification criteria and §9 test fixtures.

Tests:
  - Happy path: read_witness populated with correct fields
  - Determinism: identical hash/count on re-run
  - Empty input: EmptyInputError raised
  - Input hash is SHA-256 hex string
  - byte_count > 0 for non-empty input
  - character_count >= 0
  - read_mode defaults to "Full"
  - read_completion_status=true on successful read
"""

import hashlib
from pathlib import Path

import pytest

from mechanisms.source_capture.errors import EmptyInputError
from mechanisms.source_capture.pass_0_read_witness import run_pass_0


class TestPass0HappyPath:
    def test_simple_paragraph_read_witness_fields(self, simple_paragraph_path: Path):
        read_witness, decode_result = run_pass_0(simple_paragraph_path)

        assert "input_hash" in read_witness
        assert "byte_count" in read_witness
        assert "character_count" in read_witness
        assert read_witness["read_mode"] == "Full"
        assert read_witness["read_completion_status"] is True

    def test_input_hash_is_sha256_hex(self, simple_paragraph_path: Path):
        read_witness, _ = run_pass_0(simple_paragraph_path)

        assert len(read_witness["input_hash"]) == 64
        int(read_witness["input_hash"], 16)

    def test_byte_count_matches_file_size(self, simple_paragraph_path: Path):
        read_witness, _ = run_pass_0(simple_paragraph_path)

        expected_bytes = simple_paragraph_path.read_bytes()
        assert read_witness["byte_count"] == len(expected_bytes)
        assert read_witness["byte_count"] > 0

    def test_character_count_non_negative(self, simple_paragraph_path: Path):
        read_witness, _ = run_pass_0(simple_paragraph_path)
        assert read_witness["character_count"] >= 0

    def test_input_hash_matches_sha256(self, simple_paragraph_path: Path):
        raw = simple_paragraph_path.read_bytes()
        expected_hash = hashlib.sha256(raw).hexdigest()

        read_witness, _ = run_pass_0(simple_paragraph_path)
        assert read_witness["input_hash"] == expected_hash

    def test_read_mode_default_is_full(self, simple_paragraph_path: Path):
        read_witness, _ = run_pass_0(simple_paragraph_path)
        assert read_witness["read_mode"] == "Full"

    def test_read_mode_sampling_override(self, simple_paragraph_path: Path):
        read_witness, _ = run_pass_0(simple_paragraph_path, read_mode="Sampling")
        assert read_witness["read_mode"] == "Sampling"

    def test_decode_result_text_non_empty(self, simple_paragraph_path: Path):
        _, decode_result = run_pass_0(simple_paragraph_path)
        assert len(decode_result.text) > 0

    def test_multi_section_md(self, multi_section_path: Path):
        read_witness, decode_result = run_pass_0(multi_section_path)
        assert read_witness["read_completion_status"] is True
        assert read_witness["byte_count"] > 0
        assert decode_result.format_detected == "md"


class TestPass0Determinism:
    """Determinism: same input → identical Read Witness per Implementation Spec §8.1."""

    def test_identical_hash_on_rerun(self, simple_paragraph_path: Path):
        rw1, _ = run_pass_0(simple_paragraph_path)
        rw2, _ = run_pass_0(simple_paragraph_path)

        assert rw1["input_hash"] == rw2["input_hash"]
        assert rw1["byte_count"] == rw2["byte_count"]
        assert rw1["character_count"] == rw2["character_count"]

    def test_identical_hash_multi_section(self, multi_section_path: Path):
        rw1, _ = run_pass_0(multi_section_path)
        rw2, _ = run_pass_0(multi_section_path)
        assert rw1["input_hash"] == rw2["input_hash"]


class TestPass0ErrorCases:
    def test_empty_input_raises_empty_input_error(self, empty_path: Path):
        """Per Implementation Spec §4.1.4 and §8.1."""
        with pytest.raises(EmptyInputError):
            run_pass_0(empty_path)

    def test_file_not_found_raises_input_access_error(self):
        from mechanisms.source_capture.errors import InputAccessError
        with pytest.raises(InputAccessError):
            run_pass_0(Path("/nonexistent/path/file.txt"))
