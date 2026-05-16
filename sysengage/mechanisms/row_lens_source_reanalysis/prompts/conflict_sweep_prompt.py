"""
Cross-chunk conflict sweep prompt template.

Per spec §4.4: AI assesses whether each cross-chunk conflict represents a genuine
contradiction requiring a Concern, or a legitimate complementary classification
where the same Source validly contributes to two different Domain analyses.
"""

from __future__ import annotations

from mechanisms.row_lens_source_reanalysis.prompts.lens_definitions import (
    get_lens_content,
    get_lens_name,
)


def build_conflict_sweep_prompt(
    *,
    row_ref: int,
    conflicts: list[dict],
) -> str:
    """
    Build the prompt for the conflict sweep AI invocation.

    Parameters
    ----------
    row_ref   : Zachman row being analysed
    conflicts : list of {source_id, source_text, classifications_by_chunk}
                Each classifications_by_chunk: [{domain_id, domain_name,
                classification, signal_type, confidence}]

    Returns
    -------
    Prompt string ready for Claude Sonnet API call.
    """
    lens_name = get_lens_name(row_ref)
    lens_content = get_lens_content(row_ref)

    conflict_blocks = []
    for c in conflicts:
        cls_lines = []
        for cls in c.get("classifications_by_chunk", []):
            cls_lines.append(
                f"    Domain [{cls['domain_id']}] {cls.get('domain_name', '')}: "
                f"{cls['classification']}"
                + (f" ({cls['signal_type']})" if cls.get("signal_type") else "")
                + f" confidence={cls['confidence']:.2f}"
            )
        block = (
            f"SOURCE [{c['source_id']}]\n"
            f"  Text: {c['source_text']}\n"
            f"  Conflicting classifications:\n" + "\n".join(cls_lines)
        )
        conflict_blocks.append(block)

    conflicts_text = "\n\n".join(conflict_blocks)

    return f"""You are a systems engineering analyst performing a cross-chunk conflict sweep.

## Analytical Lens
{lens_content}

## Context
The following sources received different classifications from different Domain chunks
during Row-Lens Source Re-Analysis at the {lens_name} level (Row {row_ref}).

You must assess each conflict: is it a genuine contradiction (same source cannot
coherently belong to both classifications) or a legitimate complementary contribution
(the source is multi-faceted and validly contributes to two different Domain analyses)?

## Conflicts to Assess

{conflicts_text}

## Assessment Criteria

For each conflict, determine:

**Genuine contradiction**: The two classifications are logically incompatible —
the source cannot simultaneously represent the concepts associated with both classifications.
This indicates an ambiguity or tension in the requirements/source material that requires
practitioner attention. → Produce a Concern.

**Legitimate complementary classification**: The source is multi-faceted. It can genuinely
address multiple Domain contexts at the same analytical level. This is not a problem —
the same content legitimately enriches multiple Domain analyses. → No Concern produced;
all existing Signal classifications are retained.

## Required Output Format

Respond with ONLY a valid JSON object, no preamble, no markdown fences:

{{
  "conflicts": [
    {{
      "source_id": "<source_id>",
      "is_genuine_contradiction": true | false,
      "rationale": "<one sentence explaining the assessment>"
    }}
  ]
}}

Every source_id in the conflicts list above must appear exactly once in the output.
LPM constraint: rationale must characterise the tension — never rewrite or replace source text.
"""
