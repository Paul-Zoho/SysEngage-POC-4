"""
Public API for the Requirement Matching service.

Per Requirement Matching Spec v0.1 §4.

Stateless per call over the persistent requirement set.
Not a numbered pass — invoked over an assembled requirement set; re-invokable
incrementally.

Operations:
  match_requirement(child, pool) → MatchResult
  match_row(row_n, project_id)   — match all row n requirements against row n-1
  match_set(requirement_ids, project_id) — incremental re-match for a subset

LPM: requirement statements are NEVER rewritten.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from core.db import get_session
from mechanisms.requirement_matching.candidates import get_candidates
from mechanisms.requirement_matching.gaps import (
    compute_downward_gaps,
    write_downward_gap,
    write_upward_gap,
)
from mechanisms.requirement_matching.gating import MATCH_CONFIDENCE_BAND
from mechanisms.requirement_matching.judge import judge_duplicate, judge_refine
from mechanisms.requirement_matching.merge import execute_merge
from sqlalchemy import text, select

_log = logging.getLogger(__name__)


def _append_matching_log(
    session,
    *,
    requirement_id: str,
    outcome: str,
    parent_ids: list[str] | None = None,
    duplicate_of: str | None = None,
    confidence: float | None = None,
    auto_recorded: bool,
) -> None:
    session.execute(
        text(
            "INSERT INTO requirement_matching_log "
            "(requirement_id, outcome, parent_ids, duplicate_of, confidence, auto_recorded, created_at) "
            "VALUES (:rid, :outcome, CAST(:pids AS jsonb), :dup, :conf, :auto, :now)"
        ),
        {
            "rid": requirement_id,
            "outcome": outcome,
            "pids": json.dumps(parent_ids) if parent_ids else None,
            "dup": duplicate_of,
            "conf": confidence,
            "auto": auto_recorded,
            "now": datetime.now(timezone.utc),
        },
    )


def _load_requirements(session, project_id: str) -> list[dict]:
    """Load all active requirements for a project."""
    rows = session.execute(
        text(
            "SELECT requirement_id, statement, requirement_type, row_target, "
            "refines_refs, verification_method, fit_criteria "
            "FROM requirement WHERE project_id = :pid AND retired_at IS NULL"
        ),
        {"pid": project_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def match_requirement(
    child: dict,
    pool: list[dict],
    session=None,
) -> dict[str, Any]:
    """
    Match a single child requirement against the pool.

    Per §4.3:
    1. candidates(child) — DD-based pre-filter
    2. judge_refine + judge_duplicate
    3. Gate and act (write refines_refs / merge / gap record / flag)

    Returns
    -------
    dict: outcome, matched_parent_ids, duplicate_of, confidence, not_yet_matchable
    """
    child_row = str(child.get("row_target", ""))
    child_id = child["requirement_id"]

    # Row 1 check (D-rm-2 decidable): no parents, empty refines_refs is correct
    if child_row == "1":
        return {
            "outcome": "no_parents",
            "matched_parent_ids": [],
            "duplicate_of": None,
            "confidence": 1.0,
            "not_yet_matchable": False,
        }

    # Step 1: DD-based candidate pre-filter
    candidate_parents, candidate_siblings, not_yet_matchable = get_candidates(
        child=child, pool=pool
    )

    if not_yet_matchable:
        if session:
            _append_matching_log(
                session,
                requirement_id=child_id,
                outcome="deferred",
                confidence=None,
                auto_recorded=False,
            )
        return {
            "outcome": "deferred",
            "matched_parent_ids": [],
            "duplicate_of": None,
            "confidence": None,
            "not_yet_matchable": True,
        }

    # Step 2a: Check for duplicates among same-row candidates (D-rm-2)
    dup_result = judge_duplicate(child=child, candidate_siblings=candidate_siblings)
    if dup_result.get("_judge_failed"):
        if session:
            _append_matching_log(
                session, requirement_id=child_id, outcome="flagged",
                confidence=dup_result.get("confidence", 0.0), auto_recorded=False,
            )
        return {"outcome": "flagged", "matched_parent_ids": [], "duplicate_of": None,
                "confidence": 0.0, "not_yet_matchable": False}

    dup_confidence = float(dup_result.get("confidence", 0.0))
    if dup_result.get("outcome") == "duplicate" and dup_confidence >= MATCH_CONFIDENCE_BAND:
        dup_of = dup_result.get("duplicate_of")
        if session and dup_of:
            merge_result = execute_merge(
                session, survivor_id=dup_of, merged_id=child_id,
                rationale=dup_result.get("rationale", ""), auto_recorded=True,
            )
            _append_matching_log(
                session, requirement_id=child_id, outcome="duplicate",
                duplicate_of=dup_of, confidence=dup_confidence, auto_recorded=True,
            )
        return {"outcome": "duplicate", "matched_parent_ids": [], "duplicate_of": dup_of,
                "confidence": dup_confidence, "not_yet_matchable": False}

    # Step 2b: Refine judgement (D-rm-1)
    refine_result = judge_refine(child=child, candidate_parents=candidate_parents)
    if refine_result.get("_judge_failed"):
        if session:
            _append_matching_log(
                session, requirement_id=child_id, outcome="flagged",
                confidence=refine_result.get("confidence", 0.0), auto_recorded=False,
            )
        return {"outcome": "flagged", "matched_parent_ids": [], "duplicate_of": None,
                "confidence": 0.0, "not_yet_matchable": False}

    refine_confidence = float(refine_result.get("confidence", 0.0))
    is_multi_parent = bool(refine_result.get("is_multi_parent", False))

    # Step 3: Gate
    if refine_confidence < MATCH_CONFIDENCE_BAND or is_multi_parent:
        if session:
            _append_matching_log(
                session, requirement_id=child_id, outcome="flagged",
                confidence=refine_confidence, auto_recorded=False,
            )
        return {"outcome": "flagged", "matched_parent_ids": [], "duplicate_of": None,
                "confidence": refine_confidence, "not_yet_matchable": False}

    if refine_result.get("outcome") == "refine":
        matched_parent_ids = refine_result.get("matched_parent_ids", [])
        # Verify each parent is at row_target - 1 (decidable, per VER-rm-01)
        expected_parent_row = str(int(child_row) - 1)
        valid_parent_ids = [
            pid for pid in matched_parent_ids
            if str(next((r.get("row_target", "") for r in pool if r["requirement_id"] == pid), ""))
            == expected_parent_row
        ]
        if session and valid_parent_ids:
            session.execute(
                text("UPDATE requirement SET refines_refs = CAST(:refs AS jsonb) "
                     "WHERE requirement_id = :rid"),
                {"refs": json.dumps(valid_parent_ids), "rid": child_id},
            )
            _append_matching_log(
                session, requirement_id=child_id, outcome="refine",
                parent_ids=valid_parent_ids, confidence=refine_confidence, auto_recorded=True,
            )
        return {"outcome": "refine", "matched_parent_ids": valid_parent_ids, "duplicate_of": None,
                "confidence": refine_confidence, "not_yet_matchable": False}

    # No match
    if session:
        write_upward_gap(session, requirement_id=child_id, row_target=child_row)
        _append_matching_log(
            session, requirement_id=child_id, outcome="no_match",
            confidence=refine_confidence, auto_recorded=True,
        )
    return {"outcome": "no_match", "matched_parent_ids": [], "duplicate_of": None,
            "confidence": refine_confidence, "not_yet_matchable": False}


def match_row(row_n: int, project_id: str) -> dict[str, Any]:
    """
    Match all row n requirements against row n-1.

    Per §3.1: typical invocation. Commits refines_refs, gap records,
    merge retirements, and log entries in a single session per requirement.
    Returns a summary dict.
    """
    session = get_session()
    try:
        pool = _load_requirements(session, project_id)
        row_n_reqs = [r for r in pool if str(r.get("row_target", "")) == str(row_n)]
        parent_reqs = [r for r in pool if str(r.get("row_target", "")) == str(row_n - 1)]

        results: list[dict] = []
        refined_parent_ids: set[str] = set()

        for child in row_n_reqs:
            result = match_requirement(child, pool, session=session)
            results.append({"requirement_id": child["requirement_id"], **result})
            refined_parent_ids.update(result.get("matched_parent_ids", []))

        # Downward gap check: parent-orphans at row n-1
        parent_id_set = {r["requirement_id"] for r in parent_reqs}
        orphaned_parents = compute_downward_gaps(
            parent_ids=parent_id_set,
            refined_parent_ids=refined_parent_ids,
        )
        for orphan_id in orphaned_parents:
            orphan_row = next(
                (r["row_target"] for r in parent_reqs if r["requirement_id"] == orphan_id), str(row_n - 1)
            )
            write_downward_gap(session, requirement_id=orphan_id, row_target=str(orphan_row))

        session.commit()
        return {
            "row_matched": row_n,
            "total": len(row_n_reqs),
            "refine_count": sum(1 for r in results if r["outcome"] == "refine"),
            "no_match_count": sum(1 for r in results if r["outcome"] == "no_match"),
            "flagged_count": sum(1 for r in results if r["outcome"] == "flagged"),
            "duplicate_count": sum(1 for r in results if r["outcome"] == "duplicate"),
            "deferred_count": sum(1 for r in results if r["outcome"] == "deferred"),
            "downward_gap_count": len(orphaned_parents),
            "results": results,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def match_set(requirement_ids: list[str], project_id: str) -> dict[str, Any]:
    """
    Incremental re-match for a specific subset of requirements.
    Useful after GQA generates a new parent and re-descends.
    """
    session = get_session()
    try:
        pool = _load_requirements(session, project_id)
        children = [r for r in pool if r["requirement_id"] in requirement_ids]
        results: list[dict] = []
        for child in children:
            result = match_requirement(child, pool, session=session)
            results.append({"requirement_id": child["requirement_id"], **result})
        session.commit()
        return {"total": len(children), "results": results}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
