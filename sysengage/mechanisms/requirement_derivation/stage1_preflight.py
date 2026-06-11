"""
Stage 1 — Pre-flight, CCI/Domain Assembly, Re-run Scenario Detection (DM).

Per Requirement Derivation Mechanism Spec v0.1 §4.1:
  1. Precondition: Pass 3c (DomainDerivation) must be Completed/CompletedWithWarnings.
  2. CCI assembly: eligible CCIs from cell_content_item JOIN zachman_cell.
  3. Domain assembly: active Domains for this row/project from domain table.
  4. Zero-CCI early exit: CompletedWithWarnings; RequirementRegister preserves
     project-wide active members (not []).
  5. Pass 3c invariant guard: CCIs exist but no Domains → Failed.
  6. Large-set advisory: row CCI count vs threshold.
  7. Re-run scenario detection: three-part SHA-256 hash for rows >= 2
     (CCI-ids + active Domain-ids + surviving row n-1 requirement-ids);
     two-part for Row 1 (no seed segment). Domain-set change or seed-set
     change → FullRerun (MD-3).

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
_DEFAULT_LARGE_CCI_SET_THRESHOLD = 80


@dataclass
class EligibleCCI:
    """Lightweight container for a CCI eligible for requirement derivation."""
    ci_id: str
    column: str
    classification_type: str
    description: str


@dataclass
class ActiveDomain:
    """Active Domain assembled in Stage 1 for the per-Domain Stage 2 loop."""
    domain_id: str
    name: str
    description: str
    cell_content_item_refs: list[str]


@dataclass
class Stage1Result:
    scenario: str = "FirstRun"
    eligible_ccis: list[EligibleCCI] = field(default_factory=list)
    active_domains: list[ActiveDomain] = field(default_factory=list)
    current_hash: str = ""
    prior_pass: AnalysisPassModel | None = None
    large_cci_set_advisory: bool = False
    requirement_rerun_threshold: float = _DEFAULT_RERUN_THRESHOLD
    requirement_large_cci_set_advisory_threshold: int = _DEFAULT_LARGE_CCI_SET_THRESHOLD
    execution_warnings: list[dict[str, Any]] = field(default_factory=list)
    status: str = "continue"
    failure_reason: str | None = None


def _load_seed_ids(session: Session, project_id: str, parent_row_ref: int) -> list[str]:
    """Return sorted active requirement_ids for row n-1, used in hash computation."""
    rows = session.execute(
        text(
            "SELECT requirement_id FROM requirement "
            "WHERE project_id = :pid "
            "  AND row_target = :row "
            "  AND retired_at IS NULL "
            "ORDER BY requirement_id"
        ),
        {"pid": project_id, "row": str(parent_row_ref)},
    ).fetchall()
    return [r[0] for r in rows]


def run_stage1(
    *,
    project_id: str,
    row_ref: int,
    session: Session,
) -> Stage1Result:
    """
    Run Stage 1 pre-flight, CCI/Domain assembly, and re-run scenario detection.

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
        if profile.requirement_rerun_threshold is not None:
            result.requirement_rerun_threshold = profile.requirement_rerun_threshold
        if profile.requirement_large_cci_set_advisory_threshold is not None:
            result.requirement_large_cci_set_advisory_threshold = (
                profile.requirement_large_cci_set_advisory_threshold
            )

    # Precondition check: Pass 3c must have completed for this row/project
    prior_3c = session.execute(
        select(AnalysisPassModel)
        .where(
            AnalysisPassModel.project_id == project_id,
            AnalysisPassModel.mechanism == "DomainDerivation",
            AnalysisPassModel.execution_status.in_(
                ["Completed", "CompletedWithWarnings", "Success", "PartialSuccess"]
            ),
            AnalysisPassModel.outputs["mechanism_data"]["row_ref"].as_integer()
            == row_ref,
        )
        .limit(1)
    ).scalar_one_or_none()

    if prior_3c is None:
        result.status = "failed"
        result.failure_reason = (
            f"Pass 3c prerequisite not met — no completed Domain Derivation pass "
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

    # Zero-CCI early exit — RequirementRegister preserved (not emptied)
    if cci_count == 0:
        result.execution_warnings.append({"type": "no_cci_input"})
        result.status = "zero_cci_exit"
        return result

    # Domain assembly: active Domains for this row/project
    try:
        domain_rows = session.execute(
            text(
                "SELECT domain_id, name, description, cell_content_item_refs "
                "FROM domain "
                "WHERE project_id = :pid "
                "  AND row_target = :row "
                "  AND retired_at IS NULL"
            ),
            {"pid": project_id, "row": str(row_ref)},
        ).fetchall()
    except Exception as exc:
        result.status = "failed"
        result.failure_reason = f"Domain assembly query failed: {exc}"
        return result

    result.active_domains = [
        ActiveDomain(
            domain_id=r[0],
            name=r[1],
            description=r[2],
            cell_content_item_refs=list(r[3]) if r[3] else [],
        )
        for r in domain_rows
    ]
    domain_count = len(result.active_domains)

    # Pass 3c invariant guard: CCIs exist but no Domains should be unreachable
    # given VER-3c-05, but asserted defensively to fail closed rather than silently
    # producing orphan Requirements.
    if domain_count == 0:
        result.status = "failed"
        result.failure_reason = (
            "Pass 3c invariant violated — CCIs exist for row but no active "
            "Domains cover them. Ensure Pass 3c completed successfully."
        )
        return result

    # Large-set advisory (row-level, not per-Domain — per-Domain calls remain small)
    if cci_count > result.requirement_large_cci_set_advisory_threshold:
        result.large_cci_set_advisory = True
        _log.warning(
            "large_cci_set_advisory: %d CCIs exceeds threshold %d for row %d project %s",
            cci_count,
            result.requirement_large_cci_set_advisory_threshold,
            row_ref,
            project_id,
        )

    # Re-run scenario detection — hash (MD-3)
    # For rows >= 2 the seed set (row n-1 requirements) is also an input: include
    # sorted seed requirement_ids so that a newly-committed upstream row forces a
    # FullRerun rather than a false IdempotentRerun.
    sorted_ci_ids = sorted(c.ci_id for c in result.eligible_ccis)
    sorted_domain_ids = sorted(d.domain_id for d in result.active_domains)
    hash_input = "CCI:" + "|".join(sorted_ci_ids) + "||DOM:" + "|".join(sorted_domain_ids)
    if row_ref >= 2:
        seed_ids = _load_seed_ids(session, project_id, row_ref - 1)
        hash_input += "||SEEDS:" + "|".join(seed_ids)
        _log.info(
            "Hash: included %d seed IDs from row %d for project %s",
            len(seed_ids), row_ref - 1, project_id,
        )
    result.current_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    prior_pass = session.execute(
        select(AnalysisPassModel)
        .where(
            AnalysisPassModel.project_id == project_id,
            AnalysisPassModel.mechanism == "RequirementDerivation",
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
    prior_hash = prior_md.get("requirement_input_hash", "")

    if result.current_hash == prior_hash:
        result.scenario = "IdempotentRerun"
        result.status = "idempotent_exit"
        return result

    # Hash changed — determine scenario
    prior_domain_ids = prior_md.get("domain_id_set", [])

    # Domain-set change rule (MD-3): any change to active Domain-id set forces FullRerun
    if sorted_domain_ids != prior_domain_ids:
        _log.info(
            "Domain-id set changed since prior run — forcing FullRerun "
            "(prior=%s, current=%s)", prior_domain_ids, sorted_domain_ids
        )
        result.scenario = "FullRerun"
        return result

    # Domain set unchanged; CCI delta only — check threshold
    prior_cci_count = prior_md.get("cci_count_input", 0)

    # Zero-division guard: treat prior run with zero CCIs as FirstRun
    if prior_cci_count == 0:
        result.scenario = "FirstRun"
        return result

    # Live query: covered ci_ids from active Requirements for this row
    covered_rows = session.execute(
        text(
            "SELECT DISTINCT jsonb_array_elements_text(cci_refs) AS ci_id "
            "FROM requirement "
            "WHERE project_id = :pid "
            "  AND row_target = :row "
            "  AND retired_at IS NULL"
        ),
        {"pid": project_id, "row": str(row_ref)},
    ).fetchall()
    covered_ci_ids = {r[0] for r in covered_rows}

    current_ci_ids = {c.ci_id for c in result.eligible_ccis}
    new_cci_count = len(current_ci_ids - covered_ci_ids)

    if new_cci_count / prior_cci_count >= result.requirement_rerun_threshold:
        result.scenario = "FullRerun"
    else:
        result.scenario = "IncrementalRerun"

    return result
