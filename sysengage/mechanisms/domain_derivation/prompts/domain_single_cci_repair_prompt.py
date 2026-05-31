"""
CHK-3c-07 single-CCI domain absorption repair prompt.

Per Domain Derivation Mechanism Spec v0.18 §4.3 (CHK-3c-07):
  Invoked when one or more Domain proposals contain exactly one CCI ref.
  Injects: isolated_ccis (from single-CCI proposals), available_domains
  (non-single-CCI proposals), row_guidance.

  Response: {"assignments": [...]} per domain_single_cci_repair_response_schema.py.
  Only assign actions — no new Domain creation.
  Every isolated ci_id must appear in exactly one assignment.

IMPORTANT: This prompt uses domain_name (not domain_id) to reference the
receiving Domain. Stage 3 resolves names by case-insensitive match against
the non-single-CCI proposals. See Mechanism Spec v0.18 §5.2.
Two retries on parse failure — persistent failure leaves single-CCI domains
in place (does NOT fail the run).
"""

from __future__ import annotations

from mechanisms.domain_derivation.prompts.domain_grouping_prompt import ROW_GUIDANCE


def build_single_cci_repair_prompt(
    *,
    isolated_ccis: list[dict],
    available_domains: list[dict],
    row_ref: int,
) -> str:
    """
    Build the CHK-3c-07 repair prompt.

    isolated_ccis: list of dicts with ci_id, column, classification_type, description
                   (the CCIs from all single-CCI proposals).
    available_domains: list of dicts with name, description, cci_count
                       (all non-single-CCI proposals).
    row_ref: integer row number (used to inject row_guidance).
    """
    row_guidance = ROW_GUIDANCE.get(str(row_ref), "")

    isolated_lines = "\n".join(
        f"  {i + 1}. ci_id={c['ci_id']} | column={c['column']}"
        f" | type={c['classification_type']} | {c['description']}"
        for i, c in enumerate(isolated_ccis)
    )
    domain_lines = "\n".join(
        f"  - \"{d['name']}\" ({d['cci_count']} CCIs): {d['description']}"
        for d in available_domains
    )
    isolated_count = len(isolated_ccis)

    guidance_block = (
        f"\n{row_guidance}\n" if row_guidance else ""
    )

    return f"""You are a systems engineering analyst performing Domain Derivation quality repair.
{guidance_block}
The grouping produced {isolated_count} Domain(s) with only a single CCI reference.
Per specification, a Domain SHALL NOT be a single-artefact container — each Domain
must represent a meaningful cluster of enterprise concerns.

Isolated CCI(s) (currently forming single-CCI Domains that must be absorbed):
{isolated_lines}

Available Domains (with ≥2 CCIs — absorption targets):
{domain_lines}

Your task: assign each isolated CCI to the most appropriate available Domain.

Rules:
1. Every isolated CCI MUST be assigned to exactly one available Domain.
2. Only "assign" actions are permitted — do NOT propose new Domains.
3. Use the exact Domain name as shown above (case-insensitive matching will be applied).
4. Choose the Domain whose existing CCIs are most conceptually related to the isolated CCI.
5. Provide a brief rationale for each assignment.

Respond with a JSON object in this exact format:
{{
  "assignments": [
    {{
      "ci_id": "CCI-ROW4-C-Where-001",
      "target_domain_name": "Exact Domain Name From List Above",
      "rationale": "Brief explanation of why this CCI fits this Domain."
    }}
  ]
}}

Return only valid JSON. No text before or after the JSON object."""
