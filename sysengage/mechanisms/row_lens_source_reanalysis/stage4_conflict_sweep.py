"""
Stage 4 — Cross-Chunk Conflict Sweep.

Mode: IM (AI invocation) + DM (Concern production).
LPM: source_text is read-only; never rewritten.

Per spec §4.4:
- Receives conflict list from Stage 3.
- If conflict list is empty: Stage 4 produces no output.
- One Claude Sonnet API call for all conflicts (single invocation).
- Genuine contradictions → produce one new Concern per conflict.
- Non-contradictions → no new Concern; all existing Signals retained.
- Existing Signals from Stage 2/3 are NEVER removed by Stage 4.
- Retry up to 3 times with exponential backoff.

pass_data is mutated to record ai_model_fingerprint for conflict sweep.
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


def sweep_conflicts(
    *,
    conflicts: list[dict],
    sources_by_id: dict[str, Any],
    row_ref: int,
    pass_data: dict[str, Any],
) -> list[dict]:
    """
    Stage 4 conflict sweep.

    Parameters
    ----------
    conflicts      : cross-chunk conflict list from Stage 3
    sources_by_id  : Source objects keyed by source_id (for text lookup)
    row_ref        : current Zachman row
    pass_data      : shared pass data dict (mutated for fingerprints)

    Returns
    -------
    List of raw Concern dicts for genuine contradictions.
    Empty list if no conflicts or no genuine contradictions found.
    """
    if not conflicts:
        return []

    # Enrich conflicts with source_text for the prompt
    enriched: list[dict] = []
    for conflict in conflicts:
        source_id = conflict["source_id"]
        source = sources_by_id.get(source_id)
        source_text = getattr(source, "source_text", "") if source else ""
        enriched.append(
            {
                "source_id": source_id,
                "source_text": source_text,
                "classifications_by_chunk": conflict.get("classifications_by_chunk", []),
            }
        )

    prompt = build_conflict_sweep_prompt(
        row_ref=row_ref,
        conflicts=enriched,
    )

    client = get_ai_client()
    raw_response = _invoke_with_retry(
        client=client,
        prompt=prompt,
        label="conflict sweep",
    )

    if raw_response is None:
        # AI failure: record in pass_data; return empty (no new Concerns from sweep)
        pass_data.setdefault("mode_violations", [])
        pass_data.setdefault("ai_model_fingerprints", []).append(
            f"{MODEL} (conflict sweep — FAILED)"
        )
        return []

    model_fingerprint = raw_response.get("model", MODEL)
    pass_data.setdefault("ai_model_fingerprints", []).append(
        f"{model_fingerprint} (conflict sweep)"
    )

    valid_items, parse_failures = parse_conflict_sweep_response(
        raw_response.get("content", {})
    )

    # DM entity production: genuine contradictions → new Concerns
    new_concerns: list[dict] = []
    for item in valid_items:
        if item.is_genuine_contradiction:
            new_concerns.append(
                {
                    "source_refs": [item.source_id],
                    "description": item.rationale,
                    "confidence": 0.5,  # Conservative default for contradiction Concerns
                }
            )
        # Non-contradictions: existing Signals retained; no action needed here.

    # Collect confidences for mean calculation
    pass_data.setdefault("_collected_confidences", []).extend(
        c["confidence"] for c in new_concerns
    )

    return new_concerns


def _invoke_with_retry(
    *,
    client,
    prompt: str,
    label: str,
) -> dict | None:
    """Call Claude Sonnet API with up to 3 retries and exponential backoff."""
    for attempt, delay in enumerate([0.0] + _RETRY_DELAYS):
        if delay > 0:
            time.sleep(delay)
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            raw_text = message.content[0].text.strip()
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                raw_text = "\n".join(l for l in lines if not l.startswith("```"))
            content = json.loads(raw_text)
            return {"model": message.model, "content": content}
        except Exception:
            if attempt == _MAX_RETRIES:
                return None
    return None
