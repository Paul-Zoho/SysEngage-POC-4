"""
schemas/requirement_dd_extraction_response_schema.py

Pydantic schema for the §4.4.3a entity extraction AI response (v0.11).

The AI returns a JSON array of EntityExtractionItem — one entry per
requirement, keyed by the idx sent in the prompt.

v0.11 adds StateQualifier and state_qualifiers to EntityExtractionItem:
lifecycle states extracted alongside the bare entity term, for recording
as attribute values on the Data Dictionary entry (DD §4.4 value-record).
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class StateQualifier(BaseModel):
    entity: str
    state: str


class EntityExtractionItem(BaseModel):
    idx: int
    terms: list[str] = []
    state_qualifiers: list[StateQualifier] = []

    @field_validator("terms")
    @classmethod
    def strip_empty(cls, v: list[str]) -> list[str]:
        return [t.strip() for t in v if t and t.strip()]
