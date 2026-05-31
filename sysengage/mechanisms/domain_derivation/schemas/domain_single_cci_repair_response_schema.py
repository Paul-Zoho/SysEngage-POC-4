"""
Pydantic response schema for the CHK-3c-07 single-CCI domain absorption repair prompt.

Per Domain Derivation Mechanism Spec v0.18 §5.2:
  Root wrapper: SingleCCIRepairResponse with field "assignments".
  Each assignment: {ci_id, target_domain_name, rationale}.
  Only assign actions — no new Domain creation.

IMPORTANT — DISTINCT CLASS:
  SingleCCIAssignAction uses target_domain_name: str (references a non-single-CCI
  proposal by name). This is DISTINCT from:
    - domain_repair_response_schema.py  AssignAction: domain_name: str  (CHK-3c-04)
    - domain_incremental_response_schema.py AssignAction: domain_id: str (IncrementalRerun)
  These classes MUST NOT be imported or shared across schema files. Sharing them
  causes silent field-mismatch bugs during merge operations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SingleCCIAssignAction(BaseModel):
    model_config = {"extra": "forbid"}

    ci_id: str
    target_domain_name: str
    rationale: str


class SingleCCIRepairResponse(BaseModel):
    model_config = {"extra": "forbid"}

    assignments: list[SingleCCIAssignAction] = Field(default_factory=list)
