"""
Domain grouping prompt template — used for FirstRun and FullRerun scenarios.

Per Domain Derivation Mechanism Spec v0.17 §4.2 and §5.4:
  Injects: row_ref, row_guidance, cci_set, cci_count.
  ROW_GUIDANCE is defined inline here per §5.4 — no separate vocabulary module.
  Row 1 uses a structured multi-paragraph guidance block (injected verbatim).
  Rows 2–6 retain short phrases pending their own validation cycles.

LPM constraint: prompt instructs AI not to copy CCI descriptions verbatim.
Expected response format: {"proposals": [...]} per domain_grouping_response_schema.py.
"""

from __future__ import annotations

ROW_GUIDANCE: dict[str, str] = {
    "1": """\
Row 1 — Enterprise Scope (Planner Layer)

At this level you are identifying the enterprise's strategic context: regulatory \
boundaries, mission commitments, high-level operational constraints, and the \
environmental forces that shape what the organisation does and does not do.

Vocabulary signals: regulation, compliance obligation, mandate, policy, \
stakeholder class, operating environment, boundary, constraint, strategic goal, \
contextual driver, enterprise boundary condition.

Domain groupings should reflect distinct areas of enterprise concern — for \
example, a Regulatory Compliance domain, an Operational Boundary domain, or a \
Strategic Mission domain. Do NOT decompose into business processes or technical \
components; those belong to lower rows.

Cross-column integration: a Row 1 domain may span multiple Zachman columns \
(What, How, Where, Who, When, Why) because strategic constraints cut across all \
views of the enterprise.

Prohibition: Do NOT produce domains named after technologies, systems, data \
stores, or software components. Those are Row 3–4 concerns.""",
    "2": "business conceptual level — business processes, entities, roles, events, and rules",
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
    Row 1 injects the full ROW_GUIDANCE block verbatim; Rows 2–6 use an inline phrase.
    """
    row_key = str(row_ref)
    guidance = ROW_GUIDANCE.get(row_key, f"Row {row_ref} abstraction level")

    if row_key == "1":
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
