"""
Public API for the Requirement Matching service.

Per Requirement Matching Service Spec v0.2 §4.

Stateless per call over the persistent requirement set.
Not a numbered pass — invoked over an assembled requirement set; re-invokable
incrementally.

Operations:
  match_requirement(child, pool) → result dict
  match_row(row_n, project_id, practitioner_id)   — match all row n against row n-1
  match_set(requirement_ids, project_id, practitioner_id) — incremental re-match

v0.2 changes vs v0.1:
  - _append_matching_log() removed; provenance now goes into a per-execution
    AnalysisPass (ProvAccumulator / provenance.py), not service-log tables.
  - match_requirement() returns candidates_considered, multi_parent_ambiguous,
    ai_fingerprints, and gap_record (when applicable) so the caller accumulates
    full provenance.
  - match_row() / match_set() write an AnalysisPass at commit time.
  - gaps.py functions now return dicts (not DB writes).

LPM: requirement statements are NEVER rewritten.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from core.db import get_session
from mechanisms.requirement_matching.candidates import get_candidates
from mechanisms.requirement_matching.gaps import (
    compute_downward_gaps,
    make_downward_gap_record,
    make_upward_gap_record,
)
from mechanisms.requirement_matching.gating import MATCH_CONFIDENCE_BAND
from mechanisms.requirement_matching.judge import judge_duplicate, judge_refine
from mechanisms.requirement_matching.merge import execute_merge
from mechanisms.requirement_matching.provenance import ProvAccumulator
from sqlalchemy import text

_log = logging.getLogger(__name__)

_DEFAULT_PRACTITIONER = "SH001"


def _load_requirements(session, project_id: str) -> list[dict]:
    """Load all active requirements for a project, deterministic order."""
    rows = session.execute(
        text(
            "SELECT requirement_id, project_id, statement, requirement_type, row_target, "
            "refines_refs, verification_method, fit_criteria "
            "FROM requirement WHERE project_id = :pid AND retired_at IS NULL "
            "ORDER BY requirement_id"
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
    3. Gate and act (write refines_refs / merge)

    Returns
    -------
    dict with keys:
      outcome             — refine|no_match|duplicate|flagged|deferred|no_parents
      matched_parent_ids  — list of parent ids (refine only)
      duplicate_of        — survivor id (duplicate only)
      confidence          — float or None
      not_yet_matchable   — bool
      candidates_considered — list of requirement_ids from the DD pre-filter
      multi_parent_ambiguous — bool
      auto_recorded       — bool
      ai_fingerprints     — list of fingerprint dicts from judge calls
      gap_record          — dict or None (upward gap, when outcome=no_match, row>1)
    """
    child_row = str(child.get("row_target", ""))
    child_id = child["requirement_id"]
    _child_pid = child.get("project_id", "")

    # Row 1: no parents, empty refines_refs is correct (spec §8, F-rm-7)
    if child_row == "1":
        return {
            "outcome": "no_parents",
            "matched_parent_ids": [],
            "duplicate_of": None,
            "confidence": 1.0,
            "not_yet_matchable": False,
            "candidates_considered": [],
            "multi_parent_ambiguous": False,
            "auto_recorded": False,
            "ai_fingerprints": [],
            "gap_record": None,
        }

    # Step 1: DD-based candidate pre-filter
    candidate_parents, candidate_siblings, not_yet_matchable = get_candidates(
        child=child, pool=pool
    )
    candidate_parent_ids = [r["requirement_id"] for r in candidate_parents]
    candidate_sibling_ids = [r["requirement_id"] for r in candidate_siblings]

    if not_yet_matchable:
        return {
            "outcome": "deferred",
            "matched_parent_ids": [],
            "duplicate_of": None,
            "confidence": None,
            "not_yet_matchable": True,
            "candidates_considered": [],
            "multi_parent_ambiguous": False,
            "auto_recorded": False,
            "ai_fingerprints": [],
            "gap_record": None,
        }

    all_fingerprints: list[dict] = []

    # Step 2a: Check for duplicates among same-row candidates (D-rm-2)
    dup_result = judge_duplicate(child=child, candidate_siblings=candidate_siblings)
    all_fingerprints.extend(dup_result.get("_fingerprints", []))

    if dup_result.get("_judge_failed"):
        return {
            "outcome": "flagged",
            "matched_parent_ids": [],
            "duplicate_of": None,
            "confidence": dup_result.get("confidence", 0.0),
            "not_yet_matchable": False,
            "candidates_considered": candidate_sibling_ids,
            "multi_parent_ambiguous": False,
            "auto_recorded": False,
            "ai_fingerprints": all_fingerprints,
            "gap_record": None,
        }

    dup_confidence = float(dup_result.get("confidence", 0.0))
    if dup_result.get("outcome") == "duplicate" and dup_confidence >= MATCH_CONFIDENCE_BAND:
        dup_of = dup_result.get("duplicate_of")
        merge_record: dict | None = None
        if session and dup_of:
            mr = execute_merge(
                session, survivor_id=dup_of, merged_id=child_id,
                project_id=_child_pid,
                rationale=dup_result.get("rationale", ""), auto_recorded=True,
            )
            merge_record = mr
        return {
            "outcome": "duplicate",
            "matched_parent_ids": [],
            "duplicate_of": dup_of,
            "confidence": dup_confidence,
            "not_yet_matchable": False,
            "candidates_considered": candidate_sibling_ids,
            "multi_parent_ambiguous": False,
            "auto_recorded": True,
            "ai_fingerprints": all_fingerprints,
            "gap_record": None,
            "_merge_record": merge_record,
        }

    # Step 2b: Refine judgement (D-rm-1)
    refine_result = judge_refine(child=child, candidate_parents=candidate_parents)
    all_fingerprints.extend(refine_result.get("_fingerprints", []))

    if refine_result.get("_judge_failed"):
        return {
            "outcome": "flagged",
            "matched_parent_ids": [],
            "duplicate_of": None,
            "confidence": refine_result.get("confidence", 0.0),
            "not_yet_matchable": False,
            "candidates_considered": candidate_parent_ids,
            "multi_parent_ambiguous": False,
            "auto_recorded": False,
            "ai_fingerprints": all_fingerprints,
            "gap_record": None,
        }

    refine_confidence = float(refine_result.get("confidence", 0.0))
    is_multi_parent = bool(refine_result.get("is_multi_parent", False))

    # Step 3: Gate
    if refine_confidence < MATCH_CONFIDENCE_BAND or is_multi_parent:
        return {
            "outcome": "flagged",
            "matched_parent_ids": [],
            "duplicate_of": None,
            "confidence": refine_confidence,
            "not_yet_matchable": False,
            "candidates_considered": candidate_parent_ids,
            "multi_parent_ambiguous": is_multi_parent,
            "auto_recorded": False,
            "ai_fingerprints": all_fingerprints,
            "gap_record": None,
        }

    if refine_result.get("outcome") == "refine":
        matched_parent_ids = refine_result.get("matched_parent_ids", [])
        # Verify each parent is at row_target - 1 (decidable, per VER-rm-01)
        expected_parent_row = str(int(child_row) - 1)
        valid_parent_ids = [
            pid for pid in matched_parent_ids
            if str(next(
                (r.get("row_target", "") for r in pool if r["requirement_id"] == pid), ""
            )) == expected_parent_row
        ]
        if session and valid_parent_ids:
            session.execute(
                text("UPDATE requirement SET refines_refs = CAST(:refs AS jsonb) "
                     "WHERE requirement_id = :rid AND project_id = :pid"),
                {"refs": json.dumps(valid_parent_ids), "rid": child_id, "pid": _child_pid},
            )
        return {
            "outcome": "refine",
            "matched_parent_ids": valid_parent_ids,
            "duplicate_of": None,
            "confidence": refine_confidence,
            "not_yet_matchable": False,
            "candidates_considered": candidate_parent_ids,
            "multi_parent_ambiguous": is_multi_parent,
            "auto_recorded": True,
            "ai_fingerprints": all_fingerprints,
            "gap_record": None,
        }

    # No match — emit upward gap record (spec §4.6, F86)
    gap = make_upward_gap_record(
        requirement_id=child_id, row_target=child_row, project_id=_child_pid
    )
    return {
        "outcome": "no_match",
        "matched_parent_ids": [],
        "duplicate_of": None,
        "confidence": refine_confidence,
        "not_yet_matchable": False,
        "candidates_considered": candidate_parent_ids,
        "multi_parent_ambiguous": False,
        "auto_recorded": True,
        "ai_fingerprints": all_fingerprints,
        "gap_record": gap,
    }


