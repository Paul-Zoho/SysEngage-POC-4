"""
Step 4 — Per-Cell Deduplication Sweep.

Mode: DM (Stage 4a) + IM (Stage 4b) + DM (Stage 4c). Per-cell iteration.
No ledger write — results held in memory until Step 5.

Per CCI Construction Mechanism Spec v0.2 §4.4:

Stage 4a — Structural pre-filter (DM):
  For each pair of new candidates within the same cell: if classification_type
  and signal_refs (set equality) both match, it is a structural duplicate.
  Apply merge rule immediately without AI.

Stage 4b — AI semantic review (IM):
  Read existing committed CCIs for the cell.  Group surviving candidates +
  existing CCIs by classification_type.  For each group with >1 member, call
  Claude Sonnet with same-type pairs for semantic equivalence judgment.
  AI failure (all retries exhausted): candidates survive as Distinct (conservative,
  non-loss per spec §9.5).

Stage 4c — Merge execution (DM):
  Duplicate verdicts: merge two new candidates in-memory, or record an
  ExistingCCIUpdate if merging into a committed CCI.
  Ambiguous verdicts: both survive; reduce confidence by 0.1 (floor 0.0).

Consolidation threshold check: if candidates_in > 0 and
  (candidates_in - survivors) / candidates_in > cci_consolidation_threshold,
  record a ConsolidationFlag.
"""

from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy.orm import Session

from core.ai_client import get_ai_client, MODEL
from mechanisms.cci_construction.prompts.column_interrogatives import (
    COLUMN_INTERROGATIVES,
)
from mechanisms.cci_construction.prompts.dedup_semantic_review_prompt import (
    build_dedup_review_prompt,
)
from mechanisms.cci_construction.schemas.dedup_review_response_schema import (
    parse_dedup_response,
)
from mechanisms.cci_construction.types import (
    CandidateCCI,
    ConsolidationFlag,
    ExistingCCIUpdate,
    MergeRecord,
)
from models.cell_content_item import CellContentItemModel

_MAX_RETRIES = 3
_RETRY_DELAYS = [1.0, 2.0, 4.0]
_MAX_PAIRS_PER_CALL = 20


def deduplicate_per_cell(
    *,
    all_candidates: list[CandidateCCI],
    row_ref: int,
    project_id: str,
    consolidation_threshold: float,
    pass_data: dict[str, Any],
    session: Session,
) -> tuple[list[CandidateCCI], list[ExistingCCIUpdate], list[MergeRecord], list[ConsolidationFlag]]:
    """
    Deduplicate the global candidate set, per cell.

    Parameters
    ----------
    all_candidates          : candidates from Step 3, across all batches
    row_ref                 : Zachman row number
    project_id              : project scope
    consolidation_threshold : from ProjectProfile.cci_consolidation_threshold
    pass_data               : mutable pass dict for fingerprints/confidences
    session                 : open session for reading existing CCIs (read-only)

    Returns
    -------
    (surviving_candidates, existing_updates, merge_records, consolidation_flags)
    """
    from mechanisms.cci_construction.prompts.column_vocabulary import COLUMNS

    surviving_candidates: list[CandidateCCI] = []
    existing_updates: list[ExistingCCIUpdate] = []
    merge_records: list[MergeRecord] = []
    consolidation_flags: list[ConsolidationFlag] = []

    # Group candidates by cell_id
    candidates_by_cell: dict[str, list[CandidateCCI]] = {}
    for cand in all_candidates:
        candidates_by_cell.setdefault(cand.cell_id, []).append(cand)

    client = get_ai_client()

    for column in COLUMNS:
        cell_id = f"ZC-R{row_ref}-C-{column}"
        cell_candidates = candidates_by_cell.get(cell_id, [])

        if not cell_candidates:
            continue

        candidates_in = len(cell_candidates)

        # ------------------------------------------------------------------ #
        # Stage 4a — Structural pre-filter (DM)                              #
        # ------------------------------------------------------------------ #
        cell_candidates = _structural_pre_filter(
            candidates=cell_candidates,
            merge_records=merge_records,
        )

        # ------------------------------------------------------------------ #
        # Stage 4b — AI semantic review (IM)                                 #
        # ------------------------------------------------------------------ #
        existing_ccis = _read_existing_ccis(session=session, cell_id=cell_id, project_id=project_id)

        cell_candidates, new_existing_updates = _ai_semantic_review(
            cell_id=cell_id,
            column=column,
            row_ref=row_ref,
            candidates=cell_candidates,
            existing_ccis=existing_ccis,
            client=client,
            pass_data=pass_data,
            merge_records=merge_records,
        )

        existing_updates.extend(new_existing_updates)

        # ------------------------------------------------------------------ #
        # Consolidation threshold check (DM)                                 #
        # ------------------------------------------------------------------ #
        survivors_count = len(cell_candidates)
        if candidates_in > 0:
            reduction_ratio = (candidates_in - survivors_count) / candidates_in
            if reduction_ratio > consolidation_threshold:
                consolidation_flags.append(
                    ConsolidationFlag(
                        cell_id=cell_id,
                        candidates_in=candidates_in,
                        ccis_out=survivors_count,
                        ratio=reduction_ratio,
                    )
                )

        surviving_candidates.extend(cell_candidates)

    return surviving_candidates, existing_updates, merge_records, consolidation_flags


