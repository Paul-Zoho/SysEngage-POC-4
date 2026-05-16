"""
Pydantic schemas for AI conflict sweep response validation.

Per spec §5.1: ConflictSweepResponseItemModel validates the AI response
for Stage 4 conflict assessment.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ConflictSweepResponseItem(BaseModel):
    """Validates a single conflict assessment in the AI conflict sweep response."""

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(min_length=1)
    is_genuine_contradiction: bool
    rationale: str = Field(min_length=1)


class ConflictSweepResponse(BaseModel):
    """Wraps the full list of conflict sweep assessments."""

    model_config = ConfigDict(frozen=True)

    conflicts: list[ConflictSweepResponseItem]


def parse_conflict_sweep_response(
    raw: dict,
) -> tuple[list[ConflictSweepResponseItem], list[dict]]:
    """
    Parse and validate the raw AI JSON response for the conflict sweep.

    Returns
    -------
    (valid_items, failures)
    valid_items : list of valid ConflictSweepResponseItem
    failures    : list of {source_id_or_index, error} for invalid items
    """
    failures: list[dict] = []
    valid_items: list[ConflictSweepResponseItem] = []

    raw_conflicts = raw.get("conflicts", [])
    if not isinstance(raw_conflicts, list):
        return [], [{"source_id": "root", "error": "Response missing 'conflicts' list"}]

    for i, item in enumerate(raw_conflicts):
        try:
            valid_items.append(ConflictSweepResponseItem.model_validate(item))
        except Exception as exc:
            failures.append(
                {
                    "source_id": (
                        item.get("source_id", f"index_{i}")
                        if isinstance(item, dict)
                        else f"index_{i}"
                    ),
                    "error": str(exc),
                }
            )

    return valid_items, failures
