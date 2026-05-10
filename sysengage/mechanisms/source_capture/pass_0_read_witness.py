"""
Pass 0 — Read Witness.

Per Implementation Spec §4.1 and Row 4 Applied §9.

Mode: LPM (Literal Persistence Mode) — pure read; no content modification.
@pass_mode("LPM") declares this Pass's Transformation Mode per architectural commitment.

What this Pass does:
  1. Opens and fully reads the input file via format-specific decoder.
  2. Computes input_hash (SHA-256), byte_count, character_count.
  3. Records read_mode ("Full" by default; "Sampling" only on Practitioner override).
  4. Records read_completion_status — true on full read, false on partial decode.
  5. Returns Read Witness data dict (NOT persisted as standalone entity per F10).

Read Witness is stored on AnalysisPass.outputs.read_witness when Pass 0 completes.

Verification criteria per Implementation Spec §8.1:
  - input_hash is SHA-256 hex string
  - byte_count > 0 for non-empty input
  - character_count >= 0
  - read_mode = "Full" by default
  - read_completion_status = true on success
  - Error case: empty input → EmptyInputError; mechanism aborts
  - Determinism: same input → identical input_hash, byte_count, character_count
"""

from pathlib import Path
from typing import Any

from core.modes import pass_mode
from mechanisms.source_capture.decoders import decode_file, DecodeResult
from mechanisms.source_capture.errors import EmptyInputError


@pass_mode("LPM")
def run_pass_0(
    file_path: Path,
    *,
    read_mode: str = "Full",
) -> tuple[dict[str, Any], DecodeResult]:
    """
    Execute Pass 0 Read Witness.

    Args:
        file_path: Path to the input file.
        read_mode: "Full" (default) or "Sampling" (Practitioner override only).

    Returns:
        (read_witness_dict, decode_result) tuple.
        read_witness_dict is stored on AnalysisPass.outputs.read_witness.
        decode_result carries the decoded character stream for downstream Passes.

    Raises:
        EmptyInputError: if input file is zero bytes.
        InputAccessError: if file cannot be opened.
        UnsupportedFormatError: if format unrecognised and txt fallback fails.
    """
    decode_result = decode_file(file_path)

    if decode_result.byte_count == 0:
        raise EmptyInputError(
            f"Input file is empty (zero bytes): {file_path}. "
            "Mechanism aborts per Implementation Spec §4.1.4."
        )

    read_witness = {
        "input_hash": decode_result.input_hash,
        "byte_count": decode_result.byte_count,
        "character_count": decode_result.character_count,
        "read_mode": read_mode,
        "read_completion_status": decode_result.read_completion_status,
        "partial_failure_detail": decode_result.partial_failure_detail or None,
        "format_detected": decode_result.format_detected,
        "file_path": str(file_path),
    }

    return read_witness, decode_result
