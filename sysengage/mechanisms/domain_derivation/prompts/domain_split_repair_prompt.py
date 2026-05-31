"""
CHK-3c-08 split repair prompt template.

Per Domain Derivation Mechanism Spec v0.22 §4.3 (CHK-3c-08):
  Issues when any Domain has len(cci_refs) > floor(eligible_count / 2).
  Asks the AI to split the over-concentrated domain into 2+ sub-domains such
  that every original ci_id appears in exactly one sub-domain.

Parameters:
  concentrated_domains: list of {name, description, cci_refs} — over-concentrated proposals
  other_domains: list of {name, description, cci_count} — non-concentrated for context
  row_guidance: ROW_GUIDANCE[str(row_ref)] block injected verbatim
  concentration_threshold: int — floor(eligible_count/2)
"""

from __future__ import annotations

import json


def build_split_repair_prompt(
    *,
    concentrated_domains: list[dict],
    other_domains: list[dict],
    row_guidance: str,
    concentration_threshold: int,
) -> str:
    """
    Build the CHK-3c-08 split repair prompt.

    concentrated_domains: dicts with keys name, description, cci_refs.
    other_domains: dicts with keys name, description, cci_count.
    """
    concentrated_block = json.dumps(concentrated_domains, indent=2)
    other_block = json.dumps(
        [
            {
                "name": d["name"],
                "description": d["description"],
                "cci_count": d["cci_count"],
            }
            for d in other_domains
        ],
        indent=2,
    )

    if "\n" in row_guidance:
        guidance_section = row_guidance
    else:
        guidance_section = f"This row operates at the {row_guidance}."

    return f"""You are a systems engineering analyst reviewing Domain Derivation results.

{guidance_section}

An over-concentrated domain has been detected: one or more proposed domains contain more \
than {concentration_threshold} CCIs, which exceeds half the total CCI count for this row. \
Such a domain is likely conflating multiple distinct responsibilities and should be split.

Over-concentrated domain(s) requiring a split:
{concentrated_block}

Existing domains retained as-is (for context only — do NOT modify these):
{other_block}

Your task: split each over-concentrated domain into 2 or more smaller sub-domains.

Rules:
1. Every ci_id from the original domain MUST appear in exactly ONE sub-domain \
(Non-Loss constraint — do not omit any ci_id, do not duplicate any ci_id).
2. Each sub-domain MUST contain at least 2 CCIs — do NOT create single-CCI sub-domains.
3. Sub-domain names must NOT use '&' or 'and' — if a name requires 'and', it describes \
two separate domains that should each have their own entry.
4. Sub-domain names must be specific and architecturally meaningful (2–60 characters). \
Avoid "Miscellaneous", "Other", "General".
5. Each sub-domain description must be an original description of the sub-domain's \
responsibility — do NOT copy CCI description text verbatim.
6. You MUST produce at least 2 sub-domain proposals for each over-concentrated domain.

Respond with a JSON object in this exact format:
{{
  "proposals": [
    {{
      "name": "Sub-domain Name",
      "description": "Original description of this sub-domain's architectural responsibility.",
      "cci_refs": ["ci_id_1", "ci_id_2"],
      "rationale": "Why these CCIs form a coherent, bounded sub-domain."
    }}
  ]
}}

Return only valid JSON. No text before or after the JSON object."""
