"""
Step 6 — AnalysisPass Record Production.

Mode: DM. Fully deterministic. Runs after Step 5 commits.

Per CCI Construction Mechanism Spec v0.2 §4.6:
  Constructs the outputs.cci_data sub-structure and finalises pass_data.
  All fields in cci_data must be populated on every run — zero-value counts
  rather than null or omitted (a missing field is a schema conformance failure).

execution_status:
  Completed            — all batches processed; zero AI failures; zero step5 rejections.
  CompletedWithWarnings — some AI failures or rejections; at least one batch succeeded
                          with CCIs; OR integrity_violations present; OR consolidation flags.
  Failed               — all batches failed (AI + retries exhausted for every batch);
                         OR Step 5 transaction rolled back (handled by caller).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from mechanisms.cci_construction.types import (
    ConsolidationFlag,
    MergeRecord,
)


def build_cci_data(
    *,
    row_ref: int,
    batches_processed: int,
    batches_failed: int,
    ccis_created: int,
    ccis_merged: int,
    candidates_rejected: int,
    new_ci_ids: list[str],
    merge_records: list[MergeRecord],
    consolidation_flags: list[ConsolidationFlag],
    integrity_violations: list[dict],
    project_id: str,
    session: Any,
) -> dict[str, Any]:
    """
    Build the outputs.cci_data sub-structure per spec §7.

    Computes cells_populated and cells_empty from committed CCI counts.
    All zero-value integer fields are explicitly 0 (not null or omitted).

    `session` must be the same session that inserted the CCIs so the count
    sees the pending inserts before commit.
    """
    from models.cell_content_item import CellContentItemModel
    from models.zachman_cell import ZachmanCellModel

    # Count populated cells (cells with ≥1 CCI) for this row using the
    # caller's session — ensures visibility of the current transaction's inserts.
    populated_cell_ids = (
        session.query(CellContentItemModel.cell_id)
        .join(
            ZachmanCellModel,
            CellContentItemModel.cell_id == ZachmanCellModel.cell_id,
        )
        .filter(
            ZachmanCellModel.row_target == str(row_ref),
            CellContentItemModel.project_id == project_id,
        )
        .distinct()
        .all()
    )
    cells_populated = len(populated_cell_ids)

    cells_empty = 6 - cells_populated

    return {
        "row_ref": row_ref,
        "batches_processed": batches_processed,
        "batches_failed": batches_failed,
        "cells_populated": cells_populated,
        "cells_empty": cells_empty,
        "ccis_created": ccis_created,
        "ccis_merged": ccis_merged,
        "candidates_rejected": candidates_rejected,
        "merges": [r.to_dict() for r in merge_records],
        "consolidation_flags": [f.to_dict() for f in consolidation_flags],
        "integrity_violations": integrity_violations,
    }


def finalise_cci_pass_completed(
    pass_data: dict[str, Any],
    *,
    cci_data: dict[str, Any],
    start_monotonic: float,
) -> None:
    """Finalise pass_data for a fully successful run. Mutates pass_data in-place."""
    elapsed = time.monotonic() - start_monotonic
    pass_data["execution_status"] = "Completed"
    pass_data["pass_completed_at"] = datetime.now(timezone.utc)
    pass_data["elapsed_ms"] = int(elapsed * 1000)
    pass_data["mode_active"] = "DM"
    pass_data["declared_transformation_modes"] = ["IM", "DM"]
    pass_data["outputs"] = {
        "cci_data": cci_data,
        "mode_violations": pass_data.get("mode_violations", []),
    }


def finalise_cci_pass_completed_with_warnings(
    pass_data: dict[str, Any],
    *,
    cci_data: dict[str, Any],
    warning_reasons: list[str],
    start_monotonic: float,
) -> None:
    """Finalise pass_data for a run with warnings. Mutates pass_data in-place."""
    elapsed = time.monotonic() - start_monotonic
    pass_data["execution_status"] = "CompletedWithWarnings"
    pass_data["pass_completed_at"] = datetime.now(timezone.utc)
    pass_data["elapsed_ms"] = int(elapsed * 1000)
    pass_data["mode_active"] = "DM"
    pass_data["declared_transformation_modes"] = ["IM", "DM"]
    pass_data["outputs"] = {
        "cci_data": cci_data,
        "mode_violations": pass_data.get("mode_violations", []),
        "warning_reasons": warning_reasons,
    }


def finalise_cci_pass_failed(
    pass_data: dict[str, Any],
    *,
    failure_reason: str,
    failure_pass: str,
    start_monotonic: float,
) -> None:
    """Finalise pass_data for a failed run. Mutates pass_data in-place."""
    start_mono = pass_data.pop("_start_monotonic", None)
    elapsed = time.monotonic() - (start_mono if start_mono is not None else start_monotonic)
    pass_data["execution_status"] = "Failed"
    pass_data["pass_completed_at"] = datetime.now(timezone.utc)
    pass_data["elapsed_ms"] = int(elapsed * 1000)
    pass_data["mode_active"] = "DM"
    pass_data["declared_transformation_modes"] = ["IM", "DM"]
    pass_data["outputs"] = {
        "failure_reason": failure_reason,
        "failure_pass": failure_pass,
        "mode_violations": pass_data.get("mode_violations", []),
    }


def compute_execution_status(
    *,
    batches_processed: int,
    batches_failed: int,
    total_batches: int,
    candidates_rejected_step5: int,
    integrity_violations: list,
    consolidation_flags: list,
) -> tuple[str, list[str]]:
    """
    Compute execution_status and list of warning reasons per spec §4.6.

    Returns (execution_status, warning_reasons).
    """
    warning_reasons: list[str] = []

    if total_batches > 0 and batches_failed == total_batches:
        return "Failed", []

    if batches_failed > 0:
        warning_reasons.append(
            f"{batches_failed} of {total_batches} batch(es) failed AI invocation"
        )

    if candidates_rejected_step5 > 0:
        warning_reasons.append(
            f"{candidates_rejected_step5} candidate(s) rejected at Step 5 schema validation"
        )

    if integrity_violations:
        warning_reasons.append(
            f"{len(integrity_violations)} Signal(s) excluded due to Open Concern references"
        )

    if consolidation_flags:
        warning_reasons.append(
            f"{len(consolidation_flags)} cell(s) exceeded consolidation threshold"
        )

    if warning_reasons:
        return "CompletedWithWarnings", warning_reasons

    return "Completed", []
