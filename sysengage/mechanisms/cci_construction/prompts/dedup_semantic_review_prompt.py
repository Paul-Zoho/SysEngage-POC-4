"""
Stage 4b prompt template — per-cell semantic deduplication review.

Per CCI Construction Mechanism Spec v0.2 §4.4 and Row 4 Understanding v0.4 §12.3:
  Same-classification_type pairs (new candidates + existing CCIs) are presented
  to the AI for semantic equivalence judgment.
  Verdicts: Duplicate | Distinct | Ambiguous.
  merged_description populated by AI when verdict=Duplicate and the lower-
  confidence item contains nuance worth preserving.
"""

from __future__ import annotations

import json


def build_dedup_review_prompt(
    *,
    cell_id: str,
    column: str,
    column_interrogative: str,
    pairs: list[dict],
) -> str:
    """
    Build the Stage 4b Claude prompt for semantic deduplication of one cell.

    Parameters
    ----------
    cell_id              : e.g. "ZC-R2-C-What"
    column               : e.g. "What"
    column_interrogative : e.g. "Business entities and data objects"
    pairs                : list of pair dicts, each:
      {
        "item_a": {"source": "new_candidate"|"existing_cci",
                   "ref": str,  # candidate index or ci_id
                   "description": str,
                   "signal_refs": [str],
                   "confidence": float},
        "item_b": { ... same structure ... }
      }

    Returns
    -------
    Formatted prompt string.
    """
    pairs_json = json.dumps(pairs, indent=2)

    return f"""You are reviewing candidate CellContentItems for semantic equivalence.

## Context

Cell: {cell_id}
Column: {column}
Analytical focus: {column_interrogative}

## Task

For each pair of items below, determine whether they express the same classified meaning.
Items labelled "existing_cci" are already committed to the ledger.
Items labelled "new_candidate" are newly derived from this run.

Verdicts:
- **Duplicate**: Both items express the same classified content (despite different wording or partially different signal_refs). They should be merged into one.
- **Distinct**: The items express genuinely different content. Both should survive.
- **Ambiguous**: You cannot determine semantic equivalence with confidence. Both items survive but with reduced confidence.

For Duplicate verdicts: if the lower-confidence item's description contains nuance absent from the higher-confidence item's description, provide a `merged_description` that captures both. Otherwise leave `merged_description` as null.

## Pairs to Review

{pairs_json}

Respond with ONLY a JSON object in this exact format:
{{
  "verdicts": [
    {{
      "item_a_ref": "...",
      "item_b_ref": "...",
      "verdict": "Duplicate",
      "rationale": "Both items describe the same entity — the child's transaction record.",
      "merged_description": null
    }}
  ]
}}"""
