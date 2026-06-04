"""
Structural requirement quality rules — Phase 4 RQA (candidate rules).

Per RQA Spec v0.1 §5.4 (candidate/provisional).
Note from spec §10: "Structural rules candidate — validate once Structural
requirements exist."

Decidable checks (DM, via core/slots.py):
  - Missing Entity slot            → High (30)
  - Missing structural assertion   → Medium (15)
  - Implementation detail present  → Low (5) (technology name in a structural statement)

IM-judged checks (batched in judge.py):
  - Implied design (implementation detail below the row's abstraction) → Low (5)
  - Misclassification (is it actually Functional/Constraint?)          → Medium (15)

These are candidate rules — validated once Structural requirements exist in the
real PMT/NQPS data. Until then they are authored ahead of run evidence.
"""

from __future__ import annotations

import re

from core.slots import check_atomicity
from mechanisms.requirement_quality.scoring import (
    SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW,
)

# Heuristic: technology names that suggest implementation detail in a structural statement
_IMPL_DETAIL_RE = re.compile(
    r"\b(postgresql|mysql|redis|api|rest|json|xml|http|class|table|schema|"
    r"field|column|function|method|endpoint|sdk|orm|orm|docker|kubernetes)\b",
    re.IGNORECASE,
)


def run_decidable(
    *,
    statement: str,
) -> list[dict]:
    """
    Run all decidable Structural requirement quality checks (candidate rules).

    Returns list of violation dicts: {rule, severity, penalty, detail}
    """
    violations: list[dict] = []

    # Slot checks — Structural slots (Entity + structural assertion)
    slot_violations = check_atomicity(statement, "Structural")
    for sv in slot_violations:
        if sv.is_hard:
            violations.append({
                "rule": sv.rule,
                "severity": "High",
                "penalty": SEVERITY_HIGH,
                "detail": sv.detail,
            })
        else:
            violations.append({
                "rule": sv.rule,
                "severity": "Medium",
                "penalty": SEVERITY_MEDIUM,
                "detail": sv.detail,
            })

    # Implementation detail in structural statement (candidate rule)
    if _IMPL_DETAIL_RE.search(statement):
        m = _IMPL_DETAIL_RE.search(statement)
        violations.append({
            "rule": "structural_impl_detail",
            "severity": "Low",
            "penalty": SEVERITY_LOW,
            "detail": f"Implementation detail {m.group()!r} may be below abstraction level for a Structural requirement",
        })

    return violations
