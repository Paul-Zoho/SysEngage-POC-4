"""
Step 3 — Per-Batch CCI Construction.

Mode: IM (Stage 3a) + DM (Stage 3b, 3c). Per-batch iteration.
No ledger write — all output held in memory until Step 5.

Per CCI Construction Mechanism Spec v0.2 §4.3:
  Stage 3a — AI derivation: one Claude call per batch; all six column
    interrogatives presented; AI assigns column as part of derivation act.
  Stage 3b — Entity production: validate column, classification_type,
    signal_refs, confidence, description; reject malformed items.
  Stage 3c — Pydantic cross-field validation: signal_refs must resolve to
    signals in the current working set; cell_id must be valid for this row.
  Retry: up to 3 times with exponential backoff (1s, 2s, 4s) per batch.
  Batch failure: signals in failed batch recorded in AnalysisPass; execution
    continues with remaining batches.

pass_data is mutated to collect ai_model_fingerprints and _collected_confidences.
"""

from __future__ import annotations

import json
import time
from typing import Any

from core.ai_client import get_ai_client, MODEL
from mechanisms.cci_construction.prompts.cci_derivation_prompt import (
    build_cci_derivation_prompt,
)
from mechanisms.cci_construction.prompts.column_vocabulary import (
    COLUMN_VOCABULARY,
    VALID_COLUMNS,
)
from mechanisms.cci_construction.schemas.cci_construction_response_schema import (
    parse_cci_response,
)
from mechanisms.cci_construction.types import CandidateCCI
from models.signal import SignalModel

_MAX_RETRIES = 3
_RETRY_DELAYS = [1.0, 2.0, 4.0]


def derive_ccis_for_batches(
    *,
    batches: list[list[SignalModel]],
    row_ref: int,
    project_id: str,
    eligible_signal_ids: set[str],
    pass_data: dict[str, Any],
) -> tuple[list[CandidateCCI], int, int, int]:
    """
    Stage 3 — process every batch through AI derivation + entity production.

    Parameters
    ----------
    batches            : ordered list of Signal batches from Step 2b
    row_ref            : Zachman row number (1-6)
    project_id         : project scope
    eligible_signal_ids: set of signal_ids in the Step 1 working set (for Stage 3c)
    pass_data          : mutable pass dict (ai_model_fingerprints, confidences)

    Returns
    -------
    (all_candidates, candidates_rejected_count, batches_processed, batches_failed)
    """
    all_candidates: list[CandidateCCI] = []
    candidates_rejected_count = 0
    batches_processed = 0
    batches_failed = 0

    if not batches:
        return all_candidates, candidates_rejected_count, batches_processed, batches_failed

    client = get_ai_client()
    valid_cell_ids = {f"ZC-R{row_ref}-C-{col}" for col in VALID_COLUMNS}

    total_batches = len(batches)
    for batch_idx, batch in enumerate(batches):
        prompt = build_cci_derivation_prompt(row_ref=row_ref, signals=batch)
        batch_label = f"batch-{batch_idx + 1}"
        print(
            f"[step3] R{row_ref} {batch_label}/{total_batches}"
            f"  signals={len(batch)}",
            flush=True,
        )

        raw_response = _invoke_with_retry(client=client, prompt=prompt, label=batch_label)

        if raw_response is None:
            batches_failed += 1
            pass_data.setdefault("_batch_failures", []).append(
                {
                    "batch_index": batch_idx,
                    "signal_ids": [s.signal_id for s in batch],
                    "reason": f"AI invocation failed after {_MAX_RETRIES} retries",
                }
            )
            continue

        batches_processed += 1

        model_fingerprint = raw_response.get("model", MODEL)
        pass_data.setdefault("ai_model_fingerprints", []).append(
            f"{model_fingerprint} ({batch_label})"
        )

        valid_items, parse_failures = parse_cci_response(raw_response.get("content", {}))
        candidates_rejected_count += len(parse_failures)

        for item in valid_items:
            pass_data.setdefault("_collected_confidences", []).append(item.confidence)

            # Stage 3b — entity production (DM): validate each field
            rejection_reason = _validate_item(
                item=item,
                row_ref=row_ref,
                eligible_signal_ids=eligible_signal_ids,
                valid_cell_ids=valid_cell_ids,
            )
            if rejection_reason:
                candidates_rejected_count += 1
                pass_data.setdefault("_stage3b_rejections", []).append(
                    {"item": item.model_dump(), "reason": rejection_reason}
                )
                continue

            cell_id = f"ZC-R{row_ref}-C-{item.column}"
            candidate = CandidateCCI(
                cell_id=cell_id,
                column=item.column,
                classification_type=item.classification_type,
                description=item.description,
                signal_refs=sorted(item.signal_refs),
                confidence=item.confidence,
                trigger_condition=item.trigger_condition,
                justification=item.justification,
            )
            all_candidates.append(candidate)

    return all_candidates, candidates_rejected_count, batches_processed, batches_failed


def _validate_item(
    *,
    item,
    row_ref: int,
    eligible_signal_ids: set[str],
    valid_cell_ids: set[str],
) -> str | None:
    """
    Stage 3b + 3c validation. Returns rejection reason string or None if valid.
    """
    if item.column not in VALID_COLUMNS:
        return f"column '{item.column}' not in permitted set"

    permitted_types = COLUMN_VOCABULARY.get(item.column, [])
    if item.classification_type not in permitted_types:
        return (
            f"classification_type '{item.classification_type}' not permitted "
            f"for column '{item.column}' (permitted: {permitted_types})"
        )

    if not item.signal_refs:
        return "signal_refs is empty"

    if item.confidence < 0.0 or item.confidence > 1.0:
        return f"confidence {item.confidence} outside [0.0, 1.0]"

    if not item.description or not item.description.strip():
        return "description is empty"

    # Stage 3c: cross-field — every signal_ref must resolve to the working set
    unknown_refs = [r for r in item.signal_refs if r not in eligible_signal_ids]
    if unknown_refs:
        return f"signal_refs contain unknown ids: {unknown_refs}"

    # Stage 3c: cell_id must be valid for this row
    cell_id = f"ZC-R{row_ref}-C-{item.column}"
    if cell_id not in valid_cell_ids:
        return f"derived cell_id '{cell_id}' is not valid for row {row_ref}"

    return None


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
                max_tokens=8192,
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
