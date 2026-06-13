"""
prompts/requirement_dd_extraction_prompt.py

Batch entity extraction prompt for §4.4.3a Step 1 (v0.11).

The prompt receives the surviving requirements (statement + slot parse hint)
and returns bare entity-grade noun phrases to present to the Data Dictionary,
plus any lifecycle state qualifiers to record as entity attributes.

One call per Stage 4 run (not per requirement).

Fingerprinted as 'stage4_dd_entity_extraction' in the AnalysisPass.

v0.11 change: state-reduction rule added — state-qualified phrases
("available tasks", "completed tasks") reduce to the bare entity ("task");
states are returned separately as state_qualifiers for record_value() calls.
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
      raw_slot       — the slot text the parser located:
                         Functional  → Object (post-shall predicate minus action verb)
                         Structural  → Entity + Assertion text
                         Constraint  → Constraint-Rule (post-shall predicate, F99 v0.24)
                       May be '' if the slot is absent or unparseable.

    Returns a prompt string whose expected AI response is a JSON array of
    {idx, terms, state_qualifiers}, same length and order as items.
    """
    items_json = json.dumps(items, indent=2, ensure_ascii=False)

    return f"""You are extracting entity-grade controlled-vocabulary terms from requirement statements to populate a Data Dictionary.

For each requirement, identify the **domain entities** that the requirement's key slot **denotes** — the specific domain nouns (things, roles, concepts) the obligation is about.

## Slot guide by type
- **Functional** — reduce the Object slot to its BARE entity head(s). Strip verbs, verbal nouns ("a mechanism enabling…"), incidental modifiers, and lifecycle-state qualifiers.
  Example (clausal reduction): Object = "a mechanism enabling children to claim and complete tasks"
  → terms: ["task", "child"]
  Example (state-qualified): Object = "available tasks and completed tasks"
  → terms: ["task"]   (bare entity only; "available"/"completed" are state attributes, not new entities)
- **Structural** — return the bare entity being described and any composition element as separate terms.
  Example: "Task comprises status, assignee, and deadline"
  → terms: ["task", "task status", "task assignee"]
- **Constraint** — return the named domain concept(s) the Constraint-Rule **governs** — the noun(s)
  the rule bounds — taken from the rule predicate (post-shall), NOT the Subject. A Constraint
  has no Object slot, so entity terms come from what the rule applies to, not from "the system"
  or other thin Subject nouns.
  Example: "The system shall enforce retention of task-completion records"
  → terms: ["task completion record"]
  Example: "The enterprise shall comply with ISO-27001"
  → terms: ["ISO-27001"]
  Example: "The system shall limit task assignment to verified carers"
  → terms: ["task assignment", "carer"]
  The rule's threshold / bound / value is an **attribute** on the governed entity (never a
  clause-named canonical). Return [] if no meaningful domain entity can be identified from the rule.

## Rules
1. Each term must be an entity-grade noun phrase — typically 1–5 words, no trailing sentence punctuation.
2. Do NOT return the verbatim raw_slot if it is a clause or sentence fragment.
3. Do NOT return the full statement as a term.
4. Return an empty list [] if no meaningful entity can be identified.
5. Return the BARE source noun — do NOT coin state-qualified or role-qualified compound entities.
   "available tasks" → "task" (NOT "task opportunity" or "available task")
   "completed tasks" → "task" (NOT "completed achievement")
   "claimed task"    → "task" (NOT "claimed item")
   Lifecycle states and role qualifiers are ATTRIBUTES of the entity, not new entities.
6. Prefer specific domain vocabulary over generic nouns ("task" over "item").
7. A statement may yield 0, 1, or several terms.

## State qualifiers
When the Object or slot describes an entity in a lifecycle state (e.g. "available tasks",
"completed tasks", "claimed task"), return the state in `state_qualifiers` so it can be
recorded as an attribute on the entity's Data Dictionary entry.
- entity: the bare entity term (must appear in `terms`)
- state: the lifecycle state value (e.g. "available", "completed", "claimed")
Omit `state_qualifiers` (or use []) when no lifecycle state is expressed.

## Input
{items_json}

## Output format
Return **only** a JSON array, no prose, no code fence:
[{{"idx": 0, "terms": ["task", "child"], "state_qualifiers": [{{"entity": "task", "state": "available"}}, {{"entity": "task", "state": "completed"}}]}}, ...]

- `terms`: bare entity noun phrases (never state-qualified).
- `state_qualifiers`: list of {{entity, state}} pairs for lifecycle states present in the slot; omit or use [] when none.
Same length as input, same order.
"""
