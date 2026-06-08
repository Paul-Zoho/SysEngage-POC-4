"""
Requirement Derivation prompt template — FirstRun / FullRerun (per-Domain).

Per Requirement Derivation Mechanism Spec v0.2 §4.2 and §5.4.

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
  → `Structural`

These are reasoning signals to weigh against the CCI content and the row's
abstraction level — not a deterministic lookup. The enum value you choose is your
responsibility; it is enforced at the parse boundary."""


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

## Your task

Derive the canonical Requirements from the CCIs above. Each Requirement must:
1. Have a normative statement that expresses a single obligation at Row {row_ref} abstraction level.
2. Reference the ci_ids it is derived from (cci_refs). Every CCI SHOULD be covered by at least one Requirement.
3. Have a requirement_type assigned per the guidance above.
4. Have a confidence score between 0.0 and 1.0 reflecting your certainty.
5. Optionally include rationale, fit_criteria (REQUIRED if type=Measurement), verification_method, priority.

Do NOT include: requirement_id, row_target, domain_refs, or answer_refs — these are determined by the system.
Do NOT reproduce CCI description text verbatim in the statement.
Do NOT introduce obligations absent from the source CCIs.

Respond with a JSON array of Requirement proposals in this exact format:
[
  {{
    "statement": "The system shall ...",
    "requirement_type": "Functional",
    "cci_refs": ["{domain_cci_set[0]['ci_id'] if domain_cci_set else 'CCI-ROW' + str(row_ref) + '-C-X-001'}"],
    "rationale": "optional — why this requirement exists",
    "fit_criteria": "optional — REQUIRED if type=Measurement",
    "verification_method": "Test",
    "priority": "High",
    "confidence": 0.90
  }}
]

Return only a valid JSON array. No text before or after the array."""
