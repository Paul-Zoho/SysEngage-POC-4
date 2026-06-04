"""
Public API for Phase 4 Requirement Quality Analysis.

Per RQA Spec v0.1 §4.2.

Read-and-score — does NOT modify requirements (D-q-3 enforced).
Writes requirement_quality_result side-table records.

Operations:
  score_requirement(requirement) → QualityResult
  score_set(requirements)        → list[QualityResult]
  aggregate(result_set)          → dict (summary statistics)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from core.db import get_session
from mechanisms.requirement_quality.classify import confirm as _confirm
from mechanisms.requirement_quality.judge import run_im_checks
from mechanisms.requirement_quality.result import QualityResult
from mechanisms.requirement_quality.rules import functional, constraint, structural
from mechanisms.requirement_quality.scoring import band, score
from sqlalchemy import text, select

_log = logging.getLogger(__name__)


def _dd_resolve_fn(term: str):
    """Lazy-import DD resolve_object to avoid circular imports."""
    try:
        from mechanisms.data_dictionary.service import resolve_object
        return resolve_object(term)
    except Exception:
        return None


def score_requirement(requirement: dict) -> QualityResult:
    """
    Score a single requirement for quality.

    Per §4.2:
    1. classify.confirm → effective_type
    2. Run effective type's rule module (decidable first, then batched IM)
    3. scoring.score(violations)
    4. Build QualityResult

    Parameters
    ----------
    requirement : dict with keys: requirement_id, statement, requirement_type,
                  verification_method, fit_criteria, [object_term?]

    Returns
    -------
    QualityResult
    """
    req_id = requirement["requirement_id"]
    statement = requirement.get("statement", "")
    stored_type = requirement.get("requirement_type", "Functional")
    verification_method = requirement.get("verification_method")
    fit_criteria = requirement.get("fit_criteria")
    object_term = requirement.get("object_term")

    # Step 1: type confirmation (IM)
    classify_result = _confirm(statement=statement, requirement_type=stored_type)
    classify_failed = bool(classify_result.get("_classify_failed"))
    effective_type = classify_result["effective_type"]
    reclassified_from = stored_type if classify_result.get("reclassified") else None

    violations: list[dict] = []
    im_not_assessed: list[str] = []
    manual_review = False

    if classify_failed:
        im_not_assessed.append("type_confirmation")
        manual_review = True

    # Step 2: decidable rule checks (DM)
    if effective_type == "Functional":
        violations.extend(
            functional.run_decidable(
                statement=statement,
                verification_method=verification_method,
                fit_criteria=fit_criteria,
                object_term=object_term,
                dd_resolve_fn=_dd_resolve_fn,
            )
        )
    elif effective_type == "Constraint":
        violations.extend(
            constraint.run_decidable(
                statement=statement,
                verification_method=verification_method,
                fit_criteria=fit_criteria,
            )
        )
    elif effective_type == "Structural":
        violations.extend(structural.run_decidable(statement=statement))

    # Step 3: batched IM-judged checks (one call per requirement)
    im_violations, not_assessed, im_review = run_im_checks(
        statement=statement,
        requirement_type=effective_type,
    )
    violations.extend(im_violations)
    im_not_assessed.extend(not_assessed)
    manual_review = manual_review or im_review

    # Step 4: score
    final_score = score(violations)

    return QualityResult(
        requirement_id=req_id,
        effective_type=effective_type,
        reclassified_from=reclassified_from,
        score=final_score,
        violations=violations,
        im_not_assessed=im_not_assessed,
        manual_review_flag=manual_review,
        scored_at=datetime.now(timezone.utc),
    )


def score_set(requirements: list[dict]) -> list[QualityResult]:
    """
    Score a list of requirements and persist results to requirement_quality_result.

    LPM enforced: requirements are never modified.
    """
    results: list[QualityResult] = []
    for req in requirements:
        try:
            qr = score_requirement(req)
        except Exception as exc:
            _log.error("score_requirement failed for %s: %s", req.get("requirement_id"), exc)
            qr = QualityResult(
                requirement_id=req.get("requirement_id", "unknown"),
                effective_type=req.get("requirement_type", "Functional"),
                score=0,
                violations=[{"rule": "scoring_error", "severity": "High",
                             "penalty": 100, "detail": str(exc)}],
                manual_review_flag=True,
            )
        results.append(qr)

    _persist_results(results)
    return results


def _persist_results(results: list[QualityResult]) -> None:
    """Write quality results to requirement_quality_result side table."""
    session = get_session()
    try:
        for qr in results:
            session.execute(
                text(
                    "INSERT INTO requirement_quality_result "
                    "(requirement_id, effective_type, reclassified_from, score, violations, scored_at) "
                    "VALUES (:rid, :etype, :rcl, :score, CAST(:viols AS jsonb), :sat)"
                ),
                {
                    "rid": qr.requirement_id,
                    "etype": qr.effective_type,
                    "rcl": qr.reclassified_from,
                    "score": qr.score,
                    "viols": json.dumps(qr.violations),
                    "sat": qr.scored_at,
                },
            )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def aggregate(result_set: list[QualityResult]) -> dict[str, Any]:
    """
    Aggregate quality results across a set of requirements.

    Per §4.5: mean score; violation frequency by rule/type/row;
    score-band distribution. Advisory output only.
    """
    if not result_set:
        return {"total": 0, "mean_score": None, "band_distribution": {}, "violations_by_rule": {}}

    scores = [qr.score for qr in result_set]
    mean_score = sum(scores) / len(scores)

    band_distribution: dict[str, int] = {"high": 0, "adequate": 0, "low": 0}
    for qr in result_set:
        band_distribution[band(qr.score)] += 1

    violations_by_rule: dict[str, int] = {}
    for qr in result_set:
        for v in qr.violations:
            rule = v.get("rule", "unknown")
            violations_by_rule[rule] = violations_by_rule.get(rule, 0) + 1

    violations_by_type: dict[str, int] = {}
    for qr in result_set:
        viol_count = len(qr.violations)
        t = qr.effective_type
        violations_by_type[t] = violations_by_type.get(t, 0) + viol_count

    manual_review_count = sum(1 for qr in result_set if qr.manual_review_flag)
    reclassified_count = sum(1 for qr in result_set if qr.reclassified_from is not None)

    return {
        "total": len(result_set),
        "mean_score": round(mean_score, 1),
        "min_score": min(scores),
        "max_score": max(scores),
        "band_distribution": band_distribution,
        "violations_by_rule": dict(sorted(violations_by_rule.items(), key=lambda x: -x[1])),
        "violations_by_type": violations_by_type,
        "manual_review_count": manual_review_count,
        "reclassified_count": reclassified_count,
    }