# --------------------------------------------------------------------------- #
# Stage 4a helpers                                                             #
# --------------------------------------------------------------------------- #

def _structural_pre_filter(
    *,
    candidates: list[CandidateCCI],
    merge_records: list[MergeRecord],
) -> list[CandidateCCI]:
    """
    Exhaustive pairwise comparison — merge exact structural duplicates in-memory.
    Structural duplicate: same classification_type AND same signal_refs set.
    """
    active = list(candidates)
    i = 0
    while i < len(active):
        j = i + 1
        merged_this_round = False
        while j < len(active):
            a = active[i]
            b = active[j]
            if (
                a.classification_type == b.classification_type
                and set(a.signal_refs) == set(b.signal_refs)
            ):
                merged = _merge_two_candidates(a, b, merged_description=None)
                merge_records.append(
                    MergeRecord(
                        surviving_ci_id="(pending)",
                        original_descriptions=[a.description, b.description],
                        merged_signal_refs=merged.signal_refs,
                    )
                )
                active[i] = merged
                active.pop(j)
                merged_this_round = True
            else:
                j += 1
        if not merged_this_round:
            i += 1
    return active


def _merge_two_candidates(
    a: CandidateCCI,
    b: CandidateCCI,
    merged_description: str | None,
) -> CandidateCCI:
    """
    Apply merge rule to two new candidates. Returns a single merged CandidateCCI.
    """
    if a.confidence >= b.confidence:
        higher, lower = a, b
    else:
        higher, lower = b, a

    description = merged_description if merged_description else higher.description
    signal_refs = sorted(set(a.signal_refs) | set(b.signal_refs))

    trigger = None
    if higher.trigger_condition and lower.trigger_condition:
        trigger = higher.trigger_condition
    elif higher.trigger_condition:
        trigger = higher.trigger_condition
    elif lower.trigger_condition:
        trigger = lower.trigger_condition

    justification = None
    if higher.justification and lower.justification:
        justification = f"{higher.justification} | {lower.justification}"
    elif higher.justification:
        justification = higher.justification
    elif lower.justification:
        justification = lower.justification

    return CandidateCCI(
        cell_id=higher.cell_id,
        column=higher.column,
        classification_type=higher.classification_type,
        description=description,
        signal_refs=signal_refs,
        confidence=max(a.confidence, b.confidence),
        trigger_condition=trigger,
        justification=justification,
    )


# --------------------------------------------------------------------------- #
# Stage 4b helpers                                                             #
# --------------------------------------------------------------------------- #

def _read_existing_ccis(
    *,
    session: Session,
    cell_id: str,
    project_id: str,
) -> list[CellContentItemModel]:
    return (
        session.query(CellContentItemModel)
        .filter(
            CellContentItemModel.cell_id == cell_id,
            CellContentItemModel.project_id == project_id,
        )
        .order_by(CellContentItemModel.ci_id)
        .all()
    )


