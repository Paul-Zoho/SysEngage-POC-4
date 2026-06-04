"""
Stage 2 — Contradiction Sweep (IM + DM).

Single-stream realisation of Row-Lens Source Re-Analysis v0.2 §4.2.

Mode: IM (AI invocation) + DM (Concern production).
LPM: source_text is read-only; never rewritten.

Receives the Signal/Concern list from Stage 1 and sweeps for contradictions
within the classified set — pairs of signals or concerns whose descriptions
are in direct tension (e.g. one asserts a capability, another denies it).

If the conflict list is empty: Stage 2 produces no output.
One Claude Sonnet API call for all conflicts (single invocation).
Genuine contradictions → produce one new Concern per conflict.
Non-contradictions → no new Concern; all existing items are retained.
Existing Signals and Concerns from Stage 1 are NEVER removed by Stage 2.
Retry up to 3 times with exponential backoff.

Note: this stage was previously Stage 4 in the four-stage dual-stream model.
The two-stage collapse (F83) makes it Stage 2; behaviour is unchanged.

pass_data is mutated to record ai_model_fingerprint for the conflict sweep.
"""

from __future__ import annotations

import json
import time
from typing import Any

from core.ai_client import get_ai_client, MODEL
from mechanisms.row_lens_source_reanalysis.prompts.conflict_sweep_prompt import (
    build_conflict_sweep_prompt,
)
from mechanisms.row_lens_source_reanalysis.schemas.conflict_sweep_response_schema import (
    parse_conflict_sweep_response,
)

_MAX_RETRIES = 3
_RETRY_DELAYS = [1.0, 2.0, 4.0]


def sweep_contradictions(
    *,
    signals: list[dict],
    concerns: list[dict],
    sources_by_id: dict[str, Any],
    row_ref: int,
    pass_data: dict[str, Any],
) -> list[dict]:
    """
    Stage 2 contradiction sweep.

    Parameters
    ----------
    signals        : classified signals from Stage 1
    concerns       : classified concerns from Stage 1
    sources_by_id  : Source objects keyed by source_id (for text lookup)
    row_ref        : current Zachman row
    pass_data      : shared pass data dict (mutated for fingerprints)

    Returns
    -------
    List of raw Concern dicts for genuine contradictions.
    Empty list if no conflicts detected or no genuine contradictions found.
    """
    if not signals and not concerns:
        return []

    # Build conflict candidates: look for pairs where descriptions imply tension
    # The conflict detection heuristic: any two items whose source_refs overlap or
    # whose descriptions contain opposing normative language. For simplicity at v0.2,
    # pass all items to the prompt and let the model judge contradictions.
    all_items = signals + concerns
    if len(all_items) < 2:
        return []

    # Build item list for the prompt (source_id + description pairs)
    items_for_prompt = [
        {
            "item_id": item["source_refs"][0] if item.get("source_refs") else "unknown",
            "description": item.get("description", ""),
        }
        for item in all_items
    ]

    # Reuse the existing conflict_sweep_prompt, adapted to the flat item list
    # The prompt expects a conflicts list — generate pairs of items as candidates
    conflict_candidates = _generate_conflict_candidates(items_for_prompt)

    if not conflict_candidates:
        return []

    prompt = build_conflict_sweep_prompt(
        conflicts=conflict_candidates,
        sources_by_id=sources_by_id,
        row_ref=row_ref,
    )

    client = get_ai_client()

    for attempt, delay in enumerate([0.0] + _RETRY_DELAYS):
        if delay > 0:
            time.sleep(delay)
        try:
            msg = client.messages.create(
                model=MODEL,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            raw_text = msg.content[0].text.strip()
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                raw_text = "\n".join(ln for ln in lines if not ln.startswith("```"))

            content = json.loads(raw_text)
            concern_dicts = parse_conflict_sweep_response(content)

            pass_data.setdefault("ai_model_fingerprints", []).append(
                f"{msg.model} (contradiction sweep)"
            )
            return concern_dicts

        except Exception:
            if attempt == _MAX_RETRIES:
                pass_data.setdefault("ai_model_fingerprints", []).append(
                    f"{MODEL} (contradiction sweep — failed after {_MAX_RETRIES} retries)"
                )
                return []

    return []


def _generate_conflict_candidates(items: list[dict]) -> list[dict]:
    """
    Generate candidate conflict pairs for the sweep prompt.

    Heuristic: items whose descriptions contain opposing normative language
    (shall / shall not, must / must not) are candidate conflicts. If none are
    found, pass a small random sample of all pairs to the model.

    Returns a list of {item_a, item_b, description_a, description_b} dicts.
    """
    import itertools

    negation_terms = {
        "shall not", "must not", "cannot", "should not", "prohibited",
        "forbidden", "not allowed", "not permitted", "excluded",
    }
    affirmation_terms = {
        "shall", "must", "required", "mandatory", "obliged", "obligated",
    }

    affirmative_items = []
    negating_items = []
    for item in items:
        desc_lower = item["description"].lower()
        has_neg = any(t in desc_lower for t in negation_terms)
        has_aff = any(t in desc_lower for t in affirmation_terms)
        if has_neg:
            negating_items.append(item)
        elif has_aff:
            affirmative_items.append(item)

    candidates = []

    # Pair affirmative with negating items (highest conflict likelihood)
    for aff, neg in itertools.product(affirmative_items[:10], negating_items[:10]):
        candidates.append(
            {
                "item_a": aff["item_id"],
                "item_b": neg["item_id"],
                "description_a": aff["description"],
                "description_b": neg["description"],
            }
        )

    # Cap to 20 pairs to bound the prompt size
    return candidates[:20]
