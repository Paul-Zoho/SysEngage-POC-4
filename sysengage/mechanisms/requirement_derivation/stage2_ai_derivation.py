"""
Stage 2 — Per-Domain AI Derivation Act (IM).

Per Requirement Derivation Mechanism Spec v0.17 §4.2:
  Path R (rows >= 2, FirstRun/FullRerun only): interrogative elaboration of
    row n-1 seeds BEFORE Path N. One AI call for all seeds; each returned
    proposal has refines_refs=[seed_id] set at derivation. cci_refs may be
    empty (CHK-3d-02 relaxed in Stage 3).

  Path N (FirstRun / FullRerun): per-Domain loop — one AI call per active
    Domain. Each call produces a List[RequirementProposal] for that Domain.
    One retry on parse failure per Domain; second failure → skip Domain (log
    to validation_failures). If ALL Domains fail: execution_status = "Failed".
    Partial failure proceeds; skipped-Domain CCIs become orphans for CHK-3d-05.

  IncrementalRerun path: per-Domain loop for Domains owning ≥1 new CCI only.
    Uses IncrementalRequirementProposal schema (DISTINCT class).
    Persistent parse failure → falls back to FullRerun for the whole row.
    Path R is NOT run for IncrementalRerun.

AI model fingerprints recorded per IM call: "stage2_domain_{domain_id}",
"stage2_path_r".
LPM constraint enforced at prompt level.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.ai_client import MODEL, get_ai_client
from mechanisms.requirement_derivation.prompts.requirement_derivation_prompt import (
    build_requirement_derivation_prompt,
)
from mechanisms.requirement_derivation.prompts.requirement_incremental_prompt import (
    build_requirement_incremental_prompt,
)
from mechanisms.requirement_derivation.prompts.requirement_refinement_prompt import (
    build_requirement_refinement_prompt,
)
from mechanisms.requirement_derivation.schemas.requirement_derivation_response_schema import (
    RequirementProposal,
)
from mechanisms.requirement_derivation.schemas.requirement_incremental_response_schema import (
    IncrementalRequirementProposal,
)
from mechanisms.requirement_derivation.schemas.requirement_refinement_response_schema import (
    RefinementProposal,
)
from mechanisms.requirement_derivation.stage1_preflight import (
    ActiveDomain,
    EligibleCCI,
    Stage1Result,
)

_log = logging.getLogger(__name__)


@dataclass
class TaggedProposal:
    """A RequirementProposal tagged with its source Domain (in-memory only)."""
    source_domain_id: str
    statement: str
    requirement_type: str
    cci_refs: list[str]
    refines_refs: list[str]
    rationale: str | None
    fit_criteria: str | None
    verification_method: str | None
    priority: str | None
    confidence: float

    @classmethod
    def from_proposal(
        cls, proposal: RequirementProposal, source_domain_id: str
    ) -> "TaggedProposal":
        return cls(
            source_domain_id=source_domain_id,
            statement=proposal.statement,
            requirement_type=proposal.requirement_type,
            cci_refs=list(proposal.cci_refs),
            refines_refs=[],
            rationale=proposal.rationale,
            fit_criteria=proposal.fit_criteria,
            verification_method=proposal.verification_method,
            priority=proposal.priority,
            confidence=proposal.confidence,
        )

    @classmethod
    def from_incremental(
        cls, proposal: IncrementalRequirementProposal, source_domain_id: str
    ) -> "TaggedProposal":
        return cls(
            source_domain_id=source_domain_id,
            statement=proposal.statement,
            requirement_type=proposal.requirement_type,
            cci_refs=list(proposal.cci_refs),
            refines_refs=[],
            rationale=proposal.rationale,
            fit_criteria=proposal.fit_criteria,
            verification_method=proposal.verification_method,
            priority=proposal.priority,
            confidence=proposal.confidence,
        )

    @classmethod
    def from_refinement(
        cls,
        proposal: RefinementProposal,
        source_domain_id: str,
    ) -> "TaggedProposal":
        """Create a Path R proposal with refines_refs set at derivation."""
        return cls(
            source_domain_id=source_domain_id,
            statement=proposal.statement,
            requirement_type=proposal.requirement_type,
            cci_refs=list(proposal.cci_refs),
            refines_refs=list(proposal.refines_refs),
            rationale=proposal.rationale,
            fit_criteria=proposal.fit_criteria,
            verification_method=proposal.verification_method,
            priority=proposal.priority,
            confidence=proposal.confidence,
        )


@dataclass
class Stage2Result:
    proposals: list[TaggedProposal] = field(default_factory=list)
    ai_model_fingerprints: list[dict[str, Any]] = field(default_factory=list)
    execution_warnings: list[dict[str, Any]] = field(default_factory=list)
    validation_failures: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    failure_reason: str | None = None
    effective_scenario: str = "FirstRun"
    seed_set: list[dict[str, Any]] = field(default_factory=list)
    path_r_count: int = 0
    seed_set_surviving_count: int = 0  # VER-3d-21: independent count of surviving row n-1 reqs


def _call_ai(prompt: str, *, max_tokens: int = 8192) -> tuple[Any, dict[str, Any]]:
    """Issue a single AI call; return (message, fingerprint_dict)."""
    client = get_ai_client()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    fingerprint = {
        "model": msg.model,
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
    }
    return msg, fingerprint


def _strip_code_fence(text_: str) -> str:
    """Strip markdown ```json ... ``` or ``` ... ``` code fences if present."""
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text_, re.DOTALL)
    return m.group(1).strip() if m else text_.strip()


def _parse_derivation_response(text_: str) -> list[RequirementProposal] | None:
    try:
        data = json.loads(_strip_code_fence(text_))
        if not isinstance(data, list):
            return None
        return [RequirementProposal.model_validate(item) for item in data]
    except Exception:
        return None


def _parse_incremental_response(text_: str) -> list[IncrementalRequirementProposal] | None:
    try:
        data = json.loads(_strip_code_fence(text_))
        if not isinstance(data, list):
            return None
        return [IncrementalRequirementProposal.model_validate(item) for item in data]
    except Exception:
        return None


def _build_cci_dicts(
    eligible_ccis: list[EligibleCCI], ci_id_set: set[str]
) -> list[dict[str, Any]]:
    return [
        {
            "ci_id": c.ci_id,
            "column": c.column,
            "classification_type": c.classification_type,
            "description": c.description,
        }
        for c in eligible_ccis
        if c.ci_id in ci_id_set
    ]


def _parse_refinement_response(text_: str) -> list[RefinementProposal] | None:
    try:
        data = json.loads(_strip_code_fence(text_))
        if not isinstance(data, list):
            return None
        return [RefinementProposal.model_validate(item) for item in data]
    except Exception:
        return None


def _count_surviving_requirements(
    session: Session, project_id: str, parent_row_ref: int
) -> int:
    """Independent count of surviving row n-1 requirements (VER-3d-21 baseline)."""
    row = session.execute(
        text(
            "SELECT COUNT(*) FROM requirement "
            "WHERE project_id = :pid "
            "  AND row_target = :row "
            "  AND retired_at IS NULL"
        ),
        {"pid": project_id, "row": str(parent_row_ref)},
    ).scalar()
    return int(row or 0)


def _load_seeds(
    session: Session, project_id: str, parent_row_ref: int
) -> list[dict[str, Any]]:
    """Load active row n-1 requirements for use as Path R seeds."""
    rows = session.execute(
        text(
            "SELECT requirement_id, statement, requirement_type, domain_refs "
            "FROM requirement "
            "WHERE project_id = :pid "
            "  AND row_target = :row "
            "  AND retired_at IS NULL "
            "ORDER BY requirement_id"
        ),
        {"pid": project_id, "row": str(parent_row_ref)},
    ).fetchall()
    return [
        {
            "requirement_id": r[0],
            "statement": r[1],
            "requirement_type": r[2],
            "domain_refs": list(r[3]) if r[3] else [],
        }
        for r in rows
    ]


def _resolve_source_domain_id(
    cci_refs: list[str],
    stage1: Stage1Result,
) -> str:
    """
    Resolve source_domain_id for a Path R proposal.
    If cci_refs are set, use the domain owning the first cci_ref.
    Fallback: first active domain (arbitrary but deterministic).
    """
    if cci_refs and stage1.active_domains:
        first_ci = cci_refs[0]
        for d in stage1.active_domains:
            if first_ci in set(d.cell_content_item_refs):
                return d.domain_id
    return stage1.active_domains[0].domain_id if stage1.active_domains else ""


_PATH_R_BATCH_SIZE = 15


def _run_path_r_batch(
    batch_seeds: list[dict[str, Any]],
    batch_index: int,
    total_batches: int,
    domains_context: list[dict[str, Any]],
    row_ref: int,
    valid_seed_ids: set[str],
    stage1: Stage1Result,
    result: Stage2Result,
) -> list[TaggedProposal]:
    """
    Run one Path R batch of seeds (called by _run_path_r when batching).
    Returns proposals for this batch; logs warnings into result.
    """
    prompt = build_requirement_refinement_prompt(
        row_ref=row_ref,
        seeds=batch_seeds,
        domains=domains_context,
    )

    parsed: list[RefinementProposal] | None = None
    msg = None
    for attempt in range(2):
        try:
            msg, fp = _call_ai(prompt)
        except Exception as exc:
            _log.warning(
                "Path R batch %d/%d AI error attempt=%d: %s",
                batch_index + 1, total_batches, attempt + 1, exc,
            )
            if attempt == 1:
                result.execution_warnings.append({
                    "type": "path_r_ai_error",
                    "batch": batch_index,
                    "detail": str(exc),
                })
                return []
            continue

        fp["stage"] = f"stage2_path_r_batch{batch_index}"
        result.ai_model_fingerprints.append(fp)

        parsed = _parse_refinement_response(msg.content[0].text)
        if parsed is not None:
            break
        if attempt == 0:
            _log.warning(
                "Path R batch %d/%d parse failure — retrying once",
                batch_index + 1, total_batches,
            )

    if parsed is None:
        _log.warning(
            "Path R batch %d/%d parse failure after retry — batch skipped",
            batch_index + 1, total_batches,
        )
        raw_preview = ""
        if msg is not None and msg.content:
            raw_preview = msg.content[0].text[:200]
        result.execution_warnings.append({
            "type": "path_r_parse_failure",
            "batch": batch_index,
            "batch_seed_ids": [s["requirement_id"] for s in batch_seeds],
            "response_preview": raw_preview,
        })
        return []

    proposals: list[TaggedProposal] = []
    for item in parsed:
        if not item.refines_refs or item.refines_refs[0] not in valid_seed_ids:
            _log.warning(
                "Path R batch %d/%d: proposal with invalid refines_refs=%s — skipped",
                batch_index + 1, total_batches, item.refines_refs,
            )
            result.execution_warnings.append({
                "type": "path_r_invalid_refines_refs",
                "batch": batch_index,
                "refines_refs": item.refines_refs,
                "statement_preview": item.statement[:60],
            })
            continue
        source_did = _resolve_source_domain_id(list(item.cci_refs), stage1)
        proposals.append(TaggedProposal.from_refinement(item, source_did))

    return proposals


def _run_path_r(
    stage1: Stage1Result,
    seeds: list[dict[str, Any]],
    row_ref: int,
    result: Stage2Result,
) -> list[TaggedProposal]:
    """
    Path R — seed-elaboration (v0.14).
    Seeds are processed in batches of _PATH_R_BATCH_SIZE to keep each AI call's
    output well within the max_tokens ceiling.  All batch proposals are combined
    and returned.  Logged under fingerprint "stage2_path_r_batch<N>".
    On failure, logs a warning and returns empty list (Path N still runs).
    """
    if not seeds:
        return []

    domains_context = [
        {
            "domain_id": d.domain_id,
            "name": d.name,
            "description": d.description,
            "cell_content_items": [
                {
                    "ci_id": c.ci_id,
                    "column": c.column,
                    "classification_type": c.classification_type,
                    "description": c.description,
                }
                for c in stage1.eligible_ccis
                if c.ci_id in set(d.cell_content_item_refs)
            ],
        }
        for d in stage1.active_domains
    ]

    valid_seed_ids = {s["requirement_id"] for s in seeds}
    batches = [
        seeds[i : i + _PATH_R_BATCH_SIZE]
        for i in range(0, len(seeds), _PATH_R_BATCH_SIZE)
    ]
    total_batches = len(batches)
    _log.info(
        "Path R: %d seeds → %d batch(es) of ≤%d",
        len(seeds), total_batches, _PATH_R_BATCH_SIZE,
    )

    all_proposals: list[TaggedProposal] = []
    for batch_index, batch_seeds in enumerate(batches):
        batch_proposals = _run_path_r_batch(
            batch_seeds=batch_seeds,
            batch_index=batch_index,
            total_batches=total_batches,
            domains_context=domains_context,
            row_ref=row_ref,
            valid_seed_ids=valid_seed_ids,
            stage1=stage1,
            result=result,
        )
        all_proposals.extend(batch_proposals)
        _log.info(
            "Path R batch %d/%d: %d proposals (running total %d)",
            batch_index + 1, total_batches, len(batch_proposals), len(all_proposals),
        )

    _log.info(
        "Path R: %d proposals total from %d seeds across %d batch(es)",
        len(all_proposals), len(seeds), total_batches,
    )
    return all_proposals


def _run_derivation_path(
    stage1: Stage1Result,
    row_ref: int,
    scenario: str,
    seed_set: list[dict[str, Any]] | None = None,
) -> Stage2Result:
    """
    FirstRun / FullRerun — Path R (seed elaboration, rows >= 2) then Path N
    (per-Domain loop, one AI call per Domain).
    """
    result = Stage2Result(effective_scenario=scenario)
    result.seed_set = seed_set or []

    # Path R: seed elaboration for rows >= 2
    if row_ref >= 2 and result.seed_set:
        path_r_proposals = _run_path_r(stage1, result.seed_set, row_ref, result)
        result.proposals.extend(path_r_proposals)
        result.path_r_count = len(path_r_proposals)
        if path_r_proposals:
            _log.info(
                "Path R produced %d proposals for row %d from %d seeds",
                len(path_r_proposals), row_ref, len(result.seed_set),
            )

    eligible_by_id = {c.ci_id: c for c in stage1.eligible_ccis}

    domains_succeeded = 0
    for domain in stage1.active_domains:
        domain_ci_set = set(domain.cell_content_item_refs)
        domain_cci_list = _build_cci_dicts(stage1.eligible_ccis, domain_ci_set)

        prompt = build_requirement_derivation_prompt(
            row_ref=row_ref,
            domain={
                "domain_id": domain.domain_id,
                "name": domain.name,
                "description": domain.description,
            },
            domain_cci_set=domain_cci_list,
        )

        parsed: list[RequirementProposal] | None = None
        for attempt in range(2):
            try:
                msg, fp = _call_ai(prompt)
            except Exception as exc:
                _log.warning(
                    "Stage 2 AI error domain=%s attempt=%d: %s",
                    domain.domain_id, attempt + 1, exc,
                )
                if attempt == 1:
                    break
                continue

            fp["stage"] = f"stage2_domain_{domain.domain_id}"
            result.ai_model_fingerprints.append(fp)

            parsed = _parse_derivation_response(msg.content[0].text)
            if parsed is not None:
                break
            if attempt == 0:
                _log.warning(
                    "Stage 2 parse failure domain=%s — retrying once", domain.domain_id
                )

        if parsed is None:
            _log.warning(
                "Stage 2 parse failure domain=%s after retry — skipping",
                domain.domain_id,
            )
            result.validation_failures.append(
                {
                    "check_id": "domain_derivation_parse_failure",
                    "source_domain_id": domain.domain_id,
                    "detail": "AI derivation response parse failure after retry — domain skipped",
                }
            )
            continue

        for proposal in parsed:
            result.proposals.append(
                TaggedProposal.from_proposal(proposal, domain.domain_id)
            )
        domains_succeeded += 1

    if domains_succeeded == 0 and stage1.active_domains:
        result.status = "failed"
        result.failure_reason = (
            "AI derivation response parse failure for all Domains after retry"
        )

    return result


def _run_incremental_path(
    stage1: Stage1Result,
    session: Session,
    row_ref: int,
    project_id: str,
) -> Stage2Result:
    """
    IncrementalRerun — per-Domain loop for Domains owning ≥1 new CCI.
    Falls back to FullRerun if all incremental calls fail.
    """
    result = Stage2Result(effective_scenario="IncrementalRerun")

    # Covered ci_ids from active Requirements for this row
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
    covered_ci_ids: set[str] = {r[0] for r in covered_rows}

    # Existing Requirements per Domain (for context)
    existing_req_rows = session.execute(
        text(
            "SELECT r.requirement_id, r.statement, r.requirement_type, "
            "       r.domain_refs "
            "FROM requirement r "
            "WHERE r.project_id = :pid "
            "  AND r.row_target = :row "
            "  AND r.retired_at IS NULL"
        ),
        {"pid": project_id, "row": str(row_ref)},
    ).fetchall()

    # Build per-Domain existing Requirement summaries
    # domain_refs is a JSONB array of domain_ids; map each req to its domains
    domain_existing: dict[str, list[dict[str, Any]]] = {
        d.domain_id: [] for d in stage1.active_domains
    }
    for req_row in existing_req_rows:
        req_domain_refs = req_row[3] if req_row[3] else []
        summary = {
            "requirement_id": req_row[0],
            "statement": req_row[1],
            "requirement_type": req_row[2],
        }
        for did in req_domain_refs:
            if did in domain_existing:
                domain_existing[did].append(summary)

    all_ci_ids = {c.ci_id for c in stage1.eligible_ccis}
    new_ci_ids = all_ci_ids - covered_ci_ids

    parse_failures = 0
    for domain in stage1.active_domains:
        domain_ci_set = set(domain.cell_content_item_refs)
        domain_new_ci_ids = domain_ci_set & new_ci_ids
        if not domain_new_ci_ids:
            continue

        new_cci_list = _build_cci_dicts(stage1.eligible_ccis, domain_new_ci_ids)
        existing_reqs = domain_existing.get(domain.domain_id, [])

        prompt = build_requirement_incremental_prompt(
            row_ref=row_ref,
            domain={
                "domain_id": domain.domain_id,
                "name": domain.name,
                "description": domain.description,
            },
            existing_requirements=existing_reqs,
            new_domain_ccis=new_cci_list,
        )

        parsed_inc: list[IncrementalRequirementProposal] | None = None
        for attempt in range(2):
            try:
                msg, fp = _call_ai(prompt)
            except Exception as exc:
                _log.warning(
                    "IncrementalRerun AI error domain=%s attempt=%d: %s",
                    domain.domain_id, attempt + 1, exc,
                )
                if attempt == 1:
                    parse_failures += 1
                    break
                continue

            fp["stage"] = f"stage2_domain_{domain.domain_id}"
            result.ai_model_fingerprints.append(fp)

            parsed_inc = _parse_incremental_response(msg.content[0].text)
            if parsed_inc is not None:
                break
            if attempt == 0:
                _log.warning(
                    "IncrementalRerun parse failure domain=%s — retrying",
                    domain.domain_id,
                )

        if parsed_inc is None:
            parse_failures += 1
            _log.warning(
                "IncrementalRerun parse failure domain=%s after retry",
                domain.domain_id,
            )
            continue

        for proposal in parsed_inc:
            result.proposals.append(
                TaggedProposal.from_incremental(proposal, domain.domain_id)
            )

    # If any domain failed to parse, fall back to FullRerun
    if parse_failures > 0:
        result.execution_warnings.append({"type": "incremental_fallback_to_fullrerun"})
        _log.warning(
            "IncrementalRerun had %d parse failure(s) — falling back to FullRerun",
            parse_failures,
        )
        fallback = _run_derivation_path(stage1, row_ref, "FullRerun")
        fallback.ai_model_fingerprints = (
            result.ai_model_fingerprints + fallback.ai_model_fingerprints
        )
        fallback.execution_warnings = result.execution_warnings + fallback.execution_warnings
        return fallback

    return result


def run_stage2(
    *,
    stage1: Stage1Result,
    session: Session,
    project_id: str,
    row_ref: int,
) -> Stage2Result:
    """
    Run Stage 2 AI derivation. Routes by stage1.scenario.

    Returns Stage2Result. Check result.status before proceeding:
      "ok"     — proposals available; proceed to Stage 3
      "failed" — hard stop; write failure pass

    v0.13: FirstRun/FullRerun for rows >= 2 loads row n-1 seeds and runs
    Path R (seed elaboration) before Path N (per-Domain loop).
    """
    if stage1.scenario in ("FirstRun", "FullRerun"):
        seed_set: list[dict[str, Any]] = []
        surviving_count: int = 0
        if row_ref >= 2:
            try:
                seed_set = _load_seeds(session, project_id, row_ref - 1)
                surviving_count = _count_surviving_requirements(session, project_id, row_ref - 1)
                _log.info(
                    "Path R: loaded %d seeds from row %d for project %s (surviving=%d)",
                    len(seed_set), row_ref - 1, project_id, surviving_count,
                )
            except Exception as exc:
                _log.warning(
                    "Path R seed load failed — proceeding without seeds: %s", exc
                )
        result = _run_derivation_path(stage1, row_ref, stage1.scenario, seed_set=seed_set)
        result.seed_set_surviving_count = surviving_count
        if row_ref >= 2 and not seed_set:
            result.execution_warnings.append({
                "type": "empty_seed_set_upstream_gap",
                "parent_row_ref": row_ref - 1,
            })
            _log.warning(
                "empty_seed_set_upstream_gap: row %d has no surviving seeds from row %d "
                "(upstream pass may not have produced requirements)",
                row_ref, row_ref - 1,
            )
        return result
    else:
        return _run_incremental_path(stage1, session, row_ref, project_id)
