"""
Audit record helper for the Data Dictionary service.

Per Data Dictionary Spec v0.1 §5.3: every resolve_term appends one log row
to data_dictionary_resolution_log. The log is the per-attempt trail including
flags and rejections; the synonym entries themselves are the durable canonical-
isation-decision register.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import text


def append_resolution_log(
    session: Session,
    *,
    surface_term: str,
    provenance_ref: str | None,
    outcome: str,
    confidence: float | None,
    competing_refs: list[str] | None,
    auto_recorded: bool,
) -> None:
    """
    Insert one row into data_dictionary_resolution_log.
    outcome ∈ existing | synonym | canonical | flagged (enforced by DB CHECK).
    Caller controls the session and commits (or not).
    """
    import json

    session.execute(
        text(
            "INSERT INTO data_dictionary_resolution_log "
            "(surface_term, provenance_ref, outcome, confidence, competing_refs, auto_recorded, created_at) "
            "VALUES (:st, :pr, :outcome, :conf, CAST(:crefs AS jsonb), :auto_rec, :now)"
        ),
        {
            "st": surface_term,
            "pr": provenance_ref,
            "outcome": outcome,
            "conf": confidence,
            "crefs": json.dumps(competing_refs) if competing_refs else None,
            "auto_rec": auto_recorded,
            "now": datetime.now(timezone.utc),
        },
    )
