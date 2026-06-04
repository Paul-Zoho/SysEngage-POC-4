"""
Quality-result carrier for Phase 4 Requirement Quality Analysis.

Per RQA Spec v0.1 §5.2 (D-q-4): a side-table record, not a canonical ledger element.
Latest result per requirement supersedes on re-score.

The carrier is also the in-memory QualityResult dataclass used during scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class QualityResult:
    """
    Per-requirement quality result.

    requirement_id    : ledger requirement id (R###)
    effective_type    : confirmed type after classify.confirm (may differ from stored type)
    reclassified_from : stored type if different from effective_type (D-q-3: recorded not written)
    score             : 0–100
    violations        : [{rule, severity, penalty, detail?}]
    im_not_assessed   : IM-judged checks that could not be assessed (AI failure)
    manual_review_flag: True if IM failure occurred → fail-safe to human
    scored_at         : timestamp
    """

    requirement_id: str
    effective_type: str
    reclassified_from: str | None = None
    score: int = 100
    violations: list[dict[str, Any]] = field(default_factory=list)
    im_not_assessed: list[str] = field(default_factory=list)
    manual_review_flag: bool = False
    scored_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_db_dict(self) -> dict[str, Any]:
        """Return a dict suitable for inserting into requirement_quality_result."""
        return {
            "requirement_id": self.requirement_id,
            "effective_type": self.effective_type,
            "reclassified_from": self.reclassified_from,
            "score": self.score,
            "violations": self.violations,
            "scored_at": self.scored_at,
        }
