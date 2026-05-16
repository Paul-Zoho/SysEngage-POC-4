"""
Pydantic schema for Stage 4b AI semantic deduplication review response.

Per CCI Construction Mechanism Spec v0.2 §5.3:
  The AI returns a list of verdicts — one per candidate pair presented.
  verdict ∈ {Duplicate, Distinct, Ambiguous}.
  merged_description is populated by the AI when verdict="Duplicate" and the
  lower-confidence item contains nuance worth preserving; null otherwise.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError


class DedupVerdict(BaseModel):
    item_a_ref: str
    item_b_ref: str
    verdict: Literal["Duplicate", "Distinct", "Ambiguous"]
    rationale: str = Field(min_length=1)
    merged_description: Optional[str] = None


class DedupReviewResponse(BaseModel):
    verdicts: list[DedupVerdict]


def parse_dedup_response(
    content: dict,
) -> tuple[list[DedupVerdict], list[dict]]:
    """
    Parse the AI dedup response dict against DedupReviewResponse.

    Returns
    -------
    (verdicts, failures)
      verdicts : list of DedupVerdict that passed validation
      failures : list of {index, error} dicts for items that failed
    """
    verdicts: list[DedupVerdict] = []
    failures: list[dict] = []

    try:
        response = DedupReviewResponse.model_validate(content)
        verdicts = response.verdicts
    except ValidationError as exc:
        failures.append({"index": "response", "error": str(exc)})

    return verdicts, failures
