"""
core/slots.py — Shared typed-slot detector (F88 slot canon).

Single implementation of the F88 slot canon. Imported by:
  - Requirement Derivation CHK-3d-09 (hard-reject at creation)
  - Requirement Quality Analysis (graded-penalty scoring)

Both consumers are known by design (VER-q-06). A single shared module guarantees
that "missing Object", "compound object", and "missing Constraint Rule" mean
exactly the same thing at creation (hard reject) and at scoring (graded penalty).

Do NOT fork a local copy into either mechanism package — that would reintroduce
the drift risk VER-q-06 exists to prevent.

Slot patterns (Row 4 Requirement Derivation v0.6 §4.3 / CHK-3d-09):

  Functional   : [Condition,] Subject shall Action Object
                 Required slots: Subject, Action, Object
                 Hard violations: compound condition, compound object (two+
                 independent objects), multiple obligations (two+ "shall"),
                 missing required slot.

  Constraint   : Subject shall <constraint-verb> Constraint-Rule
                 [under Condition] [to Criteria]
                 Required slots: Subject, Constraint Rule
                 Hard violations: multiple constraint rules (two+ "shall"),
                 missing required slot.

  Structural   : Entity <structural-verb> Structural-element
                 Required slots: Entity, structural assertion
                 Hard violations: missing structural verb, missing entity,
                 missing structural element, multiple obligations.

The inseparable-single-concept exception (a conjunction that joins an
effectively-single concept such as "load and save" → single workflow) is
flagged with is_hard=False for Practitioner review, never auto-rejected.

See also: Row 4 Requirement Quality Analysis v0.1 D-q-2, VER-q-06.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class AtomicityViolation:
    """A single atomicity violation in a requirement statement."""

    rule: str
    detail: str
    is_hard: bool


_SHALL = re.compile(r"\bshall\b", re.IGNORECASE)

_CONDITION_OPENER = re.compile(
    r"\b(?:when|if|whenever|upon|where|provided\s+that|"
    r"in\s+the\s+event\s+that|unless|assuming|given\s+that)\b",
    re.IGNORECASE,
)

_AND_OR = re.compile(r"\b(?:and|or)\b", re.IGNORECASE)

_STRUCTURAL_VERB = re.compile(
    r"\b(?:comprises?|is\s+composed\s+of|consists?\s+of|has|contains?|"
    r"relates?\s+to|depends?\s+on|interfaces?\s+with|inherits?\s+from|"
    r"is\s+made\s+up\s+of|is\s+part\s+of|includes?|extends?|"
    r"is\s+structured\s+as|is\s+partitioned\s+into|aggregates?)\b",
    re.IGNORECASE,
)


def check_atomicity(statement: str, requirement_type: str) -> list[AtomicityViolation]:
    """
    Decidable atomicity check for a requirement statement.

    Returns a list of AtomicityViolation objects. Empty list means the statement
    passes all decidable atomicity checks.

    Violations with is_hard=False represent possible inseparable-single-concept
    exceptions — log for Practitioner review, do not auto-reject.

    Parameters
    ----------
    statement        : the requirement statement text
    requirement_type : 'Functional' | 'Constraint' | 'Structural'
    """
    rtype = requirement_type.strip()
    if rtype == "Functional":
        return _check_functional(statement)
    elif rtype == "Constraint":
        return _check_constraint(statement)
    elif rtype == "Structural":
        return _check_structural(statement)
    return []


def has_hard_violations(violations: list[AtomicityViolation]) -> bool:
    """Return True if any violation requires rejection under CHK-3d-09."""
    return any(v.is_hard for v in violations)


def violation_summary(violations: list[AtomicityViolation]) -> str:
    """Compact audit string for mechanism_data logging."""
    if not violations:
        return "no violations"
    return "; ".join(
        f"{v.rule}({'hard' if v.is_hard else 'soft'})" for v in violations
    )


def _check_functional(statement: str) -> list[AtomicityViolation]:
    violations: list[AtomicityViolation] = []

    shall_matches = list(_SHALL.finditer(statement))

    if not shall_matches:
        violations.append(AtomicityViolation(
            rule="missing_shall",
            detail="Functional requirement has no normative 'shall' — required slot structure absent.",
            is_hard=True,
        ))
        return violations

    # Multiple "shall" = multiple independent obligations in one statement
    if len(shall_matches) >= 2:
        violations.append(AtomicityViolation(
            rule="multiple_obligations",
            detail=(
                f"Statement contains {len(shall_matches)} 'shall' clauses — "
                "multiple obligations combined in one statement."
            ),
            is_hard=True,
        ))
        return violations

    shall_pos = shall_matches[0].start()
    subject_part = statement[:shall_pos].strip(" .,;")
    predicate_part = statement[shall_matches[0].end():].strip()

    if not subject_part:
        violations.append(AtomicityViolation(
            rule="missing_subject",
            detail="No subject found before 'shall' (Required: Subject shall Action Object).",
            is_hard=True,
        ))

    if not predicate_part:
        violations.append(AtomicityViolation(
            rule="missing_action_object",
            detail="No action/object found after 'shall' (Required: Subject shall Action Object).",
            is_hard=True,
        ))
        return violations

    # Compound condition: two or more condition openers in the full statement
    condition_matches = list(_CONDITION_OPENER.finditer(statement))
    if len(condition_matches) >= 2:
        violations.append(AtomicityViolation(
            rule="compound_condition",
            detail=(
                f"Multiple condition openers detected "
                f"({', '.join(repr(m.group()) for m in condition_matches[:3])}) — "
                "statement appears to combine two or more conditions."
            ),
            is_hard=True,
        ))

    # Compound object: conjunction in the predicate may indicate two independent objects
    and_or_in_pred = list(_AND_OR.finditer(predicate_part))
    if and_or_in_pred:
        violations.append(AtomicityViolation(
            rule="compound_object_possible_exception",
            detail=(
                f"Conjunction '{and_or_in_pred[0].group()}' in predicate may indicate "
                "a compound object. If the two elements form a single inseparable concept, "
                "this is a permitted exception (Practitioner review)."
            ),
            is_hard=False,
        ))

    return violations


def _check_constraint(statement: str) -> list[AtomicityViolation]:
    violations: list[AtomicityViolation] = []

    shall_matches = list(_SHALL.finditer(statement))

    if not shall_matches:
        violations.append(AtomicityViolation(
            rule="missing_shall",
            detail="Constraint requirement has no normative 'shall' — required slot structure absent.",
            is_hard=True,
        ))
        return violations

    # Multiple "shall" = multiple independent constraint rules
    if len(shall_matches) >= 2:
        violations.append(AtomicityViolation(
            rule="multiple_constraint_rules",
            detail=(
                f"Statement contains {len(shall_matches)} 'shall' clauses — "
                "multiple constraint rules combined in one statement."
            ),
            is_hard=True,
        ))
        return violations

    shall_pos = shall_matches[0].start()
    subject_part = statement[:shall_pos].strip(" .,;")
    predicate_part = statement[shall_matches[0].end():].strip()

    if not subject_part:
        violations.append(AtomicityViolation(
            rule="missing_subject",
            detail="No subject found before 'shall' (Required: Subject shall Constraint-Rule).",
            is_hard=True,
        ))

    if not predicate_part:
        violations.append(AtomicityViolation(
            rule="missing_constraint_rule",
            detail=(
                "No constraint rule found after 'shall' "
                "(Required: Subject shall Constraint-Rule)."
            ),
            is_hard=True,
        ))
        return violations

    # Conjunction in predicate may indicate compound rule — soft (could be a range)
    and_or_in_pred = list(_AND_OR.finditer(predicate_part))
    if and_or_in_pred:
        violations.append(AtomicityViolation(
            rule="compound_constraint_rule_possible_exception",
            detail=(
                f"Conjunction '{and_or_in_pred[0].group()}' in constraint predicate may indicate "
                "multiple rules or criteria. If elements form a single inseparable constraint "
                "(e.g. a numeric range), this is a permitted exception."
            ),
            is_hard=False,
        ))

    return violations


def _check_structural(statement: str) -> list[AtomicityViolation]:
    violations: list[AtomicityViolation] = []

    structural_match = _STRUCTURAL_VERB.search(statement)
    shall_matches = list(_SHALL.finditer(statement))

    if not structural_match and not shall_matches:
        violations.append(AtomicityViolation(
            rule="missing_structural_assertion",
            detail=(
                "No structural assertion verb found "
                "(e.g. 'comprises', 'has', 'consists of', 'relates to', 'interfaces with') "
                "and no 'shall' — required slot structure absent."
            ),
            is_hard=True,
        ))
        return violations

    # Multiple "shall" = multiple structural obligations
    if len(shall_matches) >= 2:
        violations.append(AtomicityViolation(
            rule="multiple_obligations",
            detail=(
                f"Statement contains {len(shall_matches)} 'shall' clauses — "
                "multiple structural assertions combined in one statement."
            ),
            is_hard=True,
        ))
        return violations

    # Determine split point
    if structural_match:
        entity_part = statement[:structural_match.start()].strip(" .,;")
        assertion_part = statement[structural_match.end():].strip(" .,;")
    else:
        # Structural expressed normatively: "X shall comprise Y"
        shall_pos = shall_matches[0].start()
        entity_part = statement[:shall_pos].strip(" .,;")
        assertion_part = statement[shall_matches[0].end():].strip(" .,;")

    if not entity_part:
        violations.append(AtomicityViolation(
            rule="missing_entity",
            detail="No entity found before the structural assertion verb (Required: Entity comprises/has/... Element).",
            is_hard=True,
        ))

    if not assertion_part:
        violations.append(AtomicityViolation(
            rule="missing_structural_element",
            detail="No structural element found after the assertion verb (Required: Entity comprises/has/... Element).",
            is_hard=True,
        ))

    return violations
