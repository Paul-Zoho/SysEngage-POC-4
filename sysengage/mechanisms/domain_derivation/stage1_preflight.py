"""
Stage 1 — Pre-flight, CCI Assembly, and Re-run Scenario Detection (DM).

Per Domain Derivation Mechanism Spec v0.13 §4.1:
  1. Precondition: Pass 3b must be Completed/CompletedWithWarnings for this row.
  2. CCI assembly: eligible CCIs from cell_content_item JOIN zachman_cell.
  3. Zero-CCI early exit: CompletedWithWarnings with no_cci_input warning.
  4. Large-set advisory: check CCI count against threshold.
  5. Re-run scenario detection: SHA-256 hash comparison against prior pass.
  6. IdempotentRerun exit: no Stage 2 needed.

No AI calls. DM mode only.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from models.analysis_pass import AnalysisPassModel
from models.cell_content_item import CellContentItemModel
from models.project_profile import ProjectProfileModel
from models.zachman_cell import ZachmanCellModel

_log = logging.getLogger(__name__)

_DEFAULT_RERUN_THRESHOLD = 0.20
_DEFAULT_CROSS_CUTTING_THRESHOLD = 3
_DEFAULT_LARGE_CCI_SET_THRESHOLD = 80


@dataclass
class EligibleCCI:
    """Lightweight container for a CCI eligible for domain derivation."""
    ci_id: str
    column: str
    classification_type: str
    description: str


@dataclass
class Stage1Result:
    scenario: str = "FirstRun"
    eligible_ccis: list[EligibleCCI] = field(default_factory=list)
    current_hash: str = ""
    prior_pass: AnalysisPassModel | None = None
    large_cci_set_advisory: bool = False
    domain_rerun_threshold: float = _DEFAULT_RERUN_THRESHOLD
    domain_cross_cutting_advisory_threshold: int = _DEFAULT_CROSS_CUTTING_THRESHOLD
    domain_large_cci_set_advisory_threshold: int = _DEFAULT_LARGE_CCI_SET_THRESHOLD
    execution_warnings: list[dict[str, Any]] = field(default_factory=list)
    status: str = "continue"
    failure_reason: str | None = None


def run_stage1(
    *,
    project_id: str,
    row_ref: int,
    session: Session,
) -> Stage1Result:
    """
    Run Stage 1 pre-flight, CCI assembly, and re-run scenario detection.

    result.status values:
      "continue"        — proceed to Stage 2
      "idempotent_exit" — IdempotentRerun; write pass and exit
      "zero_cci_exit"   — zero CCIs; write CompletedWithWarnings pass and exit
      "failed"          — hard stop; write failure pass and exit
    """
    result = Stage1Result()

    # Load ProjectProfile for parameter defaults
    profile = session.execute(
        select(ProjectProfileModel).where(
            ProjectProfileModel.project_id == project_id
        )
    ).scalar_one_or_none()

    if profile is not None:
        if profile.domain_rerun_threshold is not None:
            result.domain_rerun_threshold = profile.domain_rerun_threshold
        if profile.domain_cross_cutting_advisory_threshold is not None:
            result.domain_cross_cutting_advisory_threshold = (
                profile.domain_cross_cutting_advisory_threshold
            )
        if profile.domain_large_cci_set_advisory_threshold is not None:
            result.domain_large_cci_set_advisory_threshold = (
                profile.domain_large_cci_set_advisory_threshold
            )

    # Precondition check: Pass 3b must have completed for this row/project
    prior_3b = session.execute(
        select(AnalysisPassModel)
        .where(
            AnalysisPassModel.project_id == project_id,
            AnalysisPassModel.mechanism == "CCIConstruction",
            AnalysisPassModel.execution_status.in_(
                ["Completed", "CompletedWithWarnings"]
            ),
            AnalysisPassModel.outputs["cci_data"]["row_ref"].as_integer() == row_ref,
        )
        .limit(1)
    ).scalar_one_or_none()

    if prior_3b is None:
        result.status = "failed"
        result.failure_reason = (
            f"Pass 3b prerequisite not met — no completed CCI Construction pass "
            f"found for row {row_ref} in project {project_id}"
        )
        return result

    # CCI assembly: eligible CCIs for this row/project
    try:
        rows = session.execute(
            select(
                CellContentItemModel.ci_id,
                ZachmanCellModel.column,
                CellContentItemModel.classification_type,
                CellContentItemModel.description,
            )
            .join(
                ZachmanCellModel,
                (CellContentItemModel.cell_id == ZachmanCellModel.cell_id)
                & (CellContentItemModel.project_id == ZachmanCellModel.project_id),
            )
            .where(
                ZachmanCellModel.row_target == str(row_ref),
                CellContentItemModel.project_id == project_id,
            )
        ).all()
    except Exception as exc:
        result.status = "failed"
        result.failure_reason = f"CCI assembly query failed: {exc}"
        return result

    result.eligible_ccis = [
        EligibleCCI(
            ci_id=r.ci_id,
            column=r.column,
            classification_type=r.classification_type,
            description=r.description,
        )
        for r in rows
    ]

    cci_count = len(result.eligible_ccis)

    # Zero-CCI early exit
    if cci_count == 0:
        result.execution_warnings.append({"type": "no_cci_input"})
        result.status = "zero_cci_exit"
        return result

    # Large-set advisory
    if cci_count > result.domain_large_cci_set_advisory_threshold:
        result.large_cci_set_advisory = True
        _log.warning(
            "large_cci_set_advisory: %d CCIs exceeds threshold %d for row %d project %s",
            cci_count,
            result.domain_large_cci_set_advisory_threshold,
            row_ref,
            project_id,
        )

    # Re-run scenario detection
    sorted_ids = sorted(c.ci_id for c in result.eligible_ccis)
    result.current_hash = hashlib.sha256(
        "|".join(sorted_ids).encode("utf-8")
    ).hexdigest()

    prior_pass = session.execute(
        select(AnalysisPassModel)
        .where(
            AnalysisPassModel.project_id == project_id,
            AnalysisPassModel.mechanism == "DomainDerivation",
            AnalysisPassModel.execution_status != "Failed",
            AnalysisPassModel.outputs["mechanism_data"]["row_ref"].as_integer()
            == row_ref,
        )
        .order_by(AnalysisPassModel.pass_started_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    result.prior_pass = prior_pass

    if prior_pass is None:
        result.scenario = "FirstRun"
        return result

    prior_md = prior_pass.outputs.get("mechanism_data", {})
    prior_hash = prior_md.get("cci_set_hash", "")

    if result.current_hash == prior_hash:
        result.scenario = "IdempotentRerun"
        result.status = "idempotent_exit"
        return result

    prior_cci_count = prior_md.get("cci_count_input", 0)

    # Zero-division guard: treat prior run with zero CCIs as FirstRun
    if prior_cci_count == 0:
        result.scenario = "FirstRun"
        return result

    # Query committed CCI ids for this row/project from domain.cell_content_item_refs
    committed_rows = session.execute(
        text(
            "SELECT DISTINCT jsonb_array_elements_text(d.cell_content_item_refs) AS ci_id "
            "FROM domain d "
            "WHERE d.project_id = :pid "
            "  AND d.row_target = :row "
            "  AND d.retired_at IS NULL"
        ),
        {"pid": project_id, "row": str(row_ref)},
    ).fetchall()
    prior_committed_ci_ids = {r[0] for r in committed_rows}

    current_ci_ids = {c.ci_id for c in result.eligible_ccis}
    new_cci_count = len(current_ci_ids - prior_committed_ci_ids)

    if new_cci_count / prior_cci_count >= result.domain_rerun_threshold:
        result.scenario = "FullRerun"
    else:
        result.scenario = "IncrementalRerun"

    return result
