"""
Step 1 — Assemble Eligible Signal Set.

Mode: DM. No AI involvement. No ledger write.

Per CCI Construction Mechanism Spec v0.2 §4.1:
  Query all Signals where row_target = str(row_ref).
  For each Signal with derived_from_concern_id IS NOT NULL: verify the
  referenced Concern has state = 'Resolved'.  If Open or Dispositioned:
  exclude Signal from working set; record {signal_id, concern_id} in the
  integrity_violations buffer.
  Order by signal_id ASC for lexicographic determinism.

Returns the eligible Signal list and integrity_violations list.
No ledger writes produced.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.concern import ConcernModel
from models.signal import SignalModel


def assemble_eligible_signals(
    *,
    project_id: str,
    row_ref: int,
    session: Session,
) -> tuple[list[SignalModel], list[dict[str, Any]]]:
    """
    Collect all eligible Signals for the given row.

    Parameters
    ----------
    project_id : project to scope the query
    row_ref    : Zachman row number (1-6)
    session    : open SQLAlchemy session (read-only use; no writes)

    Returns
    -------
    (eligible_signals, integrity_violations)
      eligible_signals    : list of SignalModel, ordered by signal_id ASC
      integrity_violations: list of {signal_id, concern_id} for excluded Signals
    """
    row_target_str = str(row_ref)

    all_signals: list[SignalModel] = (
        session.query(SignalModel)
        .filter(
            SignalModel.project_id == project_id,
            SignalModel.row_target == row_target_str,
        )
        .order_by(SignalModel.signal_id)
        .all()
    )

    eligible: list[SignalModel] = []
    integrity_violations: list[dict[str, Any]] = []

    for sig in all_signals:
        if sig.derived_from_concern_id is None:
            eligible.append(sig)
            continue

        concern = session.get(ConcernModel, sig.derived_from_concern_id)
        if concern is not None and concern.state == "Resolved":
            eligible.append(sig)
        else:
            integrity_violations.append(
                {
                    "signal_id": sig.signal_id,
                    "concern_id": sig.derived_from_concern_id,
                }
            )

    return eligible, integrity_violations
