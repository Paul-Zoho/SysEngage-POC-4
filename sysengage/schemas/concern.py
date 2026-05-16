"""
Concern Pydantic schema — canonical ledger spec v2.12 §Element Type — Concern.

Canonical attributes (v2.12):
  concern_id, source_refs, description, state, produced_in_row,
  practitioner_id, dispositioned_with_outcome, disposition_rationale, confidence.

Non-canonical (implementation-internal): project_id.

concern_id format: CN### (CN001, CN002, ...) — no hyphen per confirmed decision.
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CONCERN_ID_PATTERN = re.compile(r"^CN\d{3,}$")

ConcernState = Literal["Open", "Resolved", "Dispositioned"]
DispositionOutcome = Literal["NotApplicable", "Indeterminate"]
RowTarget = Literal["1", "2", "3", "4", "5", "6"]


class Concern(BaseModel):
    """
    Canonical Concern entity — canonical ledger spec v2.12.

    Produced by the Row-Lens Source Re-Analysis mechanism (Phase 3 Pass 3a).
    State = Open at production time; transitions via Phase 10 Concern Resolution.
    frozen=True enforces LPM — concern descriptions reference source content
    verbatim; source_text is never rewritten.
    """

    model_config = ConfigDict(frozen=True)

    concern_id: str
    source_refs: list[str] = Field(min_length=1)
    description: str = Field(min_length=1)
    state: ConcernState = "Open"
    produced_in_row: RowTarget
    practitioner_id: str = Field(min_length=1)
    dispositioned_with_outcome: DispositionOutcome | None = None
    disposition_rationale: str | None = None
    confidence: float
    project_id: str

    @field_validator("concern_id")
    @classmethod
    def validate_concern_id(cls, v: str) -> str:
        if not CONCERN_ID_PATTERN.match(v):
            raise ValueError(
                f"concern_id must match ^CN\\d{{3,}}$ (canonical ledger spec v2.12). Got: {v!r}"
            )
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be in 0.0..1.0. Got: {v}")
        return v

    @field_validator("source_refs")
    @classmethod
    def validate_source_refs_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("source_refs must have at least one entry.")
        return v
