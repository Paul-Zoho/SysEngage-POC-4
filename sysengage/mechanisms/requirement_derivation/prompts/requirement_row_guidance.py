"""
Requirement Row Guidance — REQUIREMENT_ROW_GUIDANCE prompt constants.

Per Requirement Derivation Mechanism Spec v0.2 §5.4.

DISTINCT from the domain ROW_GUIDANCE (which governs domain naming and grouping;
imported from domain_derivation/prompts/domain_grouping_prompt.py). This dict
governs requirement STATEMENT FORMULATION at the row-appropriate abstraction
level — subject vocabulary, verb choice, type-reasoning signals, and optional-
field policy.

Row 1 is fully authored (validated against PMT Row 1 / NQPS Row 1 production
runs). Rows 2–6 are short-phrase stubs pending per-row requirement-derivation
validation cycles — same staged approach as the domain ROW_GUIDANCE.
"""

from __future__ import annotations

REQUIREMENT_ROW_GUIDANCE: dict[str, str] = {
    "1": """\
## Row 1 — Planner / Scope Layer — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the enterprise scope level — the view of
a senior executive or board member. Each requirement expresses something the enterprise
commits to, is accountable for, or is constrained by — without reference to how any
system works.

### Statement subject (REQUIRED)
Every Row 1 requirement statement takes THE ENTERPRISE as its subject:
  "The enterprise shall ..."
Do NOT write "The system shall ..." at Row 1 — that is Row 2+ vocabulary and describes
a system, not an enterprise commitment.

This holds for COMPLIANCE, LEGISLATIVE, and REGULATORY obligations, which otherwise tend
to attract conventional system-requirements phrasing. Write:
  "The enterprise shall comply with applicable legislative obligations."
NEVER:
  "The system shall comply with applicable legislative obligations."
If the source content is a regulatory or compliance constraint, the enterprise is still
the accountable subject — not a system.

### Normative form and atomicity
- Use the normative "shall". One obligation per statement.
- If a statement would join two distinct obligations with "and" / "," apply the two-step
  test: (1) is there a single obligation that subsumes both? Use it. (2) If not, split
  into two requirements. (Requirement-level analogue of the domain "and" test.)
  Example: "shall determine and present aggregate earnings" is two acts (determine;
  present) — prefer one obligation, or split.

### Statement vocabulary
Row 1 statements use enterprise-commitment verbs:
  Appropriate: recognise, establish, maintain, provide, govern, ensure, comply, commit,
               be accountable for, be entitled to, enable (at enterprise scope)
  Avoid: calculate, display, track, store, retrieve, retain, generate, manage, process
         (these describe system functions — they belong at Row 2 or below). "retain" in
         particular is storage vocabulary — say "maintain records" / "be accountable for"
         at Row 1.

### requirement_type reasoning (principle-based — choose, do not pattern-match)
Weigh the source CCIs' Zachman columns and content against the row's abstraction level:
- Why-column / motivation / rule / policy / commitment content → lean Constraint.
- How / What / When / capability / function content → lean Functional.
- Content expressing a measurable threshold, rate, latency, or capacity → Performance
  (and the statement SHOULD carry fit_criteria).
- Content expressing a quality attribute (usability, maintainability, portability) →
  Suitability or Non-Functional per the attribute.
These are reasoning signals, not a lookup table. A genuinely ambiguous obligation may
read as either Constraint or Functional — choose the dominant force; do not force a
distribution.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: include only when the content gives a measurable acceptance basis.
- verification_method (Test/Analysis/Inspection/Demonstration): include only when a
  natural method exists. An abstract enterprise constraint (e.g. "support charitable
  responsibility obligations") may have NO natural verification method at Row 1 — OMIT
  the field rather than guessing. Omission is correct, not a defect.
- priority (High/Medium/Low): include only when the source content supports a relative
  priority judgement. Do NOT default every requirement to High. If the content gives no
  basis, omit.

### What NOT to do
- Do NOT introduce actors, behaviours, or constraints not present in the source CCIs.
- Do NOT reproduce CCI description text verbatim as the statement — derive a normative
  statement from it.
- Do NOT produce one thin requirement per CCI mechanically; consolidate where CCIs
  express one obligation, split where one CCI carries two.""",

    # Rows 2–6: short-phrase stubs pending per-row requirement-derivation validation
    # cycles. Each will be expanded to a full block (subject / atomicity / vocabulary /
    # type-reasoning / optional-field policy) after that row has run-time evidence —
    # same staged approach as the domain ROW_GUIDANCE.
    "2": (
        "Business conceptual level — statements subjected to the enterprise/business or "
        "a named business actor; business-process and rule vocabulary; no implementation "
        "verbs. [Full block pending Row 2 requirement-derivation validation.]"
    ),
    "3": (
        "Logical design level — statements expressed as logical system capability; "
        "logical-design vocabulary (logical structure, behaviour, state, interaction); "
        "technology-agnostic, no physical/implementation vocabulary. "
        "[Full block pending Row 3 requirement-derivation validation.]"
    ),
    "4": (
        "Physical builder level — statements subjected to the system or a named "
        "component; specific technology and component vocabulary appropriate. "
        "[Full block pending Row 4 requirement-derivation validation.]"
    ),
    "5": (
        "Detailed design level — statements at algorithm/format/configuration detail. "
        "[Full block pending Row 5 requirement-derivation validation.]"
    ),
    "6": (
        "Operational level — statements covering runtime procedures and "
        "user/operator interactions. "
        "[Short phrase — operational content is rare in source documents.]"
    ),
}
