"""
Requirement Row Guidance — REQUIREMENT_ROW_GUIDANCE prompt constants.

Per Requirement Derivation Mechanism Spec v0.6 §5.4.

DISTINCT from the domain ROW_GUIDANCE (which governs domain naming and grouping;
imported from domain_derivation/prompts/domain_grouping_prompt.py). This dict
governs requirement STATEMENT FORMULATION at the row-appropriate abstraction
level — subject vocabulary, verb choice, type-reasoning signals, and optional-
field policy.

v0.6 adds a shared interrogative slot-completeness preamble to all five row
blocks (§12.9 / §5.4). The preamble instructs the AI to derive requirements by
filling type-required slots through source-content interrogation (Functional:
Subject/Action/Object with Object-recursion to surface Structural requirements;
Constraint: Subject/Rule/Condition/Criteria; Structural: Entity/structural
assertion). It explicitly prohibits cross-row parent invention (Matching/GQA
responsibility, not Pass 3d's).

Rows 1–5 are fully authored. Rows 1–2 are validated (Row 1: PMT Run 5 / NQPS
Run 2; Row 2: PMT Row 2 Run 1 / NQPS Row 2 Run 1). Rows 3–5 are CANDIDATE
guidance — authored ahead of run evidence, NOT yet validated. Treat as pending
test until run evidence confirms each. Row 6 is a short-phrase stub.
"""

from __future__ import annotations

_SHARED_INTERROGATIVE_PREAMBLE = """\
### Interrogative slot-completeness (shared guidance — all rows)
Derive each requirement by interrogating the source CCIs slot-by-slot. For every proposal,
verify that the type-required slots are filled before finalising the statement:

**Functional** — Subject + Action (normative "shall" verb) + Object required.
  Interrogate: Who or what is the Subject of the obligation? What Action does it perform?
  What is the Object of that action? For every named Object entity, recurse: does it carry
  a structural obligation of its own (composition, membership, attribute, relationship)?
  If so, derive a dedicated Structural requirement for that Object. Object-recursion is
  the primary mechanism by which Structural requirements surface from Functional derivation.

**Constraint** — Subject + Rule required; Condition + Criteria when present in the source.
  Interrogate: Who or what is constrained? What is the normative restriction or governance
  rule (the Rule slot — "shall not …", "shall comply with …", "shall adhere to …")? Under
  what Condition does the constraint apply? Is there a measurable acceptance criterion
  (Criteria slot)? If so, populate fit_criteria and set verification_method = "Measurement".

**Structural** — Entity + structural assertion (composition / relationship / attribute) required.
  Interrogate: What entity is being structurally described? What does it contain, consist of,
  belong to, or how is it associated with another entity? Name the entity and the assertion
  explicitly in the statement.

Stay within this row's abstraction level. Do NOT invent parent-level requirements that would
belong at Row N-1. Cross-row elaboration (parent-child requirement linkage) is the
responsibility of the Requirement Matching service — not Pass 3d.
"""

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
- Content expressing a composition, membership, or structural relationship at enterprise
  scope (e.g. enterprise comprises divisions; enterprise participates in a legal structure)
  → Structural.
These are reasoning signals, not a lookup table. A genuinely ambiguous obligation may
read as either Constraint or Functional — choose the dominant force; do not force a
distribution.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: include only when the content gives a measurable acceptance basis.
- verification_method (Test/Analysis/Inspection/Demonstration/Measurement): include only
  when a natural method exists. An abstract enterprise constraint may have NO natural
  verification method at Row 1 — OMIT rather than guessing. Omission is correct.
- priority (High/Medium/Low): include only when the source content supports a relative
  priority judgement. Do NOT default every requirement to High. If the content gives no
  basis, omit.

""" + _SHARED_INTERROGATIVE_PREAMBLE + """
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
- WHAT-column business entity composition or relationship (e.g. business role membership,
  organisational structure, artefact composition) → Structural.
Reasoning signals, not a lookup table. Note: at Row 2 the Functional/Constraint balance
is typically more even than at Row 1 — business capability declarations (HOW-column) are
genuinely Functional, while business rules (WHY-column) are genuinely Constraint. Do not
carry a Row-1 lean into Row 2; judge each statement on its source columns.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: include only when the content gives a measurable acceptance basis (more
  common at Row 2 than Row 1 — business service levels and thresholds appear here).
- verification_method (Test/Analysis/Inspection/Demonstration/Measurement): include when
  a natural method exists for the business responsibility; omit when the content gives no
  basis.
- priority (High/Medium/Low): include only when the source supports a relative judgement.
  Do NOT default every requirement to High; omit if there is no basis.

