"""
SourceAtom Pydantic schema — canonical ledger spec v2.9 §Element Type — SourceAtom.

Per Row 4 Applied §7 and Implementation Spec §5.1.

Finding F18: atom_id format uses canonical ^SA\\d{3,}$.
Finding F20: field named atom_text per canonical spec (not content per impl spec).
Finding F21 (agent): position field is an implementation extension not in canonical
spec v2.9. Required by Implementation Spec §4.4.3 for ordinal ordering of atoms
within their parent Source. Stored at DB level; excluded from canonical ledger
JSON export if needed. Resolution: add as implementation field with clear comment.
"""

import re
from pydantic import BaseModel, ConfigDict, field_validator

ATOM_ID_PATTERN = re.compile(r"^SA\d{3,}$")
SOURCE_ID_PATTERN = re.compile(r"^S\d{3,}$")
SEGMENT_ID_PATTERN = re.compile(r"^SEG\d{3,}$")


class SourceAtom(BaseModel):
    """
    Canonical SourceAtom entity.

    Represents an optional, fine-grained verbatim fragment derived from a Source.
    Used for sub-sentence (sentence, clause, line-item) provenance anchors.
    """

    model_config = ConfigDict(frozen=True)

    atom_id: str
    atom_text: str
    source_ref: str
    segment_ref: str | None = None
    parent_atom_ref: str | None = None
    confidence: float = 1.0
    position: int
    project_id: str

    @field_validator("atom_id")
    @classmethod
    def validate_atom_id(cls, v: str) -> str:
        if not ATOM_ID_PATTERN.match(v):
            raise ValueError(
                f"atom_id must match ^SA\\d{{3,}}$ (canonical ledger spec v2.9). Got: {v!r}"
            )
        return v

    @field_validator("atom_text")
    @classmethod
    def validate_atom_text_non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("atom_text must be non-empty.")
        return v

    @field_validator("source_ref")
    @classmethod
    def validate_source_ref_format(cls, v: str) -> str:
        if not SOURCE_ID_PATTERN.match(v):
            raise ValueError(f"source_ref must match ^S\\d{{3,}}$. Got: {v!r}")
        return v

    @field_validator("position")
    @classmethod
    def validate_position_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"position must be non-negative. Got: {v}")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be in 0.0..1.0. Got: {v}")
        return v
