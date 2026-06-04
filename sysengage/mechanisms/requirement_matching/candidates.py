"""
DD-based candidate pre-filter for the Requirement Matching service.

Per Requirement Matching Spec v0.1 §4.1.

The pre-filter makes matching tractable by replacing an all-pairs free-text
comparison with an entity-anchored candidate set:
  - Resolve the child requirement's Object/entity to its canonical DD entry
    (via resolve_object from the DD service).
  - Candidate parents = row n-1 requirements whose Object resolves to the same
    canonical entry, or to a related entry (via a DD relationship).
  - If the child's Object is DD-unresolved (flagged), the child is marked
    not-yet-matchable and skipped until its DD resolution completes.
"""

from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)

# Lazy import to avoid circular deps; data_dictionary.service is the DD public API
def _resolve_object(term: str) -> dict | None:
    try:
        from mechanisms.data_dictionary.service import resolve_object
        return resolve_object(term)
    except Exception as exc:
        _log.warning("resolve_object(%r) failed: %s", term, exc)
        return None


def _relationships_of(dd_id: str) -> list[str]:
    """Return dd_ids of entries directly related to dd_id."""
    try:
        from mechanisms.data_dictionary.service import relationships_of
        related = relationships_of(dd_id)
        return [r["other_id"] for r in related]
    except Exception as exc:
        _log.warning("relationships_of(%r) failed: %s", dd_id, exc)
        return []


def get_candidates(
    *,
    child: dict,
    pool: list[dict],
) -> tuple[list[dict], list[dict], bool]:
    """
    Return (candidate_parents, candidate_siblings, not_yet_matchable) for child.

    child   : {requirement_id, statement, row_target, object_term?, ...}
    pool    : all requirements to search (parents and siblings)

    Returns
    -------
    candidate_parents   : row n-1 requirements anchored to the same DD entity
    candidate_siblings  : same-row requirements anchored to the same DD entity
    not_yet_matchable   : True if child's Object is DD-unresolved (defer, not fail)
    """
    child_row = str(child.get("row_target", ""))
    parent_row = str(int(child_row) - 1) if child_row.isdigit() and int(child_row) > 1 else None

    object_term = (child.get("object_term") or "").strip()
    if not object_term:
        # No Object term — cannot do entity-anchored matching; return full pool as candidates
        # (the judge will compare by abstraction-level reasoning only)
        parents = [r for r in pool if str(r.get("row_target", "")) == parent_row] if parent_row else []
        siblings = [r for r in pool if str(r.get("row_target", "")) == child_row
                    and r.get("requirement_id") != child.get("requirement_id")]
        return parents, siblings, False

    # Try to resolve the Object term against the DD
    resolution = _resolve_object(object_term)
    if resolution is None:
        # DD service call failed (should not happen in normal flow)
        _log.warning("DD resolve_object returned None for %r — falling back to full pool", object_term)
        parents = [r for r in pool if str(r.get("row_target", "")) == parent_row] if parent_row else []
        siblings = [r for r in pool if str(r.get("row_target", "")) == child_row
                    and r.get("requirement_id") != child.get("requirement_id")]
        return parents, siblings, False

    if resolution.get("status") == "flagged":
        # DD-unresolved Object → mark as not-yet-matchable (D-rm-3 / §4.1)
        return [], [], True

    canonical_id = resolution.get("dd_id")
    if not canonical_id:
        # Unresolved/unknown → no entity anchor; use full pool
        parents = [r for r in pool if str(r.get("row_target", "")) == parent_row] if parent_row else []
        siblings = [r for r in pool if str(r.get("row_target", "")) == child_row
                    and r.get("requirement_id") != child.get("requirement_id")]
        return parents, siblings, False

    # Build entity anchor set: canonical_id + its directly related entries
    anchor_ids = {canonical_id}
    anchor_ids.update(_relationships_of(canonical_id))

    # Filter pool by entity anchor
    def _shares_entity(req: dict) -> bool:
        other_term = (req.get("object_term") or "").strip()
        if not other_term:
            return False
        other_res = _resolve_object(other_term)
        if other_res is None or other_res.get("status") == "flagged":
            return False
        return other_res.get("dd_id") in anchor_ids

    candidate_parents: list[dict] = []
    candidate_siblings: list[dict] = []

    for req in pool:
        req_row = str(req.get("row_target", ""))
        req_id = req.get("requirement_id")
        if req_id == child.get("requirement_id"):
            continue
        if req_row == parent_row and _shares_entity(req):
            candidate_parents.append(req)
        elif req_row == child_row and _shares_entity(req):
            candidate_siblings.append(req)

    # If no candidates found by entity anchor, fall back to full pool at that row
    # (ensures we don't miss cross-row matches when DD coverage is low)
    if not candidate_parents and parent_row:
        candidate_parents = [r for r in pool if str(r.get("row_target", "")) == parent_row]
    if not candidate_siblings:
        candidate_siblings = [r for r in pool if str(r.get("row_target", "")) == child_row
                              and r.get("requirement_id") != child.get("requirement_id")]

    return candidate_parents, candidate_siblings, False
