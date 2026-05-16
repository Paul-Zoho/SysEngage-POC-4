"""
Stage 2 — Per-Chunk AI Classification.

Mode: IM (AI invocation) + DM (entity production).
LPM preservation: source_text and requirement_text are read-only.

Per spec §4.2:
- One Claude Sonnet API call per Domain chunk.
- Response parsed against classification_response_schema.
- Validation failure → PartialSuccess; valid items proceed; invalid recorded.
- AI returns confidence; DM entity-production step applies concern_threshold.
- Retry up to 3 times with exponential backoff (1s, 2s, 4s).

pass_data is mutated to collect ai_model_fingerprints and _collected_confidences.
"""

from __future__ import annotations

import json
import time
from typing import Any

from core.ai_client import get_ai_client, MODEL
from mechanisms.row_lens_source_reanalysis.prompts.chunk_classification_prompt import (
    build_chunk_classification_prompt,
)
from mechanisms.row_lens_source_reanalysis.schemas.classification_response_schema import (
    parse_classification_response,
    ClassificationResponseItem,
)

_MAX_RETRIES = 3
_RETRY_DELAYS = [1.0, 2.0, 4.0]


def classify_chunks(
    *,
    chunks: list[dict],
    row_ref: int,
    concern_threshold: float,
    pass_data: dict[str, Any],
) -> list[dict]:
    """
    Stage 2 per-chunk classification.

    Returns
    -------
    List of per-chunk result dicts:
      {domain_id, signals: [raw_signal], concerns: [raw_concern],
       out_of_scope_refs: [source_id], failures: [failure_dict]}
    """
    chunk_results: list[dict] = []

    if not chunks:
        return chunk_results

    client = get_ai_client()

    for chunk in chunks:
        domain_id = chunk["domain_id"]
        domain_name = chunk["domain_name"]

        prompt = build_chunk_classification_prompt(
            row_ref=row_ref,
            domain_name=domain_name,
            requirements=chunk["requirements"],
            sources=chunk["sources"],
            concern_threshold=concern_threshold,
        )

        raw_response = _invoke_with_retry(
            client=client,
            prompt=prompt,
            label=f"chunk {domain_id}",
        )

        if raw_response is None:
            pass_data.setdefault("mode_violations", [])
            chunk_results.append(
                {
                    "domain_id": domain_id,
                    "signals": [],
                    "concerns": [],
                    "out_of_scope_refs": [],
                    "failures": [
                        {
                            "item_id": domain_id,
                            "reason": f"AI invocation failed after {_MAX_RETRIES} retries",
                        }
                    ],
                }
            )
            continue

        # Record model fingerprint
        model_fingerprint = raw_response.get("model", MODEL)
        pass_data.setdefault("ai_model_fingerprints", []).append(
            f"{model_fingerprint} (chunk {domain_id})"
        )

        # Parse response
        valid_items, parse_failures = parse_classification_response(
            raw_response.get("content", {})
        )

        # Convert to raw entity dicts applying concern_threshold (DM step)
        signals, concerns, oos_refs = _produce_entities(
            items=valid_items,
            concern_threshold=concern_threshold,
        )

        # Collect confidences for mean calculation
        pass_data.setdefault("_collected_confidences", []).extend(
            item.confidence for item in valid_items
        )

        chunk_results.append(
            {
                "domain_id": domain_id,
                "signals": signals,
                "concerns": concerns,
                "out_of_scope_refs": oos_refs,
                "failures": [
                    {"item_id": f["item_id"], "reason": f["error"]}
                    for f in parse_failures
                ],
            }
        )

    return chunk_results


def _produce_entities(
    *,
    items: list[ClassificationResponseItem],
    concern_threshold: float,
) -> tuple[list[dict], list[dict], list[str]]:
    """
    DM entity production: apply concern_threshold to AI confidence scores.

    Returns (signals, concerns, out_of_scope_refs).
    """
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
            # Either classified as Concern, or Signal with confidence < threshold
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
    """
    Call Claude Sonnet API with up to 3 retries and exponential backoff.
    Returns parsed JSON dict on success, None on final failure.
    """
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
            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                raw_text = "\n".join(
                    l for l in lines if not l.startswith("```")
                )
            content = json.loads(raw_text)
            return {"model": message.model, "content": content}
        except Exception:
            if attempt == _MAX_RETRIES:
                return None
    return None
