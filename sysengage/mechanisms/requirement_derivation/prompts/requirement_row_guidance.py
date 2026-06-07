"""
Requirement Row Guidance — REQUIREMENT_ROW_GUIDANCE prompt constants.

Per Requirement Derivation Mechanism Spec v0.9 §5.4.

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

v0.9 rewrites the Row 2 subject block from the v0.3 two-class taxonomy (business /
named-role) to a FOUR-class taxonomy (actor/stakeholder, system-affordance, business,
named-business-role) chosen by the BOUNDARY TEST. Vocabulary block made subject-class-
aware; atomicity block gains the over-generation brake (complementary actor/system
pairs are NOT duplicates). CHK-3d-08 widened accordingly in stage3 (system-subject at
Row 2 no longer a mismatch; "the enterprise" at Row 2 is the out-of-set escape).
Fixes the false-merge cascade at root — the subject slot now discriminates.

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

### Domain entity vocabulary (REQUIRED — preserve the source's nouns)
Abstraction at Row 1 lives in the SUBJECT and the VERB (the enterprise commits to / is
accountable for / establishes) — NOT in renaming the things the enterprise commits to.
KEEP the domain-entity nouns the source uses. If the source says "task", write "task" —
NOT "work unit", "value-generating activity", or "strategic instrument". If the source
says "reward" / "pocket money", write that — NOT "monetary reward as a strategic value
exchange mechanism". Do NOT coin abstract paraphrases (instrument, mechanism, metric,
exchange) for concrete source entities.
  Right:  "The enterprise shall enable children to claim and complete tasks."
  Wrong:  "The enterprise shall establish work units as strategic instruments for value
           creation."
This is a DOMAIN-ENTITY rule, not literal echoing: still neutralise genuinely system- or
UI-level source nouns to their domain entity (source "claim button" / "screen" → the
domain entity "claim" / "task", not "button"). Preserve the DOMAIN nouns (task, reward,
child, earnings); drop only implementation/UI nouns.

The entity is the BARE source noun — not a qualified, compounded, or abstracted form. The
source names ONE entity ("task") and describes it in STATES ("available", "completed",
"claimed"); the entity is `task` and the states are ATTRIBUTES, not separate entities. Do
NOT coin "task opportunity", "completed achievement", "economic activity", or "household
economy" — those are the bare entity (`task`, `child`) dressed in a state or an
abstraction. One entity, one bare name; states and roles are attributes of it.
  Right:  "...children to claim available tasks ... and view completed tasks."   (entity: task)
  Wrong:  "...identify available task opportunities ... view completed achievements." (two coined entities)
Why this matters: a single entity must carry ONE name from enterprise scope down to
realisation. That consistent thread is what the Data Dictionary resolves and what
cross-row refinement matches on; a Row-1-only synonym ("work unit" for "task") OR a
state-qualified coinage ("task opportunity"/"completed achievement" for "task") breaks the
thread (Non-Loss failure) and fragments one entity into several Data Dictionary canonicals.

### requirement_type reasoning (principle-based — choose, do not pattern-match)
Weigh the source CCIs' Zachman columns and content against the row's abstraction level:
- Why-column / motivation / rule / policy / commitment content → lean Constraint.
- How / What / When / capability / function content → lean Functional.
- Content expressing a measurable threshold, rate, latency, or capacity → Constraint,
  verified by Measurement (the statement SHOULD carry fit_criteria — the threshold).
- Content expressing a quality attribute (usability, maintainability, portability) →
  Constraint (a bound on a quality dimension), verified by Inspection or Measurement.
- Content asserting what an entity is — its composition, attributes, or relationships →
  Structural.
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
  statement from it. "Derive" means re-cast the sentence into normative enterprise-
  commitment form; it does NOT mean renaming the domain entities — keep the source's
  domain nouns (see Domain entity vocabulary above).
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
Row 2 has FOUR legitimate statement subjects. Choose by the BOUNDARY TEST — do NOT
default to the business. The boundary test: does the party or function this CCI
describes cross the system boundary?

(a) ACTOR / STAKEHOLDER subject — an external party interacting WITH the system
    (reaching in to do something). Subject = the actor; verb = their real action:
      "A child can claim a completed task."
      "A parent can view their child's earnings."
    These are Who-column, boundary-crossing statements. They NAME the system boundary
    and are first-class. Do NOT re-express them as "the business shall enable the child
    to ..." — that buries the actor in the object and loses the boundary. Required
    wherever a CCI describes an actor interacting with the system (the Who column must
    be occupied — Cell Occupancy).

(b) SYSTEM subject — the capability the system PROVIDES at the boundary (the affordance
    meeting the actor), stated as WHAT the system provides, NOT how:
      "The system shall make completed tasks claimable by entitled children."
      "The system shall make a child's earnings visible to the parent."
    Legitimate at Row 2 as a BLACK-BOX affordance. Name the provided capability and NO
    realisation (no API/schema/database/service/endpoint/algorithm/validation rule —
    that is Row 3 HOW). "The system enables claimable tasks" = Row 2 (names the
    mechanism the system provides); "the system exposes a claim operation validating
    entitlement against the ledger" = Row 3 (names the realisation).

(c) BUSINESS subject — what the business does BEHIND the boundary: a responsibility,
    rule, or artefact it maintains:
      "The business shall maintain a record of each task claim."
      "The business shall enforce the weekly reset cycle."

(d) NAMED BUSINESS ROLE — a WHO-column CCI naming an accountable internal role that
    does NOT act through the system (off-boundary accountability):
      "The account holder shall approve ..."

The boundary test, applied:
  - Party acts THROUGH the system (reaches in)        → ACTOR subject (a)
  - System OFFERS the capability to that actor         → SYSTEM subject (b)
  - Function happens BEHIND the boundary (responsibility/rule/record)
                                                        → BUSINESS subject (c)
  - Accountable internal party, off-system             → NAMED BUSINESS ROLE (d)

Subject by Zachman column (illustration — the boundary test decides; this orients):
  Who (external party interacting)     → ACTOR         "a child can claim a task"
  Who (internal accountable party)     → BUSINESS ROLE "the account holder approves"
  How (capability offered to an actor) → SYSTEM        "the system makes tasks claimable"
  How (internal business process)      → BUSINESS      "the business settles compensation"
  What (artefact the business keeps)   → BUSINESS      "maintain a record of each claim"
  When (cycle / trigger)               → BUSINESS (or Condition slot) "enforce weekly reset"
  Why (rule / goal / constraint)       → BUSINESS (Constraint) "enforce approval threshold"

Do NOT use "The enterprise shall ..." — that is Row 1 (Planner) scope vocabulary.
The distinction from Row 1: Row 1 says what the enterprise commits to at scope level
("The enterprise shall recognise child users as participants"); Row 2 says who does
what at the business boundary and what the business is responsible for behind it
("A child can claim a completed task"; "The system shall make tasks claimable"; "The
business shall maintain a record of each claim").

### Normative form and atomicity
- Use the normative "shall" (or "can"/"may" for an ACTOR capability — "a child can claim…"). One obligation per statement.
- Apply the two-step "and" test: (1) is there a single obligation that subsumes both clauses? Use it. (2) If not, split into two requirements.
- OVER-GENERATION BRAKE: a single source concept can span columns (an actor-action, the system-affordance that enables it, and a business record). Author ONLY the column-aspects the source actually expresses — do NOT mechanically manufacture an actor + system + business statement for every concept. Where both an actor-action and its system-affordance ARE expressed, author both but treat them as a COMPLEMENTARY PAIR (the affordance enables the action — related, not two independent obligations, and NOT duplicates of each other). Never state one obligation twice under two different subjects.
- Row 2 statements are STATELESS obligations — a capability/responsibility, NOT a step-by-step sequence ("first X, then Y"). A statement describing an ordered workflow has dropped to Row 3+ and must be re-stated.

### Statement vocabulary
Vocabulary depends on the SUBJECT CLASS:
  ACTOR subject — the actor's real action verb: claim, approve, view, define, submit,
    request. Do NOT wrap it as "be enabled to" / "be able to be given" — name the action.
  SYSTEM subject — the provided capability (WHAT, never HOW): make available, make
    visible, make claimable, present, provide, enable (a capability).
  BUSINESS subject / role — business-responsibility vocabulary: maintain, record,
    govern, settle, approve, authorise, account for, be responsible / accountable for,
    steward, enforce (a business rule), recognise (a business role).
  Avoid at Row 2 (ALL subjects): calculate, process, store, retrieve, aggregate,
    compute, manage, track, retain / retention, generate, display — system-function /
    technical-storage vocabulary belonging to Row 3+ ("retain"/"retention" → "maintain
    a record").
  Avoid (ALL subjects) — the WHAT/HOW guard: any word implying a technical REALISATION
    mechanism — API, schema, database, service, endpoint, algorithm, validation rule.
    This is what keeps a SYSTEM-subject statement a Row 2 black-box affordance (WHAT the
    system provides) rather than a Row 3 design (HOW it provides it).

### requirement_type reasoning (principle-based — choose, do not pattern-match)
Weigh the source CCIs' Zachman columns and content against the business-owner level:
- WHY-column business governance rules / motivation / constraints on business behaviour
  → lean Constraint ("The business shall enforce the approval threshold ...").
- HOW-column business capability declarations / WHAT-column business artefacts the
  business must maintain / WHEN-column business triggers → lean Functional ("The
  business shall maintain a record of ...").
- Content expressing a measurable business threshold, rate, or service level →
  Constraint, verified by Measurement (the statement SHOULD carry fit_criteria).
- Content expressing a business quality attribute → Constraint (quality bound).
- Content asserting what a business entity is (composition/attributes/relationships) → Structural.
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
- Do NOT bury an interacting actor inside an object ("the business shall enable the child to claim …") — author the actor as subject (a). Burying it loses the boundary.
- Do NOT introduce actors, roles, capabilities, or rules not present in the source CCIs.
- Do NOT reproduce CCI description text verbatim — derive a normative statement.
- Do NOT state a workflow sequence; state a stateless capability / responsibility.
- Do NOT frame at enterprise/scope level (Row 1).
- Do NOT describe HOW the system realises a capability (Row 3 — operations, validation, structure); for a system subject, name only WHAT it provides at the boundary.""",

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
