"""
Requirement Derivation prompt template — IncrementalRerun (per-Domain).

Per Requirement Derivation Mechanism Spec v0.2 §4.2.

Used when the Domain-id set is unchanged and the new-CCI fraction is below
requirement_rerun_threshold (MD-3). One call per Domain owning ≥1 new CCI.

Injects: row_ref, domain, existing_requirements (id+statement+type summaries),
new_domain_ccis (CCIs not yet covered by any active Requirement),
REQUIREMENT_ROW_GUIDANCE[row] (§5.4 — DISTINCT from the domain ROW_GUIDANCE).

The AI proposes new Requirements covering the new CCIs only. It should NOT
modify or restate existing Requirements. cci_refs should reference only the
new CCIs; CHK-3d-03 strips any refs outside the Domain's new-CCI set and logs
advisory incremental_ref_outside_new_set.
"""

from __future__ import annotations

from mechanisms.requirement_derivation.prompts.requirement_derivation_prompt import (
    _REQUIREMENT_TYPE_GUIDANCE,
    _STATEMENT_FORMULATION_GUIDANCE,
)
from mechanisms.requirement_derivation.prompts.requirement_row_guidance import (
    REQUIREMENT_ROW_GUIDANCE,
)


def build_requirement_incremental_prompt(
    *,
    row_ref: int,
    domain: dict,
    existing_requirements: list[dict],
    new_domain_ccis: list[dict],
) -> str:
    """
    Build the IncrementalRerun prompt for one Domain with new uncovered CCIs.

    domain: dict with keys domain_id, name, description.
    existing_requirements: list of {requirement_id, statement, requirement_type}.
    new_domain_ccis: list of {ci_id, column, classification_type, description}.
    """
    row_key = str(row_ref)
    guidance = REQUIREMENT_ROW_GUIDANCE.get(row_key, f"Row {row_ref} abstraction level")
    if "\n" in guidance:
        abstraction_block = guidance
    else:
        abstraction_block = f"Row {row_ref} operates at the {guidance}."

    domain_id = domain["domain_id"]
    domain_name = domain["name"]
    domain_desc = domain["description"]

    existing_lines = "\n".join(
        f"  {r['requirement_id']} [{r['requirement_type']}]: {r['statement']}"
        for r in existing_requirements
    ) or "  (none)"

    new_cci_lines = "\n".join(
        f"  {i + 1}. ci_id={c['ci_id']} | column={c['column']} | "
        f"type={c['classification_type']} | {c['description']}"
        for i, c in enumerate(new_domain_ccis)
    )
    new_count = len(new_domain_ccis)

    return f"""You are a systems engineering analyst performing an Incremental Requirement Derivation update (Pass 3d) for Row {row_ref} of a Zachman Framework analysis.

{abstraction_block}

Domain: {domain_id} — "{domain_name}"
Description: {domain_desc}

Existing Requirements for this Domain (DO NOT modify or restate these):
{existing_lines}

New CCIs added to this Domain since the last derivation ({new_count} total):
{new_cci_lines}

---

{_STATEMENT_FORMULATION_GUIDANCE}

---

{_REQUIREMENT_TYPE_GUIDANCE}

---

## Your task

Derive new Requirements covering ONLY the new CCIs listed above. Do not reproduce, restate, or modify the existing Requirements.

Each new Requirement must:
1. Have a normative statement at Row {row_ref} abstraction level.
2. Reference only ci_ids from the new CCIs list above in cci_refs.
3. Have a requirement_type per the guidance.
4. Have a confidence score in [0.0, 1.0].
5. Optionally include rationale, fit_criteria (REQUIRED if type=Performance), verification_method, priority.

Do NOT include: requirement_id, row_target, domain_refs, answer_refs.
Do NOT reproduce CCI description text verbatim.

Respond with a JSON array of new Requirement proposals:
[
  {{
    "statement": "The system shall ...",
    "requirement_type": "Functional",
    "cci_refs": ["{new_domain_ccis[0]['ci_id'] if new_domain_ccis else 'CCI-ROW' + str(row_ref) + '-C-X-001'}"],
    "rationale": "optional",
    "fit_criteria": "optional — required if type=Performance",
    "verification_method": null,
    "priority": null,
    "confidence": 0.85
  }}
]

Return only a valid JSON array. No text before or after the array."""
