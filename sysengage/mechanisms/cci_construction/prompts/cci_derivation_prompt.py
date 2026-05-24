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

## Derivation Rules

**Rule 1 — Atomic content items**
Each CCI must express one single, atomic piece of classified content.
Do not combine multiple distinct concepts into one CCI description.
A CCI description should be concise — one clause, not a list.

**Rule 2 — Derived statements**
CCI descriptions are derived statements of classified meaning.
Do not copy Signal text verbatim. Re-express the content in terms of the Zachman column's interrogative at the {row_label} abstraction level.

**Rule 3 — Signal grounding**
Every CCI must be grounded in at least one Signal via signal_refs.
signal_refs must only contain Signal IDs from the list above.

**Rule 4 — Column assignment**
Assign each CCI to the most appropriate column.
A single Signal may produce CCIs in multiple columns if it contains content relevant to multiple interrogatives.

**Rule 5 — Named instances**
When a Signal describes multiple DISTINCT NAMED ITEMS of the same classification_type, produce ONE SEPARATE CCI PER NAMED ITEM. Do NOT aggregate named items into a single CCI description.

Named instances are distinct, individually nameable things — such as:
- Named platforms or operating systems (iOS, Android, Windows)
- Named locations or deployment sites (London, New York, Singapore)
- Named actors or roles (Child user, Parent user, Administrator)
- Named events or triggers (WeeklyReset, MonthlyReview, OnLogin)
- Named entities or data objects (Transaction, Account, Category)

CORRECT — three separate CCIs:
  Signal: "The platform supports iOS, Android, and Windows deployment"
  Output:
    {{"column": "Where", "classification_type": "Node", "description": "iOS mobile platform deployment node", "signal_refs": ["SG545"], "confidence": 0.90}}
    {{"column": "Where", "classification_type": "Node", "description": "Android mobile platform deployment node", "signal_refs": ["SG545"], "confidence": 0.90}}
    {{"column": "Where", "classification_type": "Node", "description": "Windows desktop platform deployment node", "signal_refs": ["SG545"], "confidence": 0.90}}

INCORRECT — single aggregated CCI (never do this for named instances):
  Signal: "The platform supports iOS, Android, and Windows deployment"
  Output:
    {{"column": "Where", "classification_type": "Node", "description": "Multi-platform deployment supporting iOS, Android, and Windows", "signal_refs": ["SG545"], "confidence": 0.90}}

**Rule 6 — Confidence**
Assign confidence 0.0–1.0 reflecting how clearly the Signal supports the CCI's classification. 0.9+ for unambiguous content; 0.6–0.8 for content requiring inference; below 0.6 for speculative derivation.

**Rule 7 — Coverage preference**
Prefer producing a CCI at moderate confidence (≥ 0.65) over omitting it entirely. A genuine analytical finding should be recorded even when the evidence is partial. Only omit a CCI when there is truly no classifiable content in the Signal set for that column.

For the "What" column at Row 2 and above (data model, network, technology abstraction levels), produce Entity and Process CCIs at ≥ 0.55 confidence when the Signal is clearly scoped to that abstraction level, even if the wording is indirect. The hard floor for any CCI across all columns is 0.50 — never produce below this threshold, but do not use the floor as a reason to omit something that clearly belongs.

Respond with ONLY a JSON object in this exact format — no preamble, no explanation, no markdown:
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
