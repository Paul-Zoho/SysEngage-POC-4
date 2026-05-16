"""
Stage 2 — Residual Sources AI Classification.

Mode: IM (AI invocation) + DM (entity production).
LPM: source_text is read-only throughout.

Per spec §4.2: same three-step classification as per-chunk but without domain context.
Sources are batched into sub-batches of residual_batch_size (default 50).
Each sub-batch is one AI invocation.

pass_data is mutated to collect ai_model_fingerprints and _collected_confidences.
"""

from __future__ import annotations

import json
import time
from typing import Any

from core.ai_client import get_ai_client, MODEL
from mechanisms.row_lens_source_reanalysis.prompts.residual_classification_prompt import (
    build_residual_classification_prompt,
)
from mechanisms.row_lens_source_reanalysis.schemas.classification_response_schema import (
    parse_classification_response,
    ClassificationResponseItem,
)

_MAX_RETRIES = 3
_RETRY_DELAYS = [1.0, 2.0, 4.0]


def classify_residuals(
    *,
    residuals: list[dict],
    row_ref: int,
    concern_threshold: float,
    residual_batch_size: int,
    pass_data: dict[str, Any],
) -> dict:
    """
    Stage 2 residual classification.

    Returns
    -------
    Result dict:
      {signals: [raw_signal], concerns: [raw_concern],
       out_of_scope_refs: [source_id], failures: [failure_dict]}
    """
    signals: list[dict] = []
    concerns: list[dict] = []
    oos_refs: list[str] = []
    failures: list[dict] = []

    if not residuals:
        return {
            "signals": signals,
            "concerns": concerns,
            "out_of_scope_refs": oos_refs,
            "failures": failures,
        }

    client = get_ai_client()

    # Sub-batch residuals
    batches = [
        residuals[i : i + residual_batch_size]
        for i in range(0, len(residuals), residual_batch_size)
    ]

    for batch_idx, batch in enumerate(batches):
        prompt = build_residual_classification_prompt(
            row_ref=row_ref,
            sources=batch,
            concern_threshold=concern_threshold,
            batch_index=batch_idx,
        )

        raw_response = _invoke_with_retry(
            client=client,
            prompt=prompt,
            label=f"residual batch {batch_idx + 1}",
        )

        if raw_response is None:
            for s in batch:
                failures.append(
                    {
                        "item_id": s["source_id"],
                        "reason": f"Residual batch {batch_idx + 1}: AI invocation failed after {_MAX_RETRIES} retries",
                    }
                )
            continue

        model_fingerprint = raw_response.get("model", MODEL)
        pass_data.setdefault("ai_model_fingerprints", []).append(
            f"{model_fingerprint} (residual batch {batch_idx + 1})"
        )

        valid_items, parse_failures = parse_classification_response(
            raw_response.get("content", {})
        )

        batch_signals, batch_concerns, batch_oos = _produce_entities(
            items=valid_items,
            concern_threshold=concern_threshold,
        )

        pass_data.setdefault("_collected_confidences", []).extend(
            item.confidence for item in valid_items
        )

        signals.extend(batch_signals)
        concerns.extend(batch_concerns)
        oos_refs.extend(batch_oos)
        failures.extend(
            {"item_id": f["item_id"], "reason": f["error"]} for f in parse_failures
        )

    return {
        "signals": signals,
        "concerns": concerns,
        "out_of_scope_refs": oos_refs,
        "failures": failures,
    }


def _produce_entities(
    *,
    items: list[ClassificationResponseItem],
    concern_threshold: float,
) -> tuple[list[dict], list[dict], list[str]]:
    """DM entity production applying concern_threshold to AI confidence scores."""
    signals: list[dict] = []
    concerns: list[dict] = []
    oos_refs: list[str] = []

    for item in items:
        if item.classification == "OutOfScope":
            oos_refs.append(item.item_id)
        elif item.classification == "Signal" and item.confidence >= concern_threshold:
            signals.append(
                {
                    "source_refs": [item.item_id],
                    "signal_type": item.signal_type or "Normative",
                    "description": item.description,
                    "confidence": item.confidence,
                    "sourceatom_refs": [],
                    "derived_from_concern_id": None,
                }
            )
        else:
            concerns.append(
                {
                    "source_refs": [item.item_id],
                    "description": item.description,
                    "confidence": item.confidence,
                }
            )

    return signals, concerns, oos_refs


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
                max_tokens=4096,
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
