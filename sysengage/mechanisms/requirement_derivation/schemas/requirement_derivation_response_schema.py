"""
Pydantic response schema — primary Requirement Derivation (FirstRun / FullRerun).

Per Requirement Derivation Mechanism Spec v0.33 §5.2 / ledger v2.13.

IMPORTANT: This is a DISTINCT class from IncrementalRequirementProposal and
RepairRequirementProposal. Do NOT import or alias from either of those modules.
Sharing schema classes risks silent field-mismatch bugs.

F105 (v0.33): class_model Optional[dict] — structured class model for Structural
  requirements.  AI proposes this for Structural proposals at rows 2-5.
  entity_ref within the class_model is NOT AI-proposed; it is set in Stage 4.

F107 (v0.33): object_refs Optional[list[str]] — candidate object-reference paths
  for Functional/Constraint proposals. Materialised in Stage 4 §4.4.3a Step 4.

  statement: Optional[str] = None — may be None when class_model is present for
  a Structural proposal. Stage 4 projects a prose statement from class_model.

  Cross-field invariants:
  - class_model is not None OR (statement is not None and statement.strip())
  - class_model may only be present for Structural requirements.
  - object_refs may only be present for Functional/Constraint requirements.

The AI does NOT return requirement_id, row_target, domain_refs, answer_refs,
or refines_refs. Those are produced deterministically in Stage 4 (MD-2; F82).
requirement_type enforced to the v2.13 three-value triad (F89).
verification_method gains Measurement (v2.13).
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


class RequirementProposal(BaseModel):
    """Single Requirement proposal returned by the primary derivation AI call."""

    statement: Optional[str] = None
    requirement_type: Literal["Functional", "Constraint", "Structural"]
    cci_refs: list[str]
    rationale: Optional[str] = None
    fit_criteria: Optional[str] = None
    verification_method: Optional[
        Literal["Test", "Analysis", "Inspection", "Demonstration", "Measurement"]
    ] = None
    priority: Optional[Literal["High", "Medium", "Low"]] = None
    confidence: float

    class_model: Optional[dict[str, Any]] = None
    object_refs: Optional[list[str]] = None

    @model_validator(mode="after")
    def cross_field_invariants(self) -> "RequirementProposal":
        has_cm = self.class_model is not None
        has_stmt = self.statement is not None and bool(self.statement.strip())

        if not has_cm and not has_stmt:
            raise ValueError(
                "RequirementProposal must have either class_model or a non-empty statement"
            )

        if has_cm and self.requirement_type != "Structural":
            raise ValueError(
                f"class_model may only be present for Structural requirements, "
                f"got requirement_type={self.requirement_type!r}"
            )

        if self.object_refs and self.requirement_type == "Structural":
            raise ValueError(
                "object_refs may only be present for Functional/Constraint requirements"
            )

        return self

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
