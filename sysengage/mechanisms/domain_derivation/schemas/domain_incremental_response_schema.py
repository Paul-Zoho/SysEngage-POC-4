"""
Pydantic response schema for the IncrementalRerun AI call.

Per Domain Derivation Mechanism Spec v0.13 §5.2:
  Root wrapper: DomainIncrementalResponse with field "actions".
  Discriminated union on "action": "assign" | "new".

  AssignAction uses domain_id: str (^D\\d{3}$) — NOT domain_name.
  This is DISTINCT from the repair schema's AssignAction (which uses domain_name).
  These two classes MUST NOT be shared or imported across schema files.

Post-parse validation (applied in Stage 3, not here):
  For assign actions, domain_id must reference an existing active Domain.
  Invalid domain_id → converted to new action with advisory warning.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class AssignAction(BaseModel):
    model_config = {"extra": "forbid"}

    action: Literal["assign"]
    domain_id: str = Field(pattern=r"^D\d{3}$")
    new_cci_refs: list[str] = Field(min_length=1)


class NewDomainAction(BaseModel):
    model_config = {"extra": "forbid"}

    action: Literal["new"]
    name: str = Field(min_length=2, max_length=60)
    description: str = Field(min_length=10)
    classification_type: Optional[str] = None
    cci_refs: list[str] = Field(min_length=1)


DomainIncrementalAction = Annotated[
    Union[AssignAction, NewDomainAction],
    Field(discriminator="action"),
]


class DomainIncrementalResponse(BaseModel):
    model_config = {"extra": "forbid"}

    actions: list[DomainIncrementalAction]