def match_row(
    row_n: int,
    project_id: str,
    practitioner_id: str = _DEFAULT_PRACTITIONER,
) -> dict[str, Any]:
    """
    Match all row n requirements against row n-1.

    Per §3.1: typical invocation.  Commits refines_refs, merge retirements,
    and a single AnalysisPass (provenance) in one transaction.
    Returns a summary dict.
    """
    prov = ProvAccumulator(
        project_id=project_id,
        practitioner_id=practitioner_id,
        row_n=row_n,
        parent_row_n=row_n - 1,
    )

    session = get_session()
    try:
        pool = _load_requirements(session, project_id)
        row_n_reqs = [r for r in pool if str(r.get("row_target", "")) == str(row_n)]
        parent_reqs = [r for r in pool if str(r.get("row_target", "")) == str(row_n - 1)]

        refined_parent_ids: set[str] = set()

        for child in row_n_reqs:
            result = match_requirement(child, pool, session=session)

            # Accumulate provenance
            prov.add_match_record(
                requirement_id=child["requirement_id"],
                outcome=result["outcome"],
                confidence=result.get("confidence"),
                candidates_considered=result.get("candidates_considered", []),
                parent_ids=result.get("matched_parent_ids"),
                duplicate_of=result.get("duplicate_of"),
                auto_recorded=result.get("auto_recorded", False),
                multi_parent_ambiguous=result.get("multi_parent_ambiguous", False),
            )
            prov.add_fingerprints(result.get("ai_fingerprints", []))
            if result.get("gap_record"):
                prov.add_gap_record(result["gap_record"])
            if result.get("_merge_record"):
                prov.add_merge_record(result["_merge_record"])

            refined_parent_ids.update(result.get("matched_parent_ids", []))

        # Downward gap check: parent-orphans at row n-1
        parent_id_set = {r["requirement_id"] for r in parent_reqs}
        orphaned_parents = compute_downward_gaps(
            parent_ids=parent_id_set,
            refined_parent_ids=refined_parent_ids,
        )
        for orphan_id in orphaned_parents:
            orphan_row = next(
                (r["row_target"] for r in parent_reqs if r["requirement_id"] == orphan_id),
                str(row_n - 1),
            )
            gap = make_downward_gap_record(
                requirement_id=orphan_id, row_target=str(orphan_row), project_id=project_id
            )
            prov.add_gap_record(gap)

        # Write AnalysisPass and commit
        pass_id = prov.write_pass(session)
        session.commit()

        counts = {r["outcome"]: 0 for r in []}
        match_records = prov.match_records
        return {
            "row_matched": row_n,
            "pass_id": pass_id,
            "total": len(row_n_reqs),
            "refine_count": sum(1 for r in match_records if r["outcome"] == "refine"),
            "no_match_count": sum(1 for r in match_records if r["outcome"] == "no_match"),
            "flagged_count": sum(1 for r in match_records if r["outcome"] == "flagged"),
            "duplicate_count": sum(1 for r in match_records if r["outcome"] == "duplicate"),
            "deferred_count": sum(1 for r in match_records if r["outcome"] == "deferred"),
            "downward_gap_count": len(orphaned_parents),
            "execution_status": prov._compute_execution_status(),
        }

    except Exception as exc:
        session.rollback()
        try:
            prov.write_failure_pass(failure_reason=str(exc))
        except Exception as prov_exc:
            _log.error("Failed to write failure AnalysisPass: %s", prov_exc)
        raise
    finally:
        session.close()