def _ai_semantic_review(
    *,
    cell_id: str,
    column: str,
    row_ref: int,
    candidates: list[CandidateCCI],
    existing_ccis: list[CellContentItemModel],
    client,
    pass_data: dict[str, Any],
    merge_records: list[MergeRecord],
) -> tuple[list[CandidateCCI], list[ExistingCCIUpdate]]:
    """
    Stage 4b: group by classification_type, present same-type pairs to AI,
    then execute Stage 4c merge/ambiguity resolution.
    """
    existing_updates: list[ExistingCCIUpdate] = []

    if not candidates and not existing_ccis:
        return candidates, existing_updates

    column_interrogative = COLUMN_INTERROGATIVES[row_ref][column]

    # Build combined pool: new candidates + existing CCIs per classification_type
    type_groups: dict[str, list[dict]] = {}

    for idx, cand in enumerate(candidates):
        ref = f"new_{idx}"
        type_groups.setdefault(cand.classification_type, []).append(
            {
                "source": "new_candidate",
                "ref": ref,
                "description": cand.description,
                "signal_refs": cand.signal_refs,
                "confidence": cand.confidence,
                "_candidate_idx": idx,
            }
        )

    for cci in existing_ccis:
        type_groups.setdefault(cci.classification_type, []).append(
            {
                "source": "existing_cci",
                "ref": cci.ci_id,
                "description": cci.description,
                "signal_refs": list(cci.signal_refs),
                "confidence": cci.confidence,
                "_ci_id": cci.ci_id,
                "_cci": cci,
            }
        )

    # Only groups with >1 member need review
    active_candidate_indices: set[int] = set(range(len(candidates)))
    merged_into_existing: set[int] = set()  # candidate indices merged into existing CCIs
    surviving_candidates = list(candidates)

    for classification_type, group_items in type_groups.items():
        if len(group_items) <= 1:
            continue

        # Build pairs for this group
        pairs = _build_pairs(group_items)
        if not pairs:
            continue

        # Split into batches of _MAX_PAIRS_PER_CALL if needed
        pair_batches = [
            pairs[i : i + _MAX_PAIRS_PER_CALL]
            for i in range(0, len(pairs), _MAX_PAIRS_PER_CALL)
        ]

        for pair_batch in pair_batches:
            prompt = build_dedup_review_prompt(
                cell_id=cell_id,
                column=column,
                column_interrogative=column_interrogative,
                pairs=pair_batch,
            )

            raw_response = _invoke_with_retry(
                client=client,
                prompt=prompt,
                label=f"{cell_id} {classification_type}",
            )

            if raw_response is None:
                # Conservative: all candidates survive as Distinct (non-loss)
                pass_data.setdefault("_dedup_failures", []).append(
                    {"cell_id": cell_id, "classification_type": classification_type}
                )
                continue

            model_fingerprint = raw_response.get("model", MODEL)
            pass_data.setdefault("ai_model_fingerprints", []).append(
                f"{model_fingerprint} (dedup {cell_id})"
            )

            verdicts, _ = parse_dedup_response(raw_response.get("content", {}))

            # Build ref → item lookup for this batch
            ref_to_item: dict[str, dict] = {}
            for item in group_items:
                ref_to_item[item["ref"]] = item

            # Stage 4c — merge execution (DM)
            for verdict in verdicts:
                item_a = ref_to_item.get(verdict.item_a_ref)
                item_b = ref_to_item.get(verdict.item_b_ref)
                if item_a is None or item_b is None:
                    continue

                if verdict.verdict == "Duplicate":
                    _apply_duplicate(
                        item_a=item_a,
                        item_b=item_b,
                        merged_description=verdict.merged_description,
                        surviving_candidates=surviving_candidates,
                        existing_updates=existing_updates,
                        merged_into_existing=merged_into_existing,
                        merge_records=merge_records,
                    )

                elif verdict.verdict == "Ambiguous":
                    _apply_ambiguous(
                        item_a=item_a,
                        item_b=item_b,
                        surviving_candidates=surviving_candidates,
                    )

    # Remove candidates that were merged into existing CCIs
    final_survivors = [
        cand
        for idx, cand in enumerate(surviving_candidates)
        if idx not in merged_into_existing
    ]

    return final_survivors, existing_updates


def _build_pairs(group_items: list[dict]) -> list[dict]:
    """Build all pairwise combinations within a classification_type group."""
    pairs = []
    for i in range(len(group_items)):
        for j in range(i + 1, len(group_items)):
            a = group_items[i]
            b = group_items[j]
            pairs.append(
                {
                    "item_a": {
                        "source": a["source"],
                        "ref": a["ref"],
                        "description": a["description"],
                        "signal_refs": a["signal_refs"],
                    },
                    "item_b": {
                        "source": b["source"],
                        "ref": b["ref"],
                        "description": b["description"],
                        "signal_refs": b["signal_refs"],
                    },
                }
            )
    return pairs


