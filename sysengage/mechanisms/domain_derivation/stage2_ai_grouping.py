"""
Stage 2 — AI Grouping Act (IM).

Per Domain Derivation Mechanism Spec v0.13 §4.2:
  FirstRun/FullRerun path: domain_grouping_prompt → DomainGroupingResponse.
    One retry on parse failure; second failure → execution_status = "Failed".
  IncrementalRerun path: domain_incremental_prompt → DomainIncrementalResponse.
    One retry on parse failure; persistent failure → fall back to FullRerun.
    Fallback produces advisory "incremental_fallback_to_fullrerun" in
    execution_warnings and triggers CompletedWithWarnings.

AI model fingerprints recorded per IM call.
LPM constraint enforced at prompt level (AI instructed not to copy CCI text verbatim).
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
from mechanisms.domain_derivation.prompts.domain_grouping_prompt import (
    build_domain_grouping_prompt,
)
from mechanisms.domain_derivation.prompts.domain_incremental_prompt import (
    build_domain_incremental_prompt,
)
from mechanisms.domain_derivation.schemas.domain_grouping_response_schema import (
    DomainGroupingResponse,
    DomainProposal,
)
from mechanisms.domain_derivation.schemas.domain_incremental_response_schema import (
    DomainIncrementalResponse,
)
from mechanisms.domain_derivation.stage1_preflight import EligibleCCI, Stage1Result

_log = logging.getLogger(__name__)


@dataclass
class Stage2Result:
    proposals: list[DomainProposal] = field(default_factory=list)
    assign_membership_inserts: list[tuple[str, str]] = field(default_factory=list)
    ai_model_fingerprints: list[dict[str, Any]] = field(default_factory=list)
    execution_warnings: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    failure_reason: str | None = None
    effective_scenario: str = "FirstRun"


def _call_ai(prompt: str) -> tuple[Any, dict[str, Any]]:
    """Issue a single AI call and return (message, fingerprint_dict)."""
    client = get_ai_client()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=4096,
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


def _parse_grouping_response(text_: str) -> DomainGroupingResponse | None:
    """Parse AI text as DomainGroupingResponse; return None on failure."""
    try:
        data = json.loads(_strip_code_fence(text_))
        return DomainGroupingResponse.model_validate(data)
    except Exception:
        return None


def _parse_incremental_response(text_: str) -> DomainIncrementalResponse | None:
    """Parse AI text as DomainIncrementalResponse; return None on failure."""
    try:
        data = json.loads(_strip_code_fence(text_))
        return DomainIncrementalResponse.model_validate(data)
    except Exception:
        return None


def _build_cci_dicts(eligible_ccis: list[EligibleCCI]) -> list[dict[str, Any]]:
    return [
        {
            "ci_id": c.ci_id,
            "column": c.column,
            "classification_type": c.classification_type,
            "description": c.description,
        }
        for c in eligible_ccis
    ]


def _run_grouping_path(
    stage1: Stage1Result,
    scenario: str,
) -> Stage2Result:
    """FirstRun / FullRerun — single grouping prompt, one retry."""
    result = Stage2Result(effective_scenario=scenario)
    cci_dicts = _build_cci_dicts(stage1.eligible_ccis)
    row_num = _extract_row_from_ccis(stage1.eligible_ccis)
    prompt = build_domain_grouping_prompt(
        row_ref=row_num,
        cci_set=cci_dicts,
        cci_count=len(stage1.eligible_ccis),
    )

    for attempt in range(2):
        try:
            msg, fp = _call_ai(prompt)
        except Exception as exc:
            result.status = "failed"
            result.failure_reason = f"AI API error on attempt {attempt + 1}: {exc}"
            return result

        fp["stage"] = "stage2_primary" if attempt == 0 else "stage2_retry"
        result.ai_model_fingerprints.append(fp)

        parsed = _parse_grouping_response(msg.content[0].text)
        if parsed is not None:
            result.proposals = list(parsed.proposals)
            return result

        if attempt == 0:
            _log.warning("Stage 2 grouping parse failure — retrying once")

    result.status = "failed"
    result.failure_reason = "AI grouping response parse failure after retry"
    return result


def _run_incremental_path(
    stage1: Stage1Result,
    session: Session,
    row_ref: int,
    project_id: str,
) -> Stage2Result:
    """
    IncrementalRerun — incremental prompt, one retry, then FullRerun fallback.
    Returns Stage2Result. On FullRerun fallback, effective_scenario is updated.
    """
    result = Stage2Result(effective_scenario="IncrementalRerun")

    # Query existing active domains for this row/project
    existing_domain_rows = session.execute(
        text(
            "SELECT d.domain_id, d.name, d.description, "
            "       jsonb_array_length(d.cell_content_item_refs) AS cci_ref_count "
            "FROM domain d "
            "WHERE d.project_id = :pid "
            "  AND d.row_target = :row "
            "  AND d.retired_at IS NULL"
        ),
        {"pid": project_id, "row": str(row_ref)},
    ).fetchall()
    existing_domains = [
        {
            "domain_id": r[0],
            "name": r[1],
            "description": r[2],
            "cci_ref_count": r[3],
        }
        for r in existing_domain_rows
    ]
    existing_domain_ids = {d["domain_id"] for d in existing_domains}

    # Determine new CCIs (not yet covered by any active domain's cell_content_item_refs)
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
    committed_ci_ids = {r[0] for r in committed_rows}
    new_ccis = [c for c in stage1.eligible_ccis if c.ci_id not in committed_ci_ids]
    new_cci_dicts = _build_cci_dicts(new_ccis)

    prompt = build_domain_incremental_prompt(
        row_ref=row_ref,
        existing_domains=existing_domains,
        new_ccis=new_cci_dicts,
        new_cci_count=len(new_ccis),
    )

    parsed_inc: DomainIncrementalResponse | None = None
    for attempt in range(2):
        try:
            msg, fp = _call_ai(prompt)
        except Exception as exc:
            _log.warning(
                "IncrementalRerun AI error attempt %d: %s — falling back to FullRerun",
                attempt + 1,
                exc,
            )
            break

        fp["stage"] = "stage2_incremental" if attempt == 0 else "stage2_incremental_retry"
        result.ai_model_fingerprints.append(fp)
        parsed_inc = _parse_incremental_response(msg.content[0].text)
        if parsed_inc is not None:
            break
        if attempt == 0:
            _log.warning("IncrementalRerun parse failure — retrying once")

    if parsed_inc is None:
        # Fall back to FullRerun
        result.execution_warnings.append({"type": "incremental_fallback_to_fullrerun"})
        _log.warning("IncrementalRerun parse failed — falling back to FullRerun")
        fallback = _run_grouping_path(stage1, "FullRerun")
        fallback.ai_model_fingerprints = (
            result.ai_model_fingerprints + fallback.ai_model_fingerprints
        )
        fallback.execution_warnings = result.execution_warnings + fallback.execution_warnings
        return fallback

    # Process incremental actions
    assign_inserts: list[tuple[str, str]] = []
    new_proposals: list[DomainProposal] = []

    for action in parsed_inc.actions:
        if action.action == "assign":
            if action.domain_id in existing_domain_ids:
                for ci_id in action.new_cci_refs:
                    assign_inserts.append((action.domain_id, ci_id))
            else:
                # Invalid domain_id — convert to new action
                result.execution_warnings.append(
                    {
                        "type": "incremental_assign_invalid_domain_id",
                        "domain_id": action.domain_id,
                    }
                )
                new_proposals.append(
                    DomainProposal(
                        name=action.domain_id,
                        description=(
                            "IncrementalRerun assign action referenced non-existent "
                            "domain_id — review recommended"
                        ),
                        classification_type=None,
                        cci_refs=list(action.new_cci_refs),
                    )
                )
        else:
            new_proposals.append(
                DomainProposal(
                    name=action.name,
                    description=action.description,
                    classification_type=action.classification_type,
                    cci_refs=list(action.cci_refs),
                )
            )

    result.proposals = new_proposals
    result.assign_membership_inserts = assign_inserts
    return result


def _extract_row_from_ccis(eligible_ccis: list[EligibleCCI]) -> int:
    """Extract row number from first CCI id pattern CCI-ROW{n}-C-..."""
    if not eligible_ccis:
        return 1
    try:
        parts = eligible_ccis[0].ci_id.split("-")
        return int(parts[1].lstrip("ROW"))
    except Exception:
        return 1


def run_stage2(
    *,
    stage1: Stage1Result,
    session: Session,
    project_id: str,
    row_ref: int,
) -> Stage2Result:
    """
    Run Stage 2 AI grouping. Routes based on stage1.scenario.

    Returns Stage2Result. Check result.status before proceeding:
      "ok"     — proposals available; proceed to Stage 3
      "failed" — hard stop; write failure pass
    """
    if stage1.scenario in ("FirstRun", "FullRerun"):
        return _run_grouping_path(stage1, stage1.scenario)
    else:
        return _run_incremental_path(stage1, session, row_ref, project_id)
