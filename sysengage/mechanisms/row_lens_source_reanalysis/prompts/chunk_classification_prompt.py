"""
Chunk classification prompt template.

Per spec §4.2: three-step classification:
  1. Relevance gate (Yes/No per row lens)
  2. If Yes: confidence score (0.0-1.0) that content classifies clearly (Signal) vs ambiguously (Concern)
  3. If No: OutOfScope

The concern_threshold is passed as context but DM entity-production applies it.
AI returns confidence score; implementation decides Signal vs Concern.

Response format: JSON with items list, each item having:
  item_id, classification, confidence, description
"""

from __future__ import annotations

from mechanisms.row_lens_source_reanalysis.prompts.lens_definitions import (
    get_lens_content,
    get_lens_name,
)


def build_chunk_classification_prompt(
    *,
    row_ref: int,
    domain_name: str,
    requirements: list[dict],
    sources: list[dict],
    concern_threshold: float,
) -> str:
    """
    Build the prompt string for per-chunk AI classification.

    Parameters
    ----------
    row_ref           : Zachman row being analysed
    domain_name       : name of the Domain driving this chunk
    requirements      : list of {requirement_id, statement} dicts
    sources           : list of {source_id, source_text} dicts
    concern_threshold : T1 threshold for Signal vs Concern split (context only)

    Returns
    -------
    Prompt string ready for Claude Sonnet API call.
    """
    lens_name = get_lens_name(row_ref)
    lens_content = get_lens_content(row_ref)

    req_block = "\n".join(
        f"  [{r['requirement_id']}] {r['statement']}" for r in requirements
    )
    src_block = "\n".join(
        f"  [{s['source_id']}] {s['source_text']}" for s in sources
    )

    return f"""You are a systems engineering analyst performing Row-Lens Source Re-Analysis.

## Analytical Lens
{lens_content}

## Domain Context
Domain: {domain_name}

Associated Requirements (stream 2):
{req_block if req_block else "  (none)"}

## Sources to Classify (stream 1)
{src_block}

## Classification Task

For each Source item listed above, perform the following three steps:

**Step 1 — Relevance Gate**
Is this source relevant to the {lens_name} analytical abstraction level described above?
- YES: the source addresses content meaningful at this Zachman row.
- NO: the source is clearly outside the scope of this analytical level.

**Step 2 — If YES: Confidence Assessment**
Assess the confidence (0.0 to 1.0) that this source represents a clear, unambiguous signal at this row level:
- High confidence (≥ {concern_threshold}): the source clearly expresses a single, interpretable concept at this level → Signal.
- Low confidence (< {concern_threshold}): the source is ambiguous, contradictory, or raises a question that requires practitioner review → Concern.

**Step 3 — Classification**
Based on steps 1 and 2:
- Relevance gate = NO → classify as "OutOfScope"
- Relevance gate = YES, confidence ≥ {concern_threshold} → classify as "Signal"
- Relevance gate = YES, confidence < {concern_threshold} → classify as "Concern"

For Signal classification, also determine the signal_type from:
  Normative, Intent, Actor, Concern, Ambiguity, Quality

## Required Output Format

Respond with ONLY a valid JSON object, no preamble, no markdown fences:

{{
  "items": [
    {{
      "item_id": "<source_id>",
      "classification": "Signal" | "Concern" | "OutOfScope",
      "signal_type": "<type or null if Concern/OutOfScope>",
      "confidence": <float 0.0-1.0>,
      "description": "<one concise sentence characterising the content at this row level>"
    }}
  ]
}}

Every source_id listed above must appear exactly once in the items array.
LPM constraint: descriptions must characterise content at this analytical level — never rewrite or paraphrase the source text verbatim as a replacement.
"""
