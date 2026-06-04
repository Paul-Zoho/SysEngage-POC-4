"""
Gap record production for the Requirement Matching service.

Per Requirement Matching Spec v0.1 §4.6 (F86, F84).

Upward gap (child-orphan):
  A row n>1 requirement with empty refines_refs after matching → write an
  upward gap record for GQA to consider. Row 1 exception: empty refines_refs
  at Row 1 is correct (top of the hierarchy) → no upward gap.

Downward gap (parent-orphan):
  After matching a row, any row n-1 requirement that no row n requirement refines
  → write a downward gap record. This is the bidirectional half (Row 3 §4.2).

Both are records for gap analysis; neither is auto-fixed here.
Gap records may later promote to canonical Gap elements when GQA consumes them.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import text

_log = logging.getLogger(__name__)


def write_upward_gap(
    session: Session,
    *,
    requirement_id: str,
    row_target: str,
) -> None:
    """
    Write an upward gap record (child-orphan, no refines_refs after matching).

    Skip if row_target == '1' (Row 1 top — empty is correct, per spec §4.6).
    """
    if str(row_target) == "1":
        return
    session.execute(
        text(
            "INSERT INTO requirement_gap_record (direction, requirement_id, row_target, created_at) "
            "VALUES ('upward', :rid, :row, :now)"
        ),
        {"rid": requirement_id, "row": str(row_target), "now": datetime.now(timezone.utc)},
    )
    _log.info("Upward gap written for %s (row %s)", requirement_id, row_target)


def write_downward_gap(
    session: Session,
    *,
    requirement_id: str,
    row_target: str,
) -> None:
    """
    Write a downward gap record (parent-orphan, nothing below refines this).
    """
    session.execute(
        text(
            "INSERT INTO requirement_gap_record (direction, requirement_id, row_target, created_at) "
            "VALUES ('downward', :rid, :row, :now)"
        ),
        {"rid": requirement_id, "row": str(row_target), "now": datetime.now(timezone.utc)},
    )
    _log.info("Downward gap written for %s (row %s)", requirement_id, row_target)


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
