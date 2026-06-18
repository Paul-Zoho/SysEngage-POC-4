"""
CHK-3d-12 — Concept-coverage refinement check (rows ≥ 3; F105 / v0.33).

Per Requirement Derivation Mechanism Spec v0.33 §4.3:

  For row N (N ≥ 3), every entity in the row N-1 class_models should be
  covered by ≥1 entity in row N's class_models under a refinement_kind that
  is NOT 'introduce'.  Introduced entities legitimately have no parent.

  An entity E at row N-1 is "covered" if there exists ≥1 class_model at row N
  with entity.name == E.name (case-insensitive) AND refinement_kind != 'introduce'.

  Uncovered entities → model_coverage_gaps (advisory non-blocking).
  hard_extinction: ALL row N-1 entities uncovered AND ≥1 non-introduce entity
  at row N.  This indicates a complete design break; the check's caller may
  escalate the pass status.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

_log = logging.getLogger(__name__)


def _get_class_models_for_row(
    session: Session, project_id: str, row_ref: int
) -> list[dict[str, Any]]:
    rows = session.execute(
        text(
            "SELECT class_model FROM requirement "
            "WHERE project_id = :pid "
            "  AND row_target = :row "
            "  AND requirement_type = 'Structural' "
            "  AND retired_at IS NULL "
            "  AND class_model IS NOT NULL"
        ),
        {"pid": project_id, "row": str(row_ref)},
    ).fetchall()
    result: list[dict[str, Any]] = []
    for (cm,) in rows:
        if isinstance(cm, str):
            try:
                cm = json.loads(cm)
            except Exception:
                continue
        if isinstance(cm, dict):
            result.append(cm)
    return result


def check_concept_coverage(
    *,
    project_id: str,
    row_ref: int,
    current_row_class_models: list[dict[str, Any]],
    session: Session,
) -> dict[str, Any]:
    """
    Run CHK-3d-12 concept-coverage check.

    Args:
        project_id:               the project being checked
        row_ref:                  current row N; check is no-op for N ≤ 2
        current_row_class_models: class_model dicts produced for row N this run
        session:                  DB read session (queries prior row)

    Returns a summary dict:
        check_id, prior_row, prior_entity_count, covered_entities,
        uncovered_entities, hard_extinction, status
    """
    _base: dict[str, Any] = {
        "check_id": "CHK-3d-12",
        "prior_row": row_ref - 1,
        "prior_entity_count": 0,
        "covered_entities": [],
        "uncovered_entities": [],
        "hard_extinction": False,
        "status": "ok",
    }

    if row_ref < 3:
        return _base

    prior_cms = _get_class_models_for_row(session, project_id, row_ref - 1)
    if not prior_cms:
        return _base

    prior_entities: list[str] = [
        cm.get("entity", "").strip()
        for cm in prior_cms
        if cm.get("entity", "").strip()
    ]
    prior_entity_lower: dict[str, str] = {e.lower(): e for e in prior_entities}

    covering_lower: set[str] = {
        cm.get("entity", "").strip().lower()
        for cm in current_row_class_models
        if cm.get("refinement_kind", "") != "introduce"
        and cm.get("entity", "").strip()
    }

    covered: list[str] = []
    uncovered: list[str] = []
    for lower_name, orig_name in prior_entity_lower.items():
        (covered if lower_name in covering_lower else uncovered).append(orig_name)

    has_non_introduce = any(
        cm.get("refinement_kind", "") != "introduce"
        for cm in current_row_class_models
    )
    hard_extinction = bool(uncovered) and not covered and has_non_introduce

    if hard_extinction:
        status = "hard_extinction"
        _log.warning(
            "CHK-3d-12 hard_extinction: row %d — 0 of %d prior entities covered",
            row_ref,
            len(prior_entities),
        )
    elif uncovered:
        status = "advisory"
        _log.info(
            "CHK-3d-12 advisory: %d/%d prior entities uncovered at row %d: %s",
            len(uncovered),
            len(prior_entities),
            row_ref,
            uncovered,
        )
    else:
        status = "ok"

    return {
        "check_id": "CHK-3d-12",
        "prior_row": row_ref - 1,
        "prior_entity_count": len(prior_entities),
        "covered_entities": covered,
        "uncovered_entities": uncovered,
        "hard_extinction": hard_extinction,
        "status": status,
    }
