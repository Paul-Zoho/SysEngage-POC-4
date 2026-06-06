"""
Gap record production for the Requirement Matching service.

Per Requirement Matching Service Spec v0.2 §4.6 (F86, F84).

v0.2 change (D-rm-4 reversal): gap records are now entries in
outputs.mechanism_data.gap_records inside the per-execution AnalysisPass,
NOT rows in a requirement_gap_record DB table.  These functions return dicts;
the caller (service.py) passes them to the ProvAccumulator.

Upward gap (child-orphan):
  A row n>1 requirement with empty refines_refs after matching → emit an
  upward gap record for GQA to consider. Row 1 exception: empty refines_refs
  at Row 1 is correct (top of the hierarchy) → no upward gap.

Downward gap (parent-orphan):
  After matching a row, any row n-1 requirement that no row n requirement
  refines → emit a downward gap record.

Both are records for gap analysis; neither is auto-fixed here.
"""

from __future__ import annotations

import logging

_log = logging.getLogger(__name__)


def make_upward_gap_record(
    *,
    requirement_id: str,
    row_target: str | int,
    project_id: str | None = None,
) -> dict | None:
    """
    Return an upward gap record dict (child-orphan, no refines_refs after matching).
    Returns None for row 1 — empty refines_refs is correct there (per spec §4.6).
    """
    if str(row_target) == "1":
        return None
    _log.info("Upward gap emitted for %s/%s (row %s)", project_id, requirement_id, row_target)
    return {
        "direction": "upward",
        "requirement_id": requirement_id,
        "row_target": str(row_target),
    }


def make_downward_gap_record(
    *,
    requirement_id: str,
    row_target: str | int,
    project_id: str | None = None,
) -> dict:
    """
    Return a downward gap record dict (parent-orphan, nothing below refines this).
    """
    _log.info("Downward gap emitted for %s/%s (row %s)", project_id, requirement_id, row_target)
    return {
        "direction": "downward",
        "requirement_id": requirement_id,
        "row_target": str(row_target),
    }


def compute_downward_gaps(
    *,
    parent_ids: set[str],
    refined_parent_ids: set[str],
) -> set[str]:
    """
    Return the set of parent_ids that are not refined by any child.
    These are the parent-orphan (downward gap) candidates.
    """
    return parent_ids - refined_parent_ids
