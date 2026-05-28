"""
Domain incremental prompt template — used for IncrementalRerun scenario.

Per Domain Derivation Mechanism Spec v0.13 §4.2:
  Injects: abstraction_level_phrase, existing_domains, new_ccis, new_cci_count.
  Response: {"actions": [...]} per domain_incremental_response_schema.py.
  Actions: assign (domain_id + new_cci_refs) | new (full domain proposal).

ROW_ABSTRACTION_PHRASES imported from domain_grouping_prompt.py since it is
defined there per spec §5.4 (single definition per module, not reduplicated).
"""

from __future__ import annotations

from mechanisms.domain_derivation.prompts.domain_grouping_prompt import (
    ROW_ABSTRACTION_PHRASES,
)


def build_domain_incremental_prompt(
    *,
    row_ref: int,
    existing_domains: list[dict],
    new_ccis: list[dict],
    new_cci_count: int,
) -> str:
    """
    Build the IncrementalRerun domain grouping prompt.

    existing_domains: list of dicts with domain_id, name, description, cci_ref_count.
    new_ccis: list of dicts with ci_id, column, classification_type, description.
    """
    phrase = ROW_ABSTRACTION_PHRASES.get(str(row_ref), f"Row {row_ref} abstraction level")
    domain_lines = "\n".join(
        f"  - domain_id={d['domain_id']} | name={d['name']} | {d['cci_ref_count']} CCIs | {d['description']}"
        for d in existing_domains
    )
    cci_lines = "\n".join(
        f"  {i + 1}. ci_id={c['ci_id']} | column={c['column']} | type={c['classification_type']} | {c['description']}"
        for i, c in enumerate(new_ccis)
    )
    return f"""You are a systems engineering analyst performing incremental Domain Derivation for Row {row_ref} of a Zachman Framework analysis.

Row {row_ref} operates at the {phrase}.

Existing Domains (already committed — do NOT modify these):
{domain_lines}

New CCIs that have not yet been assigned to any Domain ({new_cci_count} total):
{cci_lines}

Your task: for each new CCI, either assign it to an existing Domain or propose a new Domain.

Rules:
1. Every new CCI MUST be handled (assign to existing Domain or place in a new Domain).
2. Use action "assign" to add one or more new CCIs to an EXISTING Domain (specify domain_id exactly as shown above).
3. Use action "new" to propose a new Domain for CCIs that do not fit any existing Domain.
4. Do NOT propose changes to existing Domain definitions — only add membership.
5. domain_id must match exactly one of the existing domain_ids shown above.

Respond with a JSON object in this exact format:
{{
  "actions": [
    {{
      "action": "assign",
      "domain_id": "D001",
      "new_cci_refs": ["CCI-ROW{row_ref}-C-Column-001"]
    }},
    {{
      "action": "new",
      "name": "New Domain Name",
      "description": "Original description (minimum 10 characters).",
      "classification_type": null,
      "cci_refs": ["CCI-ROW{row_ref}-C-Column-002"]
    }}
  ]
}}

Return only valid JSON. No text before or after the JSON object."""
