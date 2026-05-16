"""
Stage 3a prompt template — per-batch Signal-to-CCI derivation.

Per CCI Construction Mechanism Spec v0.2 §4.3 and Row 4 Understanding v0.4 §12.2:
  All six column interrogatives are presented in every batch prompt.
  The AI determines column placement as part of the derivation act.
  The response must include 'column' as a required field.
  LPM constraint: Signal descriptions are presented read-only; the AI derives
  new CCI descriptions — it must NOT copy Signal text verbatim.
"""

from __future__ import annotations

import json

from mechanisms.cci_construction.prompts.column_interrogatives import (
    COLUMN_INTERROGATIVES,
    ROW_LENS_LABELS,
)
from mechanisms.cci_construction.prompts.column_vocabulary import COLUMN_VOCABULARY
from models.signal import SignalModel


def build_cci_derivation_prompt(
    *,
    row_ref: int,
    signals: list[SignalModel],
) -> str:
    """
    Build the Stage 3a Claude prompt for a single batch of Signals.

    Parameters
    ----------
    row_ref : Zachman row number (1-6)
    signals : the batch of SignalModel instances to process

    Returns
    -------
    Formatted prompt string ready for Claude Sonnet.
    """
    row_label = ROW_LENS_LABELS.get(row_ref, f"Row {row_ref}")
    interrogatives = COLUMN_INTERROGATIVES[row_ref]

    column_section_lines: list[str] = []
    for col, framing in interrogatives.items():
        vocab = ", ".join(COLUMN_VOCABULARY[col])
        column_section_lines.append(
            f"  {col}: {framing}\n"
            f"    Permitted classification_type values: {vocab}"
        )
    column_section = "\n".join(column_section_lines)

    signal_lines: list[str] = []
    for sig in signals:
        signal_lines.append(
            f"  - signal_id: {sig.signal_id}\n"
            f"    signal_type: {sig.signal_type}\n"
            f"    confidence: {sig.confidence}\n"
            f"    description: {sig.description}"
        )
    signals_section = "\n".join(signal_lines)

    vocab_json = json.dumps(COLUMN_VOCABULARY, indent=4)

    return f"""You are performing Zachman framework analysis at the {row_label} abstraction level.

Your task: derive CellContentItems (CCIs) from the Signals below. Each CCI represents a distinct classified content item found within the Signal set — the analytical bridge between raw classification evidence and formal outputs.

## Zachman Row {row_ref} — Column Interrogatives

{column_section}

## Permitted classification_type Values by Column

{vocab_json}

## Signals to Analyse

{signals_section}

## Instructions

For each distinct classified content item you identify across ALL six Zachman columns:
1. Assign `column` — one of: What, How, Where, Who, When, Why
2. Assign `classification_type` — from the permitted values for that column ONLY
3. Write `description` — a derived statement of the classified meaning. DO NOT copy Signal text verbatim. Re-express the content as a concise classified statement appropriate to the {row_label} abstraction level.
4. List `signal_refs` — the signal_id(s) that ground this item (at least one). A Signal may ground multiple CCIs; multiple Signals may ground one CCI.
5. Assign `confidence` — your derivation confidence (0.0–1.0)
6. Optionally provide `trigger_condition` if the content is conditional
7. Optionally provide `justification` for your classification reasoning

Rules:
- Each CCI must reference at least one signal_id from the list above
- classification_type MUST be from the permitted values for the assigned column
- description MUST NOT be a verbatim copy of any Signal's description
- A single Signal may produce CCIs in multiple columns if it contains multi-column content
- Omit columns entirely if no meaningful classified content exists for them in this batch

Respond with ONLY a JSON object in this exact format:
{{
  "items": [
    {{
      "column": "What",
      "classification_type": "Entity",
      "description": "...",
      "signal_refs": ["SG001"],
      "confidence": 0.85,
      "trigger_condition": null,
      "justification": "..."
    }}
  ]
}}"""
