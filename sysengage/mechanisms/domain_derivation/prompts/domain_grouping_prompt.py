"""
Domain grouping prompt template — used for FirstRun and FullRerun scenarios.

Per Domain Derivation Mechanism Spec v0.21 §4.2 and §5.4:
  Injects: row_ref, row_guidance, cci_set, cci_count.
  ROW_GUIDANCE is defined inline here per §5.4 — no separate vocabulary module.
  Multi-line guidance blocks (Rows 1–5) are injected verbatim as a prompt
  section. Single-phrase entry (Row 6) is injected inline.

  Detection: if '\n' in guidance → verbatim block; else → inline phrase.
  This is future-proof — adding a structured block for any row requires only
  updating ROW_GUIDANCE; no template logic change needed.

LPM constraint: prompt instructs AI not to copy CCI descriptions verbatim.
Expected response format: {"proposals": [...]} per domain_grouping_response_schema.py.

v0.21 delta (from v0.20): No prompt changes — ADVC-3c-01 inverted-range guard
  added in stage3_structural_validation.py only.
v0.20 delta (from v0.19): ROW_GUIDANCE["3"], ["4"], ["5"] each replaced from
  a short phrase with a structured principle-based guidance block (same template
  as Rows 1–2). Validated against PMT Row 3 (6 CCIs), Row 4 (1 CCI), Row 5
  (9 CCIs). Row 6 remains a short phrase pending its own validation cycle.
"""

from __future__ import annotations

