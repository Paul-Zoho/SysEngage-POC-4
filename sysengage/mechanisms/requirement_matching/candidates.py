"""
DD-based candidate pre-filter for the Requirement Matching service.

Per Requirement Matching Spec v0.1 §4.1 / D-rm-1.

The pre-filter makes matching tractable by replacing an all-pairs free-text
comparison with an entity-anchored candidate set:

  - Resolve the child requirement's entity anchor by querying
    data_dictionary_entry WHERE provenance_ref = child.requirement_id
    (and data_dictionary_resolution_log for 'existing' outcomes).
  - Candidate parents = row n-1 requirements whose DD entity overlaps with
    the child's canonical entity anchor (or a related entry via DD relationships).
  - If the child's entity is DD-flagged (latest resolution outcome = 'flagged'),
    the child is marked not-yet-matchable and skipped until review completes.
  - If no DD binding exists at all (DD simply hasn't run yet for this requirement),
    fall back to the full row pool (safe; entity-anchored guarantee not yet applicable).

Requirement Derivation §4.4.3a binds entity terms to requirements by calling
resolve_and_record(term, context, provenance_ref=requirement_id), which writes to
data_dictionary_entry (for canonical/synonym outcomes) and
data_dictionary_resolution_log (for all outcomes including existing/flagged).
"""

from __future__ import annotations

import logging

_log = logging.getLogger(__name__)


def _get_canonical_ids_batch(requirement_ids: list[str]) -> dict[str, list[str]]:
    """
    Lazy import wrapper around data_dictionary.service.get_canonical_ids_by_provenance_refs.
    Returns {requirement_id: [canonical_id, ...]} for all given ids.
    """
    try:
        from mechanisms.data_dictionary.service import get_canonical_ids_by_provenance_refs
        return get_canonical_ids_by_provenance_refs(requirement_ids)
    except Exception as exc:
        _log.warning("get_canonical_ids_by_provenance_refs failed: %s", exc)
        return {rid: [] for rid in requirement_ids}


def _is_dd_flagged(requirement_id: str) -> bool:
    """
    Lazy import wrapper around data_dictionary.service.has_flagged_dd_resolution.
    Returns True if the most recent DD resolution attempt for this requirement was flagged.
    """
    try:
        from mechanisms.data_dictionary.service import has_flagged_dd_resolution
        return has_flagged_dd_resolution(requirement_id)
    except Exception as exc:
        _log.warning("has_flagged_dd_resolution(%r) failed: %s", requirement_id, exc)
        return False


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

    child : {requirement_id, statement, row_target, ...}
    pool  : all requirements to search (parents and siblings combined)

    Returns
    -------
    candidate_parents   : row n-1 requirements sharing a DD entity with child
    candidate_siblings  : same-row requirements sharing a DD entity with child
    not_yet_matchable   : True if child's entity is DD-flagged (defer, not fail)

    Entity anchor algorithm
    -----------------------
    1. Batch-load canonical_ids for child + all pool members in one DB round-trip.
    2. If child has no canonical_ids:
       a. If the DD resolution log shows 'flagged' as the latest outcome → defer.
       b. Otherwise DD hasn't run yet → fall back to full pool for this child.
    3. Build anchor_ids = child's canonical_ids ∪ all DD relationships of each.
    4. Candidate = pool member whose canonical_ids intersect anchor_ids.
    5. If the anchor filter yields nothing at a given row (DD coverage gap),
       fall back to the full row at that level rather than returning an empty set.
    """
    child_id: str = child["requirement_id"]
    child_row = str(child.get("row_target", ""))
    parent_row = (
        str(int(child_row) - 1)
        if child_row.isdigit() and int(child_row) > 1
        else None
    )

    # ------------------------------------------------------------------
    # Step 1 — batch-load canonical_ids for child + every pool member
    # ------------------------------------------------------------------
    all_req_ids: list[str] = [child_id] + [
        r["requirement_id"] for r in pool if r.get("requirement_id")
    ]
    canonical_ids_by_req = _get_canonical_ids_batch(all_req_ids)

    child_canonical_ids: list[str] = canonical_ids_by_req.get(child_id, [])

    # ------------------------------------------------------------------
    # Step 2 — handle child with no DD binding
    # ------------------------------------------------------------------
    if not child_canonical_ids:
        if _is_dd_flagged(child_id):
            # DD ran but flagged this requirement's entity term → defer
            _log.debug(
                "get_candidates: %s is DD-flagged → not_yet_matchable", child_id
            )
            return [], [], True

        # DD has not yet bound any entity terms to this child → full-pool fallback
        _log.debug(
            "get_candidates: %s has no DD binding → full-pool fallback", child_id
        )
        parents = (
            [r for r in pool if str(r.get("row_target", "")) == parent_row]
            if parent_row
            else []
        )
        siblings = [
            r for r in pool
            if str(r.get("row_target", "")) == child_row
            and r.get("requirement_id") != child_id
        ]
        return parents, siblings, False

    # ------------------------------------------------------------------
    # Step 3 — build anchor set: child's canonical_ids + related entries
    # ------------------------------------------------------------------
    anchor_ids: set[str] = set(child_canonical_ids)
    for cid in child_canonical_ids:
        anchor_ids.update(_relationships_of(cid))

    _log.debug(
        "get_candidates: %s anchor_ids=%s", child_id, sorted(anchor_ids)
    )

    # ------------------------------------------------------------------
    # Step 4 — filter pool by entity anchor
    # ------------------------------------------------------------------
    candidate_parents: list[dict] = []
    candidate_siblings: list[dict] = []

    for req in pool:
        req_id = req.get("requirement_id")
        if not req_id or req_id == child_id:
            continue

        req_canonical_ids = canonical_ids_by_req.get(req_id, [])
        if not req_canonical_ids:
            continue  # no DD binding for this pool member; skip in entity filter

        if not anchor_ids.intersection(req_canonical_ids):
            continue

        req_row = str(req.get("row_target", ""))
        if req_row == parent_row:
            candidate_parents.append(req)
        elif req_row == child_row:
            candidate_siblings.append(req)

    # ------------------------------------------------------------------
    # Step 5 — fallback per row if anchor filter found nothing (coverage gap)
    # ------------------------------------------------------------------
    if not candidate_parents and parent_row:
        _log.debug(
            "get_candidates: %s no entity-anchored parents → full parent-row fallback",
            child_id,
        )
        candidate_parents = [
            r for r in pool if str(r.get("row_target", "")) == parent_row
        ]
    if not candidate_siblings:
        _log.debug(
            "get_candidates: %s no entity-anchored siblings → full sibling-row fallback",
            child_id,
        )
        candidate_siblings = [
            r for r in pool
            if str(r.get("row_target", "")) == child_row
            and r.get("requirement_id") != child_id
        ]

    return candidate_parents, candidate_siblings, False
