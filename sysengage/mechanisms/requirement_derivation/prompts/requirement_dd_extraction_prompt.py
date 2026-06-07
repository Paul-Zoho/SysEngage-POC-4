"""
prompts/requirement_dd_extraction_prompt.py

Batch entity extraction prompt for §4.4.3a Step 1 (v0.8).

The prompt receives the surviving requirements (statement + slot parse hint)
and returns entity-grade noun phrases to present to the Data Dictionary.
One call per Stage 4 run (not per requirement).

Fingerprinted as 'stage4_dd_entity_extraction' in the AnalysisPass.
"""

from __future__ import annotations

import json
from typing import Any


def build_dd_extraction_prompt(items: list[dict[str, Any]]) -> str:
    """
    Build the batch entity extraction prompt.

    items: list of {idx, statement, requirement_type, raw_slot}
      idx            — integer index for round-trip matching
      statement      — full requirement statement
      requirement_type — 'Functional' | 'Structural' | 'Constraint'
      raw_slot       — the slot text the parser located (Object / Entity+Assertion
                       / Subject); may be '' if unparseable

    Returns a prompt string whose expected AI response is a JSON array of
    {idx: int, terms: list[str]}, same length and order as items.
    """
    items_json = json.dumps(items, indent=2, ensure_ascii=False)

    return f"""You are extracting entity-grade controlled-vocabulary terms from requirement statements to populate a Data Dictionary.

For each requirement, identify the **domain entities** that the requirement's key slot **denotes** — the specific domain nouns (things, roles, states, concepts) the obligation is about.

## Slot guide by type
- **Functional** — reduce the Object slot to its entity head(s). Strip verbs, verbal nouns ("a mechanism enabling…"), and incidental modifiers. Keep the domain nouns.
  Example: Object = "a mechanism enabling household members to select and claim available work opportunities"
  → terms: ["work opportunity", "household member"]
- **Structural** — return the entity being described and any composition element as separate terms.
  Example: "Work Opportunity comprises status, assignee, and deadline"
  → terms: ["work opportunity", "work opportunity status", "work opportunity assignee"]
- **Constraint** — return the subject entity (the thing being constrained), reduced to its noun head.
  Example: Subject = "The settlement amount"
  → terms: ["settlement amount"]

## Rules
1. Each term must be an entity-grade noun phrase — typically 1–5 words, no trailing sentence punctuation.
2. Do NOT return the verbatim raw_slot if it is a clause or sentence fragment.
3. Do NOT return the full statement as a term.
4. Return an empty list [] if no meaningful entity can be identified.
5. Prefer specific domain vocabulary over generic nouns ("task assignment" over "assignment").
6. A statement may yield 0, 1, or several terms.

## Input
{items_json}

## Output format
Return **only** a JSON array, no prose, no code fence:
[{{"idx": 0, "terms": ["term a", "term b"]}}, ...]

Same length as input, same order.
"""
