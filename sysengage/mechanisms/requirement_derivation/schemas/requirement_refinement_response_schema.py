"""
Response schema for Path R (seed-elaboration) AI derivation.

Per Requirement Derivation Spec v0.13 §4.2 (Path R):
  Each returned item elaborates exactly one row n-1 seed requirement.
  - refines_refs must contain exactly one seed_id (the parent).
  - cci_refs may be empty (Matching service populates later; CHK-3d-02 relaxed).
  - statement, requirement_type, confidence are required.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class RefinementProposal(BaseModel):
    """A single row n requirement proposal that elaborates a row n-1 seed."""

    statement: str
    requirement_type: Literal["Functional", "Constraint", "Structural"]
    refines_refs: list[str] = Field(
        description="Exactly one seed_id (the row n-1 requirement being elaborated)."
    )
    cci_refs: list[str] = Field(
        default_factory=list,
        description="Row n CCI ids this proposal addresses. May be empty.",
    )
    rationale: str | None = None
    fit_criteria: str | None = None
    verification_method: str | None = None
    priority: Optional[Literal["High", "Medium", "Low"]] = None
    confidence: float = 1.0
