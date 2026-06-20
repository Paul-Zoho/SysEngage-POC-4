"""
Requirement Derivation prompt template — FirstRun / FullRerun (per-Domain).

Per Requirement Derivation Mechanism Spec v0.33 §4.2 and §5.4.

One call per active Domain in Stage 2. Injects:
  row_ref, domain (domain_id, name, description), domain_cci_set,
  REQUIREMENT_ROW_GUIDANCE[row] (§5.4 — DISTINCT from the domain ROW_GUIDANCE),
  statement formulation discipline, requirement_type reasoning signals.

§5.4 guidance blocks:
  (a) REQUIREMENT_ROW_GUIDANCE[row] — row-specific subject, vocabulary, type-reasoning
      signals, and optional-field policy (Row 1 fully authored; Rows 2–6 stubs).
      Also carries the shared interrogative-completeness preamble (ADVC-3d-02) and
      shared concern-atomicity + non-redundancy block (ADVC-3d-03, v0.12).
  (b) Statement formulation discipline — atomic, single intent, normative phrasing,
      no inferred content; "and" compound test.
  (c) requirement_type reasoning signals — Why→Constraint, How/What/When→Functional,
      measurable threshold→Measurement (fit_criteria REQUIRED), quality attribute→Constraint.

F105 (v0.33): Structural proposals at rows 2–5 SHOULD include a class_model dict
  that models the entity (attributes, relationships, refinement_kind). When class_model
  is supplied, statement may be omitted (null) — the system projects a prose statement.

F107 (v0.33): Functional and Constraint proposals MAY include object_refs — a list
  of candidate object-reference paths in the form "EntityName.attr_name[.value]".
  These are materialised against the Structural class_models in Stage 4.

LPM constraint: AI instructed not to reproduce CCI description text verbatim.
Expected response format: JSON array of RequirementProposal objects.
"""

from __future__ import annotations

from mechanisms.requirement_derivation.prompts.requirement_row_guidance import (
    REQUIREMENT_ROW_GUIDANCE,
)

_STATEMENT_FORMULATION_GUIDANCE = """\
## Requirement Statement Formulation Discipline (§5.4a)

Each requirement statement MUST be:
- **Atomic**: expresses exactly one obligation. If the statement requires "and" to
  express two distinct obligations, split it into two Requirements.
  Apply the same two-step test as Domain naming:
  (1) Is there a single unifying obligation that subsumes both? If yes, express it.
  (2) If no single obligation exists, create two Requirements instead.
- **Single intent**: one subject, one predicate, one constraint.
- **Normative**: phrased as "The system shall …" or "X shall …" at the row-appropriate
  subject level. Avoid descriptive phrasing ("The system provides …", "There is …").
- **No inferred content**: the statement introduces NO actors, behaviours, or constraints
  that are absent from the source CCIs. Do not extrapolate beyond the CCI evidence.
- **Not verbatim**: do NOT reproduce CCI description text word-for-word. Express the
  obligation in your own normative form."""

_REQUIREMENT_TYPE_GUIDANCE = """\
## Requirement Type Classification Guidance (§5.4b)

Choose `requirement_type` by reasoning about the source CCIs' Zachman column and content:

- **Why-column CCIs** (motivation, rules, policy, governance constraints)
  → lean toward `Constraint`
- **How-column / What-column / When-column CCIs** (function, entity behaviour, event
  processing, lifecycle transitions, capability declarations)
  → lean toward `Functional`
- **CCIs expressing a measurable threshold, rate, latency, capacity, or SLA**
  → `Measurement` — the statement MUST carry `fit_criteria` with the specific
  measurable criterion; set verification_method = "Measurement"
- **CCIs expressing a quality attribute** (usability, maintainability, portability,
  reliability, accessibility) → `Constraint` (a quality bound); verification_method
  Inspection or Measurement as appropriate
- **CCIs asserting entity composition, attributes, or structural relationships**
  → `Structural` — prefer a `class_model` dict (see F105 below)

These are reasoning signals to weigh against the CCI content and the row's
abstraction level — not a deterministic lookup. The enum value you choose is your
responsibility; it is enforced at the parse boundary."""

