"""
CHK-3c-08 split repair response schema.

Per Domain Derivation Mechanism Spec v0.22 §5.2:
  SplitDomainProposal: new proposal produced from an over-concentrated domain's CCI set.
  SplitRepairResponse: wraps a list of SplitDomainProposal (min 2 items required).

IMPORTANT — DISTINCT CLASS: do NOT import or share these classes across other schema
files.  SplitDomainProposal produces new domain proposals with cci_refs lists; it does
NOT reference existing domains by name or id (unlike CHK-3c-04 and CHK-3c-07 schemas).

Four schemas — all distinct:
  domain_repair_response_schema.py:           assign/new actions with domain_name  → CHK-3c-04
  domain_incremental_response_schema.py:      assign/new actions with domain_id    → IncrementalRerun
  domain_single_cci_repair_response_schema.py: assign-only with domain_name        → CHK-3c-07
  domain_split_repair_response_schema.py:     new proposals with cci_refs lists    → CHK-3c-08 (this file)
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SplitDomainProposal(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    description: str = Field(min_length=10)
    cci_refs: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)

    model_config = {"extra": "forbid"}


class SplitRepairResponse(BaseModel):
    proposals: list[SplitDomainProposal] = Field(min_length=2)

    model_config = {"extra": "forbid"}