ROW_GUIDANCE: dict[str, str] = {
    "1": """\
## Row 1 — Planner / Scope Layer

At this row you are working at the enterprise scope level — the view of a senior
executive or board member who needs to understand what the enterprise is committing
to and why, without reference to how any system works.

### What a Row 1 domain represents
A Row 1 domain is a bounded enterprise concern — a cluster of things the enterprise
must care about, be accountable for, or govern. It is NOT:
- An application feature or system function
- A process step or workflow
- A technical component or implementation partition
- A single CCI grouped alone for convenience

A Row 1 domain SHOULD be nameable to a non-technical executive without explanation.
If the name requires knowledge of how the system works, it is at the wrong level.

### Vocabulary signals
Row 1 domain names use nouns of enterprise concern:
  Appropriate: accountability, governance, participation, oversight, stewardship,
               obligation, entitlement, transparency, commitment, responsibility
  Avoid: calculate, display, track, manage, process, generate, store, retrieve
         (these describe system functions — they belong at Row 2 or below)

### Cross-column integration
Row 1 domains span multiple Zachman columns. An enterprise concern inherently
involves what is at stake (WHAT), why it matters (WHY), who is accountable (WHO),
how commitment is expressed (HOW), and when it applies (WHEN). A domain drawing
from only one Zachman column is likely too narrow — consider absorbing it into a
broader concern.

### What to look for in the CCI set
Group CCIs by the enterprise-level concern they express, not by the interrogative
that produced them or the feature they describe. Ask: if you stripped away all the
system-specific details, what is the enterprise fundamentally committing to?

Common enterprise-level concern themes that emerge at this level include:
- Who participates and what their relationship to the enterprise is
- What the enterprise is accountable for delivering or maintaining
- What governs or constrains behaviour across the enterprise
- What information the enterprise must retain and be answerable for

These are illustrative, not prescriptive — use the CCI content to discover what
concerns this specific enterprise actually has. Do not force CCIs into a theme if
the content does not support it.

### Prohibition rules
- Do NOT create a domain containing only one CCI
- Do NOT name a domain after a Zachman interrogative ("WHO Domain", "WHY Domain")
- Do NOT use feature-level or function-level names for domains
- Do NOT create overlapping domains where the same concern appears in two groups""",

    "2": """\
## Row 2 — Owner / Business Level

At this row you are working at the business-owner level — the view of someone who
understands what the enterprise is responsible for delivering and how it must behave,
but who is not concerned with how that responsibility is technically realised.

### What a Row 2 domain represents
A Row 2 domain is a bounded, persistent business responsibility. Three tests determine
whether a candidate is a genuine domain:
- **Bounded:** A single scope statement can be written for it without using 'and'.
  If 'and' is required, it is probably two domains.
- **Persistent:** The responsibility applies across the lifecycle — it is not a single
  activity or event.
- **Distinct failure mode:** When this responsibility fails, it fails differently from
  neighbouring responsibilities. If two candidates fail in the same way, they are
  probably one domain.

A Row 2 domain is NOT:
- A system function or algorithm ("Earnings Calculator", "Task Processor")
- A workflow step or process phase
- A technical component, API, schema, or database concept
- A single actor in isolation ("Child User Domain")
- A Zachman column heading ("HOW Domain", "WHO Domain")

### Row 2 Zachman column semantics
Row 2 CCIs express the following at each column:
- **WHAT**: Business artefacts — the things that exist and are exchanged in the
  business (entities, relationships, attributes). Not data models or schemas.
- **HOW**: Business capability declarations — what the business must be able to do,
  stated as stateless obligations. NOT step-by-step workflows or process sequences.
- **WHERE**: Business context and boundary — where the business operates, the scope
  of its reach.
- **WHO**: Business roles and accountabilities — who is responsible and accountable.
  Not interaction sequences or system actors.
- **WHEN**: Business lifecycle and triggers — what business events cause things to
  happen, what cycles govern operations. Not schedules or technical timers.
- **WHY**: Business governance rules and motivation — why things must be true, what
  constraints govern business behaviour, what the business is trying to achieve.

Group CCIs by the business responsibility they collectively express, drawing across
columns. A domain drawing from only one column is likely too narrow.

### Domain qualification questions
For each proposed domain, ask:
- Can a single scope statement be written for it?
- Does it persist across multiple business contexts and user roles?
- When this domain fails, does it fail differently from the others?
- Can it be explained to a business owner in one sentence without using 'and'?
- Could this responsibility evolve independently without forcing changes to neighbours?
- Does this domain align with a single business objective, or are multiple objectives
  being conflated? If multiple, it should be split.
- Are there overlapping domains that need to be consolidated or separated?

If the answer to any question is 'no', reconsider the boundary.

### Vocabulary signals
Row 2 domain names use business responsibility vocabulary:
  Appropriate: accountability, entitlement, stewardship, governance, settlement,
               participation, oversight, obligation, responsibility, record
  Avoid: calculate, process, store, retrieve, aggregate, compute, manage, track
         (these describe system functions — they belong at Row 3 or below)
  Also avoid: any word that implies a technical mechanism (API, schema, database,
              algorithm, service, endpoint)
  Also avoid: '&' and 'and' as connectors in domain names — a name requiring 'and'
              suggests two separate domains that should each have their own entry

### Stakeholder actors
Business actors (WHO-column CCIs) are rarely a standalone domain on their own —
they are actors *within* business responsibilities. Group the actor alongside the
CCIs that describe their primary business responsibility rather than isolating
them as a separate actor domain.

### Prohibition rules
- Do NOT create a domain containing only one CCI
- Do NOT isolate a stakeholder actor as a standalone domain
- Do NOT use workflow or function verbs in domain names
- Do NOT create domains whose boundaries cannot be explained to a business owner
- Do NOT use '&' or 'and' in domain names — if a name requires 'and', it is
  probably two domains that should be listed separately""",

    "3": """\
## Row 3 — Designer / Logical Level

At this row you are working at the logical design level — the view of a system
designer who is translating business obligations into logical structures, behaviours,
and rules, without committing to any specific technology or implementation.

### What a Row 3 domain represents
A Row 3 domain is a bounded logical design responsibility — a coherent cluster of
logical structures, behaviours, or constraints that must be designed together and
can be assessed for logical completeness independently. It IS NOT:
- A business capability (that belongs at Row 2)
- A physical technology component or platform (that belongs at Row 4)
- A code module, class, or implementation unit
- A deployment or runtime concern

A Row 3 domain should be describable to a technically-minded architect without
naming any specific technology. If the name requires knowing the implementation
platform, it is at the wrong level.

### Row 3 Zachman column semantics
- **WHAT**: Logical data structures — entities, relationships, attributes, and
  constraints expressed as a logical model (not physical tables or schemas)
- **HOW**: Logical processes and rules — how the system logically transforms,
  validates, or routes information; logical state transitions; NOT code or algorithms
- **WHERE**: Logical system boundary and interaction topology — how logical components
  relate and communicate; NOT physical deployment targets or infrastructure
- **WHO**: Logical actors and roles — the system's logical participants and their
  authorisation boundaries; NOT UI components or physical user interfaces
- **WHEN**: Logical event and state model — what conditions trigger logical state
  changes; NOT schedules, timers, or cron configurations
- **WHY**: Logical constraints and integrity rules — the design-level invariants the
  system must enforce; NOT business policies (Row 2) or code assertions (Row 5)

### Domain qualification questions
- Does this cluster of CCIs share a logical design boundary that can be assessed
  for completeness independently?
- Would a change to this logical design necessarily ripple through all CCIs in
  the cluster?
- Does this domain fail differently from neighbouring domains — in a way that a
  designer (not a business owner, not a developer) would recognise?
- Can the domain be described in one sentence without naming any technology?

### Vocabulary signals
Row 3 domain names use logical design vocabulary:
  Appropriate: logical model, logical structure, logical behaviour, state management,
               constraint enforcement, data model, interaction model, access model,
               visibility model, computation model, lifecycle
  Avoid: physical technology names (PostgreSQL, React, Redis, AWS, iOS), code
         patterns (class, function, module, endpoint), business policy language
         (obligation, stewardship, entitlement — those are Row 2)

### Cross-column integration
Row 3 domains should integrate logical structure (WHAT) with logical behaviour (HOW)
and logical constraints (WHY). A domain drawing from only HOW is likely a process
description, not a logical design responsibility. A domain drawing from only WHY is
likely a constraint definition that should be anchored to a structural or behavioural
domain.

### Sparse CCI sets at Row 3
Row 3 sometimes has few CCIs if the source document is operationally-framed. When
the CCI set is sparse (fewer than 8 CCIs), expect 2–3 domains. Do not force more
domains than the CCI content supports — a smaller number of richer domains is
preferable to many thin ones.

### Prohibition rules
- Do NOT create a domain containing only one CCI (unless cci_count_input == 1)
- Do NOT name a domain after a technology, platform, or framework
- Do NOT use business-obligation language (Row 2 vocabulary) in domain names
- Do NOT create domains that only describe a single Zachman column in isolation""",

    "4": """\
## Row 4 — Builder / Physical Level

At this row you are working at the physical builder level — the view of a builder
who is making concrete technology choices and specifying physical components,
without yet writing code or configuring runtime details.

### What a Row 4 domain represents
A Row 4 domain is a bounded physical construction responsibility — a coherent cluster
of physical technology choices, component specifications, or platform decisions that
must be built together. It IS NOT:
- A business responsibility (Row 2)
- A logical design concern (Row 3)
- A code-level implementation detail, configuration value, or runtime parameter (Row 5)

A Row 4 domain names a physical technology area that a builder would take
responsibility for constructing. The domain name can and should reference specific
technologies, platforms, or physical components.

### Row 4 Zachman column semantics
- **WHAT**: Physical data artefacts — physical schemas, storage formats, data
  structures as they will actually be built
- **HOW**: Physical processes and algorithms — the concrete mechanisms that realise
  logical behaviours; specific APIs, service contracts, integration patterns
- **WHERE**: Physical deployment targets — specific platforms, infrastructure nodes,
  hosting environments (e.g. iOS, Android, Windows, AWS region)
- **WHO**: Physical user interfaces and system interfaces — the concrete components
  through which actors interact with the system
- **WHEN**: Physical scheduling and triggering — specific timers, cron jobs, event
  queues, scheduling mechanisms
- **WHY**: Physical constraints — platform version requirements, hardware limits,
  compliance mandates expressed as build-level constraints

### Domain qualification questions
- Does this cluster of CCIs require the same physical technology or platform context?
- Would a builder owning this domain have a coherent, bounded construction scope?
- Does this domain fail differently from neighbouring domains — in the way a builder
  (not a designer, not a developer) would recognise?
- Can the domain be described in terms of physical artefacts without describing code?

### Vocabulary signals
Row 4 domain names use physical construction vocabulary:
  Appropriate: platform, component, infrastructure, deployment, interface,
               integration, physical schema, service, API, build, configuration
  Avoid: business-level language (Row 2), logical abstractions without physical
         specifics (Row 3), code-level implementation detail (Row 5)

### Sparse CCI sets at Row 4
Row 4 is often sparse for systems whose primary content is conceptual or logical.
A single-CCI row is legitimate — if only one physical constraint or component exists
in the source material, one domain is the correct outcome. Do not invent domains to
fill expected counts. The CHK-3c-07 single-CCI absorption rule does not fire when
cci_count_input == 1.

### Cross-column integration
Row 4 domains should reflect genuine physical construction boundaries. A deployment
platform domain (WHERE-heavy) is valid at Row 4 because physical platform concerns
are genuinely coherent at this level. A domain drawing from only WHY (a physical
constraint) is thinner but may be unavoidable when the source material contains
only a constraint at this row.

### Prohibition rules
- Do NOT create domains that describe business obligations (Row 2 vocabulary)
- Do NOT create domains that describe logical design without physical specifics
- Do NOT name a domain after a logical concept without its physical realisation""",

    "5": """\
## Row 5 — Implementer / Detailed Design Level

At this row you are working at the detailed design level — the view of an implementer
who is specifying the precise detail needed to build and configure the system:
algorithms, data formats, platform-specific configurations, interface contracts,
and detailed runtime behaviours.

### What a Row 5 domain represents
A Row 5 domain is a bounded detailed implementation responsibility — a coherent
cluster of detailed specifications that an implementer must produce together.
It IS NOT:
- A business responsibility (Row 2)
- A logical design concern (Row 3)
- A high-level physical construction decision (Row 4)

A Row 5 domain represents a coherent area of detailed specification — the things
an implementer needs to fully specify before a developer can write code without
making additional design decisions.

### Row 5 Zachman column semantics
- **WHAT**: Detailed data specifications — exact field definitions, data types,
  format constraints, validation rules, enumeration values
- **HOW**: Detailed algorithms and process specifications — step-by-step logic,
  precise transformation rules, error handling specifications
- **WHERE**: Detailed deployment specifications — exact platform versions, node
  configurations, network topology details, infrastructure parameters
- **WHO**: Detailed interface specifications — precise UI component definitions,
  interaction specifications, user interface configurations per actor
- **WHEN**: Detailed timing specifications — exact cycle durations, timeout values,
  scheduling parameters, event sequencing constraints
- **WHY**: Detailed constraint specifications — precise validation rules, platform
  version requirements expressed as implementable constraints

### Domain qualification questions
- Does this cluster of CCIs share a detailed specification boundary that an
  implementer would own together?
- Could an implementer produce a complete detailed specification for this domain
  without needing decisions from neighbouring domains?
- Does this domain fail differently from neighbouring domains — in a way that an
  implementer (not a designer, not a business owner) would recognise?

### Vocabulary signals
Row 5 domain names use detailed implementation vocabulary:
  Appropriate: interface, configuration, specification, deployment, platform-specific,
               detailed, implementation, cycle, timing, format, contract
  Avoid: business-level language (Row 2), logical abstractions (Row 3), generic
         high-level physical terms without specifics (Row 4)

### Column-sparse CCI sets at Row 5
Row 5 CCIs often cluster in specific columns depending on the source document's
focus. A Row 5 CCI set containing only WHERE and WHO CCIs (platform deployment
nodes and user interface actors) is legitimate — group them by their natural
implementation boundary. WHERE CCIs (deployment nodes) naturally form a deployment
infrastructure domain. WHO CCIs (UI actors) naturally form a user interface
specification domain. WHEN CCIs (timing cycles) may be absorbed into the domain
whose behaviour they govern.

For sparse CCI sets, prefer fewer, richer domains over many thin ones. A domain
containing 2–3 CCIs from complementary columns is preferable to isolated single-
column domains.

### Prohibition rules
- Do NOT create a domain containing only one CCI (unless cci_count_input == 1)
- Do NOT use business-level or logical-level vocabulary in domain names
- Do NOT create overlapping domains where the same specification concern appears twice
- Do NOT force more domains than the CCI content supports""",

    "6": "operational level — runtime procedures, user interactions, support processes, and operational behaviours",
}


