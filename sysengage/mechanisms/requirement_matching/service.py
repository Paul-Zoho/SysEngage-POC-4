"""
Public API for the Requirement Matching service.

Per Requirement Matching Service Spec v0.5 §4.

Stateless per call over the persistent requirement set.
Not a numbered pass — invoked over an assembled requirement set; re-invokable
incrementally.

Operations:
  match_requirement(child, pool) → result dict   — pure judge, no DB writes
  match_row(row_n, project_id, practitioner_id)  — match all row n against row n-1
  match_set(requirement_ids, project_id, ...)    — incremental re-match

v0.3 changes vs v0.2:
  - match_row() restructured into two passes to support union-find merge:
      Pass 1 — judge all row-n requirements (no DB writes); collect duplicate pairs.
      Union-find — resolve all collected pairs into equivalence classes; select
                   survivor = min(requirement_id) per class (deterministic).
      Pass 2 — execute one execute_class_merge() per class; write refines_refs
               for non-retired requirements only.
  - match_requirement() no longer performs any DB writes; session parameter removed.
    All DB writes are concentrated in match_row() / match_set().
  - merge_records schema: retired_ids[] (array) + repointed_refs[] (list of ids).
  - Hard Non-Loss assertion in execute_class_merge() (fail-closed; NonLossViolationError
    leaves the class intact and flags all members for review).

v0.2 changes vs v0.1:
  - _append_matching_log() removed; provenance goes into a per-execution AnalysisPass.
  - gaps.py functions return dicts (not DB writes).

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
    make_no_candidates_gap_record,
    make_upward_gap_record,
)
from mechanisms.requirement_matching.gating import MATCH_CONFIDENCE_BAND
from mechanisms.requirement_matching.judge import judge_duplicate, judge_refine
from mechanisms.requirement_matching.merge import (
    NonLossViolationError,
    build_equivalence_classes,
    execute_class_merge,
    select_survivor,
)
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
) -> dict[str, Any]:
    """
    Judge a single child requirement against the pool.  Pure function — no DB writes.

    Per §4.3:
    1. candidates(child) — DD-based pre-filter
    2. judge_duplicate (same-row) then judge_refine (cross-row)
    3. Gate and classify

    DB writes (refines_refs, merge retirements) are performed by the caller
    (match_row / match_set) after equivalence-class resolution.

    Returns
    -------
    dict with keys:
      outcome             — refine|no_match|duplicate|flagged|deferred|no_parents
      matched_parent_ids  — list of parent ids (refine only, pre-row-validation)
      duplicate_of        — id nominated by judge (duplicate only; may be updated
                            by caller to actual class survivor after union-find)
      confidence          — float or None
      not_yet_matchable   — bool
      candidates_considered — list of requirement_ids from the DD pre-filter
      multi_parent_ambiguous — bool
      auto_recorded       — bool
      ai_fingerprints     — list of fingerprint dicts from judge calls
      gap_record          — dict or None (upward gap when outcome=no_match, row>1)
    """
    child_row = str(child.get("row_target", ""))
    child_id = child["requirement_id"]

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

    # D-rm-6: DD-resolved child with zero parent candidates → no_candidates.
    # Distinct from no_match (≥1 candidate offered but none judged a parent).
    # Do NOT call judge_refine on an empty candidate set — that would silently
    # stamp no_match (rationale: "No candidate parents to compare against"),
    # masking what is really a pre-filter / cross-row vocabulary miss.
    if not candidate_parents:
        _child_pid = child.get("project_id", "")
        gap = make_no_candidates_gap_record(
            requirement_id=child_id, row_target=child_row, project_id=_child_pid
        )
        return {
            "outcome": "no_candidates",
            "matched_parent_ids": [],
            "duplicate_of": None,
            "confidence": None,
            "not_yet_matchable": False,
            "candidates_considered": [],
            "multi_parent_ambiguous": False,
            "auto_recorded": False,
            "ai_fingerprints": [],
            "gap_record": gap,
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
        # NOTE: No DB write here. The caller (match_row) collects all duplicate pairs,
        # runs union-find to form equivalence classes, and executes one class merge
        # per class with survivor = min(requirement_id).
        return {
            "outcome": "duplicate",
            "matched_parent_ids": [],
            "duplicate_of": dup_of,
            "confidence": dup_confidence,
            "not_yet_matchable": False,
            "candidates_considered": candidate_sibling_ids,
            "multi_parent_ambiguous": False,
            "auto_recorded": dup_confidence >= MATCH_CONFIDENCE_BAND,
            "ai_fingerprints": all_fingerprints,
            "gap_record": None,
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
        # NOTE: row-validation and DB write happen in the caller after union-find.
        return {
            "outcome": "refine",
            "matched_parent_ids": matched_parent_ids,
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
    _child_pid = child.get("project_id", "")
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


def _apply_refine_write(session, child: dict, result: dict, pool: list[dict]) -> None:
    """Write refines_refs for a refine-outcome child (row-validation included)."""
    child_row = str(child.get("row_target", ""))
    child_id = child["requirement_id"]
    project_id = child.get("project_id", "")
    matched_parent_ids = result.get("matched_parent_ids", [])

    if not matched_parent_ids:
        return

    expected_parent_row = str(int(child_row) - 1) if child_row.isdigit() else ""
    valid_parent_ids = [
        pid for pid in matched_parent_ids
        if str(next(
            (r.get("row_target", "") for r in pool if r["requirement_id"] == pid),
            "",
        )) == expected_parent_row
    ]
    if not valid_parent_ids:
        return

    session.execute(
        text(
            "UPDATE requirement SET refines_refs = CAST(:refs AS jsonb) "
            "WHERE requirement_id = :rid AND project_id = :pid"
        ),
        {"refs": json.dumps(valid_parent_ids), "rid": child_id, "pid": project_id},
    )
    result["matched_parent_ids"] = valid_parent_ids


def match_row(
    row_n: int,
    project_id: str,
    practitioner_id: str = _DEFAULT_PRACTITIONER,
) -> dict[str, Any]:
    """
    Match all row n requirements against row n-1.

    Per §3.1 / §4.5: two-pass design for correct duplicate handling.
      Pass 1 — judge every row-n requirement (pure; no DB writes).
               Collect duplicate (child_id, duplicate_of) pairs.
      Union-find — resolve pairs into equivalence classes;
                   survivor = min(requirement_id) per class.
      Pass 2 — execute one execute_class_merge() per class;
               write refines_refs for non-retired requirements;
               write one AnalysisPass and commit.

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

        # ----------------------------------------------------------------
        # Pass 1: judge all row-n requirements (no DB writes)
        # ----------------------------------------------------------------
        judged: list[tuple[dict, dict]] = []  # (child, result)
        dup_pairs: list[tuple[str, str]] = []

        for child in row_n_reqs:
            result = match_requirement(child, pool)
            judged.append((child, result))
            if result["outcome"] == "duplicate" and result.get("duplicate_of"):
                dup_pairs.append((child["requirement_id"], result["duplicate_of"]))

        # ----------------------------------------------------------------
        # Union-find: resolve equivalence classes; select min-id survivors
        # ----------------------------------------------------------------
        classes = build_equivalence_classes(dup_pairs)
        # Map every requirement_id that participates in a class → its survivor
        id_to_survivor: dict[str, str] = {}
        for cls in classes:
            survivor = select_survivor(cls)
            for member in cls:
                id_to_survivor[member] = survivor

        all_retired: set[str] = set()
        for cls in classes:
            survivor = select_survivor(cls)
            all_retired.update(cls - {survivor})

        # ----------------------------------------------------------------
        # Pass 2: DB writes
        # ----------------------------------------------------------------

        # 2a: Execute one class merge per equivalence class
        class_merge_records: list[dict] = []
        non_loss_flagged: set[str] = set()  # ids whose class failed Non-Loss

        for cls in classes:
            survivor_id = select_survivor(cls)
            if len(cls) == 1:
                continue  # single-member — no merge needed

            # Best confidence: max over all duplicate-outcome judgements for class members
            cls_confs = [
                r.get("confidence") or 0.0
                for child, r in judged
                if child["requirement_id"] in cls and r["outcome"] == "duplicate"
            ]
            best_conf = max(cls_confs) if cls_confs else 0.0

            try:
                mr = execute_class_merge(
                    session,
                    class_members=cls,
                    survivor_id=survivor_id,
                    project_id=project_id,
                    confidence=best_conf,
                    rationale="Duplicate equivalence class (union-find, v0.3)",
                    auto_recorded=best_conf >= MATCH_CONFIDENCE_BAND,
                )
                class_merge_records.append(mr)
            except NonLossViolationError as exc:
                _log.error("Non-Loss violation for class %s: %s", sorted(cls), exc)
                # Fail-closed: leave class intact, flag all members for review
                non_loss_flagged.update(cls)
                all_retired -= (cls - {survivor_id})

        # 2b: Write refines_refs for non-retired requirements
        for child, result in judged:
            child_id = child["requirement_id"]
            if child_id in all_retired:
                continue
            if result["outcome"] == "refine":
                _apply_refine_write(session, child, result, pool)

        # ----------------------------------------------------------------
        # Provenance accumulation
        # ----------------------------------------------------------------
        refined_parent_ids: set[str] = set()

        for child, result in judged:
            child_id = child["requirement_id"]
            outcome = result["outcome"]

            # Flags from Non-Loss violation override
            if child_id in non_loss_flagged:
                outcome = "flagged"
            elif child_id in all_retired:
                # Update duplicate_of to the actual class survivor
                outcome = "duplicate"
                result["duplicate_of"] = id_to_survivor.get(child_id, result.get("duplicate_of"))

            prov.add_match_record(
                requirement_id=child_id,
                outcome=outcome,
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

            refined_parent_ids.update(result.get("matched_parent_ids") or [])

        for mr in class_merge_records:
            prov.add_merge_record(mr)

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

        match_records = prov.match_records
        return {
            "row_matched": row_n,
            "pass_id": pass_id,
            "total": len(row_n_reqs),
            "refine_count": sum(1 for r in match_records if r["outcome"] == "refine"),
            "no_match_count": sum(1 for r in match_records if r["outcome"] == "no_match"),
            "no_candidates_count": sum(1 for r in match_records if r["outcome"] == "no_candidates"),
            "flagged_count": sum(1 for r in match_records if r["outcome"] == "flagged"),
            "duplicate_count": sum(1 for r in match_records if r["outcome"] == "duplicate"),
            "deferred_count": sum(1 for r in match_records if r["outcome"] == "deferred"),
            "downward_gap_count": len(orphaned_parents),
            "merge_class_count": len(class_merge_records),
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

    Same two-pass pattern as match_row() for duplicate correctness.
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

        # Pass 1: judge (no DB writes)
        judged: list[tuple[dict, dict]] = []
        dup_pairs: list[tuple[str, str]] = []

        for child in children:
            result = match_requirement(child, pool)
            judged.append((child, result))
            if result["outcome"] == "duplicate" and result.get("duplicate_of"):
                dup_pairs.append((child["requirement_id"], result["duplicate_of"]))

        # Union-find
        classes = build_equivalence_classes(dup_pairs)
        id_to_survivor: dict[str, str] = {}
        for cls in classes:
            survivor = select_survivor(cls)
            for member in cls:
                id_to_survivor[member] = survivor

        all_retired: set[str] = set()
        for cls in classes:
            survivor = select_survivor(cls)
            all_retired.update(cls - {survivor})

        # Pass 2: DB writes
        class_merge_records: list[dict] = []
        non_loss_flagged: set[str] = set()

        for cls in classes:
            survivor_id = select_survivor(cls)
            if len(cls) == 1:
                continue
            cls_confs = [
                r.get("confidence") or 0.0
                for child, r in judged
                if child["requirement_id"] in cls and r["outcome"] == "duplicate"
            ]
            best_conf = max(cls_confs) if cls_confs else 0.0
            try:
                mr = execute_class_merge(
                    session,
                    class_members=cls,
                    survivor_id=survivor_id,
                    project_id=project_id,
                    confidence=best_conf,
                    rationale="Duplicate equivalence class (union-find, v0.3)",
                    auto_recorded=best_conf >= MATCH_CONFIDENCE_BAND,
                )
                class_merge_records.append(mr)
            except NonLossViolationError as exc:
                _log.error("Non-Loss violation for class %s: %s", sorted(cls), exc)
                non_loss_flagged.update(cls)
                all_retired -= (cls - {survivor_id})

        for child, result in judged:
            if child["requirement_id"] not in all_retired and result["outcome"] == "refine":
                _apply_refine_write(session, child, result, pool)

        for child, result in judged:
            child_id = child["requirement_id"]
            outcome = result["outcome"]
            if child_id in non_loss_flagged:
                outcome = "flagged"
            elif child_id in all_retired:
                outcome = "duplicate"
                result["duplicate_of"] = id_to_survivor.get(child_id, result.get("duplicate_of"))

            prov.add_match_record(
                requirement_id=child_id,
                outcome=outcome,
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

        for mr in class_merge_records:
            prov.add_merge_record(mr)

        pass_id = prov.write_pass(session)
        session.commit()

        match_records = prov.match_records
        return {
            "total": len(children),
            "pass_id": pass_id,
            "refine_count": sum(1 for r in match_records if r["outcome"] == "refine"),
            "no_match_count": sum(1 for r in match_records if r["outcome"] == "no_match"),
            "no_candidates_count": sum(1 for r in match_records if r["outcome"] == "no_candidates"),
            "flagged_count": sum(1 for r in match_records if r["outcome"] == "flagged"),
            "duplicate_count": sum(1 for r in match_records if r["outcome"] == "duplicate"),
            "merge_class_count": len(class_merge_records),
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
