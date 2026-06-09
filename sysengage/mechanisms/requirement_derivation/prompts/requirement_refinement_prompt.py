"""
Path R — Seed-elaboration (refinement-driven derivation) prompt.

Per Requirement Derivation Spec v0.13 §4.2 (Path R):
  For rows >= 2, interrogate row n-1 seeds to produce row n children.
  Each child refines exactly one seed (refines_refs=[seed_id]).
  Children should draw on the available row n CCIs where applicable.

LPM constraint: seed statements and CCI descriptions are never rewritten.
"""

from __future__ import annotations

import json
from typing import Any


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

    return f"""You are a systems-engineering assistant helping derive Row {row_ref} requirements
by elaborating Row {row_ref - 1} requirements one abstraction level down.

## Task — Path R: Seed Elaboration

You are given:
1. **Row {row_ref - 1} seeds** — requirements at the parent abstraction level.
2. **Row {row_ref} domains and CCIs** — the available content at the target level.

For each seed, produce one or more Row {row_ref} requirement proposals that refine it.
Each proposal must:
- Carry `refines_refs` containing exactly the seed's `requirement_id`.
- Express the same obligation as the seed, made more concrete / specific for Row {row_ref}.
- Where relevant CCIs are available, reference them in `cci_refs`; otherwise leave `cci_refs` empty.
- Never invent content absent from the seed or the CCIs (LPM constraint).
- Never copy a seed statement verbatim.

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
  "statement": "<Row {row_ref} requirement statement>",
  "requirement_type": "<Functional|Constraint|Structural>",
  "refines_refs": ["<seed_requirement_id>"],
  "cci_refs": ["<ci_id>", ...],
  "rationale": "<brief rationale>",
  "fit_criteria": "<measurement criterion or null>",
  "verification_method": "<Inspection|Demonstration|Test|Analysis|Measurement or null>",
  "priority": "<Must|Should|Could|null>",
  "confidence": 0.0
}}
```

Rules:
- `refines_refs` must contain exactly ONE requirement_id from the seeds list above.
- `cci_refs` may be empty if no CCI precisely matches; do not fabricate CCI ids.
- `requirement_type` must match the intellectual kind of the statement
  (behaviour → Functional; bound/rule → Constraint; data/structure → Structural).
- `confidence` is your confidence that this proposal correctly refines the seed (0–1).
- Return only the JSON array; no explanatory text.
"""