def build_domain_grouping_prompt(
    *,
    row_ref: int,
    cci_set: list[dict],
    cci_count: int,
) -> str:
    """
    Build the primary domain grouping prompt (FirstRun / FullRerun).

    cci_set: list of dicts with keys ci_id, column, classification_type, description.
    Multi-line guidance blocks (currently Rows 1 and 2) are injected verbatim as a
    prompt section. Single-phrase entries (Rows 3–6) are injected inline.
    """
    row_key = str(row_ref)
    guidance = ROW_GUIDANCE.get(row_key, f"Row {row_ref} abstraction level")

    if "\n" in guidance:
        abstraction_block = guidance
    else:
        abstraction_block = f"Row {row_ref} operates at the {guidance}."

    cci_lines = "\n".join(
        f"  {i + 1}. ci_id={c['ci_id']} | column={c['column']} | type={c['classification_type']} | {c['description']}"
        for i, c in enumerate(cci_set)
    )
    return f"""You are a systems engineering analyst performing Domain Derivation for Row {row_ref} of a Zachman Framework analysis.

{abstraction_block}

Your task: group the following {cci_count} CellContentItems (CCIs) into meaningful Domains. Each Domain represents a coherent cluster of architectural concerns at this abstraction level.

CCIs to group:
{cci_lines}

Rules:
1. Every CCI MUST appear in at least one Domain (Non-Loss constraint — do not omit any ci_id).
2. A CCI may appear in more than one Domain if it is genuinely cross-cutting.
3. Domain names must be specific and architecturally meaningful (2–60 characters). Avoid "Miscellaneous", "Other", "General".
4. Do NOT copy CCI description text verbatim into Domain descriptions. Write original descriptions of the Domain's architectural responsibility.
5. Each Domain must reference at least one CCI.

Respond with a JSON object in this exact format:
{{
  "proposals": [
    {{
      "name": "Domain Name",
      "description": "Original description of this domain's architectural responsibility (minimum 10 characters).",
      "classification_type": "optional classification string or null",
      "cci_refs": ["CCI-ROW{row_ref}-C-Column-001", "..."]
    }}
  ]
}}

Return only valid JSON. No text before or after the JSON object."""
