"""
Unit tests for core/output_naming.py.

No database, no filesystem writes for most tests (tmp_path used where
file-count behaviour needs a real directory).
"""

from __future__ import annotations

import os
import pytest

from core.output_naming import (
    PASS_LABEL_MAP,
    OutputNamingError,
    generate_filename,
    validate_filename,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_file(directory: str, name: str) -> None:
    open(os.path.join(directory, name), "w").close()


# ---------------------------------------------------------------------------
# validate_filename
# ---------------------------------------------------------------------------

class TestValidateFilename:
    """Spec v0.2 validation regex acceptance and rejection cases."""

    @pytest.mark.parametrize("name", [
        "PMT_Ph01_0a_SourceCapture_R1_Run1.json",
        "PMT_Ph01_0a_SourceCapture_R2_Run1.json",
        "PMT_Ph03_3a_RowLensSourceReanalysis_R1_Run1.json",
        "PMT_Ph03_3a_RowLensSourceReanalysis_R2_Run1.json",
        "PMT_Ph03_3b_CCIConstruction_R1_Run1.json",
        "PMT_Ph03_3b_CCIConstruction_R1_Run2.json",
        "PMT_Ph03_3b_CCIConstruction_R2_Run1.json",
        "PMT_Ph03_3c_DomainDerivation_R1_Run1.json",
        "PMT_Ph03_3d_RequirementDerivation_R1_Run1.json",
        "ACME_Ph03_3b_CCIConstruction_R1_Run1.json",
        "PMT_Ph01_0b_SegmentCapture_R1_Run1.json",
        "AB_Ph10_SourceCapture_R6_Run99.json",
    ])
    def test_valid_names_accepted(self, name: str) -> None:
        assert validate_filename(name), f"Expected valid: {name!r}"

    @pytest.mark.parametrize("name", [
        "",
        "pmt_Ph01_0a_SourceCapture_R1_Run1.json",   # lowercase project id
        "PMT1_Ph01_0a_SourceCapture_R1_Run1.json",  # digit in project id
        "PMT-X_Ph01_0a_SourceCapture_R1_Run1.json", # hyphen in project id
        "PMT_ph01_0a_SourceCapture_R1_Run1.json",   # lowercase 'ph'
        "PMT_Ph1_0a_SourceCapture_R1_Run1.json",    # phase not zero-padded
        "PMT_Ph01_0a_sourceCapture_R1_Run1.json",   # passLabel starts lowercase
        "PMT_Ph01_0a_SourceCapture_R0_Run1.json",   # row 0 out of range
        "PMT_Ph01_0a_SourceCapture_R7_Run1.json",   # row 7 out of range
        "PMT_Ph01_0a_SourceCapture_R1_run1.json",   # lowercase 'run'
        "PMT_Ph01_0a_SourceCapture_R1_Run1.txt",    # wrong extension
        "PMT_Ph01_0a_SourceCapture_R1_Run1",        # no extension
        "PMT_Ph01_0a_SourceCapture_R1_Run1.json.bak",
    ])
    def test_invalid_names_rejected(self, name: str) -> None:
        assert not validate_filename(name), f"Expected invalid: {name!r}"


# ---------------------------------------------------------------------------
# generate_filename — pass label mapping
# ---------------------------------------------------------------------------

class TestGenerateFilenamePassLabels:
    """generate_filename produces the correct passLabel for all defined passes."""

    @pytest.mark.parametrize("phase,pass_,expected_label", [
        ("01", "0a", "SourceCapture"),
        ("01", "0b", "SegmentCapture"),
        ("03", "3a", "RowLensSourceReanalysis"),
        ("03", "3b", "CCIConstruction"),
        ("03", "3c", "DomainDerivation"),
        ("03", "3d", "RequirementDerivation"),
    ])
    def test_correct_pass_label(self, phase: str, pass_: str, expected_label: str, tmp_path) -> None:
        name = generate_filename("PMT", phase, pass_, "1", str(tmp_path))
        assert f"_{expected_label}_" in name, (
            f"Expected passLabel {expected_label!r} in {name!r}"
        )

    def test_phase_auto_zero_padded(self, tmp_path) -> None:
        name_int = generate_filename("PMT", 3, "3b", "1", str(tmp_path))
        name_str = generate_filename("PMT", "3", "3b", "1", str(tmp_path))
        assert "_Ph03_" in name_int
        assert "_Ph03_" in name_str

    def test_row_as_int(self, tmp_path) -> None:
        name = generate_filename("PMT", "03", "3b", 1, str(tmp_path))
        assert "_R1_" in name

    def test_full_canonical_example(self, tmp_path) -> None:
        name = generate_filename("PMT", "03", "3a", "1", str(tmp_path))
        assert name == "PMT_Ph03_3a_RowLensSourceReanalysis_R1_Run1.json"

    def test_acme_project_id(self, tmp_path) -> None:
        name = generate_filename("ACME", "03", "3b", "1", str(tmp_path))
        assert name.startswith("ACME_Ph03_3b_CCIConstruction_R1_Run1")

    def test_generated_name_passes_validation(self, tmp_path) -> None:
        for (phase, pass_) in PASS_LABEL_MAP:
            name = generate_filename("PMT", phase, pass_, "1", str(tmp_path))
            assert validate_filename(name), f"Generated name failed validation: {name!r}"


# ---------------------------------------------------------------------------
# generate_filename — run number derivation
# ---------------------------------------------------------------------------

class TestRunNumberDerivation:
    """Run number is derived from counting existing files in out_dir."""

    def test_run1_when_directory_empty(self, tmp_path) -> None:
        name = generate_filename("PMT", "03", "3b", "1", str(tmp_path))
        assert name.endswith("_Run1.json")

    def test_run1_when_directory_does_not_exist(self, tmp_path) -> None:
        non_existent = str(tmp_path / "new_subdir")
        name = generate_filename("PMT", "03", "3b", "1", non_existent)
        assert name.endswith("_Run1.json")

    def test_run2_after_one_existing_json(self, tmp_path) -> None:
        _make_file(str(tmp_path), "PMT_Ph03_3b_CCIConstruction_R1_Run1.json")
        name = generate_filename("PMT", "03", "3b", "1", str(tmp_path))
        assert name.endswith("_Run2.json")

    def test_run3_after_two_existing_files(self, tmp_path) -> None:
        _make_file(str(tmp_path), "PMT_Ph03_3b_CCIConstruction_R1_Run1.json")
        _make_file(str(tmp_path), "PMT_Ph03_3b_CCIConstruction_R1_Run2.json")
        name = generate_filename("PMT", "03", "3b", "1", str(tmp_path))
        assert name.endswith("_Run3.json")

    def test_run_number_not_affected_by_different_row(self, tmp_path) -> None:
        _make_file(str(tmp_path), "PMT_Ph03_3b_CCIConstruction_R2_Run1.json")
        name = generate_filename("PMT", "03", "3b", "1", str(tmp_path))
        assert name.endswith("_Run1.json"), (
            "Files for R2 should not affect run counter for R1"
        )

    def test_run_number_not_affected_by_different_pass(self, tmp_path) -> None:
        _make_file(str(tmp_path), "PMT_Ph03_3a_RowLensSourceReanalysis_R1_Run1.json")
        name = generate_filename("PMT", "03", "3b", "1", str(tmp_path))
        assert name.endswith("_Run1.json"), (
            "Files for 3a should not affect run counter for 3b"
        )

    def test_run_number_counts_highest_not_total(self, tmp_path) -> None:
        _make_file(str(tmp_path), "PMT_Ph03_3b_CCIConstruction_R1_Run1.json")
        _make_file(str(tmp_path), "PMT_Ph03_3b_CCIConstruction_R1_Run3.json")
        name = generate_filename("PMT", "03", "3b", "1", str(tmp_path))
        assert name.endswith("_Run4.json"), (
            "Run number should be max(existing) + 1, not count + 1"
        )

    def test_unrelated_files_ignored(self, tmp_path) -> None:
        _make_file(str(tmp_path), "README.md")
        _make_file(str(tmp_path), "some_other_project.json")
        name = generate_filename("PMT", "03", "3b", "1", str(tmp_path))
        assert name.endswith("_Run1.json")


# ---------------------------------------------------------------------------
# generate_filename — error cases
# ---------------------------------------------------------------------------

class TestGenerateFilenameErrors:
    """OutputNamingError raised for invalid inputs."""

    def test_project_id_with_digit(self, tmp_path) -> None:
        with pytest.raises(OutputNamingError, match="project_id"):
            generate_filename("PMT1", "03", "3b", "1", str(tmp_path))

    def test_project_id_lowercase(self, tmp_path) -> None:
        with pytest.raises(OutputNamingError, match="project_id"):
            generate_filename("pmt", "03", "3b", "1", str(tmp_path))

    def test_project_id_with_hyphen(self, tmp_path) -> None:
        with pytest.raises(OutputNamingError, match="project_id"):
            generate_filename("PM-T", "03", "3b", "1", str(tmp_path))

    def test_project_id_single_letter(self, tmp_path) -> None:
        with pytest.raises(OutputNamingError, match="project_id"):
            generate_filename("P", "03", "3b", "1", str(tmp_path))

    def test_row_zero(self, tmp_path) -> None:
        with pytest.raises(OutputNamingError, match="row"):
            generate_filename("PMT", "03", "3b", "0", str(tmp_path))

    def test_row_seven(self, tmp_path) -> None:
        with pytest.raises(OutputNamingError, match="row"):
            generate_filename("PMT", "03", "3b", "7", str(tmp_path))

    def test_unknown_pass(self, tmp_path) -> None:
        with pytest.raises(OutputNamingError, match="passLabel"):
            generate_filename("PMT", "03", "9z", "1", str(tmp_path))

    def test_unknown_phase(self, tmp_path) -> None:
        with pytest.raises(OutputNamingError, match="passLabel"):
            generate_filename("PMT", "99", "3b", "1", str(tmp_path))

    def test_non_integer_phase(self, tmp_path) -> None:
        with pytest.raises(OutputNamingError, match="phase"):
            generate_filename("PMT", "abc", "3b", "1", str(tmp_path))
