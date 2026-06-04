"""
False-merge rejection propagation for the Data Dictionary service.

Per Data Dictionary Spec v0.1 §4.6.

When a Practitioner rejects a synonym entry (a false merge):
  1. Create a new canonical entry from the synonym's surface_term.
  2. Delete/retire the synonym entry.
  3. Re-resolution trigger — find requirement Object bindings that resolved to
     the wrongly-merged canonical entry via this surface term (traceable through
     provenance_ref), and mark them for re-resolution against the corrected dict.

The dependent-binding re-resolution is queued (logged), not silent.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import text

_log = logging.getLogger(__name__)


def reject_synonym(
    session: Session,
    *,
    synonym_dd_id: str,
    project_id: str,
) -> dict:
    """
    Reject a synonym entry (false-merge correction).

    Parameters
    ----------
    session       : active SQLAlchemy session (caller commits)
    synonym_dd_id : dd_id of the synonym entry to reject
    project_id    : project for provenance re-resolution scoping

    Returns
    -------
    dict with keys: new_canonical_id, retired_synonym_id, reresolution_count
    """
    # 1. Load the synonym entry
    row = session.execute(
        text("SELECT dd_id, entry_kind, surface_term, resolves_to, provenance_ref "
             "FROM data_dictionary_entry WHERE dd_id = :did"),
        {"did": synonym_dd_id},
    ).mappings().one_or_none()

    if row is None:
        raise ValueError(f"DD entry {synonym_dd_id!r} not found")
    if row["entry_kind"] != "synonym":
        raise ValueError(f"DD entry {synonym_dd_id!r} is not a synonym (kind={row['entry_kind']!r})")

    surface_term = row["surface_term"]
    wrongly_merged_canonical = row["resolves_to"]

    # 2. Allocate new dd_id for the new canonical entry
    # Use the same sequential allocation pattern: find the max existing DD### and increment
    max_row = session.execute(
        text("SELECT dd_id FROM data_dictionary_entry ORDER BY dd_id DESC LIMIT 1")
    ).scalar_one_or_none()
    next_num = 1
    if max_row:
        try:
            next_num = int(max_row[2:]) + 1
        except (ValueError, IndexError):
            next_num = 1
    new_dd_id = f"DD{next_num:03d}"

    # 3. Create new canonical entry from the surface_term
    session.execute(
        text(
            "INSERT INTO data_dictionary_entry "
            "(dd_id, entry_kind, name, description, attributes, provenance_ref, confidence, created_at) "
            "VALUES (:did, 'canonical', :name, :desc, '[]'::jsonb, :pref, 1.0, :now)"
        ),
        {
            "did": new_dd_id,
            "name": surface_term,
            "desc": f"Canonical entry promoted from rejected synonym '{surface_term}' (was merged with {wrongly_merged_canonical})",
            "pref": row["provenance_ref"],
            "now": datetime.now(timezone.utc),
        },
    )

    # 4. Retire the synonym entry
    session.execute(
        text("UPDATE data_dictionary_entry SET retired_at = :now WHERE dd_id = :did"),
        {"now": datetime.now(timezone.utc), "did": synonym_dd_id},
    )

    # 5. Re-resolution trigger — log dependent bindings for re-resolution
    # Find resolution_log entries for this surface_term that auto-recorded as synonym
    rereg_rows = session.execute(
        text(
            "SELECT log_id, provenance_ref FROM data_dictionary_resolution_log "
            "WHERE surface_term = :st AND outcome = 'synonym' AND auto_recorded = true"
        ),
        {"st": surface_term},
    ).mappings().all()

    reresolution_count = len(rereg_rows)
    if reresolution_count:
        _log.warning(
            "reject_synonym: %d binding(s) for surface_term=%r previously resolved to %s now need re-resolution. "
            "provenance_refs: %s",
            reresolution_count,
            surface_term,
            wrongly_merged_canonical,
            [r["provenance_ref"] for r in rereg_rows],
        )

    return {
        "new_canonical_id": new_dd_id,
        "retired_synonym_id": synonym_dd_id,
        "reresolution_count": reresolution_count,
    }
