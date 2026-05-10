"""
Segment Pydantic schema — canonical ledger spec v2.9 §Element Type — Segment.

Per Row 4 Applied §7 and Implementation Spec §5.1.

Finding F18: segment_id format uses canonical ^SEG\\d{3,}$ (not SEG### from
the identifier table in replit.md, which happens to match — but confirmed here
against canonical spec directly).
"""

import re
from pydantic import BaseModel, ConfigDict, field_validator

SEGMENT_ID_PATTERN = re.compile(r"^SEG\d{3,}$")


class Segment(BaseModel):
    """
    Canonical Segment entity.

    Represents a coarse-grained structural grouping of Source excerpts.
    Optional — produced only when input has structural markers (section
    headings, document boundaries) per Pass 0A Segment Construction.
    """

    model_config = ConfigDict(frozen=True)

    segment_id: str
    title: str
    description: str | None = None
    source_refs: list[str] = []
    parent_segment_ref: str | None = None
    confidence: float = 1.0
    project_id: str

    @field_validator("segment_id")
    @classmethod
    def validate_segment_id(cls, v: str) -> str:
        if not SEGMENT_ID_PATTERN.match(v):
            raise ValueError(
                f"segment_id must match ^SEG\\d{{3,}}$ (canonical ledger spec v2.9). Got: {v!r}"
            )
        return v

    @field_validator("title")
    @classmethod
    def validate_title_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Segment title must be non-empty per canonical spec.")
        return v

    @field_validator("description")
    @classmethod
    def validate_description_if_present(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("description, if present, must not be empty.")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be in 0.0..1.0. Got: {v}")
        return v
