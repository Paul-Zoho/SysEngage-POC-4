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

Slot patterns (Row 4 Requirement Derivation v0.24 §4.3 / CHK-3d-09):

  Functional   : [Condition,] Subject shall Action Object
                 Required slots: Subject, Action, Object
                 Hard violations: compound condition, conjoined predicate (two
                 distinct finite verb phrases — F98), compound object (two+
                 objects under one verb — F98 promoted to hard), multiple
                 obligations (two+ "shall"), missing required slot.

  Constraint   : Subject shall <constraint-verb> Constraint-Rule
                 [under Condition] [to Criteria]
                 Required slots: Subject, Constraint Rule
                 Hard violations: conjoined predicate (F98), compound constraint
                 rule (F98 promoted to hard), multiple constraint rules (two+
                 "shall"), missing required slot.

  Structural   : Entity <structural-verb> Structural-element
                 Required slots: Entity, structural assertion
                 Hard violations: missing structural verb, missing entity,
                 missing structural element, multiple obligations.

F98 (v0.24) — conjoined-predicate hard branch: after isolating the predicate,
apply a verb-phrase test on both sides of any 'and' conjunction (F104 P1: 'or'
in the predicate is a single-obligation choice/hedge, not a compound trigger):
  - Both conjuncts carry a distinct finite action verb → conjoined_predicate,
    is_hard=True (CHK-3d-09 in-place decompose repair in Stage 3).
  - Single verb with conjoined nouns/objects → compound_object (Functional) or
    compound_constraint_rule (Constraint), is_hard=True (previously soft).
  - Relative clause continuation (and which/that…, no second finite verb) → no flag.

F103 (v0.26) — member-list carve-out: within the compound_object /
compound_constraint_rule branch, if the predicate verb is a member-list verb
(accept / define / consist of / contain / include / revoke / grant), the
conjunction joins inseparable enumeration members, definition elements, or
operation/privilege list items — not separable obligations. Downgraded to
is_hard=False (soft PLB-3d-01 advisory). Realises Row 3 RD v0.15 §4.1.1(b).

F104 (v0.27) — conjoined-predicate detector precision (four carve-outs):
  P1 — conjunction only, never disjunction: only 'and' feeds the predicate/object
       hard branches. 'or' in the predicate is a single-obligation choice/hedge
       and does not trigger the compound detector. Slot-sensitive: 'or' joining
       two condition openers still fires compound_condition (unchanged, uses
       _CONDITION_OPENER, not the predicate conjunction check).
  P2 — main-predicate scope: the verb-on-both-sides test is scoped to the main
       predicate only. Locate the first relative-pronoun boundary (that/which/who);
       any 'and' to its right is inside the subordinate clause and exempt from the
       test. The existing "and which/that" carve-out is retained for the case where
       the relative pronoun immediately follows the conjunction.
  P3 — operation/privilege lists extend the F103 member-list carve-out. The
       member-list check runs BEFORE the action-verb test so that operation names
       (e.g. DELETE, UPDATE) under a governing verb (revoke, grant) are not
       mis-read as independent finite action verbs.
  P4 — temporal/sequencing subordinators are not conjunctions. A conjunction
       whose right conjunct begins with 'then', 'prior to', 'before', or 'after'
       is a temporal qualifier (one action with sequencing) — not a conjoined
       obligation — and does not trigger the hard branch.

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

# F104 P1 (v0.27): 'and'-only pattern for predicate/object hard branches.
# 'or' in the predicate is a single-obligation choice/hedge — not a compound
# trigger. Only _AND feeds the hard branches; _AND_OR is kept for any callers
# that still need disjunction awareness (e.g. _RELATIVE_CLAUSE).
_AND = re.compile(r"\band\b", re.IGNORECASE)

# F98 (v0.24) — relative clause patterns for conjoined-predicate exemption.
# _RELATIVE_CLAUSE: "and which/that" immediately at the junction.
# _RELATIVE_CLAUSE_BOUNDARY (F104 P2): first that/which/who in the predicate;
# any 'and' to its right is inside the subordinate clause and exempt.
_RELATIVE_CLAUSE = re.compile(r"\band\s+(?:which|that)\b", re.IGNORECASE)
_RELATIVE_CLAUSE_BOUNDARY = re.compile(r"\b(?:that|which|who)\b", re.IGNORECASE)

# F104 P4 (v0.27): temporal/sequencing subordinators. If the right conjunct
# (text after 'and') begins with one of these words, the conjunction is a
# temporal qualifier — one action with sequencing — not a conjoined obligation.
_TEMPORAL_SUBORDINATOR = re.compile(
    r"^(?:then|prior\s+to|before|after)\b", re.IGNORECASE
)

