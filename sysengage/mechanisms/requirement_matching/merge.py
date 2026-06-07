"""
Duplicate-merge and reference repointing for the Requirement Matching service.

Per Requirement Matching Spec v0.3 §4.5.

v0.3 changes (this version):
  Duplicate claims are pairwise and may be reciprocal (A↔B) or chained (A≡B≡C).
  This module first resolves all pairs into duplicate equivalence classes (union-find /
  connected components), then executes ONE merge per class with:
    - survivor  = min(requirement_id) — deterministic, order-independent
    - retired   = all other class members (soft-retire, id not reused)
    - refs      = union of cci_refs / domain_refs across the whole class
    - repoint   = any refines_refs pointing at any retired id → repointed to survivor
    - schema    = {survivor_id, retired_ids: [...], repointed_refs: [...], confidence}

  Hard Non-Loss assertion (fail-closed): each class must have exactly one active
  survivor after the merge.  If survivor_id is in retired_ids OR len(class) -
  len(retired) ≠ 1, NonLossViolationError is raised and the class is left intact.
  This is the explicit guard against the both-members-retired failure observed in
  PMT T&E (R026↔R035) and confirmed in R2 Run8.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import text

_log = logging.getLogger(__name__)


class NonLossViolationError(Exception):
    """
    Raised when a duplicate equivalence class merge would leave no active survivor.
    The merge is rejected; all class members are left intact and flagged for review.
    """


# ---------------------------------------------------------------------------
# Union-find helpers
# ---------------------------------------------------------------------------

def build_equivalence_classes(pairs: list[tuple[str, str]]) -> list[set[str]]:
    """
    Given a list of (a, b) duplicate-of directed edges, build connected components.

    The direction of each edge is irrelevant — {a, b} belong to the same class
    regardless of which way the judge nominated the relationship.  Reciprocal pairs
    (A→B and B→A) and chained triples (A→B and B→C) both collapse into one class.

    Returns a list of sets; each set is one equivalence class.
    Only requirement_ids that appear in at least one pair are included.
    """
    parent: dict[str, str] = {}

    def _find(x: str) -> str:
        if parent.setdefault(x, x) != x:
            parent[x] = _find(parent[x])
        return parent[x]

    def _union(x: str, y: str) -> None:
        parent[_find(x)] = _find(y)

    for a, b in pairs:
        _union(a, b)

    classes: dict[str, set[str]] = {}
    for node in parent:
        root = _find(node)
        classes.setdefault(root, set()).add(node)

    return list(classes.values())


def select_survivor(class_members: Iterable[str]) -> str:
    """
    Return the minimum requirement_id in the class.
    Deterministic and order-independent — a reciprocal pair always resolves
    to the same survivor regardless of processing order.
    """
    return min(class_members)


# ---------------------------------------------------------------------------
# Class-level merge execution
# ---------------------------------------------------------------------------

def execute_class_merge(
    session,
    *,
    class_members: set[str],
    survivor_id: str,
    project_id: str,
    confidence: float,
    rationale: str,
    auto_recorded: bool,
) -> dict:
    """
    Merge an entire equivalence class down to survivor_id.

    1. Hard Non-Loss assertion — fail-closed before any DB write.
    2. Load all member rows; union cci_refs / domain_refs onto survivor.
    3. Retire all non-survivors (soft retire, id not reused).
    4. Repoint refines_refs: any active requirement whose refines_refs contains a
       retired id → repointed to survivor_id.

    Returns
    -------
    {
        "survivor_id": str,
        "retired_ids": list[str],          # sorted, non-empty
        "repointed_refs": list[str],       # requirement_ids that were repointed
        "confidence": float,
        "auto_recorded": bool,
    }

    Raises
    ------
    NonLossViolationError
        If the assertion would retire all members (survivor_id also in retired set,
        or class has only one member but it would be both survivor and retired).
        The caller must leave all class members intact and flag them for review.
    ValueError
        If survivor_id is not found in project_id.
    """
    retired_ids = sorted(class_members - {survivor_id})

    # Hard Non-Loss assertion (fail-closed)
    expected_active = len(class_members) - len(retired_ids)
    if survivor_id in retired_ids or expected_active != 1:
        raise NonLossViolationError(
            f"Non-Loss assertion failed: class={sorted(class_members)!r}, "
            f"survivor={survivor_id!r}, retired={retired_ids!r}. "
            "Retiring all members of a class is forbidden. "
            "Merge rejected; requirements left intact, flagged for review."
        )

    if not retired_ids:
        # Single-member class — no merge needed (shouldn't normally reach here,
        # but handle gracefully rather than crashing)
        _log.debug("execute_class_merge called for single-member class %r — no-op", survivor_id)
        return {
            "survivor_id": survivor_id,
            "retired_ids": [],
            "repointed_refs": [],
            "confidence": confidence,
            "auto_recorded": auto_recorded,
        }

    now = datetime.now(timezone.utc)

    # Load survivor
    survivor_row = session.execute(
        text(
            "SELECT cci_refs, domain_refs FROM requirement "
            "WHERE requirement_id = :rid AND project_id = :pid"
        ),
        {"rid": survivor_id, "pid": project_id},
    ).mappings().one_or_none()
    if survivor_row is None:
        raise ValueError(
            f"Survivor {survivor_id!r} not found in project {project_id!r}"
        )

    all_cci_refs: set[str] = set(survivor_row["cci_refs"] or [])
    all_domain_refs: set[str] = set(survivor_row["domain_refs"] or [])

    # Union refs from all non-survivors and retire them
    for retired_id in retired_ids:
        member_row = session.execute(
            text(
                "SELECT cci_refs, domain_refs FROM requirement "
                "WHERE requirement_id = :rid AND project_id = :pid"
            ),
            {"rid": retired_id, "pid": project_id},
        ).mappings().one_or_none()

        if member_row is not None:
            all_cci_refs.update(member_row["cci_refs"] or [])
            all_domain_refs.update(member_row["domain_refs"] or [])
        else:
            _log.warning(
                "Retiring %r but it was not found in project %r — skipping ref union",
                retired_id, project_id,
            )

        session.execute(
            text(
                "UPDATE requirement SET retired_at = :now "
                "WHERE requirement_id = :rid AND project_id = :pid"
            ),
            {"now": now, "rid": retired_id, "pid": project_id},
        )

    # Update survivor with unioned refs
    session.execute(
        text(
            "UPDATE requirement SET "
            "cci_refs = CAST(:cci_refs AS jsonb), "
            "domain_refs = CAST(:domain_refs AS jsonb) "
            "WHERE requirement_id = :rid AND project_id = :pid"
        ),
        {
            "cci_refs": json.dumps(sorted(all_cci_refs)),
            "domain_refs": json.dumps(sorted(all_domain_refs)),
            "rid": survivor_id,
            "pid": project_id,
        },
    )

    # Repoint refines_refs for each retired id
    repointed_refs: list[str] = []
    for retired_id in retired_ids:
        dependents = session.execute(
            text(
                "SELECT requirement_id, refines_refs FROM requirement "
                "WHERE refines_refs @> CAST(:rid_array AS jsonb) "
                "  AND project_id = :pid AND retired_at IS NULL"
            ),
            {"rid_array": json.dumps([retired_id]), "pid": project_id},
        ).mappings().all()

        for dep in dependents:
            old_refs = dep["refines_refs"] or []
            new_refs = [survivor_id if r == retired_id else r for r in old_refs]
            session.execute(
                text(
                    "UPDATE requirement SET refines_refs = CAST(:refs AS jsonb) "
                    "WHERE requirement_id = :rid AND project_id = :pid"
                ),
                {"refs": json.dumps(new_refs), "rid": dep["requirement_id"], "pid": project_id},
            )
            dep_id = dep["requirement_id"]
            if dep_id not in repointed_refs:
                repointed_refs.append(dep_id)

    _log.info(
        "Class merge: survivor=%s, retired=%s, repointed=%s (auto_recorded=%s): %s",
        survivor_id, retired_ids, repointed_refs, auto_recorded, rationale,
    )

    return {
        "survivor_id": survivor_id,
        "retired_ids": retired_ids,
        "repointed_refs": repointed_refs,
        "confidence": confidence,
        "auto_recorded": auto_recorded,
    }
