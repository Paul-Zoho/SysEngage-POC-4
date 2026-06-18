"""
ClassModel Pydantic schema — F105 (v0.33).

AI-proposed structured class model for Structural requirements.
entity_ref is NOT AI-proposed — it is set in Stage 4 §4.4.3a from the
DD canonical dd_id after name resolution.

Per Requirement Derivation Mechanism Spec v0.33 §5.2 and §5.4.

Tier guidance:
  2 — conceptual:   entity + semantic_type on each attr + associations
  3 — logical:      + logical_type + domain (value-set) + business keys
  4 — physical:     + physical_type + null_allowed + PK/FK constraints
  5 — deployment:   + precision + check_expression + storage_notes
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class AttributeDef(BaseModel):
    """Single attribute/field within a ClassModel."""

    name: str
    origin: Literal["refines", "realises", "introduced"]

    semantic_type: Optional[str] = None
    logical_type: Optional[str] = None
    domain: Optional[list[str]] = None

    key: Optional[Literal["PK", "FK", "AK", "BK"]] = None
    target_ref: Optional[str] = None

    null_allowed: Optional[bool] = None
    physical_type: Optional[str] = None
    precision: Optional[str] = None
    check_expression: Optional[str] = None
    storage_notes: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("attribute name must not be empty")
        return v


class RelationshipDef(BaseModel):
    """Association/relationship from this entity to another."""

    target: str
    target_ref: Optional[str] = None

    cardinality: Optional[str] = None
    label: Optional[str] = None

    @field_validator("target")
    @classmethod
    def target_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("relationship target must not be empty")
        return v


class ClassModel(BaseModel):
    """
    Structured class model for a Structural requirement (F105).

    AI proposes: entity, tier, refinement_kind, attributes, relationships.
    entity_ref is NOT AI-proposed; it is set by Stage 4 §4.4.3a after DD
    resolution.
    """

    entity: str
    entity_ref: Optional[str] = None

    tier: int
    refinement_kind: Literal[
        "identity",
        "decompose",
        "realise_relationship",
        "introduce",
        "merge",
    ]

    attributes: list[AttributeDef] = []
    relationships: list[RelationshipDef] = []

    @field_validator("entity")
    @classmethod
    def entity_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("entity name must not be empty")
        return v

    @field_validator("tier")
    @classmethod
    def tier_in_range(cls, v: int) -> int:
        if v not in {2, 3, 4, 5}:
            raise ValueError(f"tier must be 2–5, got {v}")
        return v
