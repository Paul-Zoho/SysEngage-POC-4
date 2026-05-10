"""
Tests for the Source Capture CLI verification utility.

Happy-path smoke test: verifies the utility produces parseable, schema-conformant
canonical ledger output when given a valid input file.

Failure-path tests: verifies the utility exits non-zero with a stderr message
for bad input conditions.

The CLI is invoked as:
    python -m sysengage.tools.run_capture <input_file> <output_ledger>

This works from any working directory — including sysengage/ — because the
sysengage package is installed in editable mode via pip install -e sysengage/.

Detailed content verification (entity counts, atom texts, etc.) continues to
live in tests/source_capture/.  These tests cover only the CLI layer.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SYSENGAGE_DIR = Path(__file__).parent.parent.parent


def _run_cli(input_path: str, output_path: str) -> subprocess.CompletedProcess:
    """
    Invoke the CLI utility as a subprocess from the sysengage/ directory.

    The sysengage package is installed in editable mode, so no PYTHONPATH
    manipulation is needed — `python -m sysengage.tools.run_capture` resolves
    correctly from any working directory.
    """
    return subprocess.run(
        [sys.executable, "-m", "sysengage.tools.run_capture", input_path, output_path],
        cwd=str(SYSENGAGE_DIR),
        capture_output=True,
        text=True,
    )


def test_run_capture_produces_valid_ledger(tmp_path: Path) -> None:
    """
    End-to-end happy-path smoke test.

    Creates a minimal text input, invokes the CLI utility from sysengage/, and
    verifies:
    - exit code is 0
    - output JSON is valid and contains all required top-level keys
    - elements array contains at least one Source and one AnalysisPass
    - stdout summary contains the AnalysisPass ID and entity counts
    """
    input_path = tmp_path / "sample_input.txt"
    input_path.write_text(
        "The system shall accept user input. It shall respond within two seconds.",
        encoding="utf-8",
    )
    output_path = tmp_path / "ledger_output.json"

    completed = _run_cli(str(input_path), str(output_path))

    assert completed.returncode == 0, (
        f"CLI exited with code {completed.returncode}.\n"
        f"stdout: {completed.stdout}\n"
        f"stderr: {completed.stderr}"
    )

    assert output_path.exists(), "Output ledger file was not created."

    ledger = json.loads(output_path.read_text(encoding="utf-8"))

    for key in (
        "sysengage_ledger_version",
        "schema_id",
        "run_id",
        "created_utc",
        "generator",
        "elements",
    ):
        assert key in ledger, f"Missing top-level key '{key}' in ledger output."

    assert isinstance(ledger["elements"], list), "'elements' must be a list."

    element_types = [e.get("element_type") for e in ledger["elements"]]
    assert "Source" in element_types, (
        f"Expected at least one Source element; got types: {element_types}"
    )
    assert "AnalysisPass" in element_types, (
        f"Expected at least one AnalysisPass element; got types: {element_types}"
    )

    stdout = completed.stdout
    assert "Source Capture completed." in stdout
    assert "AnalysisPass ID:" in stdout
    assert "Sources produced:" in stdout
    assert "Ledger written to:" in stdout


def test_run_capture_missing_file_exits_nonzero(tmp_path: Path) -> None:
    """
    Failure path: missing input file → exit 1, descriptive error to stderr.
    """
    nonexistent = tmp_path / "does_not_exist.txt"
    output_path = tmp_path / "ledger.json"

    completed = _run_cli(str(nonexistent), str(output_path))

    assert completed.returncode != 0, (
        "Expected non-zero exit code for missing input file."
    )
    assert "not found" in completed.stderr.lower() or "error" in completed.stderr.lower(), (
        f"Expected an error message in stderr; got: {completed.stderr!r}"
    )


def test_run_capture_unsupported_format_exits_nonzero(tmp_path: Path) -> None:
    """
    Failure path: binary file with unsupported extension → exit 1.
    The mechanism raises UnsupportedFormatError which the CLI translates to
    a non-zero exit with a descriptive stderr message.
    """
    bad_input = tmp_path / "binary_blob.xyz"
    bad_input.write_bytes(b"\xff\xfe\x00\x01\x02\x03BINARY_DATA\x80\x81\x82")
    output_path = tmp_path / "ledger.json"

    completed = _run_cli(str(bad_input), str(output_path))

    assert completed.returncode != 0, (
        "Expected non-zero exit code for unsupported format input."
    )
    assert completed.stderr.strip(), (
        "Expected an error message in stderr for unsupported format."
    )