_CLASS_MODEL_GUIDANCE_COMMON_TAIL = """\

**refinement_kind** options:
- `identity` — the entity carries the same concept as the row N-1 version with added detail
- `decompose` — this entity is one structural part of a row N-1 entity
- `realise_relationship` — this entity realises a relationship between two row N-1 entities
- `introduce` — an entirely new entity introduced at this tier (no parent at row N-1)
- `merge` — two or more row N-1 entities merge into this one at row N

**origin** on each attribute:
- `refines` — the attribute exists in the parent entity at row N-1
- `realises` — the attribute realises a relationship from row N-1
- `introduced` — new at this tier, no parent attribute"""


def _build_class_model_guidance(row_ref: int) -> str:
    """
    Return the F105 class_model guidance block scoped to the given row.

    P1 (Row 1): no class_model — CHK-3d-11 hard-rejects any class_model here.
    P2 (Row 2): restricted attribute profile — name/semantic_type/origin/description only.
    Row 3: adds logical type/key/domain/target_ref (physical types rejected by CHK-3d-11).
    Row 4+: all attribute fields permitted.
    """
    if row_ref == 1:
        return """\
## F105 — class_model for Structural Requirements (rows 2–5)

**P1 — YOU ARE AT ROW 1 (Scope/Planner level). DO NOT include `class_model`.**

Row 1 Structural requirements express enterprise-scope obligations in prose only.
`class_model` structural modelling begins at Row 2.  Any `class_model` on a Row 1
proposal will be HARD-rejected by CHK-3d-11 (`tier1_class_model`) and the entire
proposal will be excluded from production.  Do not author class_model at Row 1."""

    if row_ref == 2:
        # f-string: {{ → literal {, }} → literal }, {{field}} → literal {field}
        return f"""\
## F105 — class_model for Structural Requirements (rows 2–5)

When `requirement_type` is `Structural`, you SHOULD provide a `class_model` dict.
When class_model is provided, `statement` is optional — the system will project prose.

**P2 — YOU ARE AT ROW 2 (Conceptual/Owner level). RESTRICTED ATTRIBUTE PROFILE.**
Row 2 models the CONCEPTUAL data shape only. Each attribute MUST include ONLY:
  • `name`          — snake_case attribute name DERIVED from the statement
                      (e.g. "monetary_value", "availability_status", "completion_date").
                      NEVER use "attr_name" literally; NEVER leave it null.
  • `semantic_type` — a semantic CATEGORY noun such as "money", "identifier",
                      "lifecycle_state", "name", "date", "quantity", "code",
                      "reference", "flag", "amount", "label".
                      Do NOT use POS tags ("Noun", "Verb", "Qualifier") — wrong.
  • `origin`        — refines | realises | introduced
  • `description`   — one-line description

Do NOT set `type`, `key`, `domain`, or `target_ref` on Row 2 attributes.
Those fields belong at Row 4 (physical/builder level).
CHK-3d-11 HARD-rejects Row 2 attributes that carry `key`, `domain`, or `target_ref`
(`profile_violation_row2:{{field}}`) — the entire proposal is excluded.

Row 2 class_model schema:
```json
{{
  "entity": "CanonicalEntityName",
  "tier": 2,
  "refinement_kind": "identity|decompose|realise_relationship|introduce|merge",
  "attributes": [
    {{
      "name": "monetary_value",
      "semantic_type": "money",
      "origin": "introduced",
      "description": "Monetary value associated with the task"
    }}
  ],
  "relationships": [
    {{
      "kind": "association|aggregation|composition|dependency",
      "target": "TargetEntityName",
      "cardinality": "one-to-many|many-to-many|one-to-one"
    }}
  ]
}}
```
""" + _CLASS_MODEL_GUIDANCE_COMMON_TAIL + """

Constraints (enforced by CHK-3d-11):
- tier MUST be 2
- refinement_kind MUST be one of the five values above
- At least one attribute is required; ≥1 attribute must have semantic_type set
- Row 2 attributes: ONLY name/semantic_type/origin/description (P2 — see above)"""

    if row_ref == 3:
        # f-string: {{ → literal {, }} → literal }
        return f"""\
## F105 — class_model for Structural Requirements (rows 2–5)

When `requirement_type` is `Structural`, you SHOULD provide a `class_model` dict.
When class_model is provided, `statement` is optional — the system will project prose.

**Row 3 (Logical/Designer level) attribute profile.**
Row 3 adds `type` (LOGICAL types only — see enum), `key`, `domain`, `target_ref`.
Physical DB types such as VARCHAR(255) or BIGINT are NOT permitted at Row 3 —
CHK-3d-11 HARD-rejects them (`profile_violation_row3:type_not_logical`).

**`name` field**: use a referenceable snake_case noun derived from the concept
(e.g. "availability_status", "monetary_value", "completion_date", "task_ref").
NEVER copy the placeholder literally. NEVER leave `name` null or empty.

Logical `type` closed enum: String | Integer | DateTime | Boolean | Decimal | Enum | Reference | JSON

Row 3 class_model schema:
```json
{{
  "entity": "CanonicalEntityName",
  "tier": 3,
  "refinement_kind": "identity|decompose|realise_relationship|introduce|merge",
  "attributes": [
    {{
      "name": "availability_status",
      "type": "String|Integer|DateTime|Boolean|Decimal|Enum|Reference|JSON",
      "key": "PK|FK|null",
      "semantic_type": "identifier|lifecycle_state|quantity|money|name|date|...",
      "origin": "refines|realises|introduced",
      "domain": ["allowed_value_1", "allowed_value_2"],
      "target_ref": "ForeignEntityName"
    }}
  ],
  "relationships": [
    {{
      "kind": "association|aggregation|composition|dependency",
      "target": "TargetEntityName",
      "cardinality": "one-to-many|many-to-many|one-to-one"
    }}
  ]
}}
```
""" + _CLASS_MODEL_GUIDANCE_COMMON_TAIL + """

Constraints (enforced by CHK-3d-11):
- tier MUST be 3
- refinement_kind MUST be one of the five values above
- At least one attribute is required
- type MUST be from the closed logical enum (no physical types)
- FK attributes must have a non-empty target_ref"""

    # Row 4+ — full physical schema
    # f-string: {{ → literal {, }} → literal }, {row_ref} → substituted
    return f"""\
## F105 — class_model for Structural Requirements (rows 2–5)

When `requirement_type` is `Structural`, you SHOULD provide a `class_model` dict.
When class_model is provided, `statement` is optional — the system will project prose.

**`name` field**: use a referenceable snake_case noun derived from the concept
(e.g. "availability_status", "monetary_value", "completion_date", "task_ref").
NEVER copy the placeholder literally. NEVER leave `name` null or empty.

class_model schema:
```json
{{
  "entity": "CanonicalEntityName",
  "tier": {row_ref},
  "refinement_kind": "identity|decompose|realise_relationship|introduce|merge",
  "attributes": [
    {{
      "name": "availability_status",
      "type": "String|Integer|DateTime|Boolean|Decimal|Enum|Reference|JSON",
      "key": "PK|FK|null",
      "semantic_type": "identifier|lifecycle_state|quantity|money|name|date|...",
      "origin": "refines|realises|introduced",
      "domain": ["allowed_value_1", "allowed_value_2"],
      "target_ref": "ForeignEntityName"
    }}
  ],
  "relationships": [
    {{
      "kind": "association|aggregation|composition|dependency",
      "target": "TargetEntityName",
      "cardinality": "one-to-many|many-to-many|one-to-one"
    }}
  ]
}}
```
""" + _CLASS_MODEL_GUIDANCE_COMMON_TAIL + f"""

Constraints (enforced by CHK-3d-11):
- tier MUST equal {row_ref}
- refinement_kind MUST be one of the five values above
- At least one attribute is required
- FK attributes must have a non-empty target_ref"""