def match_set(
    requirement_ids: list[str],
    project_id: str,
    practitioner_id: str = _DEFAULT_PRACTITIONER,
) -> dict[str, Any]:
    """
    Incremental re-match for a specific subset of requirements.
    Useful after GQA generates a new parent and re-descends.
    Writes a single AnalysisPass per invocation (mechanism_data.row_ref=None).
    """
    prov = ProvAccumulator(
        project_id=project_id,
        practitioner_id=practitioner_id,
        row_n=None,
        parent_row_n=None,
    )

    session = get_session()
    try:
        pool = _load_requirements(session, project_id)
        children = [r for r in pool if r["requirement_id"] in requirement_ids]

        for child in children:
            result = match_requirement(child, pool, session=session)
            prov.add_match_record(
                requirement_id=child["requirement_id"],
                outcome=result["outcome"],
                confidence=result.get("confidence"),
                candidates_considered=result.get("candidates_considered", []),
                parent_ids=result.get("matched_parent_ids"),
                duplicate_of=result.get("duplicate_of"),
                auto_recorded=result.get("auto_recorded", False),
                multi_parent_ambiguous=result.get("multi_parent_ambiguous", False),
            )
            prov.add_fingerprints(result.get("ai_fingerprints", []))
            if result.get("gap_record"):
                prov.add_gap_record(result["gap_record"])
            if result.get("_merge_record"):
                prov.add_merge_record(result["_merge_record"])

        pass_id = prov.write_pass(session)
        session.commit()

        match_records = prov.match_records
        return {
            "total": len(children),
            "pass_id": pass_id,
            "refine_count": sum(1 for r in match_records if r["outcome"] == "refine"),
            "no_match_count": sum(1 for r in match_records if r["outcome"] == "no_match"),
            "flagged_count": sum(1 for r in match_records if r["outcome"] == "flagged"),
        }

    except Exception as exc:
        session.rollback()
        try:
            prov.write_failure_pass(failure_reason=str(exc))
        except Exception as prov_exc:
            _log.error("Failed to write failure AnalysisPass: %s", prov_exc)
        raise
    finally:
        session.close()
