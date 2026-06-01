"""
Pydantic response schema — primary Requirement Derivation (FirstRun / FullRerun).

Per Requirement Derivation Mechanism Spec v0.1 §5.2.

IMPORTANT: This is a DISTINCT class from IncrementalRequirementProposal and
RepairRequirementProposal. Do NOT import or alias from either of those modules.
Sharing schema classes risks silent field-mismatch bugs.

The AI does NOT return requirement_id, row_target, domain_refs, or answer_refs.
Those are produced deterministically in Stage 4 (MD-2).
The requirement_type enum is enforced at the parse boundary (MD-5).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class RequirementProposal(BaseModel):
    """Single Requirement proposal returned by the primary derivation AI call."""

    statement: str
    requirement_type: Literal[
        "Functional", "Constraint", "Performance", "Suitability", "Non-Functional"
    ]
    cci_refs: list[str]
    rationale: Optional[str] = None
    fit_criteria: Optional[str] = None
    verification_method: Optional[
        Literal["Test", "Analysis", "Inspection", "Demonstration"]
    ] = None
    priority: Optional[Literal["High", "Medium", "Low"]] = None
    confidence: float

    @field_validator("statement")
    @classmethod
    def statement_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("statement must not be empty")
        return v

    @field_validator("cci_refs")
    @classmethod
    def cci_refs_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("cci_refs must contain at least one entry")
        return v

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be in [0.0, 1.0]")
        return v


RequirementDerivationResponse = list[RequirementProposal]
