"""
Step 2 — Upsert ZachmanCells and Partition Signals into Batches.

Mode: DM. No AI involvement.

Per CCI Construction Mechanism Spec v0.2 §4.2:

Step 2a — ZachmanCell upsert (own short transaction):
  For each column in [What, How, Where, Who, When, Why]: UPSERT zachman_cell
  ON CONFLICT DO NOTHING.  Committed in its own short transaction immediately
  before the main mechanism transaction opens.  Rationale: ZachmanCells must
  exist as FK anchors for CCI inserts in Step 5; if the main transaction rolls
  back, ZachmanCells remain (idempotent — correct for re-run semantics).

Step 2b — Batch partitioning (in-memory, no ledger write):
  Partition the eligible Signal working set (ordered by signal_id ASC) into
  batches of size cci_batch_size.  The final batch may be smaller.
  Batch boundaries have no analytical significance — duplicates across batch
  boundaries are caught by Step 4's per-cell deduplication.
"""

from __future__ import annotations

from models.signal import SignalModel
from models.zachman_cell import ZachmanCellModel
from core.db import get_session

COLUMNS: list[str] = ["What", "How", "Where", "Who", "When", "Why"]


def upsert_zachman_cells(
    *,
    project_id: str,
    row_ref: int,
) -> list[str]:
    """
    Upsert all six ZachmanCells for the given row in an isolated transaction.

    Returns the list of cell_ids upserted (always six).
    Commits immediately.  Idempotent on re-run.
    """
    session = get_session()
    try:
        cell_ids: list[str] = []
        for column in COLUMNS:
            cell_id = f"ZC-R{row_ref}-C-{column}"
            existing = session.get(ZachmanCellModel, {"cell_id": cell_id, "project_id": project_id})
            if existing is None:
                cell = ZachmanCellModel(
                    cell_id=cell_id,
                    row_target=str(row_ref),
                    column=column,
                    project_id=project_id,
                )
                session.add(cell)
            cell_ids.append(cell_id)
        session.commit()
        return cell_ids
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def partition_signals_into_batches(
    *,
    signals: list[SignalModel],
    batch_size: int,
) -> list[list[SignalModel]]:
    """
    Partition the eligible Signal list into fixed-size batches.

    Signals are already ordered by signal_id ASC from Step 1.
    The final batch may be smaller than batch_size.
    Returns an empty list if signals is empty.
    """
    if not signals:
        return []
    return [signals[i : i + batch_size] for i in range(0, len(signals), batch_size)]
