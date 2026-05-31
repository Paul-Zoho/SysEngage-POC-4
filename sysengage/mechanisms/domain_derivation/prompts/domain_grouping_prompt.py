"""
Domain grouping prompt template — used for FirstRun and FullRerun scenarios.

Per Domain Derivation Mechanism Spec v0.19 §4.2 and §5.4:
  Injects: row_ref, row_guidance, cci_set, cci_count.
  ROW_GUIDANCE is defined inline here per §5.4 — no separate vocabulary module.
  Multi-line guidance blocks (Row 1, Row 2) are injected verbatim as a prompt
  section. Single-phrase entries (Rows 3–6) are injected inline.

  Detection: if '\n' in guidance → verbatim block; else → inline phrase.
  This is future-proof — adding a structured block for any row requires only
  updating ROW_GUIDANCE; no template logic change needed.

LPM constraint: prompt instructs AI not to copy CCI descriptions verbatim.
Expected response format: {"proposals": [...]} per domain_grouping_response_schema.py.

v0.19 delta (from v0.18): ROW_GUIDANCE["2"] replaced from short phrase with
  structured principle-based guidance block (same format as Row 1).
  ROW_GUIDANCE["1"] updated to the canonical v0.19 structured form.
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

If the answer to any question is 'no', reconsider the boundary.

### Vocabulary signals
Row 2 domain names use business responsibility vocabulary:
  Appropriate: accountability, entitlement, stewardship, governance, settlement,
               participation, oversight, obligation, responsibility, record
  Avoid: calculate, process, store, retrieve, aggregate, compute, manage, track
         (these describe system functions — they belong at Row 3 or below)
  Also avoid: any word that implies a technical mechanism (API, schema, database,
              algorithm, service, endpoint)

### Stakeholder actors
Business actors (WHO-column CCIs) are rarely a standalone domain on their own —
they are actors *within* business responsibilities. Group the actor alongside the
CCIs that describe their primary business responsibility rather than isolating
them as a separate actor domain.

### Prohibition rules
- Do NOT create a domain containing only one CCI
- Do NOT isolate a stakeholder actor as a standalone domain
- Do NOT use workflow or function verbs in domain names
- Do NOT create domains whose boundaries cannot be explained to a business owner""",

    "3": "logical design level — logical structures, behaviours, interactions, and state models; technology-agnostic",
    "4": "physical builder level — specific technologies, components, deployment targets, and implementation patterns",
    "5": "detailed design level — algorithms, data formats, implementation specifications, and detailed configurations",
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
