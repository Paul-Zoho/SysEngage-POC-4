"""
Stage 3 — Structural Validation (DM, with conditional IM repair).

Per Domain Derivation Mechanism Spec v0.13 §4.3:
  All six checks run in sequence on the AI proposal in-memory. No DB calls
  except the optional repair AI call (CHK-3c-04 conditional IM sub-act).

  CHK-3c-01  No empty cci_refs per proposal.
  CHK-3c-02  All cci_refs resolve to the eligible set (strip invalid refs).
  CHK-3c-03  No duplicate Domain names (case-insensitive merge).
  CHK-3c-04  Non-Loss: every eligible CCI covered; repair prompt if orphans.
  CHK-3c-05  Cross-cutting advisory: CCI appearing in > threshold Domains.
  CHK-3c-06  At least one Domain survives after CHK-3c-01..04.
  ADVC-3c-01 Domain count soft-bounds advisory.

assign_membership_inserts from IncrementalRerun are NOT written here — they
are passed through to Stage 4 unchanged.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from core.ai_client import MODEL, get_ai_client
from mechanisms.domain_derivation.prompts.domain_repair_prompt import (
    build_domain_repair_prompt,
)
from mechanisms.domain_derivation.schemas.domain_grouping_response_schema import (
    DomainProposal,
)
from mechanisms.domain_derivation.schemas.domain_repair_response_schema import (
    DomainRepairResponse,
)
from mechanisms.domain_derivation.stage1_preflight import EligibleCCI, Stage1Result
from mechanisms.domain_derivation.stage2_ai_grouping import Stage2Result

_log = logging.getLogger(__name__)


@dataclass
class Stage3Result:
    proposals: list[DomainProposal] = field(default_factory=list)
    assign_membership_inserts: list[tuple[str, str]] = field(default_factory=list)
    repair_prompt_issued: bool = False
    orphaned_ccis: list[str] = field(default_factory=list)
    cross_cutting_advisories: list[dict[str, Any]] = field(default_factory=list)
    validation_failures: list[dict[str, Any]] = field(default_factory=list)
    ai_model_fingerprints: list[dict[str, Any]] = field(default_factory=list)
    execution_warnings: list[dict[str, Any]] = field(default_factory=list)
    concern_entities: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    failure_reason: str | None = None


def _call_repair_ai(prompt: str) -> tuple[Any, dict[str, Any]]:
    """Issue the repair AI call. One attempt only — no retry per spec."""
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


def _parse_repair_response(text_: str) -> DomainRepairResponse | None:
    """Parse AI text as DomainRepairResponse; return None on failure."""
    try:
        data = json.loads(text_)
        return DomainRepairResponse.model_validate(data)
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

    Returns Stage3Result with validated/repaired proposals and any
    cross-cutting advisories, validation failures, and concern entities.
    """
    result = Stage3Result(
        assign_membership_inserts=list(stage2.assign_membership_inserts),
    )

    eligible_ci_ids: set[str] = {c.ci_id for c in stage1.eligible_ccis}
    proposals: list[DomainProposal] = list(stage2.proposals)

    # CHK-3c-01 — No empty cci_refs
    surviving: list[DomainProposal] = []
    for p in proposals:
        if len(p.cci_refs) == 0:
            result.validation_failures.append(
                {
                    "check_id": "CHK-3c-01",
                    "domain_name": p.name,
                    "detail": "empty cci_refs",
                }
            )
        else:
            surviving.append(p)

    if not surviving and proposals:
        result.status = "failed"
        result.failure_reason = "All Domain proposals have empty cci_refs (CHK-3c-01)"
        return result
    proposals = surviving

    # CHK-3c-02 — All cci_refs resolve to eligible set
    cleaned: list[DomainProposal] = []
    for p in proposals:
        valid_refs = [r for r in p.cci_refs if r in eligible_ci_ids]
        invalid_refs = [r for r in p.cci_refs if r not in eligible_ci_ids]
        for ref in invalid_refs:
            result.validation_failures.append(
                {
                    "check_id": "CHK-3c-02",
                    "domain_name": p.name,
                    "detail": f"cci_ref {ref!r} not in eligible set — stripped",
                }
            )
        if valid_refs:
            cleaned.append(
                DomainProposal(
                    name=p.name,
                    description=p.description,
                    classification_type=p.classification_type,
                    cci_refs=valid_refs,
                )
            )
        else:
            result.validation_failures.append(
                {
                    "check_id": "CHK-3c-01",
                    "domain_name": p.name,
                    "detail": "empty cci_refs after stripping invalid refs (CHK-3c-02)",
                }
            )
    proposals = cleaned

    # CHK-3c-03 — No duplicate Domain names (case-insensitive merge)
    seen: dict[str, int] = {}
    merged: list[DomainProposal] = []
    for p in proposals:
        key = p.name.lower().strip()
        if key in seen:
            # Merge: union of cci_refs into the first occurrence
            existing = merged[seen[key]]
            combined = list(dict.fromkeys(existing.cci_refs + p.cci_refs))
            merged[seen[key]] = DomainProposal(
                name=existing.name,
                description=existing.description,
                classification_type=existing.classification_type,
                cci_refs=combined,
            )
            result.execution_warnings.append(
                {"type": "duplicate_domain_name_merged", "domain_name": p.name}
            )
        else:
            seen[key] = len(merged)
            merged.append(p)
    proposals = merged

    # CHK-3c-04 — Non-Loss: every eligible CCI covered
    covered = {ref for p in proposals for ref in p.cci_refs}
    orphaned = eligible_ci_ids - covered

    if orphaned:
        result.repair_prompt_issued = True
        orphaned_cci_dicts = [
            {
                "ci_id": c.ci_id,
                "column": c.column,
                "classification_type": c.classification_type,
                "description": c.description,
            }
            for c in stage1.eligible_ccis
            if c.ci_id in orphaned
        ]
        current_proposal_dicts = [
            {
                "name": p.name,
                "description": p.description,
                "cci_ref_count": len(p.cci_refs),
            }
            for p in proposals
        ]
        repair_prompt = build_domain_repair_prompt(
            orphaned_ccis=orphaned_cci_dicts,
            current_proposals=current_proposal_dicts,
        )
        try:
            msg, fp = _call_repair_ai(repair_prompt)
            result.ai_model_fingerprints.append(fp)
            parsed_repair = _parse_repair_response(msg.content[0].text)
        except Exception as exc:
            _log.warning("Repair AI call failed: %s", exc)
            parsed_repair = None

        if parsed_repair is not None:
            # Merge repair actions into proposals
            proposal_name_index = {p.name.lower().strip(): i for i, p in enumerate(proposals)}
            for action in parsed_repair.actions:
                if action.action == "assign":
                    key = action.domain_name.lower().strip()
                    if key in proposal_name_index:
                        idx = proposal_name_index[key]
                        existing = proposals[idx]
                        combined = list(
                            dict.fromkeys(existing.cci_refs + list(action.new_cci_refs))
                        )
                        proposals[idx] = DomainProposal(
                            name=existing.name,
                            description=existing.description,
                            classification_type=existing.classification_type,
                            cci_refs=combined,
                        )
                    else:
                        # Name not found — treat as new Domain
                        result.execution_warnings.append(
                            {
                                "type": "repair_assign_name_not_found",
                                "domain_name": action.domain_name,
                            }
                        )
                        new_p = DomainProposal(
                            name=action.domain_name,
                            description=(
                                "Domain created from repair assignment — review recommended"
                            ),
                            classification_type=None,
                            cci_refs=list(action.new_cci_refs),
                        )
                        proposal_name_index[action.domain_name.lower().strip()] = len(proposals)
                        proposals.append(new_p)
                else:
                    new_p = DomainProposal(
                        name=action.name,
                        description=action.description,
                        classification_type=action.classification_type,
                        cci_refs=list(action.cci_refs),
                    )
                    proposal_name_index[action.name.lower().strip()] = len(proposals)
                    proposals.append(new_p)

        # Re-compute orphans after repair
        covered = {ref for p in proposals for ref in p.cci_refs}
        orphaned = eligible_ci_ids - covered

    if orphaned:
        # Persistent orphans — record and raise Concern
        result.orphaned_ccis = sorted(orphaned)
        result.status = "ok_with_warnings"
        result.concern_entities.append(
            {
                "description": (
                    f"Pass 3c Domain Derivation: {len(orphaned)} CCI(s) could not be "
                    f"assigned to any Domain after repair attempt. Practitioner review "
                    f"required. Orphaned ci_ids: {sorted(orphaned)}"
                ),
                "source_refs": sorted(orphaned),
                "practitioner_id": practitioner_id,
                "project_id": project_id,
                "produced_in_row": str(row_ref),
            }
        )

    # CHK-3c-05 — Cross-cutting advisory
    from math import ceil

    ci_domain_count: dict[str, int] = {}
    for p in proposals:
        for ref in p.cci_refs:
            ci_domain_count[ref] = ci_domain_count.get(ref, 0) + 1

    for ci_id, count in ci_domain_count.items():
        if count > stage1.domain_cross_cutting_advisory_threshold:
            result.cross_cutting_advisories.append(
                {"ci_id": ci_id, "domain_count": count}
            )

    # CHK-3c-06 — At least one Domain survives
    if not proposals:
        result.status = "failed"
        result.failure_reason = "zero domains survived structural validation"
        return result

    # ADVC-3c-01 — Domain count soft-bounds advisory
    eligible_count = len(stage1.eligible_ccis)
    proposal_count = len(proposals)
    lower_bound = 1 + ceil(eligible_count / 15)
    upper_bound_val = eligible_count / 2
    if proposal_count < lower_bound or proposal_count > upper_bound_val:
        result.execution_warnings.append(
            {
                "type": "domain_count_advisory",
                "domain_count": proposal_count,
                "cci_count": eligible_count,
                "lower_bound": lower_bound,
                "upper_bound": int(upper_bound_val),
            }
        )

    result.proposals = proposals
    return result
