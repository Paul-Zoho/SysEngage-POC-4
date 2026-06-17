"""
prompts/requirement_conjoined_decompose_prompt.py

In-place decompose repair prompt for CHK-3d-09 conjoined-predicate hard violations (F98).

Per Requirement Derivation Mechanism Spec v0.24 §4.3:

  When CHK-3d-09 detects a conjoined-predicate hard violation (two distinct finite
  verb phrases joined by 'and'/'or' under one 'shall'), the repair is NOT the
  orphan-pool / CHK-3d-05 re-derive path (which risks dropping one half). Instead,
  the flagged compound statement is decomposed in-place: the AI re-expresses it as
  N atomic statements, each carrying a single obligation. Any inter-half dependency
  is expressed as a Condition slot on the dependent statement.

  One call per flagged compound proposal (not batched across proposals).
  The response schema is RepairRequirementProposal (same field shape as the repair
  schema — distinct class, shared shape).
"""

from __future__ import annotations

from mechanisms.requirement_derivation.prompts.requirement_derivation_prompt import (
    _REQUIREMENT_TYPE_GUIDANCE,
)
from mechanisms.requirement_derivation.prompts.requirement_row_guidance import (
    REQUIREMENT_ROW_GUIDANCE,
)


def build_conjoined_decompose_prompt(
    *,
    row_ref: int,
    compound_statement: str,
    requirement_type: str,
    cci_refs: list[str],
    rationale: str | None = None,
    fit_criteria: str | None = None,
    verification_method: str | None = None,
    priority: str | None = None,
    confidence: float = 0.80,
) -> str:
    """
    Build the CHK-3d-09 conjoined-predicate in-place decompose prompt.

    row_ref:            current row number.
    compound_statement: the flagged compound statement containing two conjoined
                        verb phrases under one 'shall'.
    requirement_type:   'Functional' | 'Constraint' | 'Structural'
    cci_refs:           the original proposal's cci_refs (AI distributes across
                        atomic children or duplicates as appropriate).
    """
    row_key = str(row_ref)
    row_guidance = REQUIREMENT_ROW_GUIDANCE.get(row_key, f"Row {row_ref} abstraction level")
    if "\n" in row_guidance:
        abstraction_block = row_guidance
    else:
        abstraction_block = f"Row {row_ref} operates at the {row_guidance}."

    rationale_line = f'  rationale:    "{rationale}"' if rationale else "  rationale:    (from original, if applicable)"
    fit_crit_line = f'  fit_criteria: "{fit_criteria}"' if fit_criteria else ""
    vm_line = f'  verification_method: "{verification_method}"' if verification_method else ""
    priority_line = f'  priority: "{priority}"' if priority else ""
    original_cci_list = ", ".join(f'"{c}"' for c in cci_refs)

    return f"""You are a systems engineering analyst performing a CHK-3d-09 atomicity repair (F98 — conjoined-predicate decomposition).

{abstraction_block}

## Problem

The following {requirement_type} requirement statement was rejected because it contains two distinct finite verb phrases joined by 'and'/'or' under one 'shall' — it expresses two separate obligations in one statement:

  COMPOUND STATEMENT: "{compound_statement}"
  Original cci_refs:  [{original_cci_list}]
  Original metadata:
{rationale_line}
{fit_crit_line}
{vm_line}
{priority_line}
  confidence: {confidence}

## Your task

Decompose the compound statement into **2 (or more, if needed) atomic statements**, each expressing a single obligation. Rules:

1. Each atomic statement must contain exactly one 'shall' and one finite verb phrase in the predicate.
2. If one half logically depends on the other (e.g. "shall display X and notify Y when X changes"), express the dependency as a **Condition slot** on the dependent statement (e.g. "When X changes, the system shall notify Y").
3. Distribute the original cci_refs across the atomic statements. If a CCI is relevant to both halves, include it in both. Every original CCI must appear in at least one atomic statement's cci_refs.
4. Preserve the original requirement_type ("{requirement_type}") for all atomic statements unless a specific half is clearly a different type.
5. Keep the subject consistent with the original statement's row-level vocabulary.
6. Do NOT introduce obligations absent from the original statement.
7. Do NOT reproduce the compound statement verbatim as one of the outputs.

---

{_REQUIREMENT_TYPE_GUIDANCE}

---

Respond with a **JSON array** of atomic Requirement proposals (minimum 2 items):
[
  {{
    "statement": "<atomic statement 1 — one 'shall', one finite verb>",
    "requirement_type": "{requirement_type}",
    "cci_refs": ["<relevant ci_ids from original>"],
    "rationale": "optional",
    "fit_criteria": null,
    "verification_method": null,
    "priority": null,
    "confidence": 0.85
  }},
  {{
    "statement": "<atomic statement 2 — one 'shall', one finite verb>",
    "requirement_type": "{requirement_type}",
    "cci_refs": ["<relevant ci_ids from original>"],
    "rationale": "optional",
    "fit_criteria": null,
    "verification_method": null,
    "priority": null,
    "confidence": 0.85
  }}
]

Do NOT include: requirement_id, row_target, domain_refs, answer_refs.
Return only a valid JSON array. No text before or after the array."""
