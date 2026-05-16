"""
Residual Sources classification prompt template.

Same three-step classification as chunk prompt but without domain_name or
requirements parameters (residual Sources were not matched to any Domain chunk).

Per spec §4.2: same structure as per-chunk, no domain context.
"""

from __future__ import annotations

from mechanisms.row_lens_source_reanalysis.prompts.lens_definitions import (
    get_lens_content,
    get_lens_name,
)


def build_residual_classification_prompt(
    *,
    row_ref: int,
    sources: list[dict],
    concern_threshold: float,
    batch_index: int = 0,
) -> str:
    """
    Build the prompt string for residual Sources classification.

    Parameters
    ----------
    row_ref           : Zachman row being analysed
    sources           : list of {source_id, source_text} dicts in this batch
    concern_threshold : T1 threshold for Signal vs Concern split (context only)
    batch_index       : sub-batch index for logging (0-indexed)

    Returns
    -------
    Prompt string ready for Claude Sonnet API call.
    """
    lens_name = get_lens_name(row_ref)
    lens_content = get_lens_content(row_ref)

    src_block = "\n".join(
        f"  [{s['source_id']}] {s['source_text']}" for s in sources
    )

    batch_note = (
        f" (residual batch {batch_index + 1})" if batch_index > 0 else " (residual)"
    )

    return f"""You are a systems engineering analyst performing Row-Lens Source Re-Analysis{batch_note}.

## Analytical Lens
{lens_content}

Note: These sources were not matched to any specific Domain chunk from stream 2.
Classify them independently against the {lens_name} analytical level.

## Sources to Classify (stream 1, residual)
{src_block}

## Classification Task

For each Source item listed above, perform the following three steps:

**Step 1 — Relevance Gate**
Is this source relevant to the {lens_name} analytical abstraction level described above?
- YES: the source addresses content meaningful at this Zachman row.
- NO: the source is clearly outside the scope of this analytical level.

**Step 2 — If YES: Confidence Assessment**
Assess the confidence (0.0 to 1.0) that this source represents a clear, unambiguous signal at this row level:
- High confidence (≥ {concern_threshold}): clearly expresses a single interpretable concept → Signal.
- Low confidence (< {concern_threshold}): ambiguous, contradictory, or requires practitioner review → Concern.

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
LPM constraint: descriptions characterise content — never rewrite or replace source text verbatim.
"""
