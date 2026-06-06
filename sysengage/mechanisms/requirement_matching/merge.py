"""
Duplicate-merge and reference repointing for the Requirement Matching service.

Per Requirement Matching Spec v0.1 §4.5 (D-rm-1).

When two requirements at the same row duplicate:
  - Collapse to one survivor (preserve union of cci_refs / domain_refs / provenance).
  - Repoint references: any refines_refs in the row BELOW that pointed at the
    merged-away id is repointed to the survivor.
  - The retired id is marked retired, NOT deleted (id not reused).
  - High-confidence merges auto-record; low-confidence flag for Practitioner.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import text

_log = logging.getLogger(__name__)


def execute_merge(
    session: Session,
    *,
    survivor_id: str,
    merged_id: str,
    project_id: str,
    rationale: str,
    auto_recorded: bool,
) -> dict:
    """
    Collapse merged_id into survivor_id within project_id.

    1. Merge cci_refs, domain_refs from merged_id into survivor_id.
    2. Repoint refines_refs in all requirements that reference merged_id.
    3. Mark merged_id as retired.

    project_id is required because requirement_id values are project-scoped
    (e.g. R001 exists in every project); without it, queries return multiple rows.

    Returns dict: {survivor_id, retired_id, repointed_count}
    """
    now = datetime.now(timezone.utc)

    # Load both requirements (always filter by project_id — requirement_id is not globally unique)
    survivor = session.execute(
        text(
            "SELECT cci_refs, domain_refs FROM requirement "
            "WHERE requirement_id = :rid AND project_id = :pid"
        ),
        {"rid": survivor_id, "pid": project_id},
    ).mappings().one_or_none()

    merged = session.execute(
        text(
            "SELECT cci_refs, domain_refs FROM requirement "
            "WHERE requirement_id = :rid AND project_id = :pid"
        ),
        {"rid": merged_id, "pid": project_id},
    ).mappings().one_or_none()

    if survivor is None or merged is None:
        raise ValueError(f"Cannot find survivor={survivor_id!r} or merged={merged_id!r} in project {project_id!r}")

    # Union cci_refs and domain_refs (de-duplicate)
    merged_cci_refs = list(set(
        (survivor["cci_refs"] or []) + (merged["cci_refs"] or [])
    ))
    merged_domain_refs = list(set(
        (survivor["domain_refs"] or []) + (merged["domain_refs"] or [])
    ))

    # Update survivor
    session.execute(
        text(
            "UPDATE requirement SET "
            "cci_refs = CAST(:cci_refs AS jsonb), domain_refs = CAST(:domain_refs AS jsonb) "
            "WHERE requirement_id = :rid AND project_id = :pid"
        ),
        {
            "cci_refs": json.dumps(sorted(merged_cci_refs)),
            "domain_refs": json.dumps(sorted(merged_domain_refs)),
            "rid": survivor_id,
            "pid": project_id,
        },
    )

    # Retire merged requirement
    session.execute(
        text(
            "UPDATE requirement SET retired_at = :now "
            "WHERE requirement_id = :rid AND project_id = :pid"
        ),
        {"now": now, "rid": merged_id, "pid": project_id},
    )

    # Repoint refines_refs: any requirement whose refines_refs contains merged_id
    # should be repointed to survivor_id (scoped to project_id)
    dependents = session.execute(
        text(
            "SELECT requirement_id, refines_refs FROM requirement "
            "WHERE refines_refs @> CAST(:rid_array AS jsonb) "
            "  AND project_id = :pid AND retired_at IS NULL"
        ),
        {"rid_array": json.dumps([merged_id]), "pid": project_id},
    ).mappings().all()

    repointed_count = 0
    for dep in dependents:
        old_refs = dep["refines_refs"] or []
        new_refs = [survivor_id if r == merged_id else r for r in old_refs]
        session.execute(
            text("UPDATE requirement SET refines_refs = CAST(:refs AS jsonb) "
                 "WHERE requirement_id = :rid"),
            {"refs": json.dumps(new_refs), "rid": dep["requirement_id"]},
        )
        repointed_count += 1

    _log.info(
        "Merged %s → %s (auto_recorded=%s, repointed=%d): %s",
        merged_id, survivor_id, auto_recorded, repointed_count, rationale,
    )

    return {
        "survivor_id": survivor_id,
        "retired_id": merged_id,
        "repointed_count": repointed_count,
    }
