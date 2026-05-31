"""
Stage 4 — Entity Production and Ledger Commit (DM).

Per Domain Derivation Mechanism Spec v0.17 §4.4:
  4.4.1  domain_id allocation (global per-project, includes retired).
  4.4.2  Domain entity construction (six canonical attributes).
  4.4.3  Ledger transaction:
           FullRerun retirement UPDATE
           INSERT domain rows (with cell_content_item_refs JSONB)
           UPDATE domain.cell_content_item_refs for incremental assigns — step 3b
           UPDATE register member_ids (project-wide, no row_target filter)
  4.4.4  FullRerun retirement mapping (Jaccard token overlap, threshold 0.50).
  4.4.5  downstream_rerun_required flag.
  4.4.6  AnalysisPass written OUTSIDE the main ledger transaction.

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

from core.audit_trail import commit_failure_pass, create_analysis_pass_record, persist_analysis_pass
from core.db import format_identifier, get_next_sequence_value, get_session
from mechanisms.domain_derivation.schemas.domain_grouping_response_schema import DomainProposal
from mechanisms.domain_derivation.stage1_preflight import Stage1Result
from mechanisms.domain_derivation.stage2_ai_grouping import Stage2Result
from mechanisms.domain_derivation.stage3_structural_validation import Stage3Result
from models.concern import ConcernModel

_log = logging.getLogger(__name__)

_JACCARD_THRESHOLD = 0.50  # hardcoded per spec §4.4.4 — not configurable


@dataclass
class Stage4Result:
    domain_count_produced: int = 0
    domain_count_retired: int = 0
    domains_produced: list[dict[str, Any]] = field(default_factory=list)
    retirement_mapping: list[dict[str, Any]] = field(default_factory=list)
    downstream_rerun_required: bool = False
    status: str = "ok"
    failure_reason: str | None = None


def _jaccard_overlap(name_a: str, name_b: str) -> float:
    """Token-level Jaccard overlap between two Domain names (lowercase split)."""
    tokens_a = set(name_a.lower().split())
    tokens_b = set(name_b.lower().split())
    if not tokens_a and not tokens_b:
        return 1.0
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


def _compute_retirement_mapping(
    prior_active: list[dict[str, Any]],
    new_proposals: list[DomainProposal],
) -> list[dict[str, Any]]:
    """
    For each retiring Domain, find the new proposal with highest Jaccard name overlap.
    Returns list of {old_domain_id, inferred_successor_domain_id|None}.
    Per spec §4.4.4: capture BEFORE the transaction opens.
    """
    mapping = []
    for old in prior_active:
        best_score = 0.0
        best_new_idx = None
        for i, np_ in enumerate(new_proposals):
            score = _jaccard_overlap(old["name"], np_.name)
            if score > best_score:
                best_score = score
                best_new_idx = i
        mapping.append(
            {
                "old_domain_id": old["domain_id"],
                "_new_proposal_idx": best_new_idx,
                "_best_score": best_score,
                "inferred_successor_domain_id": None,
            }
        )
    return mapping


def _allocate_domain_ids(
    session: Session,
    project_id: str,
    count: int,
) -> list[str]:
    """
    Allocate `count` new domain_ids (D001, D002, ...).
    MAX query includes retired Domains — ids are never reused per spec §4.4.1.
    """
    row = session.execute(
        text(
            "SELECT MAX(CAST(SUBSTRING(domain_id FROM 2) AS INTEGER)) "
            "FROM domain WHERE project_id = :pid"
        ),
        {"pid": project_id},
    ).fetchone()
    next_seq = 1 if row[0] is None else row[0] + 1
    return [f"D{str(i).zfill(3)}" for i in range(next_seq, next_seq + count)]


def _query_all_active_domain_ids(session: Session, project_id: str) -> list[str]:
    """All active domain_ids for project (no row_target filter) per spec §4.4.3 step 4."""
    rows = session.execute(
        text(
            "SELECT domain_id FROM domain "
            "WHERE project_id = :pid AND retired_at IS NULL"
        ),
        {"pid": project_id},
    ).fetchall()
    return [r[0] for r in rows]


def _query_active_domains_for_row(
    session: Session, project_id: str, row_ref: int
) -> list[dict[str, Any]]:
    """Active domains for a specific row — used for FullRerun retirement."""
    rows = session.execute(
        text(
            "SELECT domain_id, name FROM domain "
            "WHERE project_id = :pid "
            "  AND row_target = :row "
            "  AND retired_at IS NULL"
        ),
        {"pid": project_id, "row": str(row_ref)},
    ).fetchall()
    return [{"domain_id": r[0], "name": r[1]} for r in rows]


def _check_downstream_rerun_required(
    session: Session, project_id: str, row_ref: int
) -> bool:
    """Check if Pass 3d has previously completed for this row/project."""
    row = session.execute(
        text(
            "SELECT pass_id FROM analysis_pass "
            "WHERE project_id = :pid "
            "  AND mechanism = 'RequirementDerivation' "
            "  AND execution_status IN ('Completed', 'CompletedWithWarnings') "
            "  AND outputs->'mechanism_data'->>'row_ref' = :row "
            "LIMIT 1"
        ),
        {"pid": project_id, "row": str(row_ref)},
    ).fetchone()
    return row is not None


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

    # --- 4.4.4 Retirement mapping (BEFORE opening transaction) ---
    retirement_mapping: list[dict[str, Any]] = []
    prior_active_domains: list[dict[str, Any]] = []

    if effective_scenario == "FullRerun":
        prior_active_domains = _query_active_domains_for_row(
            session, project_id, row_ref
        )
        result.domain_count_retired = len(prior_active_domains)
        retirement_mapping = _compute_retirement_mapping(
            prior_active_domains, stage3.proposals
        )

    # --- 4.4.5 downstream_rerun_required ---
    if effective_scenario == "FullRerun":
        result.downstream_rerun_required = _check_downstream_rerun_required(
            session, project_id, row_ref
        )

    # --- 4.4.1 domain_id allocation ---
    new_ids = _allocate_domain_ids(session, project_id, len(stage3.proposals))

    # Map new domain_ids to proposals
    proposal_domain_map: dict[str, str] = {}
    for idx, (proposal, domain_id) in enumerate(zip(stage3.proposals, new_ids)):
        proposal_domain_map[proposal.name] = domain_id

    # Finalise retirement mapping successor IDs now that new_ids are known
    if retirement_mapping:
        for entry in retirement_mapping:
            pidx = entry.pop("_new_proposal_idx")
            score = entry.pop("_best_score")
            if pidx is not None and score >= _JACCARD_THRESHOLD:
                entry["inferred_successor_domain_id"] = new_ids[pidx]
            else:
                entry["inferred_successor_domain_id"] = None
    result.retirement_mapping = retirement_mapping

    # --- 4.4.3 Ledger transaction ---
    now = datetime.now(timezone.utc)
    try:
        # Step 1: FullRerun retirement UPDATE
        if effective_scenario == "FullRerun":
            session.execute(
                text(
                    "UPDATE domain SET retired_at = :now "
                    "WHERE project_id = :pid "
                    "  AND row_target = :row "
                    "  AND retired_at IS NULL"
                ),
                {"now": now, "pid": project_id, "row": str(row_ref)},
            )

        # Step 2: INSERT new Domain entities (six canonical attributes per spec v0.14)
        for proposal, domain_id in zip(stage3.proposals, new_ids):
            session.execute(
                text(
                    "INSERT INTO domain "
                    "(domain_id, project_id, name, description, "
                    " classification_type, row_target, cell_content_item_refs, created_at) "
                    "VALUES (:did, :pid, :name, :desc, :ctype, :row, CAST(:ccirefs AS jsonb), :now)"
                ),
                {
                    "did": domain_id,
                    "pid": project_id,
                    "name": proposal.name,
                    "desc": proposal.description,
                    "ctype": proposal.classification_type,
                    "row": str(row_ref),
                    "ccirefs": json.dumps(sorted(proposal.cci_refs)),
                    "now": now,
                },
            )

        # Step 3b: IncrementalRerun — append new ci_ids to existing domain rows
        # Group by domain_id so each domain gets one UPDATE with all its new refs.
        _assigns: dict[str, list[str]] = {}
        for existing_domain_id, ci_id in stage3.assign_membership_inserts:
            _assigns.setdefault(existing_domain_id, []).append(ci_id)
        for did, ci_ids in _assigns.items():
            session.execute(
                text(
                    "UPDATE domain "
                    "SET cell_content_item_refs = cell_content_item_refs || CAST(:new_refs AS jsonb) "
                    "WHERE domain_id = :did AND project_id = :pid AND retired_at IS NULL"
                ),
                {"did": did, "pid": project_id, "new_refs": json.dumps(sorted(ci_ids))},
            )

        # Insert concern entities if any persistent orphans
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

        # Step 4: UPDATE DomainRegister — project-wide, no row_target filter
        # Query active domain_ids AFTER inserts (within this transaction)
        active_ids_rows = session.execute(
            text(
                "SELECT domain_id FROM domain "
                "WHERE project_id = :pid AND retired_at IS NULL"
            ),
            {"pid": project_id},
        ).fetchall()
        all_active_ids = sorted(r[0] for r in active_ids_rows)

        update_count = session.execute(
            text(
                "UPDATE register SET member_ids = :mi "
                "WHERE register_type = 'Domain' AND project_id = :pid"
            ),
            {"mi": json.dumps(all_active_ids), "pid": project_id},
        ).rowcount

        if update_count == 0:
            raise RuntimeError(
                "DomainRegister not found — migration may not have run"
            )

        session.commit()

    except Exception as exc:
        session.rollback()
        result.status = "failed"
        result.failure_reason = f"Ledger transaction rolled back: {exc}"
        return result

    # Build domains_produced summary
    # Count cross-cutting CCIs per domain (appearing in >1 domain)
    all_cci_refs_flat: list[str] = [
        ci_id
        for proposal in stage3.proposals
        for ci_id in proposal.cci_refs
    ]
    cci_occurrence: dict[str, int] = {}
    for ci_id in all_cci_refs_flat:
        cci_occurrence[ci_id] = cci_occurrence.get(ci_id, 0) + 1

    for proposal, domain_id in zip(stage3.proposals, new_ids):
        cross_cut_count = sum(
            1 for ci_id in proposal.cci_refs if cci_occurrence[ci_id] > 1
        )
        result.domains_produced.append(
            {
                "domain_id": domain_id,
                "name": proposal.name,
                "cci_ref_count": len(proposal.cci_refs),
                "cross_cutting_cci_count": cross_cut_count,
            }
        )

    result.domain_count_produced = len(stage3.proposals)
    return result
