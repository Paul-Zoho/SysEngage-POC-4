"""
Pydantic schema for Stage 3a AI derivation response.

Per CCI Construction Mechanism Spec v0.2 §5.3:
  The AI response must include 'column' as a required field — the AI assigns
  column placement as part of the derivation act (no pre-partitioning by column).
  Items failing validation are recorded as candidates_rejected; valid items
  proceed to Stage 3b entity production.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError


class CCIResponseItem(BaseModel):
    column: Literal["What", "How", "Where", "Who", "When", "Why"]
    classification_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    signal_refs: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    trigger_condition: Optional[str] = None
    justification: Optional[str] = None


class CCIConstructionResponse(BaseModel):
    items: list[CCIResponseItem]


def parse_cci_response(
    content: dict,
) -> tuple[list[CCIResponseItem], list[dict]]:
    """
    Parse the AI response dict against CCIConstructionResponse.

    Returns
    -------
    (valid_items, failures)
      valid_items : list of CCIResponseItem that passed Pydantic validation
      failures    : list of {index, error} dicts for items that failed
    """
    valid_items: list[CCIResponseItem] = []
    failures: list[dict] = []

    try:
        response = CCIConstructionResponse.model_validate(content)
    except ValidationError as exc:
        failures.append({"index": "response", "error": str(exc)})
        return valid_items, failures

    for idx, raw_item in enumerate(response.items):
        valid_items.append(raw_item)

    return valid_items, failures