_ACTION_VERB = re.compile(
    r"\b(?:provide|ensure|allow|enable|create|update|delete|manage|track|record|"
    r"maintain|calculate|notify|send|receive|store|retrieve|process|validate|"
    r"confirm|reject|assign|allocate|report|generate|support|handle|monitor|"
    r"enforce|prevent|restrict|permit|perform|execute|complete|cancel|approve|"
    r"deny|submit|publish|display|show|sort|filter|group|merge|split|convert|"
    r"import|export|archive|schedule|trigger|alert|audit|verify|check|capture|"
    r"collect|aggregate|derive|produce|accept|limit|access|control|govern|"
    r"comply|adhere|conform|contain|hold|apply|define|register|activate|"
    r"deactivate|start|stop|pause|resume|suspend|present|require|include|exclude|"
    r"log|flag|mark|link|bind|route|redirect|authenticate|authorise|authorize|"
    r"encrypt|decrypt|refresh|expire|revoke|enforce|notify|propagate|invoke|"
    r"validate|index|cache|queue|dispatch|emit|consume|publish|subscribe)\b",
    re.IGNORECASE,
)

# F103 (v0.26) / F104 P3 (v0.27): member-list verbs — enumeration-or-definition
# verbs (and operation/privilege-set verbs) that introduce an inseparable value,
# member, or privilege list rather than separable obligations.
# When 'and' in the predicate falls under one of these verbs, the compound is an
# inseparable member/operation list — downgrade from hard to soft PLB-3d-01.
# F104 P3: member-list check runs BEFORE the action-verb test so that operation
# names (DELETE, UPDATE) under a governing verb (revoke, grant) are not mis-read
# as independent finite action verbs.
_MEMBER_LIST_VERB = re.compile(
    r"\b(?:accept|define|consist\s+of|contain|include|revoke|grant)\b",
    re.IGNORECASE,
)

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

    # Compound condition: two or more condition openers in the full statement.
    # Uses _CONDITION_OPENER (when/if/…) — unaffected by F104 P1 (the 'or'
    # change applies to the predicate conjunction check only, not here).
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

    # Compound / conjoined predicate: 'and' conjunction in the predicate (F98 v0.24 /
    # F104 v0.27). Resolution order per F104:
    #   P1: only 'and' feeds these hard branches; 'or' = choice/hedge, no flag.
    #   P2: conjunction to the right of a relative-clause boundary → exempt.
    #   (retained) "and which/that" carve-out → exempt.
    #   P4: right conjunct begins with temporal subordinator → exempt (sequence).
    #   P3: predicate governed by a member-list verb → soft PLB-3d-01 (runs BEFORE
    #       action-verb test so operation names like DELETE don't mis-trigger).
    #   conjoined_predicate: right conjunct has its own finite action verb → hard.
    #   compound_object: single verb with conjoined nouns/objects → hard.
    and_in_pred = list(_AND.finditer(predicate_part))
    if and_in_pred:
        and_match = and_in_pred[0]
        # P2: relative-clause boundary — first that/which/who appearing before
        # the conjunction means the 'and' is inside the subordinate clause.
        boundary = _RELATIVE_CLAUSE_BOUNDARY.search(predicate_part)
        if boundary and boundary.start() < and_match.start():
            pass  # inside relative clause — one obligation, no violation
        elif _RELATIVE_CLAUSE.search(predicate_part):
            pass  # "and which/that" at the junction — relative clause, no violation
        else:
            right_conjunct = predicate_part[and_match.end():].strip()
            # P4: temporal subordinator — one sequential action, not a split.
            if _TEMPORAL_SUBORDINATOR.match(right_conjunct):
                pass  # temporal qualifier, no violation
            else:
                # P3: member-list carve-out runs BEFORE action-verb test.
                _member_list = bool(_MEMBER_LIST_VERB.search(predicate_part))
                if _member_list:
                    violations.append(AtomicityViolation(
                        rule="compound_object",
                        detail=(
                            f"Conjunction '{and_match.group()}' in predicate "
                            "joins members of an inseparable enumeration, definition, "
                            "or operation/privilege list under a member-list verb "
                            "(F103/F104 carve-out) — logged for Practitioner review, "
                            "not a separable obligation."
                        ),
                        is_hard=False,
                    ))
                elif _ACTION_VERB.search(right_conjunct):
                    violations.append(AtomicityViolation(
                        rule="conjoined_predicate",
                        detail=(
                            f"Conjunction '{and_match.group()}' in predicate separates "
                            "two distinct finite verb phrases — each half is a separate "
                            "obligation (F98). Decompose into two atomic single-verb statements."
                        ),
                        is_hard=True,
                    ))
                else:
                    violations.append(AtomicityViolation(
                        rule="compound_object",
                        detail=(
                            f"Conjunction '{and_match.group()}' in predicate "
                            "joins multiple objects under one verb — compound object (F98). "
                            "Split into separate single-object statements."
                        ),
                        is_hard=True,
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

    # Compound / conjoined constraint predicate: same four-way resolution as
    # _check_functional (F98 v0.24 / F104 v0.27). See _check_functional comments.
    and_in_pred = list(_AND.finditer(predicate_part))
    if and_in_pred:
        and_match = and_in_pred[0]
        # P2: relative-clause boundary
        boundary = _RELATIVE_CLAUSE_BOUNDARY.search(predicate_part)
        if boundary and boundary.start() < and_match.start():
            pass  # inside relative clause — one obligation, no violation
        elif _RELATIVE_CLAUSE.search(predicate_part):
            pass  # "and which/that" at the junction — relative clause, no violation
        else:
            right_conjunct = predicate_part[and_match.end():].strip()
            # P4: temporal subordinator
            if _TEMPORAL_SUBORDINATOR.match(right_conjunct):
                pass  # temporal qualifier, no violation
            else:
                # P3: member-list carve-out runs BEFORE action-verb test.
                _member_list = bool(_MEMBER_LIST_VERB.search(predicate_part))
                if _member_list:
                    violations.append(AtomicityViolation(
                        rule="compound_constraint_rule",
                        detail=(
                            f"Conjunction '{and_match.group()}' in constraint predicate "
                            "joins members of an inseparable enumeration, value, "
                            "or operation/privilege list under a member-list verb "
                            "(F103/F104 carve-out) — logged for Practitioner review, "
                            "not separable Constraint Rules."
                        ),
                        is_hard=False,
                    ))
                elif _ACTION_VERB.search(right_conjunct):
                    violations.append(AtomicityViolation(
                        rule="conjoined_predicate",
                        detail=(
                            f"Conjunction '{and_match.group()}' in constraint predicate "
                            "separates two distinct finite verb phrases — two Constraint Rules "
                            "in one statement (F98). Decompose into two atomic Constraint statements."
                        ),
                        is_hard=True,
                    ))
                else:
                    violations.append(AtomicityViolation(
                        rule="compound_constraint_rule",
                        detail=(
                            f"Conjunction '{and_match.group()}' in constraint predicate "
                            "joins multiple rule elements under one constraint verb — compound "
                            "Constraint Rule (F98). Split into separate single-rule Constraints."
                        ),
                        is_hard=True,
                    ))

    return violations


_RELATIONSHIP_VERB = re.compile(
    r"\b(?:relates?\s+to|depends?\s+on|interfaces?\s+with|inherits?\s+from|"
    r"is\s+part\s+of|extends?)\b",
    re.IGNORECASE,
)


def extract_slot_terms(statement: str, requirement_type: str) -> dict:
    """
    Extract named slot terms from a requirement statement for DD binding.

    Per §4.4.3a (v0.7): reuses CHK-3d-09/ADVC-3d-02 slot parse patterns.
    Called by Stage 4 to identify Functional Objects, Structural entities /
    elements, and Constraint subjects for presentation to the DD service.

    Returns a dict whose keys depend on requirement_type:
      Functional  → {"object": str | None}
      Structural  → {"entity": str | None, "assertion": str | None,
                     "is_relationship": bool}
      Constraint  → {"subject": str | None, "rule": str | None}
                    subject = pre-shall noun phrase; rule = post-shall predicate.
                    Use "rule" for DD entity extraction (§4.4.3a F99): entities
                    are the domain concepts the Rule governs, not the Subject.
    Any value may be None if the slot is absent or unparseable.
    """
    rtype = requirement_type.strip()
    if rtype == "Functional":
        return _extract_functional_slots(statement)
    elif rtype == "Structural":
        return _extract_structural_slots(statement)
    elif rtype == "Constraint":
        return _extract_constraint_slots(statement)
    return {}


def _extract_functional_slots(statement: str) -> dict:
    """Extract Object from Functional: [Condition,] Subject shall Action Object."""
    m = _SHALL.search(statement)
    if not m:
        return {"object": None}
    predicate = statement[m.end():].strip()
    parts = predicate.split(None, 1)
    obj = parts[1].strip() if len(parts) >= 2 else predicate
    return {"object": obj or None}


def _extract_structural_slots(statement: str) -> dict:
    """Extract Entity and Assertion from Structural: Entity <structural-verb> Element."""
    m = _STRUCTURAL_VERB.search(statement)
    if m:
        entity = statement[:m.start()].strip(" .,;") or None
        assertion = statement[m.end():].strip(" .,;") or None
        is_rel = bool(_RELATIONSHIP_VERB.search(statement))
        return {"entity": entity, "assertion": assertion, "is_relationship": is_rel}
    m2 = _SHALL.search(statement)
    if m2:
        entity = statement[:m2.start()].strip(" .,;") or None
        rest = statement[m2.end():].strip()
        parts = rest.split(None, 1)
        assertion = parts[1].strip() if len(parts) >= 2 else (rest or None)
        return {"entity": entity, "assertion": assertion, "is_relationship": False}
    return {"entity": None, "assertion": None, "is_relationship": False}


def _extract_constraint_slots(statement: str) -> dict:
    """Extract Subject and Constraint-Rule from Constraint: Subject shall <constraint-verb> Rule.

    Returns both slots:
      subject — pre-shall noun phrase (the entity bearing the obligation)
      rule    — post-shall predicate (the domain concept(s) the rule governs)

    For DD entity extraction (§4.4.3a F99), use "rule" not "subject":
    a Constraint has no Object slot, so entity terms come from the rule
    predicate — the noun(s) the rule bounds — not from the thin Subject.
    """
    m = _SHALL.search(statement)
    if not m:
        return {"subject": None, "rule": None}
    subject = statement[:m.start()].strip(" .,;") or None
    rule = statement[m.end():].strip() or None
    return {"subject": subject, "rule": rule}


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
