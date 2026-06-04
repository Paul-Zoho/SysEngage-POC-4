"""
Pydantic response schema — IncrementalRerun Requirement Derivation.

Per Requirement Derivation Mechanism Spec v0.6 §5.2 / ledger v2.13.

IMPORTANT: IncrementalRequirementProposal is a DISTINCT class from
RequirementProposal and RepairRequirementProposal. Do NOT import or alias
from either of those modules. Incremental proposals cover only new_domain_ccis
for a Domain whose Domain-id set is unchanged (MD-3).

requirement_type enforced to v2.13 three-value triad (F89).
verification_method gains Measurement (v2.13).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class IncrementalRequirementProposal(BaseModel):
    """
    Single Requirement proposal returned by the IncrementalRerun AI call.

    Field shape mirrors RequirementProposal but is a completely separate class.
    cci_refs entries referencing already-covered CCIs are stripped in Stage 3
    CHK-3d-03 with advisory incremental_ref_outside_new_set.
    """

    statement: str
    requirement_type: Literal["Functional", "Constraint", "Structural"]
    cci_refs: list[str]
    rationale: Optional[str] = None
    fit_criteria: Optional[str] = None
    verification_method: Optional[
        Literal["Test", "Analysis", "Inspection", "Demonstration", "Measurement"]
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


RequirementIncrementalResponse = list[IncrementalRequirementProposal]