""" + _SHARED_INTERROGATIVE_PREAMBLE + """
### What NOT to do
- Do NOT introduce business roles, capabilities, or rules not present in the source CCIs.
- Do NOT reproduce CCI description text verbatim — derive a normative statement.
- Do NOT state a workflow sequence; state a stateless business capability.
- Do NOT frame at enterprise/scope level (Row 1) or technical level (Row 3+).""",

    # Rows 3–5: AUTHORED AHEAD OF TEST (Mechanism Spec v0.4). Candidate guidance —
    # NOT yet validated against run evidence (Rows 1–2 were validate-then-author;
    # Rows 3–5 authored together to accelerate the remaining rows on the proven
    # pattern). Treat as pending test until run evidence confirms each.
    # Row 6 remains a short-phrase stub.
    "3": """\
## Row 3 — Designer / Logical Level — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the logical design level — the view of a
system designer translating business obligations into logical structures, behaviours,
and rules, WITHOUT committing to any specific technology or implementation. Each
requirement expresses a logical system capability or a logical integrity constraint —
technology-agnostic, but more concrete than a business responsibility.

### Statement subject (REQUIRED)
Row 3 requirement statements take THE SYSTEM as subject, expressed LOGICALLY:
  "The system shall ..."
This is the row where "The system shall …" becomes correct (it is wrong at Rows 1–2).
But the system is described LOGICALLY — what it must do or enforce as a logical design,
NOT how it is built. Do NOT name technologies, platforms, or code constructs (that is
Row 4+). Do NOT frame as a business responsibility ("The business shall…" is Row 2).
The distinction from Row 2: Row 2 says what the business must be able to do ("The
business shall maintain a record of completed tasks"); Row 3 says how the system
logically realises that ("The system shall maintain a logical association between each
task instance and its completion state").

### Normative form and atomicity
- Use the normative "shall". One logical capability or constraint per statement.
- Apply the two-step "and" test; split genuine compound obligations.
- A Row 3 statement may describe a logical state transition or rule, but NOT a
  step-by-step algorithm (that is Row 5). "The system shall transition a task to
  Claimed state when a child claims it" is logical; "the system shall iterate the task
  list and set status=1" is algorithmic (Row 5) and out of level.

### Statement vocabulary
Row 3 statements use logical-design vocabulary:
  Appropriate: logical structure, logical association, state, state transition,
               validate, enforce (an invariant), derive, logical constraint, access
               boundary, visibility, lifecycle, logical model, decision logic
  Avoid: physical technology names (PostgreSQL, React, Redis, AWS, iOS), code constructs
         (class, function, module, endpoint, table, schema), business-obligation language
         (Row 2: stewardship, entitlement, accountability), and algorithmic/output detail
         (Row 5: calculate, compute, format, report — prefer "derive" / "decision logic"
         / "visibility model").

### requirement_type reasoning (principle-based — choose, do not pattern-match)
- WHY-column logical integrity rules / design-level invariants → lean Constraint ("The
  system shall enforce that …").
- HOW-column logical processes / WHAT-column logical structures / WHEN-column logical
  state triggers → lean Functional ("The system shall maintain / validate / derive …").
- WHAT-column logical entity composition or structural relationship (e.g. a logical model
  entity that comprises or associates other entities) → Structural.
Reasoning signals, not a lookup. Judge each statement on its source columns; do not
carry a lean from another row.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: include when a logical acceptance basis exists (a state invariant can
  often be expressed as a checkable condition).
- verification_method: Analysis or Inspection are common at Row 3 (logical assessment);
  include when a natural method exists, omit otherwise.
- priority: include only when the source supports a relative judgement; do not default
  to High.

""" + _SHARED_INTERROGATIVE_PREAMBLE + """
### What NOT to do
- Do NOT name technologies, platforms, or code constructs (Row 4+).
- Do NOT frame as a business responsibility (Row 2) or describe a step-by-step algorithm (Row 5).
- Do NOT reproduce CCI description text verbatim — derive a normative statement.""",

    "4": """\
## Row 4 — Builder / Physical Level — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the physical builder level — the view of a
builder making concrete technology choices and specifying physical components, without
yet writing code or configuring runtime detail. Each requirement expresses a physical
construction obligation — a concrete technology, component, or platform decision.

### Statement subject (REQUIRED)
Row 4 statements take THE SYSTEM or a NAMED PHYSICAL COMPONENT as subject:
  "The system shall ..."           (default)
  "<Named component> shall ..."    (when a CCI identifies a specific physical component,
                                   e.g. "The mobile application shall ...")
Technology and platform names are APPROPRIATE here (unlike Row 3). The distinction from
Row 3: Row 3 says what the system must do logically; Row 4 says how it is physically
realised ("The system shall persist task records in a relational store", "The mobile
application shall run on iOS and Android").

### Normative form and atomicity
- Normative "shall"; one physical construction obligation per statement; apply the "and" test.
- Physical does not mean code-level — a Row 4 statement specifies the technology/component
  choice, not the algorithm or configuration value (those are Row 5).

### Statement vocabulary
Row 4 statements use physical-construction vocabulary:
  Appropriate: platform, component, infrastructure, deployment, interface, integration,
               physical schema, service, API, persist, host, named technologies (iOS,
               Android, relational store, REST, etc.)
  Avoid: business-level language (Row 2), purely logical abstractions with no physical
         specifics (Row 3), and code-level/configuration detail (Row 5: exact field
         types, timeout values, algorithm steps).

### requirement_type reasoning (principle-based — choose, do not pattern-match)
- WHY-column physical constraints (platform version requirements, hardware limits,
  build-level compliance mandates) → lean Constraint.
- HOW/WHAT/WHERE/WHO physical construction obligations (components, schemas, deployment
  targets, interfaces) → lean Functional.
- WHAT-column physical component composition or schema structure → Structural.
Judge each statement on its source columns.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: more frequently warranted at Row 4 (physical performance/capacity has
  measurable acceptance bases).
- verification_method: Test and Demonstration become common at Row 4 (physical artefacts
  are testable); include when a natural method exists.
- priority: include when the source supports it; do not default to High.

""" + _SHARED_INTERROGATIVE_PREAMBLE + """
### What NOT to do
- Do NOT frame as business (Row 2) or purely logical (Row 3) — name the physical realisation.
- Do NOT drop to code-level/configuration detail (Row 5).
- Do NOT reproduce CCI description text verbatim.

### Sparse rows
Row 4 is often sparse for conceptually-framed source material. If the row has zero CCIs
the mechanism takes the no_cci_input path (e.g. NQPS Row 4) — this guidance is not invoked.
A single physical constraint legitimately yields a single requirement.""",

    "5": """\
## Row 5 — Implementer / Detailed Design Level — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the detailed design level — the view of an
implementer specifying the precise detail needed before a developer writes code:
algorithms, data formats, platform-specific configuration, interface contracts, detailed
runtime behaviours. Each requirement expresses a detailed specification obligation.

### Statement subject (REQUIRED)
Row 5 statements take THE SYSTEM or a NAMED COMPONENT/INTERFACE as subject:
  "The system shall ..."
  "<Named component/interface> shall ..."
The distinction from Row 4: Row 4 chooses the technology ("persist in a relational
store"); Row 5 specifies the detail ("store the reward value as a decimal(10,2) field
with a non-negative constraint"). Row 5 is where exact formats, algorithms, and
configuration values are correct.

### Normative form and atomicity
- Normative "shall"; one detailed specification per statement; apply the "and" test.
- Row 5 statements may specify precise algorithmic steps, exact field definitions,
  exact timing values — the detail a developer needs without making further design
  decisions.

### Statement vocabulary
Row 5 statements use detailed-implementation vocabulary:
  Appropriate: exact field definitions, data types, format constraints, validation
               rules, enumeration values, algorithm steps, timeout values, cycle
               durations, interface contracts, configuration parameters, calculate,
               compute, format (these algorithmic/output verbs are CORRECT at Row 5)
  Avoid: business-level (Row 2) and high-level logical/physical framing without the
         precise detail (Rows 3–4). At Row 5 the detail is the point — a vague
         statement is out of level downward.

### requirement_type reasoning (principle-based — choose, do not pattern-match)
- WHY-column detailed constraints (precise validation rules, exact platform version
  requirements expressed as implementable constraints) → lean Constraint.
- HOW-column detailed algorithms / WHAT-column detailed data specifications / WHEN-column
  detailed timing → lean Functional.
- WHAT-column precise data structure definition or schema composition (field sets, type
  hierarchies) → Structural.
- Detailed performance specifications (exact latency/throughput targets with values) →
  include fit_criteria; verification_method = "Measurement" when a numeric threshold
  is the acceptance criterion.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: frequently warranted at Row 5 and often IS the specification (exact
  values, formats, thresholds).
- verification_method: Test is common at Row 5 (detailed specs are directly testable);
  Measurement when the criterion is a measurable numeric value.
- priority: include when the source supports it; do not default to High.

""" + _SHARED_INTERROGATIVE_PREAMBLE + """
### What NOT to do
- Do NOT frame at business/logical/physical-choice level without the implementable detail.
- Do NOT reproduce CCI description text verbatim — derive a normative specification.

### Column-sparse rows
Row 5 CCIs often cluster by column (deployment nodes, UI actors, timing cycles). Derive
requirements grouped by their natural implementation boundary; a sparse single-column
row legitimately yields few requirements.""",

    "6": (
        "Operational level — statements covering runtime procedures and user/operator "
        "interactions; subject is the system or the operator as the operational content "
        "dictates. [Short phrase — operational content is rare in the reference source "
        "documents; full block pending Row 6 requirement-derivation validation if/when "
        "operational CCIs appear.]"
    ),
}
