"""
Pydantic response schema — CHK-3d-05 Non-Loss repair and CHK-3d-09 decompose.

Per Requirement Derivation Mechanism Spec v0.28 §5.2 / ledger v2.13.

IMPORTANT: RepairRequirementProposal is a DISTINCT class from RequirementProposal
and IncrementalRequirementProposal. Do NOT import or alias from either of those
modules. Repair proposals cover orphaned ci_ids and are scoped to a single owning
Domain. Every proposal must cover at least one orphaned CCI.

requirement_type enforced to v2.13 three-value triad (F89).
verification_method gains Measurement (v2.13).

F106 (v0.28) relaxations for the CHK-3d-09 decompose path:
  - cci_refs drops minItems=1 / cci_refs_not_empty: a decompose child inherits
    the parent compound's cci_refs in the executor and must not fail parse for
    an empty value.  The CHK-3d-05 orphan-repair path's coverage is enforced by
    its post-merge orphan re-check, not by a schema validator.
  - confidence is Optional/defaulted (0.85): a null from the AI must not fail
    the parse.  The executor normalises None → 0.85 before building TaggedProposal.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class RepairRequirementProposal(BaseModel):
    """
    Single covering Requirement proposal produced by the CHK-3d-05 repair AI call
    or the CHK-3d-09 conjoined-predicate decompose call.

    Field shape mirrors RequirementProposal but is a completely separate class.
    Each CHK-3d-05 proposal covers ≥1 orphaned CCI and is scoped to one owning
    Domain.  CHK-3d-09 decompose children inherit the parent compound's cci_refs
    in the executor (F106) and are not required to carry their own at parse time.
    """

    statement: str
    requirement_type: Literal["Functional", "Constraint", "Structural"]
    cci_refs: list[str] = []
    rationale: Optional[str] = None
    fit_criteria: Optional[str] = None
    verification_method: Optional[
        Literal["Test", "Analysis", "Inspection", "Demonstration", "Measurement"]
    ] = None
    priority: Optional[Literal["High", "Medium", "Low"]] = None
    confidence: Optional[float] = 0.85

    @field_validator("statement")
    @classmethod
    def statement_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("statement must not be empty")
        return v

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be in [0.0, 1.0]")
        return v


RequirementRepairResponse = list[RepairRequirementProposal]
