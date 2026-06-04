"""
Stage 1 — Source Classification (IM + DM).

Single-stream realisation of Row-Lens Source Re-Analysis v0.2 §4.1.

Mode: IM (AI invocation) + DM (entity production).
LPM: source_text is read-only throughout.

All project Sources for the row are classified directly — no domain-chunk
assembly and no stream 2 (dual-stream model removed per F83). Sources are
batched into sub-batches of batch_size (default 50, from ProjectProfile
residual_batch_size — retained for batch-size semantics, not chunk semantics).

One Claude Sonnet API call per sub-batch. Parse failure for a batch excludes
that batch's sources with PartialSuccess semantics; valid items proceed.

SR-1 decidable check: Requirement element ids (^R\\d{3}$) must never appear
in Signal or Concern source_refs in the single-stream model. Any such ref is
treated as a referential integrity failure (surfaced to the orchestrator as a
failure_detail item, not a hard stop).

pass_data is mutated to collect ai_model_fingerprints and _collected_confidences.
"""

from __future__ import annotations

import json
import re
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

_REQUIREMENT_ID_RE = re.compile(r"^R\d{3}$")


def classify_sources(
    *,
    sources: list[dict],
    row_ref: int,
    concern_threshold: float,
    batch_size: int,
    pass_data: dict[str, Any],
) -> dict:
    """
    Stage 1 single-stream source classification.

    Parameters
    ----------
    sources          : list of {source_id, source_text} dicts (all project sources)
    row_ref          : current Zachman row being re-analysed
    concern_threshold: confidence threshold from ProjectProfile
    batch_size       : sub-batch size (from ProjectProfile.residual_batch_size)
    pass_data        : mutable pass record (mutated for fingerprints/confidences)

    Returns
    -------
    {signals, concerns, out_of_scope_refs, failures}
    """
    signals: list[dict] = []
    concerns: list[dict] = []
    oos_refs: list[str] = []
    failures: list[dict] = []

    if not sources:
        return {
            "signals": signals,
            "concerns": concerns,
            "out_of_scope_refs": oos_refs,
            "failures": failures,
        }

    client = get_ai_client()

    batches = [
        sources[i : i + batch_size]
        for i in range(0, len(sources), batch_size)
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
            label=f"source batch {batch_idx + 1}",
        )

        if raw_response is None:
            for s in batch:
                failures.append(
                    {
                        "item_id": s["source_id"],
                        "reason": (
                            f"Source batch {batch_idx + 1}: AI invocation failed "
                            f"after {_MAX_RETRIES} retries"
                        ),
                    }
                )
            continue

        model_fingerprint = raw_response.get("model", MODEL)
        pass_data.setdefault("ai_model_fingerprints", []).append(
            f"{model_fingerprint} (source batch {batch_idx + 1})"
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

    # SR-1: no Requirement ids may appear in source_refs in single-stream model
    sr1_failures = _check_sr1(signals, concerns)
    if sr1_failures:
        failures.extend(sr1_failures)
        # Remove the offending items from the produced sets
        bad_ids = {f["item_id"] for f in sr1_failures}
        signals = [s for s in signals if s["source_refs"][0] not in bad_ids]
        concerns = [c for c in concerns if c["source_refs"][0] not in bad_ids]

    return {
        "signals": signals,
        "concerns": concerns,
        "out_of_scope_refs": oos_refs,
        "failures": failures,
    }


def _check_sr1(signals: list[dict], concerns: list[dict]) -> list[dict]:
    """
    SR-1: No Requirement ids (^R\\d{3}$) in source_refs.

    In the single-stream model, all source_refs must point at Source elements.
    A Requirement id in source_refs is a structural violation — it indicates
    the AI treated row N-1 Requirements as inputs, which is the dual-stream
    pattern removed by F83.
    """
    failures: list[dict] = []
    for item_list in (signals, concerns):
        for item in item_list:
            for ref in item.get("source_refs", []):
                if _REQUIREMENT_ID_RE.match(str(ref)):
                    failures.append(
                        {
                            "item_id": ref,
                            "reason": (
                                f"SR-1: Requirement id {ref!r} found in source_refs — "
                                "Requirement ids are not valid source references in the "
                                "single-stream model (F83)."
                            ),
                        }
                    )
    return failures


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
                raw_text = "\n".join(ln for ln in lines if not ln.startswith("```"))
            content = json.loads(raw_text)
            return {"model": message.model, "content": content}
        except Exception:
            if attempt == _MAX_RETRIES:
                return None
    return None
