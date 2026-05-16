"""
Pydantic schemas for AI classification response validation.

Per spec §5.1: ClassificationResponseItemModel validates per-item AI response.
Applied at the AI response boundary — validation failure produces PartialSuccess.

signal_type is required when classification="Signal", null otherwise.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SignalType = Literal["Normative", "Intent", "Actor", "Concern", "Ambiguity", "Quality"]
ClassificationType = Literal["Signal", "Concern", "OutOfScope"]


class ClassificationResponseItem(BaseModel):
    """Validates a single item in the AI classification response."""

    model_config = ConfigDict(frozen=True)

    item_id: str = Field(min_length=1)
    classification: ClassificationType
    signal_type: SignalType | None = None
    confidence: float
    description: str = Field(min_length=1)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0]. Got: {v}")
        return v

    @model_validator(mode="after")
    def validate_signal_type_when_signal(self) -> ClassificationResponseItem:
        if self.classification == "Signal" and self.signal_type is None:
            raise ValueError(
                "signal_type must be provided when classification='Signal'."
            )
        return self


class ClassificationResponse(BaseModel):
    """Wraps the full list of classification response items."""

    model_config = ConfigDict(frozen=True)

    items: list[ClassificationResponseItem]


def parse_classification_response(
    raw: dict,
) -> tuple[list[ClassificationResponseItem], list[dict]]:
    """
    Parse and validate the raw AI JSON response for classification.

    Returns
    -------
    (valid_items, failures)
    valid_items : list of valid ClassificationResponseItem
    failures    : list of {item_id_or_index, error} for invalid items
    """
    failures: list[dict] = []
    valid_items: list[ClassificationResponseItem] = []

    raw_items = raw.get("items", [])
    if not isinstance(raw_items, list):
        return [], [{"item_id": "root", "error": "Response missing 'items' list"}]

    for i, item in enumerate(raw_items):
        try:
            valid_items.append(ClassificationResponseItem.model_validate(item))
        except Exception as exc:
            failures.append(
                {
                    "item_id": item.get("item_id", f"index_{i}") if isinstance(item, dict) else f"index_{i}",
                    "error": str(exc),
                }
            )

    return valid_items, failures
