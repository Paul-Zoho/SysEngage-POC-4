"""
Pydantic response schema — CHK-3d-05 Non-Loss repair.

Per Requirement Derivation Mechanism Spec v0.1 §5.2.

IMPORTANT: RepairRequirementProposal is a DISTINCT class from RequirementProposal
and IncrementalRequirementProposal. Do NOT import or alias from either of those
modules. Repair proposals cover orphaned ci_ids and are scoped to a single owning
Domain. Every proposal must cover at least one orphaned CCI.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class RepairRequirementProposal(BaseModel):
    """
    Single covering Requirement proposal produced by the CHK-3d-05 repair AI call.

    Field shape mirrors RequirementProposal but is a completely separate class.
    Each proposal covers ≥1 orphaned CCI and is scoped to one owning Domain.
    """

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


RequirementRepairResponse = list[RepairRequirementProposal]
