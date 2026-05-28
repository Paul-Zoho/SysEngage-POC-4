"""
Pydantic response schema for the CHK-3c-04 repair prompt (Stage 3 conditional IM).

Per Domain Derivation Mechanism Spec v0.13 §5.2:
  Root wrapper: DomainRepairResponse with field "actions".
  Discriminated union on "action": "assign" | "new".

  AssignAction uses domain_name: str — NOT domain_id.
  The AI sees Domain names (not ids) in the repair prompt context.
  Stage 3 resolves domain_name to an existing proposal by case-insensitive match.

IMPORTANT: This AssignAction class is DISTINCT from the one in
domain_incremental_response_schema.py (which uses domain_id: str).
These two classes MUST NOT be shared or imported across schema files to
prevent silent field-mismatch bugs during merge.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class AssignAction(BaseModel):
    model_config = {"extra": "forbid"}

    action: Literal["assign"]
    domain_name: str
    new_cci_refs: list[str] = Field(min_length=1)


class NewDomainAction(BaseModel):
    model_config = {"extra": "forbid"}

    action: Literal["new"]
    name: str = Field(min_length=2, max_length=60)
    description: str = Field(min_length=10)
    classification_type: Optional[str] = None
    cci_refs: list[str] = Field(min_length=1)


DomainRepairAction = Annotated[
    Union[AssignAction, NewDomainAction],
    Field(discriminator="action"),
]


class DomainRepairResponse(BaseModel):
    model_config = {"extra": "forbid"}

    actions: list[DomainRepairAction]