_OBJECT_REFS_GUIDANCE = """\
## F107 — object_refs for Functional and Constraint Requirements

Functional and Constraint proposals MAY include `object_refs`: a list of paths that
reference specific structural objects the requirement operates on. Format:

    "EntityName.attr_name"           — references an attribute
    "EntityName.attr_name.value"     — references a specific allowed value

These are resolved in Stage 4 against the Structural class_models produced in the same
row. Include only paths you can justify from the CCI evidence. Omit `object_refs` or
leave it null when no structural object references are evident.

Example:
```json
"object_refs": ["Payment.status.pending", "Order.total"]
```"""


def build_requirement_derivation_prompt(
    *,
    row_ref: int,
    domain: dict,
    domain_cci_set: list[dict],
) -> str:
    """
    Build the primary Requirement Derivation prompt for one Domain (FirstRun / FullRerun).

    domain: dict with keys domain_id, name, description.
    domain_cci_set: list of dicts with keys ci_id, column, classification_type, description.
    """
    row_key = str(row_ref)
    guidance = REQUIREMENT_ROW_GUIDANCE.get(row_key, f"Row {row_ref} abstraction level")
    if "\n" in guidance:
        abstraction_block = guidance
    else:
        abstraction_block = f"Row {row_ref} operates at the {guidance}."

    cci_lines = "\n".join(
        f"  {i + 1}. ci_id={c['ci_id']} | column={c['column']} | "
        f"type={c['classification_type']} | {c['description']}"
        for i, c in enumerate(domain_cci_set)
    )
    domain_id = domain["domain_id"]
    domain_name = domain["name"]
    domain_desc = domain["description"]
    cci_count = len(domain_cci_set)
    example_ci_id = domain_cci_set[0]["ci_id"] if domain_cci_set else f"CCI-R{row_ref}-C-X-001"

    structural_clause = (
        " For Structural requirements (rows 2–5), prefer providing a class_model dict "
        "(see F105 above). statement may be omitted when class_model is provided."
    )

    return f"""You are a systems engineering analyst performing Requirement Derivation (Pass 3d) for Row {row_ref} of a Zachman Framework analysis.

{abstraction_block}

You are deriving Requirements for a single Domain. The Domain groups related CellContentItems (CCIs) at this abstraction level.

Domain: {domain_id} — "{domain_name}"
Description: {domain_desc}

CCIs in this Domain ({cci_count} total):
{cci_lines}

---

{_STATEMENT_FORMULATION_GUIDANCE}

---

{_REQUIREMENT_TYPE_GUIDANCE}

---

{_build_class_model_guidance(row_ref)}

---

{_OBJECT_REFS_GUIDANCE}

---

## Your task

Derive the canonical Requirements from the CCIs above. Each Requirement must:
1. Have a normative statement that expresses a single obligation at Row {row_ref} abstraction level.{structural_clause}
2. Reference the ci_ids it is derived from (cci_refs). Every CCI SHOULD be covered by at least one Requirement.
3. Have a requirement_type assigned per the guidance above.
4. Have a confidence score between 0.0 and 1.0 reflecting your certainty.
5. Optionally include rationale, fit_criteria (REQUIRED if type=Measurement), verification_method, priority.

Do NOT include: requirement_id, row_target, domain_refs, or answer_refs — these are determined by the system.
Do NOT reproduce CCI description text verbatim in the statement.
Do NOT introduce obligations absent from the source CCIs.

Respond with a JSON array of Requirement proposals. Example format (one Structural with class_model, one Functional with object_refs):
[
  {{
    "statement": null,
    "requirement_type": "Structural",
    "cci_refs": ["{example_ci_id}"],
    "class_model": {{
      "entity": "ExampleEntity",
      "tier": {row_ref},
      "refinement_kind": "identity",
      "attributes": [
        {{"name": "id", "type": "Integer", "key": "PK", "semantic_type": "identifier", "origin": "refines", "domain": null, "target_ref": null}},
        {{"name": "status", "type": "Enum", "key": null, "semantic_type": "lifecycle_state", "origin": "introduced", "domain": ["active", "inactive"], "target_ref": null}}
      ],
      "relationships": []
    }},
    "rationale": "optional — why this entity exists at this tier",
    "confidence": 0.90
  }},
  {{
    "statement": "The system shall ...",
    "requirement_type": "Functional",
    "cci_refs": ["{example_ci_id}"],
    "object_refs": ["ExampleEntity.status.active"],
    "rationale": "optional",
    "fit_criteria": null,
    "verification_method": "Test",
    "priority": "High",
    "confidence": 0.85
  }}
]

Return only a valid JSON array. No text before or after the array."""
