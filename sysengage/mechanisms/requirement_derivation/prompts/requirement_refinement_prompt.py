"""
Path R — Seed-elaboration (refinement-driven derivation) prompt.

Per Requirement Derivation Spec v0.17 §4.2 (Path R):
  For rows >= 2, interrogate row n-1 seeds to produce row n children.
  Each child refines exactly one seed (refines_refs=[seed_id]).
  Injects REQUIREMENT_ROW_GUIDANCE[str(row_ref)] so the model knows the
  target-row abstraction level and vocabulary — critical for jumps like
  logical (Row 3) → physical (Row 4) where the transformation expectation
  differs fundamentally from the seed vocabulary.

LPM constraint: seed statements and CCI descriptions are never rewritten.
"""

from __future__ import annotations

import json
from typing import Any

from mechanisms.requirement_derivation.prompts.requirement_row_guidance import (
    REQUIREMENT_ROW_GUIDANCE,
)


def build_requirement_refinement_prompt(
    *,
    row_ref: int,
    seeds: list[dict[str, Any]],
    domains: list[dict[str, Any]],
) -> str:
    """
    Build the Path R elaboration prompt.

    Parameters
    ----------
    row_ref   — the current row being derived (n >= 2).
    seeds     — list of row n-1 seed requirements (dicts with requirement_id,
                statement, requirement_type, domain_refs).
    domains   — active domains for row n, each with domain_id, name, description,
                and cell_content_items (list of {ci_id, column, classification_type,
                description}).
    """
    seeds_block = json.dumps(seeds, indent=2)
    domains_block = json.dumps(domains, indent=2)
    row_guidance = REQUIREMENT_ROW_GUIDANCE.get(str(row_ref), "")

    return f"""You are a systems-engineering assistant helping derive Row {row_ref} requirements
by elaborating Row {row_ref - 1} requirements one abstraction level down.

## Row {row_ref} Statement Formulation Guidance

The requirements you produce MUST conform to the Row {row_ref} abstraction level described below.
Read this guidance carefully — it defines the correct subject, vocabulary, and type reasoning
for Row {row_ref}. A Row {row_ref - 1} seed expressed at the wrong abstraction level is NOT
a valid Row {row_ref} requirement; you must re-express it at Row {row_ref}.

{row_guidance}

## Task — Path R: Interrogative Seed Elaboration

For each Row {row_ref - 1} seed below, ask: *What does realising this obligation require at
Row {row_ref}?* Apply the Row {row_ref} slot interrogatives to the seed's intent:
- *Who/what acts or is obligated at Row {row_ref}?* (Subject — per guidance above)
- *What capability, construction, or constraint does Row {row_ref} require?* (Action/Object)
- *When / Under what condition?* (Condition, if the seed implies one)
- *What bound, rule, or structure does it impose?* (Constraint Rule / Structural assertion)

Produce one or more Row {row_ref} child proposals per seed. Each proposal must:
- Carry `refines_refs` containing exactly the seed's `requirement_id`.
- Be expressed at Row {row_ref} abstraction (per the guidance above) — not a paraphrase of
  the seed at the seed's level.
- Where relevant CCIs are available, reference them in `cci_refs`; otherwise leave `cci_refs`
  empty (a pure-seed child with empty `cci_refs` is valid).
- Never invent content absent from the seed or the CCIs (LPM constraint).
- Never copy a seed statement verbatim.
- A seed child may be a system requirement OR a process/organisational requirement — do NOT
  force a system subject if the seed's obligation is realised outside the system boundary.
- There is NO terminal exit: every seed must yield at least one child.

## Row {row_ref - 1} Seeds

```json
{seeds_block}
```

## Row {row_ref} Domains and CCIs

```json
{domains_block}
```

## Output Format

Return a JSON array of objects. Each object must conform to:

```json
{{
  "statement": "<Row {row_ref} requirement statement — at Row {row_ref} abstraction>",
  "requirement_type": "<Functional|Constraint|Structural>",
  "refines_refs": ["<seed_requirement_id>"],
  "cci_refs": ["<ci_id>", ...],
  "rationale": "<brief rationale>",
  "fit_criteria": "<measurement criterion or null>",
  "verification_method": "<Inspection|Demonstration|Test|Analysis|Measurement or null>",
  "priority": "<High|Medium|Low|null>",
  "confidence": 0.0
}}
```

Rules:
- `refines_refs` must contain exactly ONE requirement_id from the seeds list above.
- `cci_refs` may be empty if no CCI precisely matches; do not fabricate CCI ids.
- `requirement_type` must match the intellectual kind of the statement at Row {row_ref}
  (behaviour → Functional; bound/rule → Constraint; data/structure → Structural).
- `confidence` is your confidence that this proposal correctly refines the seed (0–1).
- Return only the JSON array; no explanatory text.
"""
