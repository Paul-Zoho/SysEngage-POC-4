"""
Stage 3 — Structural Validation (DM, with conditional IM repair).

Per Domain Derivation Mechanism Spec v0.18 §4.3:
  All checks run in sequence on the AI proposal in-memory. No DB calls
  except the optional repair AI calls (CHK-3c-04 and CHK-3c-07 IM sub-acts).

  CHK-3c-01  No empty cci_refs per proposal.
  CHK-3c-02  All cci_refs resolve to the eligible set (strip invalid refs).
  CHK-3c-03  No duplicate Domain names (case-insensitive merge).
  CHK-3c-04  Non-Loss: every eligible CCI covered; repair prompt if orphans.
  CHK-3c-05  Cross-cutting advisory: CCI appearing in > threshold Domains.
  CHK-3c-06  At least one Domain survives after CHK-3c-01..04.
  CHK-3c-07  Single-CCI domain absorption (IM conditional): absorb isolated
             single-CCI Domains into neighbouring Domains via repair prompt.
  ADVC-3c-01 Domain count soft-bounds advisory.

assign_membership_inserts from IncrementalRerun are NOT written here — they
are passed through to Stage 4 unchanged.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from core.ai_client import MODEL, get_ai_client
from mechanisms.domain_derivation.prompts.domain_repair_prompt import (
    build_domain_repair_prompt,
)
from mechanisms.domain_derivation.prompts.domain_single_cci_repair_prompt import (
    build_single_cci_repair_prompt,
)
from mechanisms.domain_derivation.schemas.domain_grouping_response_schema import (
    DomainProposal,
)
from mechanisms.domain_derivation.schemas.domain_repair_response_schema import (
    DomainRepairResponse,
)
from mechanisms.domain_derivation.schemas.domain_single_cci_repair_response_schema import (
    SingleCCIRepairResponse,
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
    single_cci_absorption_issued: bool = False
    absorptions: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    failure_reason: str | None = None


def _call_repair_ai(prompt: str, stage_label: str) -> tuple[Any, dict[str, Any]]:
    """Issue an AI call. One attempt only for CHK-3c-04; two retries for CHK-3c-07."""
    client = get_ai_client()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    fingerprint = {
        "stage": stage_label,
        "model": msg.model,
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
    }
    return msg, fingerprint


def _strip_code_fence(text_: str) -> str:
    """Strip markdown ```json ... ``` or ``` ... ``` code fences if present."""
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text_, re.DOTALL)
    return m.group(1).strip() if m else text_.strip()


def _parse_repair_response(text_: str) -> DomainRepairResponse | None:
    """Parse AI text as DomainRepairResponse; return None on failure."""
    try:
        data = json.loads(_strip_code_fence(text_))
        return DomainRepairResponse.model_validate(data)
    except Exception:
        return None


def _parse_single_cci_repair_response(text_: str) -> SingleCCIRepairResponse | None:
    """Parse AI text as SingleCCIRepairResponse; return None on failure."""
    try:
        data = json.loads(_strip_code_fence(text_))
        return SingleCCIRepairResponse.model_validate(data)
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
            msg, fp = _call_repair_ai(repair_prompt, "stage3_repair")
            result.ai_model_fingerprints.append(fp)
            parsed_repair = _parse_repair_response(msg.content[0].text)
        except Exception as exc:
            _log.warning("Repair AI call failed: %s", exc)
            parsed_repair = None

        if parsed_repair is not None:
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

        covered = {ref for p in proposals for ref in p.cci_refs}
        orphaned = eligible_ci_ids - covered

    if orphaned:
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

    # CHK-3c-07 — Single-CCI domain absorption (IM conditional)
    # Per spec v0.18 §4.3: fire only when cci_count_input > 1, len(proposals) > 1,
    # and NOT all proposals are single-CCI.
    cci_count_input = len(stage1.eligible_ccis)
    single_cci_proposals = [p for p in proposals if len(p.cci_refs) == 1]

    _skip_chk3c07 = False
    if cci_count_input <= 1:
        _skip_chk3c07 = True
    elif len(proposals) == 1:
        _skip_chk3c07 = True
    elif len(single_cci_proposals) == len(proposals):
        result.execution_warnings.append({"type": "chk3c07_all_domains_single_cci"})
        _log.info("CHK-3c-07: all proposals are single-CCI — circular absorption risk, skipping")
        _skip_chk3c07 = True

    if single_cci_proposals and not _skip_chk3c07:
        isolated_ci_ids = [p.cci_refs[0] for p in single_cci_proposals]
        isolated_cci_dicts = [
            {
                "ci_id": c.ci_id,
                "column": c.column,
                "classification_type": c.classification_type,
                "description": c.description,
            }
            for c in stage1.eligible_ccis
            if c.ci_id in isolated_ci_ids
        ]
        available_domain_dicts = [
            {
                "name": p.name,
                "description": p.description,
                "cci_count": len(p.cci_refs),
            }
            for p in proposals
            if len(p.cci_refs) > 1
        ]

        chk07_prompt = build_single_cci_repair_prompt(
            isolated_ccis=isolated_cci_dicts,
            available_domains=available_domain_dicts,
            row_ref=row_ref,
        )

        parsed_chk07: SingleCCIRepairResponse | None = None
        for attempt in range(2):
            try:
                msg07, fp07 = _call_repair_ai(chk07_prompt, "stage3_chk3c07_repair")
                result.ai_model_fingerprints.append(fp07)
                parsed_chk07 = _parse_single_cci_repair_response(msg07.content[0].text)
                if parsed_chk07 is not None:
                    break
                _log.warning("CHK-3c-07 repair parse failure (attempt %d/2)", attempt + 1)
            except Exception as exc:
                _log.warning("CHK-3c-07 repair AI call failed (attempt %d/2): %s", attempt + 1, exc)

        if parsed_chk07 is not None:
            result.single_cci_absorption_issued = True
            proposal_name_idx = {p.name.lower().strip(): i for i, p in enumerate(proposals)}
            absorbed_ci_ids: set[str] = set()

            for assignment in parsed_chk07.assignments:
                ci_id = assignment.ci_id
                target_key = assignment.target_domain_name.lower().strip()

                if ci_id not in isolated_ci_ids:
                    _log.warning(
                        "CHK-3c-07: assignment ci_id %r not in isolated list — skipped", ci_id
                    )
                    continue

                source_domain_name = next(
                    (p.name for p in single_cci_proposals if p.cci_refs[0] == ci_id), ci_id
                )

                if target_key in proposal_name_idx:
                    idx = proposal_name_idx[target_key]
                    if len(proposals[idx].cci_refs) == 1:
                        _log.warning(
                            "CHK-3c-07: target domain %r is itself single-CCI — skipped", target_key
                        )
                        continue
                    existing = proposals[idx]
                    new_refs = list(dict.fromkeys(existing.cci_refs + [ci_id]))
                    proposals[idx] = DomainProposal(
                        name=existing.name,
                        description=existing.description,
                        classification_type=existing.classification_type,
                        cci_refs=new_refs,
                    )
                    result.absorptions.append(
                        {
                            "ci_id": ci_id,
                            "absorbed_from_domain_name": source_domain_name,
                            "absorbed_into_domain_name": existing.name,
                        }
                    )
                    absorbed_ci_ids.add(ci_id)
                else:
                    _log.warning(
                        "CHK-3c-07: target domain name %r not matched — ci_id %r left in place",
                        assignment.target_domain_name,
                        ci_id,
                    )

            # Remove single-CCI proposals whose ci_ids were successfully absorbed
            proposals = [
                p for p in proposals
                if not (len(p.cci_refs) == 1 and p.cci_refs[0] in absorbed_ci_ids)
            ]

            if result.absorptions:
                result.execution_warnings.append(
                    {
                        "type": "chk3c07_absorption_performed",
                        "count": len(result.absorptions),
                    }
                )

            # Safety re-check: CHK-3c-04 Non-Loss after absorption merge
            covered_after = {ref for p in proposals for ref in p.cci_refs}
            still_orphaned = eligible_ci_ids - covered_after
            if still_orphaned:
                _log.warning(
                    "CHK-3c-07 safety check: %d CCI(s) became orphaned after absorption merge — %s",
                    len(still_orphaned),
                    sorted(still_orphaned),
                )
                result.orphaned_ccis = sorted(set(result.orphaned_ccis) | still_orphaned)
                if result.status != "ok_with_warnings":
                    result.status = "ok_with_warnings"
        else:
            # CHK-3c-07 repair failed after retries — leave single-CCI proposals in place
            result.single_cci_absorption_issued = False
            result.execution_warnings.append(
                {
                    "type": "chk3c07_repair_failed",
                    "isolated_ci_ids": isolated_ci_ids,
                }
            )
            _log.warning(
                "CHK-3c-07: repair prompt failed after 2 attempts — "
                "%d single-CCI domain(s) left in place", len(single_cci_proposals)
            )

    # ADVC-3c-01 — Domain count soft-bounds advisory
    from math import ceil

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
