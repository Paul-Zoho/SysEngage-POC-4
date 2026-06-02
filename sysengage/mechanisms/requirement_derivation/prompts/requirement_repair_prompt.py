"""
Requirement Derivation repair prompt template — CHK-3d-05 Non-Loss repair.

Per Requirement Derivation Mechanism Spec v0.2 §4.3.

Dispatched when orphaned CCIs remain after the primary derivation loop. Each
orphaned CCI belongs to an owning Domain (guaranteed by Pass 3c Non-Loss /
VER-3c-05). The AI derives a covering Requirement for each orphan, scoped within
its owning Domain. One repair call covers all orphaned CCIs in one pass.

Injects REQUIREMENT_ROW_GUIDANCE[row_ref] (§5.4 — DISTINCT from the domain
ROW_GUIDANCE) so repair statements observe the same subject and vocabulary
discipline as the primary derivation prompt.

No retry on parse failure. Persistent failure → orphaned_ccis recorded,
CompletedWithWarnings, Concern raised.
"""

from __future__ import annotations

from mechanisms.requirement_derivation.prompts.requirement_derivation_prompt import (
    _REQUIREMENT_TYPE_GUIDANCE,
    _STATEMENT_FORMULATION_GUIDANCE,
)
from mechanisms.requirement_derivation.prompts.requirement_row_guidance import (
    REQUIREMENT_ROW_GUIDANCE,
)


def build_requirement_repair_prompt(
    *,
    row_ref: int,
    orphaned_ccis: list[dict],
    requirement_type_guidance: str | None = None,
) -> str:
    """
    Build the CHK-3d-05 Non-Loss repair prompt.

    row_ref: current row number (used to inject REQUIREMENT_ROW_GUIDANCE).
    orphaned_ccis: list of dicts with keys:
      ci_id, column, classification_type, description,
      owning_domain_id, owning_domain_name.
    """
    row_key = str(row_ref)
    row_guidance = REQUIREMENT_ROW_GUIDANCE.get(row_key, f"Row {row_ref} abstraction level")
    if "\n" in row_guidance:
        abstraction_block = row_guidance
    else:
        abstraction_block = f"Row {row_ref} operates at the {row_guidance}."

    orphan_lines = "\n".join(
        f"  {i + 1}. ci_id={c['ci_id']} | domain={c['owning_domain_id']} "
        f"(\"{c['owning_domain_name']}\") | column={c['column']} | "
        f"type={c['classification_type']} | {c['description']}"
        for i, c in enumerate(orphaned_ccis)
    )
    count = len(orphaned_ccis)
    type_block = requirement_type_guidance or _REQUIREMENT_TYPE_GUIDANCE

    return f"""You are a systems engineering analyst performing a Non-Loss repair for Requirement Derivation (Pass 3d, CHK-3d-05).

{abstraction_block}

The following {count} CellContentItem(s) (CCIs) were not covered by any Requirement after the primary derivation pass. Each CCI must be covered by at least one Requirement (Non-Loss constraint).

Orphaned CCIs requiring coverage:
{orphan_lines}

---

{_STATEMENT_FORMULATION_GUIDANCE}

---

{type_block}

---

## Your task

Derive covering Requirements for the orphaned CCIs above. For each orphaned CCI:
1. Produce a normative Requirement that covers the CCI.
2. Include the CCI's ci_id in cci_refs. You may group multiple orphaned CCIs from the
   SAME owning Domain into one Requirement if they express a single unified obligation.
   Do NOT group CCIs from different Domains into one Requirement.
3. Assign requirement_type per the guidance.
4. Provide confidence in [0.0, 1.0].
5. Optionally include rationale, fit_criteria (REQUIRED if type=Performance),
   verification_method, priority.

Do NOT include: requirement_id, row_target, domain_refs, answer_refs.
Do NOT reproduce CCI description text verbatim.
Do NOT introduce obligations absent from the source CCIs.

Respond with a JSON array of covering Requirement proposals:
[
  {{
    "statement": "The system shall ...",
    "requirement_type": "Functional",
    "cci_refs": ["{orphaned_ccis[0]['ci_id'] if orphaned_ccis else 'CCI-ROW-X'}"],
    "rationale": "optional",
    "fit_criteria": "optional — required if type=Performance",
    "verification_method": null,
    "priority": null,
    "confidence": 0.80
  }}
]

Return only a valid JSON array. No text before or after the array."""