def _apply_duplicate(
    *,
    item_a: dict,
    item_b: dict,
    merged_description: str | None,
    surviving_candidates: list[CandidateCCI],
    existing_updates: list[ExistingCCIUpdate],
    merged_into_existing: set[int],
    merge_records: list[MergeRecord],
) -> None:
    """Stage 4c: handle a Duplicate verdict."""
    a_is_existing = item_a["source"] == "existing_cci"
    b_is_existing = item_b["source"] == "existing_cci"

    if a_is_existing and not b_is_existing:
        _merge_candidate_into_existing(
            existing_item=item_a,
            new_item=item_b,
            merged_description=merged_description,
            surviving_candidates=surviving_candidates,
            existing_updates=existing_updates,
            merged_into_existing=merged_into_existing,
            merge_records=merge_records,
        )
    elif b_is_existing and not a_is_existing:
        _merge_candidate_into_existing(
            existing_item=item_b,
            new_item=item_a,
            merged_description=merged_description,
            surviving_candidates=surviving_candidates,
            existing_updates=existing_updates,
            merged_into_existing=merged_into_existing,
            merge_records=merge_records,
        )
    elif not a_is_existing and not b_is_existing:
        # Both are new candidates: merge in-memory
        idx_a = item_a.get("_candidate_idx")
        idx_b = item_b.get("_candidate_idx")
        if idx_a is None or idx_b is None:
            return

        cand_a = surviving_candidates[idx_a]
        cand_b = surviving_candidates[idx_b]

        if cand_a.confidence >= cand_b.confidence:
            higher_idx, lower_idx = idx_a, idx_b
        else:
            higher_idx, lower_idx = idx_b, idx_a

        merged = _merge_two_candidates(
            surviving_candidates[higher_idx],
            surviving_candidates[lower_idx],
            merged_description=merged_description,
        )
        merge_records.append(
            MergeRecord(
                surviving_ci_id="(pending)",
                original_descriptions=[cand_a.description, cand_b.description],
                merged_signal_refs=merged.signal_refs,
            )
        )
        surviving_candidates[higher_idx] = merged
        # Mark lower as merged (set to None sentinel — filtered at end)
        surviving_candidates[lower_idx] = None  # type: ignore[assignment]


def _merge_candidate_into_existing(
    *,
    existing_item: dict,
    new_item: dict,
    merged_description: str | None,
    surviving_candidates: list[CandidateCCI],
    existing_updates: list[ExistingCCIUpdate],
    merged_into_existing: set[int],
    merge_records: list[MergeRecord],
) -> None:
    """Stage 4c: merge a new candidate into an existing committed CCI."""
    ci_id = existing_item["_ci_id"]
    cci = existing_item["_cci"]
    new_idx = new_item.get("_candidate_idx")
    if new_idx is None:
        return

    new_cand = surviving_candidates[new_idx]
    if new_cand is None:
        return

    merged_refs = sorted(set(list(cci.signal_refs) + new_cand.signal_refs))
    merged_conf = max(cci.confidence, new_cand.confidence)
    final_description = (
        merged_description
        if merged_description
        else (cci.description if cci.confidence >= new_cand.confidence else new_cand.description)
    )

    existing_updates.append(
        ExistingCCIUpdate(
            ci_id=ci_id,
            cell_id=cci.cell_id,
            merged_signal_refs=merged_refs,
            merged_confidence=merged_conf,
            merged_description=final_description,
            original_descriptions=[cci.description, new_cand.description],
        )
    )
    merge_records.append(
        MergeRecord(
            surviving_ci_id=ci_id,
            original_descriptions=[cci.description, new_cand.description],
            merged_signal_refs=merged_refs,
        )
    )
    merged_into_existing.add(new_idx)
    surviving_candidates[new_idx] = None  # type: ignore[assignment]


def _apply_ambiguous(
    *,
    item_a: dict,
    item_b: dict,
    surviving_candidates: list[CandidateCCI],
) -> None:
    """Stage 4c: handle an Ambiguous verdict — both survive; reduce confidence by 0.1."""
    for item in (item_a, item_b):
        if item["source"] == "new_candidate":
            idx = item.get("_candidate_idx")
            if idx is not None and surviving_candidates[idx] is not None:
                cand = surviving_candidates[idx]
                cand.confidence = max(0.0, round(cand.confidence - 0.1, 10))


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
