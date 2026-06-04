"""
Quality score arithmetic for Phase 4 Requirement Quality Analysis.

Per RQA Spec v0.1 §4.2 and D-q-5.

Framework constants (not ProjectProfile parameters):
  SEVERITY_HIGH   = 30
  SEVERITY_MEDIUM = 15
  SEVERITY_LOW    =  5
  START_SCORE     = 100
  FLOOR_SCORE     =   0

Score = max(0, 100 − Σ penalties).

Bands (informational thresholds for aggregate reporting):
  ≥ 80 → High quality
  50–79 → Adequate
  < 50 → Low quality / prioritise revision
"""

from __future__ import annotations

SEVERITY_HIGH: int = 30
SEVERITY_MEDIUM: int = 15
SEVERITY_LOW: int = 5
START_SCORE: int = 100
FLOOR_SCORE: int = 0

BAND_HIGH_THRESHOLD: int = 80
BAND_ADEQUATE_THRESHOLD: int = 50


def score(violations: list[dict]) -> int:
    """
    Compute quality score from a list of violation dicts.

    Each violation dict must have a 'penalty' key (int).
    Score = max(0, 100 - sum(penalties)).
    """
    total_penalty = sum(v.get("penalty", 0) for v in violations)
    return max(FLOOR_SCORE, START_SCORE - total_penalty)


def band(score_value: int) -> str:
    """Return the score band label for a given score."""
    if score_value >= BAND_HIGH_THRESHOLD:
        return "high"
    if score_value >= BAND_ADEQUATE_THRESHOLD:
        return "adequate"
    return "low"
