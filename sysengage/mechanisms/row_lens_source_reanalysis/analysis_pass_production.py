"""
AnalysisPass record production for Row-Lens Source Re-Analysis.

Per spec §4.5 and §7.2 (v0.2): builds the row_lens_data sub-structure and
finalises the pass_data dict with the mechanism-specific execution status.

v0.2 changes vs v0.1:
- build_row_lens_data: removed stream2_* fields and chunk_* fields.
  Added source_count. assembly param removed — caller passes scalars directly.

execution_status values per spec §8.1 AP-2:
  "Completed"              — all stages succeeded, invariant holds, no warnings
  "CompletedWithWarnings"  — stages succeeded, invariant holds, some RI/ME failures
  "Failed"                 — invariant violation or stage-level failure

mode_active="IM"; declared_transformation_modes=["IM","DM","LPM"] per spec §6.1.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any


def build_row_lens_data(
    *,
    row_ref: int,
    source_count: int,
    signal_count: int,
    concern_count: int,
    out_of_scope_refs: list[str],
    ai_model_fingerprints: list[str],
    concern_threshold_used: float,
    failure_detail: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Build the outputs.row_lens_data sub-structure per spec §7.2 (v0.2).

    Single-stream fields only — no stream2_* or chunk_* fields.
    Stored in AnalysisPass.outputs JSONB field.
    """
    data: dict[str, Any] = {
        "row_ref": row_ref,
        "source_count": source_count,
        "signal_count_produced": signal_count,
        "concern_count_produced": concern_count,
        "out_of_scope_count": len(out_of_scope_refs),
        "out_of_scope_refs": out_of_scope_refs,
        "ai_model_fingerprints": ai_model_fingerprints,
        "concern_threshold_used": concern_threshold_used,
    }
    if failure_detail:
        data["failure_detail"] = failure_detail
    return data


def finalise_pass_completed(
    pass_data: dict[str, Any],
    *,
    row_lens_data: dict[str, Any],
    start_monotonic: float,
) -> None:
    """
    Finalise pass_data for a fully successful run — execution_status = "Completed".
    Mutates pass_data in-place.
    """
    elapsed = time.monotonic() - start_monotonic
    pass_data["execution_status"] = "Completed"
    pass_data["pass_completed_at"] = datetime.now(timezone.utc)
    pass_data["elapsed_ms"] = int(elapsed * 1000)
    pass_data["mode_active"] = "IM"
    pass_data["declared_transformation_modes"] = ["IM", "DM", "LPM"]
    pass_data["outputs"] = {
        "row_lens_data": row_lens_data,
        "mode_violations": pass_data.get("mode_violations", []),
    }


def finalise_pass_completed_with_warnings(
    pass_data: dict[str, Any],
    *,
    row_lens_data: dict[str, Any],
    failure_detail: list[dict],
    start_monotonic: float,
) -> None:
    """
    Finalise pass_data for a run with RI/ME warnings — "CompletedWithWarnings".
    Invariant holds but some items were excluded from commit set.
    Mutates pass_data in-place.
    """
    elapsed = time.monotonic() - start_monotonic
    pass_data["execution_status"] = "CompletedWithWarnings"
    pass_data["pass_completed_at"] = datetime.now(timezone.utc)
    pass_data["elapsed_ms"] = int(elapsed * 1000)
    pass_data["mode_active"] = "IM"
    pass_data["declared_transformation_modes"] = ["IM", "DM", "LPM"]
    pass_data["outputs"] = {
        "row_lens_data": row_lens_data,
        "mode_violations": pass_data.get("mode_violations", []),
        "failure_reason": f"{len(failure_detail)} item(s) excluded due to RI/ME checks",
        "failure_detail": failure_detail,
        "failure_pass": "AnalysisPassProduction",
    }


def finalise_pass_failed(
    pass_data: dict[str, Any],
    *,
    failure_reason: str,
    failure_pass: str,
    start_monotonic: float,
) -> None:
    """
    Finalise pass_data for a failed run — execution_status = "Failed".
    Mutates pass_data in-place. Caller commits this in a separate transaction.
    """
    start_mono = pass_data.pop("_start_monotonic", None)
    elapsed = time.monotonic() - (start_mono if start_mono is not None else start_monotonic)
    pass_data["execution_status"] = "Failed"
    pass_data["pass_completed_at"] = datetime.now(timezone.utc)
    pass_data["elapsed_ms"] = int(elapsed * 1000)
    pass_data["mode_active"] = "IM"
    pass_data["declared_transformation_modes"] = ["IM", "DM", "LPM"]
    pass_data["outputs"] = {
        "failure_reason": failure_reason,
        "failure_pass": failure_pass,
        "mode_violations": pass_data.get("mode_violations", []),
    }
