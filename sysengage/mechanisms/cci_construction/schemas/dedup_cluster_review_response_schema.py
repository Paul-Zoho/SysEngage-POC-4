"""
Pydantic schema for Stage 4b AI cluster deduplication review response.

Per CCI Construction Mechanism Spec v0.7 §5.3 and Row 3 Mechanism Spec v0.6 §4:
  The AI returns clusters of semantically equivalent items (Duplicate verdict)
  and ambiguous pairs/groups where equivalence cannot be determined.
  Items not mentioned are implicitly Distinct and survive unchanged.

  clusters  — list of ClusterEntry, each covering 2+ member_refs
  ambiguous — list of AmbiguousEntry, each covering 2+ member_refs
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class ClusterEntry(BaseModel):
    member_refs: list[str] = Field(min_length=2)
    verdict: Literal["Duplicate"]
    representative_description: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class AmbiguousEntry(BaseModel):
    member_refs: list[str] = Field(min_length=2)
    rationale: str = Field(min_length=1)


class ClusterReviewResponse(BaseModel):
    clusters: list[ClusterEntry]
    ambiguous: list[AmbiguousEntry]


def parse_cluster_review_response(
    content: dict,
) -> tuple[ClusterReviewResponse | None, list[dict]]:
    """
    Parse the AI cluster review response dict against ClusterReviewResponse.

    Returns
    -------
    (response, failures)
      response : ClusterReviewResponse if validation passed, else None
      failures : list of {field, error} dicts for validation failures
    """
    try:
        response = ClusterReviewResponse.model_validate(content)
        return response, []
    except ValidationError as exc:
        return None, [{"field": "response", "error": str(exc)}]
