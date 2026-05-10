"""
Smoke test for the Source Capture CLI verification utility.

Verifies that the utility:
  - exits 0 on valid input
  - writes parseable JSON
  - produces a schema-conformant canonical ledger with the expected top-level keys
  - includes at least one Source element and at least one AnalysisPass element

Detailed content verification (entity counts, atom texts, etc.) continues to
live in tests/source_capture/.  This test covers only the CLI layer.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SYSENGAGE_DIR = Path(__file__).parent.parent.parent


def test_run_capture_produces_valid_ledger(tmp_path: Path) -> None:
    """
    End-to-end smoke test for run_capture.py.

    Creates a minimal text input, invokes the CLI utility as a subprocess,
    and verifies the output ledger JSON is schema-conformant.
    """
    input_path = tmp_path / "sample_input.txt"
    input_path.write_text(
        "The system shall accept user input. It shall respond within two seconds.",
        encoding="utf-8",
    )

    output_path = tmp_path / "ledger_output.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sysengage.tools.run_capture",
            str(input_path),
            str(output_path),
        ],
        cwd=str(SYSENGAGE_DIR.parent),
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, (
        f"CLI exited with code {completed.returncode}.\n"
        f"stdout: {completed.stdout}\n"
        f"stderr: {completed.stderr}"
    )

    assert output_path.exists(), "Output ledger file was not created."

    ledger = json.loads(output_path.read_text(encoding="utf-8"))

    for key in ("sysengage_ledger_version", "schema_id", "run_id", "created_utc", "generator", "elements"):
        assert key in ledger, f"Missing top-level key '{key}' in ledger output."

    assert isinstance(ledger["elements"], list), "'elements' must be a list."

    element_types = [e.get("element_type") for e in ledger["elements"]]
    assert "Source" in element_types, (
        f"Expected at least one Source element; got types: {element_types}"
    )
    assert "AnalysisPass" in element_types, (
        f"Expected at least one AnalysisPass element; got types: {element_types}"
    )
