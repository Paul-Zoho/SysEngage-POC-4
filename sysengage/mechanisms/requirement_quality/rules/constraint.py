"""
Constraint requirement quality rules — Phase 4 RQA.

Per RQA Spec v0.1 §5.3 (realises Row 3 §5.3, merged DC/Env/Perf rules).

verification_method selects which rules bite — the key Constraint insight from
D-q-1: a Constraint verified by Inspection has no obligation to carry fit_criteria;
one verified by Measurement does (as the acceptance basis IS the measurable value).

Decidable checks (DM, via core/slots.py):
  - Missing Subject slot                            → High (30)
  - Missing Rule slot (the constraint expression)   → High (30)
  - Multiple lifecycle phases (operate/store/transport co-occurrence) → Medium (15)
  - Missing measurable Criteria when verification_method='Measurement' → High (30)
    (NOT fired for Inspection-verified Constraints)

IM-judged checks (batched in judge.py):
  - Ambiguous verb                → Low (5)
  - Implied design                → Low (5)
  - Subjective/unquantified terms → Low (5)
  - Misclassification (is it actually Functional/Structural?) → Medium (15)
"""

from __future__ import annotations

import re

from core.slots import check_atomicity
from mechanisms.requirement_quality.scoring import (
    SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW,
)

_LIFECYCLE_PHASES = [
    r"\boperat", r"\bstor", r"\btransport", r"\bmainten", r"\bdispos",
]
_LIFECYCLE_RE = [re.compile(p, re.IGNORECASE) for p in _LIFECYCLE_PHASES]


def run_decidable(
    *,
    statement: str,
    verification_method: str | None,
    fit_criteria: str | None,
) -> list[dict]:
    """
    Run all decidable Constraint requirement quality checks.

    Returns list of violation dicts: {rule, severity, penalty, detail}
    """
    violations: list[dict] = []

    # Slot checks — Constraint slots (Subject + Rule)
    slot_violations = check_atomicity(statement, "Constraint")
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

    # Multiple lifecycle phases co-occurrence
    stmt_lower = statement.lower()
    phases_found = [p for p_re, p in zip(_LIFECYCLE_RE, _LIFECYCLE_PHASES) if p_re.search(stmt_lower)]
    if len(phases_found) >= 2:
        violations.append({
            "rule": "multiple_lifecycle_phases",
            "severity": "Medium",
            "penalty": SEVERITY_MEDIUM,
            "detail": f"Statement references multiple lifecycle phases — atomicity concern",
        })

    # Missing Criteria when Measurement (High — the acceptance basis IS the value)
    # NOT fired for Inspection-verified constraints
    if verification_method == "Measurement" and not (fit_criteria and fit_criteria.strip()):
        violations.append({
            "rule": "missing_criteria_when_measurement",
            "severity": "High",
            "penalty": SEVERITY_HIGH,
            "detail": "Constraint with verification_method='Measurement' requires fit_criteria",
        })

    return violations
