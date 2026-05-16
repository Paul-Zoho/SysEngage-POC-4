"""
Signal Pydantic schema — canonical ledger spec v2.12 §Element Type — Signal.

Canonical attributes (v2.12):
  signal_id, signal_type, row_target, description, source_refs,
  sourceatom_refs, confidence, derived_from_concern_id.

Non-canonical (implementation-internal, stripped at export): project_id.

signal_id format: SG### (SG001, SG002, ..., SG1000, ...)
derived_from_concern_id format: CN### when present — null at production time per spec.
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SIGNAL_ID_PATTERN = re.compile(r"^SG\d{3,}$")
CONCERN_ID_PATTERN = re.compile(r"^CN\d{3,}$")

SignalType = Literal["Normative", "Intent", "Actor", "Concern", "Ambiguity", "Quality"]
RowTarget = Literal["1", "2", "3", "4", "5", "6"]


class Signal(BaseModel):
    """
    Canonical Signal entity — canonical ledger spec v2.12.

    Produced by the Row-Lens Source Re-Analysis mechanism (Phase 3 Pass 3a).
    frozen=True enforces LPM preservation — Signal descriptions reference
    source content but never replace or rewrite it.
    """

    model_config = ConfigDict(frozen=True)

    signal_id: str
    signal_type: SignalType
    row_target: RowTarget
    description: str = Field(min_length=1)
    source_refs: list[str] = Field(min_length=1)
    sourceatom_refs: list[str] = Field(default_factory=list)
    confidence: float
    derived_from_concern_id: str | None = None
    project_id: str

    @field_validator("signal_id")
    @classmethod
    def validate_signal_id(cls, v: str) -> str:
        if not SIGNAL_ID_PATTERN.match(v):
            raise ValueError(
                f"signal_id must match ^SG\\d{{3,}}$ (canonical ledger spec v2.12). Got: {v!r}"
            )
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be in 0.0..1.0. Got: {v}")
        return v

    @field_validator("derived_from_concern_id")
    @classmethod
    def validate_derived_from_concern_id(cls, v: str | None) -> str | None:
        if v is not None and not CONCERN_ID_PATTERN.match(v):
            raise ValueError(
                f"derived_from_concern_id must match ^CN\\d{{3,}}$ when present. Got: {v!r}"
            )
        return v

    @field_validator("source_refs")
    @classmethod
    def validate_source_refs_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("source_refs must have at least one entry.")
        return v
