"""
Step 5 — Assign Identifiers and Commit.

Mode: DM. No AI involvement. All Pass 3b ledger writes happen here.

Per CCI Construction Mechanism Spec v0.2 §4.5:
  Transaction boundary opens at entry to this step.

  Identifier allocation (per cell):
    Query existing CCIs to find MAX sequence number for the cell.
    Parse sequence from ci_id trailing segment: CCI-ROW{row}-C-{column}-{seq}.
    If no existing CCIs: max = 0. Next seq = max + 1.
    Allocate ci_ids zero-padded to 3 digits.

  Write operations (all in one atomic transaction):
    1. INSERT new CCIs (surviving candidates not merged into existing).
    2. UPDATE existing CCIs that received merges (signal_refs, confidence, description).

  Schema validation before INSERT: validate each candidate against CCI Pydantic model.
    Validation failure: recorded in candidates_rejected; INSERT skipped; continue.

  Transaction commits at return. Caller handles rollback on exception.

  Returns counts and the set of new ci_ids inserted.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from mechanisms.cci_construction.types import (
    CandidateCCI,
    ExistingCCIUpdate,
    MergeRecord,
)
from models.cell_content_item import CellContentItemModel

_CI_ID_PATTERN = re.compile(
    r"^CCI-ROW([1-6])-C-(What|How|Where|Who|When|Why)-(\d{3})$"
)


def commit_ccis(
    *,
    session: Session,
    surviving_candidates: list[CandidateCCI],
    existing_updates: list[ExistingCCIUpdate],
    row_ref: int,
    project_id: str,
) -> tuple[list[str], int, int, int]:
    """
    Allocate identifiers and write all Pass 3b entities to the ledger.

    Parameters
    ----------
    session             : open Session — caller opens it; caller must commit/rollback
    surviving_candidates: new CCIs to INSERT (Nones filtered out)
    existing_updates    : existing CCIs to UPDATE in-place
    row_ref             : Zachman row number
    project_id          : project scope

    Returns
    -------
    (new_ci_ids, ccis_created, ccis_merged, candidates_rejected_in_step5)
    """
    from mechanisms.cci_construction.prompts.column_vocabulary import COLUMNS

    # Filter out None sentinels (candidates merged into others during Step 4)
    candidates = [c for c in surviving_candidates if c is not None]

    # --- Identifier allocation: group by column, query max per cell ---
    candidates_by_column: dict[str, list[CandidateCCI]] = {}
    for cand in candidates:
        candidates_by_column.setdefault(cand.column, []).append(cand)

    col_seq_starts: dict[str, int] = {}
    for column in COLUMNS:
        cell_id = f"ZC-R{row_ref}-C-{column}"
        existing_ccis = (
            session.query(CellContentItemModel)
            .filter(
                CellContentItemModel.cell_id == cell_id,
                CellContentItemModel.project_id == project_id,
            )
            .all()
        )
        if existing_ccis:
            max_seq = max(
                _extract_sequence(cci.ci_id) for cci in existing_ccis
            )
        else:
            max_seq = 0
        col_seq_starts[column] = max_seq + 1

    # --- INSERT new CCIs ---
    new_ci_ids: list[str] = []
    ccis_created = 0
    candidates_rejected_step5 = 0

    for column in COLUMNS:
        col_candidates = candidates_by_column.get(column, [])
        next_seq = col_seq_starts[column]
        for cand in col_candidates:
            ci_id = f"CCI-ROW{row_ref}-C-{column}-{str(next_seq).zfill(3)}"
            next_seq += 1

            # Schema validation before INSERT
            rejection_reason = _validate_candidate_for_insert(cand, ci_id)
            if rejection_reason:
                candidates_rejected_step5 += 1
                continue

            cci = CellContentItemModel(
                ci_id=ci_id,
                cell_id=cand.cell_id,
                classification_type=cand.classification_type,
                signal_refs=cand.signal_refs,
                description=cand.description,
                trigger_condition=cand.trigger_condition,
                justification=cand.justification,
                confidence=cand.confidence,
                project_id=project_id,
            )
            session.add(cci)
            # Mutate the in-memory candidate so callers can resolve
            # pending merge records after this function returns.
            cand.ci_id = ci_id
            new_ci_ids.append(ci_id)
            ccis_created += 1

    # --- UPDATE existing CCIs that received merges ---
    ccis_merged = 0
    now = datetime.now(timezone.utc)
    for update in existing_updates:
        existing = session.get(CellContentItemModel, {"ci_id": update.ci_id, "project_id": project_id})
        if existing is None:
            continue
        existing.signal_refs = update.merged_signal_refs
        existing.confidence = update.merged_confidence
        existing.description = update.merged_description
        existing.updated_at = now
        ccis_merged += 1

    return new_ci_ids, ccis_created, ccis_merged, candidates_rejected_step5


def _extract_sequence(ci_id: str) -> int:
    """Parse the trailing 3-digit sequence number from a ci_id."""
    match = _CI_ID_PATTERN.match(ci_id)
    if match:
        return int(match.group(3))
    return 0


def _validate_candidate_for_insert(
    cand: CandidateCCI,
    ci_id: str,
) -> str | None:
    """Final schema check before INSERT. Returns reason string or None if valid."""
    from mechanisms.cci_construction.prompts.column_vocabulary import COLUMN_VOCABULARY

    if not _CI_ID_PATTERN.match(ci_id):
        return f"ci_id '{ci_id}' does not match canonical format"

    if not cand.cell_id:
        return "cell_id is empty"

    if not cand.classification_type:
        return "classification_type is empty"

    permitted = COLUMN_VOCABULARY.get(cand.column, [])
    if cand.classification_type not in permitted:
        return f"classification_type '{cand.classification_type}' not permitted for column '{cand.column}'"

    if not cand.signal_refs:
        return "signal_refs is empty"

    if not cand.description or not cand.description.strip():
        return "description is empty"

    if cand.confidence < 0.0 or cand.confidence > 1.0:
        return f"confidence {cand.confidence} outside [0.0, 1.0]"

    return None
