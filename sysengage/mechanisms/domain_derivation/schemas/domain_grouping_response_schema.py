"""
Pydantic response schema for the domain grouping AI call (FirstRun / FullRerun).

Per Domain Derivation Mechanism Spec v0.13 §5.2:
  Root wrapper: DomainGroupingResponse with field "proposals"
  DomainProposal: name (2–60 chars), description (min 10 chars),
    classification_type (optional), cci_refs (non-empty list).

IMPORTANT: Do NOT import AssignAction or NewDomainAction from this file into
domain_repair_response_schema.py or domain_incremental_response_schema.py.
Each schema file defines its own action classes independently.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class DomainProposal(BaseModel):
    model_config = {"extra": "forbid"}

    name: str = Field(min_length=2, max_length=60)
    description: str = Field(min_length=10)
    classification_type: Optional[str] = None
    cci_refs: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_fields(self) -> "DomainProposal":
        if not self.name.strip():
            raise ValueError("name must not be blank")
        if not self.description.strip():
            raise ValueError("description must not be blank")
        return self


class DomainGroupingResponse(BaseModel):
    model_config = {"extra": "forbid"}

    proposals: list[DomainProposal]
