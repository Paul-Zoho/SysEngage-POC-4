"""
Functional requirement quality rules — Phase 4 RQA.

Per RQA Spec v0.1 §5.2 (realises Row 3 §5.2).

Decidable checks (DM, via core/slots.py):
  - Missing Subject slot          → High (30)
  - Missing Action slot           → High (30)
  - Missing Object slot           → Medium (15)
  - Compound condition/object     → Medium (15)
  - Missing measurable Criteria when verification_method='Measurement' → Medium (15)
  - Object/entity not DD-resolved → Medium (15)

IM-judged checks (batched in judge.py, called from service.py):
  - Ambiguous verb (handle/manage/support/process) → Low (5)
  - Implied design                                 → Low (5)
  - Subjective/unquantified terms                  → Low (5)
  - Behaviour misclassification (should be Constraint or Structural) → Medium (15)
"""

from __future__ import annotations

from core.slots import check_atomicity
from mechanisms.requirement_quality.scoring import (
    SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW,
)


def run_decidable(
    *,
    statement: str,
    verification_method: str | None,
    fit_criteria: str | None,
    object_term: str | None = None,
    dd_resolve_fn=None,
) -> list[dict]:
    """
    Run all decidable Functional requirement quality checks.

    Parameters
    ----------
    statement           : the requirement statement
    verification_method : value from the requirement (may be None)
    fit_criteria        : value from the requirement (may be None)
    object_term         : extracted object term (optional; enables DD check)
    dd_resolve_fn       : callable(term) → dict (DD resolve_object; may be None)

    Returns
    -------
    list of violation dicts: {rule, severity, penalty, detail}
    """
    violations: list[dict] = []

    # Slot checks via the shared detector (same code as RD CHK-3d-09 — VER-q-06)
    slot_violations = check_atomicity(statement, "Functional")
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

    # Missing measurable Criteria when verification_method = Measurement
    if verification_method == "Measurement" and not (fit_criteria and fit_criteria.strip()):
        violations.append({
            "rule": "missing_criteria_when_measurement",
            "severity": "Medium",
            "penalty": SEVERITY_MEDIUM,
            "detail": "verification_method='Measurement' requires fit_criteria",
        })

    # Object/entity not DD-resolved (decidable lookup)
    if object_term and dd_resolve_fn is not None:
        try:
            res = dd_resolve_fn(object_term)
            if res is None or res.get("status") == "flagged" or not res.get("dd_id"):
                violations.append({
                    "rule": "object_dd_unresolved",
                    "severity": "Medium",
                    "penalty": SEVERITY_MEDIUM,
                    "detail": f"Object term {object_term!r} not resolved in Data Dictionary",
                })
        except Exception:
            pass  # DD lookup failure is advisory — not scored

    return violations
