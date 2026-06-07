"""
schemas/requirement_dd_extraction_response_schema.py

Pydantic schema for the §4.4.3a entity extraction AI response (v0.8).

The AI returns a JSON array of EntityExtractionItem — one entry per
requirement, keyed by the idx sent in the prompt.
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class EntityExtractionItem(BaseModel):
    idx: int
    terms: list[str] = []

    @field_validator("terms")
    @classmethod
    def strip_empty(cls, v: list[str]) -> list[str]:
        return [t.strip() for t in v if t and t.strip()]
