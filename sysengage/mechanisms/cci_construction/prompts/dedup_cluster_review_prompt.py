"""
Stage 4b prompt template — per-cell semantic cluster deduplication review.

Per CCI Construction Mechanism Spec v0.13 §4.4:
  All members of a classification_type group are presented to the AI in a single
  call.  The AI identifies clusters of semantically equivalent items (Duplicate),
  flags uncertain equivalences (Ambiguous), and treats everything else as Distinct.
  Items not mentioned in any cluster or ambiguous entry are implicitly Distinct.

  Named-instance preservation directive variant: activated when any new candidate
  in the group carries stage4a_routed=True.  Stage 4a routed these candidates
  because they share the same classification_type and signal_refs but have
  materially different descriptions — confirming they are distinct named instances
  derived from the same Signal.  The AI is given a preservation directive: it
  MUST return ALL items as Distinct.  The AI's latitude to merge is removed
  entirely for these groups — the distinctness is a structural fact, not a
  judgment the AI is being asked to make.
"""

from __future__ import annotations

import json


def build_cluster_review_prompt(
    *,
    cell_id: str,
    column: str,
    column_interrogative: str,
    members: list[dict],
    named_instance_framing: bool = False,
) -> str:
    """
    Build the Stage 4b Claude prompt for semantic cluster deduplication of one group.

    Parameters
    ----------
    cell_id              : e.g. "ZC-R2-C-What"
    column               : e.g. "What"
    column_interrogative : e.g. "Business entities and data objects"
    members              : list of member dicts, each:
      {
        "ref":         str,    # unique reference string (candidate index or ci_id)
        "source":      str,    # "new_candidate" | "existing_cci"
        "description": str,
        "signal_refs": [str],
        "confidence":  float
      }
    named_instance_framing : bool
      When True, use the named-instance preservation directive variant.
      Set by Stage 4a when one or more new candidates in this group share the
      same classification_type and signal_refs but have materially different
      descriptions — confirming they are distinct named instances.  The AI is
      given a directive to return ALL items as Distinct; its latitude to merge
      is removed entirely for these groups (spec v0.13 §4.4).

    Returns
    -------
    Formatted prompt string.
    """
    members_json = json.dumps(members, indent=2)

    if named_instance_framing:
        return f"""You are processing CellContentItems that Stage 4a has confirmed as distinct named instances.

## Context

Cell: {cell_id}
Column: {column}
Analytical focus: {column_interrogative}

## Named-Instance Preservation Directive

Stage 4a has determined that these items are confirmed distinct named instances derived from the same Signal. They share the same classification type and signal_refs but have materially different descriptions. You MUST return ALL items as Distinct. Do not merge any of them regardless of semantic similarity. The distinctness is a structural fact established by the derivation process, not a judgment you are being asked to make.

## Items

{members_json}

Respond with ONLY a JSON object with empty arrays:
{{
  "clusters": [],
  "ambiguous": []
}}"""

    return f"""You are reviewing CellContentItems for semantic equivalence within a single classification group.

## Context

Cell: {cell_id}
Column: {column}
Analytical focus: {column_interrogative}

All items below share the same classification_type. Your task is to identify which items express the same classified meaning and should be merged.

Items labelled "existing_cci" are already committed to the ledger.
Items labelled "new_candidate" are newly derived from this run.

## Task

Identify **clusters** — groups of 2 or more items that express the same classified content (despite different wording or partially overlapping signal_refs). Each cluster should be merged into one.

For items whose equivalence is genuinely uncertain, flag them as **Ambiguous** — both survive but with reduced confidence.

Items not mentioned in any cluster or ambiguous entry are treated as **Distinct** and survive unchanged. Do not list Distinct items explicitly.

For each Duplicate cluster: provide a `representative_description` that captures the full meaning of the cluster. If the items are near-identical in meaning, use the clearest wording. If one item contains nuance absent from the others, incorporate it.

## Items to Review

{members_json}

Respond with ONLY a JSON object in this exact format:
{{
  "clusters": [
    {{
      "member_refs": ["ref_a", "ref_b"],
      "verdict": "Duplicate",
      "representative_description": "The unified description capturing full cluster meaning.",
      "rationale": "Both items describe the same entity — the child's transaction record."
    }}
  ],
  "ambiguous": [
    {{
      "member_refs": ["ref_c", "ref_d"],
      "rationale": "These items may describe the same concept but the wording diverges enough to be uncertain."
    }}
  ]
}}

Rules:
- Each ref may appear in at most one cluster or one ambiguous entry.
- A cluster must have at least 2 member_refs.
- An ambiguous entry must have at least 2 member_refs.
- If there are no duplicate clusters, return an empty "clusters" array.
- If there are no ambiguous pairs, return an empty "ambiguous" array.
- Do NOT include Distinct items in the response."""
