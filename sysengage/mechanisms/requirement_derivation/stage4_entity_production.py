"""
Stage 4 — Entity Production and Ledger Commit (DM).

Per Requirement Derivation Mechanism Spec v0.1 §4.4:
  4.4.1  requirement_id allocation (global per-project R###, includes retired).
  4.4.2  domain_refs DM-derivation (MD-2): intersect cci_refs with active Domain
         memberships; assert ≥1 domain_ref. Fail-closed if empty.
  4.4.3  Requirement entity construction (all spec §5.1 columns).
  4.4.4  FullRerun retirement (retired_at = now() on prior active Requirements).
  4.4.5  downstream_rerun_required: check Phase 5/6/8 AnalysisPasses.
  4.4.6  Single transaction: retire (FullRerun), insert Requirements, replace
         RequirementRegister.member_ids (project-wide), write AnalysisPass.

Note: F80 disposition — domain_refs are derived by domain_id, never by name.
Cross-row Domain name duplication (NQPS "Quality Governance" at Row 1 and Row 2)
is harmless to derivation. F80 left Open per D5.

No AI calls. DM mode only.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.db import format_identifier, get_next_sequence_value
from mechanisms.requirement_derivation.stage1_preflight import ActiveDomain, Stage1Result
from mechanisms.requirement_derivation.stage2_ai_derivation import Stage2Result
from mechanisms.requirement_derivation.stage3_structural_validation import Stage3Result, TaggedProposal
from models.concern import ConcernModel

_log = logging.getLogger(__name__)

_JACCARD_THRESHOLD = 0.50


@dataclass
class Stage4Result:
    requirement_count_produced: int = 0
    requirement_count_retired: int = 0
    requirements_produced: list[dict[str, Any]] = field(default_factory=list)
    requirement_type_distribution: dict[str, int] = field(default_factory=dict)
    retirement_mapping: list[dict[str, Any]] = field(default_factory=list)
    downstream_rerun_required: bool = False
    status: str = "ok"
    failure_reason: str | None = None


def _jaccard_overlap(stmt_a: str, stmt_b: str) -> float:
    tokens_a = set(stmt_a.lower().split())
    tokens_b = set(stmt_b.lower().split())
    if not tokens_a and not tokens_b:
        return 1.0
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


def _allocate_requirement_ids(
    session: Session, project_id: str, count: int
) -> list[str]:
    """
    Allocate `count` new requirement_ids (R001, R002, …).
    MAX query includes retired Requirements — ids are never reused per spec §4.4.1.

    Known constraint: max 999 Requirement instances per project (R001–R999).
    If a project approaches 800 allocated ids (including retired), raise a tracker
    finding for a 4-digit format extension (R####).
    """
    row = session.execute(
        text(
            "SELECT MAX(CAST(SUBSTRING(requirement_id FROM 2) AS INTEGER)) "
            "FROM requirement WHERE project_id = :pid"
        ),
        {"pid": project_id},
    ).fetchone()
    next_seq = 1 if row[0] is None else row[0] + 1

    # Ceiling advisory — log if approaching R999
    if next_seq + count > 800:
        _log.warning(
            "requirement_id ceiling advisory: next_seq=%d count=%d for project=%s — "
            "approaching R999 limit; raise tracker finding for 4-digit extension",
            next_seq, count, project_id,
        )

    return [f"R{str(i).zfill(3)}" for i in range(next_seq, next_seq + count)]


def _query_active_requirements_for_row(
    session: Session, project_id: str, row_ref: int
) -> list[dict[str, Any]]:
    rows = session.execute(
        text(
            "SELECT requirement_id, statement FROM requirement "
            "WHERE project_id = :pid "
            "  AND row_target = :row "
            "  AND retired_at IS NULL"
        ),
        {"pid": project_id, "row": str(row_ref)},
    ).fetchall()
    return [{"requirement_id": r[0], "statement": r[1]} for r in rows]


def _query_all_active_requirement_ids(
    session: Session, project_id: str
) -> list[str]:
    """Project-wide active requirement_ids — no row_target filter."""
    rows = session.execute(
        text(
            "SELECT requirement_id FROM requirement "
            "WHERE project_id = :pid AND retired_at IS NULL"
        ),
        {"pid": project_id},
    ).fetchall()
    return [r[0] for r in rows]


def _check_downstream_rerun_required(
    session: Session, project_id: str, row_ref: int
) -> bool:
    """Check if Phase 5, Phase 6, or Phase 8 AnalysisPasses exist for this row/project."""
    row = session.execute(
        text(
            "SELECT pass_id FROM analysis_pass "
            "WHERE project_id = :pid "
            "  AND mechanism IN ('CellQuality', 'CoverageAnalysis', 'CoverageAnalysis8') "
            "  AND execution_status IN ('Completed', 'CompletedWithWarnings') "
            "  AND outputs->'mechanism_data'->>'row_ref' = :row "
            "LIMIT 1"
        ),
        {"pid": project_id, "row": str(row_ref)},
    ).fetchone()
    return row is not None


def _compute_retirement_mapping(
    prior_active: list[dict[str, Any]],
    new_proposals: list[TaggedProposal],
    new_ids: list[str],
) -> list[dict[str, Any]]:
    """
    For each retiring Requirement, find the new Requirement with highest Jaccard
    statement overlap. Per spec §4.4.4: threshold 0.50.
    """
    mapping = []
    for old in prior_active:
        best_score = 0.0
        best_new_idx = None
        for i, prop in enumerate(new_proposals):
            score = _jaccard_overlap(old["statement"], prop.statement)
            if score > best_score:
                best_score = score
                best_new_idx = i
        inferred_successor = (
            new_ids[best_new_idx]
            if best_new_idx is not None and best_score >= _JACCARD_THRESHOLD
            else None
        )
        mapping.append(
            {
                "old_requirement_id": old["requirement_id"],
                "inferred_successor_requirement_id": inferred_successor,
            }
        )
    return mapping


def _derive_domain_refs(
    proposal: TaggedProposal,
    active_domains: list[ActiveDomain],
) -> list[str]:
    """
    MD-2: DM-derived domain_refs — set of domain_ids whose cell_content_item_refs
    intersect proposal.cci_refs. Never AI-proposed.

    F80 disposition: derived by domain_id, never by name — cross-row name
    duplication is harmless to this computation.
    """
    proposal_ci_ids = set(proposal.cci_refs)
    domain_refs = sorted(
        d.domain_id
        for d in active_domains
        if proposal_ci_ids & set(d.cell_content_item_refs)
    )
    return domain_refs


def run_stage4(
    *,
    stage1: Stage1Result,
    stage2: Stage2Result,
    stage3: Stage3Result,
    project_id: str,
    row_ref: int,
    practitioner_id: str,
    pass_data: dict[str, Any],
    session: Session,
) -> Stage4Result:
    """
    Run Stage 4 entity production and ledger commit.

    pass_data: mutable pass record built by orchestrator (mutated in place).
    Returns Stage4Result.
    """
    result = Stage4Result()
    effective_scenario = stage2.effective_scenario
    proposals = stage3.proposals

    # --- 4.4.5 downstream_rerun_required (check before transaction) ---
    if effective_scenario in ("FullRerun", "IncrementalRerun"):
        result.downstream_rerun_required = _check_downstream_rerun_required(
            session, project_id, row_ref
        )

    # --- 4.4.4 Retirement mapping (BEFORE opening transaction) ---
    prior_active: list[dict[str, Any]] = []
    if effective_scenario == "FullRerun":
        prior_active = _query_active_requirements_for_row(session, project_id, row_ref)
        result.requirement_count_retired = len(prior_active)

    # --- 4.4.2 domain_refs DM-derivation; reject empty (MD-2 fail-closed) ---
    valid_proposals: list[TaggedProposal] = []
    for proposal in proposals:
        domain_refs = _derive_domain_refs(proposal, stage1.active_domains)
        if not domain_refs:
            # Fail-closed: empty domain_refs is a defect — log and exclude
            stage3.validation_failures.append(
                {
                    "check_id": "MD-2",
                    "source_domain_id": proposal.source_domain_id,
                    "detail": "domain_refs derivation empty — proposal excluded",
                }
            )
            _log.warning(
                "MD-2 fail-closed: empty domain_refs for proposal from domain=%s; excluded",
                proposal.source_domain_id,
            )
            continue
        # Store derived domain_refs on the proposal (temporary attribute, not schema)
        proposal._domain_refs = domain_refs  # type: ignore[attr-defined]
        valid_proposals.append(proposal)

    # If MD-2 exclusions created new orphans, they remain in stage3.orphaned_ccis already
    # (they passed CHK-3d-05 but are now excluded at Stage 4). Surface as warnings.
    excluded_count = len(proposals) - len(valid_proposals)
    if excluded_count > 0:
        pass_data.setdefault("execution_warnings_stage4", []).append(
            {"type": "md2_domain_refs_empty_excluded", "count": excluded_count}
        )

    proposals = valid_proposals

    # --- 4.4.1 requirement_id allocation ---
    new_ids = _allocate_requirement_ids(session, project_id, len(proposals))

    # Retirement mapping (now that new_ids are known)
    if effective_scenario == "FullRerun" and prior_active:
        result.retirement_mapping = _compute_retirement_mapping(
            prior_active, proposals, new_ids
        )

    # --- 4.4.6 Ledger transaction ---
    now = datetime.now(timezone.utc)
    try:
        # Step 1: FullRerun retirement UPDATE
        if effective_scenario == "FullRerun":
            session.execute(
                text(
                    "UPDATE requirement SET retired_at = :now "
                    "WHERE project_id = :pid "
                    "  AND row_target = :row "
                    "  AND retired_at IS NULL"
                ),
                {"now": now, "pid": project_id, "row": str(row_ref)},
            )

        # Step 2: INSERT new Requirement entities
        for proposal, req_id in zip(proposals, new_ids):
            domain_refs = getattr(proposal, "_domain_refs", [])
            session.execute(
                text(
                    "INSERT INTO requirement "
                    "(requirement_id, project_id, statement, requirement_type, "
                    " row_target, rationale, cci_refs, domain_refs, fit_criteria, "
                    " verification_method, priority, answer_refs, confidence, "
                    " retired_at, created_at) "
                    "VALUES (:rid, :pid, :stmt, :rtype, :row, :rationale, "
                    "        CAST(:cci_refs AS jsonb), CAST(:domain_refs AS jsonb), "
                    "        :fit_criteria, :verification_method, :priority, "
                    "        CAST(:answer_refs AS jsonb), :confidence, NULL, :now)"
                ),
                {
                    "rid": req_id,
                    "pid": project_id,
                    "stmt": proposal.statement,
                    "rtype": proposal.requirement_type,
                    "row": str(row_ref),
                    "rationale": proposal.rationale,
                    "cci_refs": json.dumps(sorted(proposal.cci_refs)),
                    "domain_refs": json.dumps(domain_refs),
                    "fit_criteria": proposal.fit_criteria,
                    "verification_method": proposal.verification_method,
                    "priority": proposal.priority,
                    "answer_refs": json.dumps([]),
                    "confidence": proposal.confidence,
                    "now": now,
                },
            )

        # Step 3: Insert Concern entities for persistent orphans
        for concern_data in stage3.concern_entities:
            seq_val = get_next_sequence_value(session, "cn_id_seq")
            concern_id = format_identifier("CN", seq_val)
            session.add(
                ConcernModel(
                    concern_id=concern_id,
                    source_refs=concern_data["source_refs"],
                    description=concern_data["description"],
                    state="Open",
                    produced_in_row=concern_data["produced_in_row"],
                    practitioner_id=concern_data["practitioner_id"],
                    confidence=1.0,
                    project_id=concern_data["project_id"],
                    created_at=now,
                )
            )

        # Step 4: UPDATE RequirementRegister — project-wide, no row_target filter
        active_ids_rows = session.execute(
            text(
                "SELECT requirement_id FROM requirement "
                "WHERE project_id = :pid AND retired_at IS NULL"
            ),
            {"pid": project_id},
        ).fetchall()
        all_active_ids = sorted(r[0] for r in active_ids_rows)

        update_count = session.execute(
            text(
                "UPDATE register SET member_ids = :mi "
                "WHERE register_type = 'Requirement' AND project_id = :pid"
            ),
            {"mi": json.dumps(all_active_ids), "pid": project_id},
        ).rowcount

        if update_count == 0:
            raise RuntimeError(
                "RequirementRegister not found — migration may not have run"
            )

        session.commit()

    except Exception as exc:
        session.rollback()
        result.status = "failed"
        result.failure_reason = f"Ledger transaction rolled back: {exc}"
        return result

    # Build result summary
    type_dist: dict[str, int] = {
        "Functional": 0,
        "Constraint": 0,
        "Performance": 0,
        "Suitability": 0,
        "Non-Functional": 0,
    }
    reqs_produced = []
    for proposal, req_id in zip(proposals, new_ids):
        type_dist[proposal.requirement_type] = (
            type_dist.get(proposal.requirement_type, 0) + 1
        )
        domain_refs = getattr(proposal, "_domain_refs", [])
        reqs_produced.append(
            {
                "requirement_id": req_id,
                "requirement_type": proposal.requirement_type,
                "cci_ref_count": len(proposal.cci_refs),
                "domain_refs": domain_refs,
            }
        )

    result.requirement_count_produced = len(proposals)
    result.requirement_type_distribution = type_dist
    result.requirements_produced = reqs_produced
    return result
