"""
Domain repair prompt template — used when CHK-3c-04 (Non-Loss) detects orphans.

Per Domain Derivation Mechanism Spec v0.13 §4.3:
  Invoked when the primary grouping omits one or more CCIs.
  Injects: orphaned_ccis, current_proposals.
  Response: {"actions": [...]} per domain_repair_response_schema.py.
  Actions: assign (domain_name matched case-insensitively) | new.

IMPORTANT: The assign action uses domain_name (not domain_id) because the AI
has only seen Domain names in the prompt context. Stage 3 resolves names to
proposals via case-insensitive match. See Mechanism Spec v0.13 §5.2.
One attempt only — no retry on repair prompt failure.
"""

from __future__ import annotations


def build_domain_repair_prompt(
    *,
    orphaned_ccis: list[dict],
    current_proposals: list[dict],
) -> str:
    """
    Build the repair prompt for orphaned CCIs.

    orphaned_ccis: list of dicts with ci_id, column, classification_type, description.
    current_proposals: list of dicts with name, description, cci_ref_count.
    """
    orphan_lines = "\n".join(
        f"  {i + 1}. ci_id={c['ci_id']} | column={c['column']} | type={c['classification_type']} | {c['description']}"
        for i, c in enumerate(orphaned_ccis)
    )
    proposal_lines = "\n".join(
        f"  - \"{p['name']}\" ({p['cci_ref_count']} CCIs): {p['description']}"
        for p in current_proposals
    )
    orphan_count = len(orphaned_ccis)
    return f"""You are a systems engineering analyst performing Domain Derivation repair.

The primary grouping call missed {orphan_count} CCI(s). These CCIs were not assigned to any Domain:

Orphaned CCIs:
{orphan_lines}

Current Domain proposals (already defined — use these names exactly when assigning):
{proposal_lines}

Your task: for each orphaned CCI, either assign it to one of the existing Domains or propose a new Domain.

Rules:
1. Every orphaned CCI MUST be handled.
2. Use action "assign" to add orphaned CCIs to an EXISTING Domain — use the exact Domain name as shown above.
3. Use action "new" to propose a new Domain if the orphaned CCIs do not fit any existing Domain.
4. Use the exact domain name from the list above for "assign" actions (case-insensitive matching will be applied).

Respond with a JSON object in this exact format:
{{
  "actions": [
    {{
      "action": "assign",
      "domain_name": "Exact Domain Name From List Above",
      "new_cci_refs": ["orphaned-ci-id-1"]
    }},
    {{
      "action": "new",
      "name": "New Domain Name",
      "description": "Original description (minimum 10 characters).",
      "classification_type": null,
      "cci_refs": ["orphaned-ci-id-2"]
    }}
  ]
}}

Return only valid JSON. No text before or after the JSON object."""
