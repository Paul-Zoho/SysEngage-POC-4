"""
Gap record production for the Requirement Matching service.

Per Requirement Matching Service Spec v0.4 §4.6 (F86, F84, D-rm-6).

v0.2 change (D-rm-4 reversal): gap records are now entries in
outputs.mechanism_data.gap_records inside the per-execution AnalysisPass,
NOT rows in a requirement_gap_record DB table.  These functions return dicts;
the caller (service.py) passes them to the ProvAccumulator.

Upward gap (child-orphan, no_match):
  A row n>1 requirement with empty refines_refs after matching, where ≥1
  parent candidate was considered and none judged a parent → emit an upward
  gap record for GQA. Row 1 exception: no gap.

No-candidates gap (child-orphan, no_candidates) — v0.4 / D-rm-6:
  A row n>1 requirement that was DD-resolved but for which the pre-filter
  returned zero parent candidates → emit an `unmatched_no_candidates` gap
  record. Distinct from an upward no_match: this may be genuine novelty OR
  a cross-row vocabulary / pre-filter miss — NOT a confident novel-orphan.

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


def make_no_candidates_gap_record(
    *,
    requirement_id: str,
    row_target: str | int,
    project_id: str | None = None,
) -> dict:
    """
    Return an unmatched_no_candidates gap record (D-rm-6, v0.4).

    Fires when the child is DD-resolved but the entity pre-filter returned zero
    row n-1 parent candidates — the child was never assessed against a parent.

    Distinct from make_upward_gap_record (no_match outcome):
      no_match    — ≥1 candidate offered, none judged a parent → confident novel-orphan.
      no_candidates — 0 candidates offered → possible novelty OR cross-row vocabulary
                    / pre-filter miss; NOT a confident novel-orphan claim.

    GQA uses the `kind` field to distinguish these two cases and choose an
    appropriate review action.
    """
    _log.info(
        "No-candidates gap emitted for %s/%s (row %s)", project_id, requirement_id, row_target
    )
    return {
        "direction": "upward",
        "kind": "unmatched_no_candidates",
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
