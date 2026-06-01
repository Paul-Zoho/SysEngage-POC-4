"""
Stage 3 — Structural Validation (DM, with conditional IM repair).

Per Requirement Derivation Mechanism Spec v0.1 §4.3:
  All checks run in sequence on the accumulated proposal set. Pure in-memory
  operations except the Non-Loss repair prompt (IM conditional sub-act).

  CHK-3d-01  No empty statement.
  CHK-3d-02  No empty cci_refs.
  CHK-3d-03  cci_refs resolve to source Domain's eligible membership (strip out-of-Domain).
  CHK-3d-04  fit_criteria integrity (strip present-but-empty; advisory for Performance
             without fit_criteria).
  CHK-3d-05  Non-Loss: every eligible CCI covered by ≥1 Requirement; repair prompt
             if orphans. Persistent orphan → CompletedWithWarnings + Concern raised.
  CHK-3d-06  Failure if all proposals rejected and repair produced nothing.
  CHK-3d-07  Exact-duplicate collapse (same statement + cci_refs set).
  ADVC-3d-01 Requirement-per-Domain soft bounds advisory.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from core.ai_client import MODEL, get_ai_client
from mechanisms.requirement_derivation.prompts.requirement_repair_prompt import (
    build_requirement_repair_prompt,
)
from mechanisms.requirement_derivation.schemas.requirement_repair_response_schema import (
    RepairRequirementProposal,
)
from mechanisms.requirement_derivation.stage1_preflight import (
    ActiveDomain,
    EligibleCCI,
    Stage1Result,
)
from mechanisms.requirement_derivation.stage2_ai_derivation import (
    Stage2Result,
    TaggedProposal,
)

_log = logging.getLogger(__name__)


@dataclass
class Stage3Result:
    proposals: list[TaggedProposal] = field(default_factory=list)
    repair_prompt_issued: bool = False
    orphaned_ccis: list[str] = field(default_factory=list)
    validation_failures: list[dict[str, Any]] = field(default_factory=list)
    duplicate_requirements_collapsed: list[dict[str, Any]] = field(default_factory=list)
    ai_model_fingerprints: list[dict[str, Any]] = field(default_factory=list)
    execution_warnings: list[dict[str, Any]] = field(default_factory=list)
    concern_entities: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    failure_reason: str | None = None


def _call_repair_ai(prompt: str) -> tuple[Any, dict[str, Any]]:
    client = get_ai_client()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    fingerprint = {
        "stage": "stage3_repair",
        "model": msg.model,
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
    }
    return msg, fingerprint


def _strip_code_fence(text_: str) -> str:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text_, re.DOTALL)
    return m.group(1).strip() if m else text_.strip()


def _parse_repair_response(text_: str) -> list[RepairRequirementProposal] | None:
    try:
        data = json.loads(_strip_code_fence(text_))
        if not isinstance(data, list):
            return None
        return [RepairRequirementProposal.model_validate(item) for item in data]
    except Exception:
        return None


def run_stage3(
    *,
    stage1: Stage1Result,
    stage2: Stage2Result,
    practitioner_id: str,
    project_id: str,
    row_ref: int,
) -> Stage3Result:
    """
    Run Stage 3 structural validation.

    Returns Stage3Result with validated proposals, validation_failures,
    orphaned_ccis, concern_entities, and execution_warnings.
    """
    result = Stage3Result()

    eligible_ci_ids: set[str] = {c.ci_id for c in stage1.eligible_ccis}
    cci_by_id: dict[str, EligibleCCI] = {c.ci_id: c for c in stage1.eligible_ccis}
    domain_by_id: dict[str, ActiveDomain] = {
        d.domain_id: d for d in stage1.active_domains
    }

    proposals: list[TaggedProposal] = list(stage2.proposals)

    # -------------------------------------------------------------------------
    # CHK-3d-01 — No empty statement
    # -------------------------------------------------------------------------
    surviving: list[TaggedProposal] = []
    for p in proposals:
        if not p.statement or not p.statement.strip():
            result.validation_failures.append(
                {
                    "check_id": "CHK-3d-01",
                    "source_domain_id": p.source_domain_id,
                    "detail": "empty statement",
                }
            )
        else:
            surviving.append(p)
    proposals = surviving

    # -------------------------------------------------------------------------
    # CHK-3d-02 — No empty cci_refs
    # -------------------------------------------------------------------------
    surviving = []
    for p in proposals:
        if not p.cci_refs:
            result.validation_failures.append(
                {
                    "check_id": "CHK-3d-02",
                    "source_domain_id": p.source_domain_id,
                    "detail": "empty cci_refs",
                }
            )
        else:
            surviving.append(p)
    proposals = surviving

    # -------------------------------------------------------------------------
    # CHK-3d-03 — cci_refs resolve to source Domain's eligible membership
    # -------------------------------------------------------------------------
    cleaned: list[TaggedProposal] = []
    for p in proposals:
        domain = domain_by_id.get(p.source_domain_id)
        if domain is None:
            # Source domain no longer present — reject proposal
            result.validation_failures.append(
                {
                    "check_id": "CHK-3d-03",
                    "source_domain_id": p.source_domain_id,
                    "detail": "source_domain_id not found in active domains",
                }
            )
            continue

        domain_member_ids: set[str] = set(domain.cell_content_item_refs)
        valid_refs = [r for r in p.cci_refs if r in domain_member_ids]
        invalid_refs = [r for r in p.cci_refs if r not in domain_member_ids]
        for ref in invalid_refs:
            result.validation_failures.append(
                {
                    "check_id": "CHK-3d-03",
                    "source_domain_id": p.source_domain_id,
                    "detail": f"cci_ref {ref!r} not in source Domain membership — stripped",
                }
            )

        if not valid_refs:
            # All refs stripped → reject (CHK-3d-02 effect)
            result.validation_failures.append(
                {
                    "check_id": "CHK-3d-02",
                    "source_domain_id": p.source_domain_id,
                    "detail": "empty cci_refs after stripping out-of-Domain refs (CHK-3d-03)",
                }
            )
        else:
            p.cci_refs = valid_refs
            cleaned.append(p)
    proposals = cleaned

    # -------------------------------------------------------------------------
    # CHK-3d-04 — fit_criteria integrity
    # -------------------------------------------------------------------------
    for p in proposals:
        if p.fit_criteria is not None and not p.fit_criteria.strip():
            p.fit_criteria = None
            result.execution_warnings.append(
                {
                    "type": "fit_criteria_empty_stripped",
                    "source_domain_id": p.source_domain_id,
                }
            )
        if p.requirement_type == "Performance" and p.fit_criteria is None:
            result.execution_warnings.append(
                {
                    "type": "performance_missing_fit_criteria",
                    "source_domain_id": p.source_domain_id,
                    "statement_preview": p.statement[:80],
                }
            )

    # -------------------------------------------------------------------------
    # CHK-3d-05 — Non-Loss: every eligible CCI covered by ≥1 Requirement
    # -------------------------------------------------------------------------
    covered = {ref for p in proposals for ref in p.cci_refs}
    orphaned = eligible_ci_ids - covered

    if orphaned:
        result.repair_prompt_issued = True
        result.execution_warnings.append(
            {"type": "chk3d05_repair_performed", "orphan_count": len(orphaned)}
        )

        # Build orphaned CCI dicts with owning Domain
        orphaned_cci_dicts: list[dict[str, Any]] = []
        for ci_id in sorted(orphaned):
            cci = cci_by_id.get(ci_id)
            if cci is None:
                continue
            # Find owning domain(s) — guaranteed non-empty by Pass 3c Non-Loss
            owning_domain: ActiveDomain | None = None
            for domain in stage1.active_domains:
                if ci_id in set(domain.cell_content_item_refs):
                    owning_domain = domain
                    break
            if owning_domain is None:
                # Fallback: assign to first domain (should not happen given Pass 3c VER-3c-05)
                owning_domain = stage1.active_domains[0]

            orphaned_cci_dicts.append(
                {
                    "ci_id": ci_id,
                    "column": cci.column,
                    "classification_type": cci.classification_type,
                    "description": cci.description,
                    "owning_domain_id": owning_domain.domain_id,
                    "owning_domain_name": owning_domain.name,
                }
            )

        repair_prompt = build_requirement_repair_prompt(orphaned_ccis=orphaned_cci_dicts)

        parsed_repair: list[RepairRequirementProposal] | None = None
        try:
            msg, fp = _call_repair_ai(repair_prompt)
            result.ai_model_fingerprints.append(fp)
            parsed_repair = _parse_repair_response(msg.content[0].text)
        except Exception as exc:
            _log.warning("CHK-3d-05 repair AI call failed: %s", exc)
            result.execution_warnings.append(
                {"type": "chk3d05_repair_failed", "detail": str(exc)}
            )

        if parsed_repair is not None:
            for repair_proposal in parsed_repair:
                # Tag with owning domain of first cci_ref that is in orphaned set
                owning_did = orphaned_cci_dicts[0]["owning_domain_id"]
                for cci_dict in orphaned_cci_dicts:
                    if cci_dict["ci_id"] in repair_proposal.cci_refs:
                        owning_did = cci_dict["owning_domain_id"]
                        break
                proposals.append(
                    TaggedProposal(
                        source_domain_id=owning_did,
                        statement=repair_proposal.statement,
                        requirement_type=repair_proposal.requirement_type,
                        cci_refs=list(repair_proposal.cci_refs),
                        rationale=repair_proposal.rationale,
                        fit_criteria=repair_proposal.fit_criteria,
                        verification_method=repair_proposal.verification_method,
                        priority=repair_proposal.priority,
                        confidence=repair_proposal.confidence,
                    )
                )
        else:
            result.execution_warnings.append({"type": "chk3d05_repair_failed"})

        # Re-compute orphaned after repair
        covered = {ref for p in proposals for ref in p.cci_refs}
        orphaned = eligible_ci_ids - covered

    if orphaned:
        result.orphaned_ccis = sorted(orphaned)
        result.status = "ok_with_warnings"
        result.concern_entities.append(
            {
                "description": (
                    f"Pass 3d Requirement Derivation: {len(orphaned)} CCI(s) could not be "
                    f"covered by any Requirement after repair attempt. Practitioner review "
                    f"required. Orphaned ci_ids: {sorted(orphaned)}"
                ),
                "source_refs": sorted(orphaned),
                "practitioner_id": practitioner_id,
                "project_id": project_id,
                "produced_in_row": str(row_ref),
            }
        )

    # -------------------------------------------------------------------------
    # CHK-3d-06 — Failure if all proposals rejected
    # -------------------------------------------------------------------------
    if not proposals:
        result.status = "failed"
        result.failure_reason = "No valid Requirement proposals survived validation"
        return result

    # -------------------------------------------------------------------------
    # CHK-3d-07 — Exact-duplicate collapse (same statement + cci_refs set)
    # -------------------------------------------------------------------------
    seen_keys: dict[tuple, int] = {}
    deduped: list[TaggedProposal] = []
    for p in proposals:
        key = (p.statement.lower().strip(), frozenset(p.cci_refs))
        if key in seen_keys:
            # Collapse — record advisory; keep first
            result.execution_warnings.append(
                {"type": "duplicate_requirement_collapsed"}
            )
            result.duplicate_requirements_collapsed.append(
                {
                    "kept_statement": deduped[seen_keys[key]].statement,
                    "collapsed_count": 1,
                }
            )
        else:
            seen_keys[key] = len(deduped)
            deduped.append(p)
    proposals = deduped

    # -------------------------------------------------------------------------
    # ADVC-3d-01 — Requirement-per-Domain soft bounds
    # -------------------------------------------------------------------------
    for domain in stage1.active_domains:
        domain_proposals = [p for p in proposals if p.source_domain_id == domain.domain_id]
        req_count = len(domain_proposals)
        cci_count = len(domain.cell_content_item_refs)
        if req_count > cci_count:
            result.execution_warnings.append(
                {
                    "type": "requirement_count_advisory",
                    "domain_id": domain.domain_id,
                    "requirement_count": req_count,
                    "cci_count": cci_count,
                }
            )
            _log.info(
                "ADVC-3d-01: domain=%s produced %d Requirements for %d CCIs — "
                "possible over-decomposition",
                domain.domain_id, req_count, cci_count,
            )

    result.proposals = proposals
    return result
