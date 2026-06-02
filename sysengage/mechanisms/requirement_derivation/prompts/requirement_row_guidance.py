"""
Requirement Row Guidance — REQUIREMENT_ROW_GUIDANCE prompt constants.

Per Requirement Derivation Mechanism Spec v0.3 §5.4.

DISTINCT from the domain ROW_GUIDANCE (which governs domain naming and grouping;
imported from domain_derivation/prompts/domain_grouping_prompt.py). This dict
governs requirement STATEMENT FORMULATION at the row-appropriate abstraction
level — subject vocabulary, verb choice, type-reasoning signals, and optional-
field policy.

Rows 1 and 2 are fully authored. Row 1 is validated (PMT Row 1 Run 5 / NQPS
Row 1 Run 2). Row 2 is authored pending test. Rows 3–6 are short-phrase stubs
pending per-row requirement-derivation validation cycles — same staged approach
as the domain ROW_GUIDANCE.
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

    "2": """\
## Row 2 — Owner / Business Level — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the business-owner level — the view of
someone who understands what the enterprise is responsible for delivering and how it
must behave, but who is NOT concerned with how that responsibility is technically
realised. Each requirement expresses a business capability, obligation, or rule the
business must satisfy — stated as a persistent business responsibility, not a workflow
step and not a system function.

### Statement subject (REQUIRED)
Row 2 requirement statements take THE BUSINESS as their subject, or a named BUSINESS
ROLE where the source CCI identifies an accountable business actor:
  "The business shall ..."        (default)
  "<Business role> shall ..."     (when a WHO-column CCI names an accountable role,
                                   e.g. "The account holder shall ...")
Do NOT use "The enterprise shall ..." — that is Row 1 (Planner) vocabulary, framing a
scope-level commitment rather than a business responsibility. Do NOT use "The system
shall ..." — that is Row 3+ vocabulary describing a technical realisation.
The distinction from Row 1: Row 1 says what the enterprise commits to at scope level
("The enterprise shall recognise child users as participants"); Row 2 says what the
business must be able to do or must enforce to deliver on that commitment ("The business
shall maintain a record of each participant's compensated work").

### Normative form and atomicity
- Use the normative "shall". One business responsibility per statement.
- Apply the two-step "and" test (requirement-level analogue of the domain "and" test):
  (1) is there a single responsibility that subsumes both clauses? Use it.
  (2) If not, split into two requirements.
- Row 2 capability statements are STATELESS obligations — "the business shall be able to
  X" — NOT step-by-step sequences ("first the business does X, then Y"). A statement
  describing an ordered workflow has dropped to Row 3+ and must be re-stated as a
  capability.

### Statement vocabulary
Row 2 statements use business-responsibility vocabulary:
  Appropriate: maintain, record, govern, settle, approve, authorise, account for,
               be responsible for, be accountable for, steward, enforce (a business
               rule), make available, recognise (a business role)
  Avoid: calculate, process, store, retrieve, aggregate, compute, manage, track,
         retain, retention, generate, display
         (these describe system functions or technical storage — they belong at Row 3
         or below; use "record", "maintain", "account for", "make available" instead).
         "retain"/"retention" in particular is technical storage vocabulary — say
         "maintain a record" / "be accountable for" at Row 2.
  Also avoid: any word implying a technical mechanism (API, schema, database, service,
              endpoint, algorithm).

### requirement_type reasoning (principle-based — choose, do not pattern-match)
Weigh the source CCIs' Zachman columns and content against the business-owner level:
- WHY-column business governance rules / motivation / constraints on business behaviour
  → lean Constraint ("The business shall enforce the approval threshold ...").
- HOW-column business capability declarations / WHAT-column business artefacts the
  business must maintain / WHEN-column business triggers → lean Functional ("The
  business shall maintain a record of ...").
- Content expressing a measurable business threshold, rate, or service level →
  Performance (and the statement SHOULD carry fit_criteria).
- Content expressing a business quality attribute → Suitability or Non-Functional.
Reasoning signals, not a lookup table. Note: at Row 2 the Functional/Constraint balance
is typically more even than at Row 1 — business capability declarations (HOW-column) are
genuinely Functional, while business rules (WHY-column) are genuinely Constraint. Do not
carry a Row-1 lean into Row 2; judge each statement on its source columns.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: include only when the content gives a measurable acceptance basis (more
  common at Row 2 than Row 1 — business service levels and thresholds appear here).
- verification_method (Test/Analysis/Inspection/Demonstration): include when a natural
  method exists for the business responsibility; omit when the content gives no basis.
- priority (High/Medium/Low): include only when the source supports a relative judgement.
  Do NOT default every requirement to High; omit if there is no basis.

### What NOT to do
- Do NOT introduce business roles, capabilities, or rules not present in the source CCIs.
- Do NOT reproduce CCI description text verbatim — derive a normative statement.
- Do NOT state a workflow sequence; state a stateless business capability.
- Do NOT frame at enterprise/scope level (Row 1) or technical level (Row 3+).""",

    # Rows 3–6: short-phrase stubs pending per-row requirement-derivation validation
    # cycles. Each will be expanded to a full block (subject / atomicity / vocabulary /
    # type-reasoning / optional-field policy) after that row has run-time evidence —
    # same staged approach as the domain ROW_GUIDANCE.
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
