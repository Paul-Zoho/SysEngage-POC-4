"""
Step 4 — Per-Cell Deduplication Sweep.

Mode: DM (Stage 4a) + IM (Stage 4b) + DM (Stage 4c). Per-cell iteration.
No ledger write — results held in memory until Step 5.

Per CCI Construction Mechanism Spec v0.8 §4.4 and Row 3 Mechanism Spec v0.7 §4:

Stage 4a — Structural pre-filter (DM):
  Exhaustive pairwise comparison of new candidates within each cell.
  Three-condition rule (v0.8):
    1. classification_type equality
    2. signal_refs set equality
    3. Jaccard token-overlap of descriptions >= stage4a_similarity_threshold
  All three conditions met → structural duplicate: merge immediately without AI.
  Conditions 1+2 met but condition 3 fails (descriptions materially differ) →
    route both candidates to Stage 4b for AI semantic review (no Stage 4a merge).
  Condition 1 fails → leave for Stage 4b as normal.

Stage 4b — AI cluster review (IM):
  Read existing committed CCIs for the cell via a fresh connection with SSL retry.
  NoneType guard: any None or confidence-less item excluded before cluster review;
  recorded as step4_nonetype_excluded in execution_warnings.
  Combine surviving new candidates and existing CCIs; group by classification_type.
  For each group with >1 member: one AI call presenting the full group.
  Group-size cap: if a group exceeds 50 members, split into sub-groups of 50 and
  process each sub-group as a separate AI call; results aggregated before Stage 4c.
  AI failure (all retries exhausted): candidates survive as Distinct (conservative,
  non-loss per spec §9.5).
  SSL failure on existing-CCI read: set existing_ccis = []; record
  step4_read_failure in execution_warnings; proceed with new candidates only.

Stage 4c — Merge execution (DM):
  Duplicate cluster: merge all N members — union signal_refs, max confidence,
  AI representative_description.  If any existing CCIs in the cluster: retain
  the highest-confidence existing CCI; discard all new candidates in the cluster.
  If all new candidates: produce one merged candidate; discard the rest.
  Ambiguous entry: all members survive; reduce confidence by 0.1 (floor 0.0).

Consolidation threshold check: if candidates_in > 0 and
  (candidates_in - survivors) / candidates_in > cci_consolidation_threshold,
  record a ConsolidationFlag.
"""

from __future__ import annotations

import json
import time
from typing import Any

import sqlalchemy.exc

from core.ai_client import get_ai_client, MODEL
from core.db import get_session
from mechanisms.cci_construction.prompts.column_interrogatives import (
    COLUMN_INTERROGATIVES,
)
from mechanisms.cci_construction.prompts.dedup_cluster_review_prompt import (
    build_cluster_review_prompt,
)
from mechanisms.cci_construction.schemas.dedup_cluster_review_response_schema import (
    parse_cluster_review_response,
)
from mechanisms.cci_construction.types import (
    CandidateCCI,
    ConsolidationFlag,
    ExecutionWarning,
    ExistingCCIUpdate,
    MergeRecord,
)
from models.cell_content_item import CellContentItemModel

_MAX_RETRIES = 3
_RETRY_DELAYS = [1.0, 2.0, 4.0]
_GROUP_SIZE_CAP = 50


def deduplicate_per_cell(
    *,
    all_candidates: list[CandidateCCI],
    row_ref: int,
    project_id: str,
    consolidation_threshold: float,
    stage4a_similarity_threshold: float = 0.60,
    pass_data: dict[str, Any],
) -> tuple[
    list[CandidateCCI],
    list[ExistingCCIUpdate],
    list[MergeRecord],
    list[ConsolidationFlag],
    list[ExecutionWarning],
]:
    """
    Deduplicate the global candidate set, per cell.

    Parameters
    ----------
    all_candidates                : candidates from Step 3, across all batches
    row_ref                       : Zachman row number
    project_id                    : project scope
    consolidation_threshold       : from ProjectProfile.cci_consolidation_threshold
    stage4a_similarity_threshold  : Jaccard threshold for Stage 4a auto-merge
                                    (from ProjectProfile.stage4a_similarity_threshold,
                                    default 0.60 per spec v0.8 §3.2)
    pass_data                     : mutable pass dict for fingerprints/confidences

    Returns
    -------
    (surviving_candidates, existing_updates, merge_records,
     consolidation_flags, execution_warnings)
    """
    from mechanisms.cci_construction.prompts.column_vocabulary import COLUMNS

    surviving_candidates: list[CandidateCCI] = []
    existing_updates: list[ExistingCCIUpdate] = []
    merge_records: list[MergeRecord] = []
    consolidation_flags: list[ConsolidationFlag] = []
    execution_warnings: list[ExecutionWarning] = []

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
            similarity_threshold=stage4a_similarity_threshold,
        )

        # ------------------------------------------------------------------ #
        # Stage 4b — AI cluster review (IM)                                  #
        # ------------------------------------------------------------------ #
        cell_candidates, new_existing_updates = _ai_cluster_review(
            cell_id=cell_id,
            column=column,
            row_ref=row_ref,
            candidates=cell_candidates,
            project_id=project_id,
            client=client,
            pass_data=pass_data,
            merge_records=merge_records,
            execution_warnings=execution_warnings,
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

    return (
        surviving_candidates,
        existing_updates,
        merge_records,
        consolidation_flags,
        execution_warnings,
    )


# --------------------------------------------------------------------------- #
# Stage 4a helpers                                                             #
# --------------------------------------------------------------------------- #

_STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "and", "or", "of",
    "in", "to", "for", "that", "this", "it", "its", "be", "by", "at",
    "as", "on", "with", "from", "not", "but",
})


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """
    Jaccard token-overlap similarity between two description strings.

    Tokens are whitespace-split, lowercased, and filtered against a compact
    English stopword list.  Returns 0.0 if either token set is empty after
    filtering (conservative — routes the pair to Stage 4b).

    Per spec v0.8 §4.4: used only within Stage 4a to guard auto-merge.
    """
    import re

    def _tokenise(text: str) -> frozenset[str]:
        raw = re.split(r"[\s\W]+", text.lower())
        return frozenset(t for t in raw if t and t not in _STOPWORDS)

    tokens_a = _tokenise(text_a)
    tokens_b = _tokenise(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union > 0 else 0.0


def _structural_pre_filter(
    *,
    candidates: list[CandidateCCI],
    merge_records: list[MergeRecord],
    similarity_threshold: float = 0.60,
) -> list[CandidateCCI]:
    """
    Exhaustive pairwise comparison — merge structural duplicates in-memory.

    Three-condition rule per spec v0.8 §4.4:
      1. classification_type equality
      2. signal_refs set equality
      3. Jaccard description similarity >= similarity_threshold

    All three → merge at Stage 4a (structural duplicate).
    Conditions 1+2 only (descriptions differ materially) → leave both in
      the active list; they will be picked up by Stage 4b for AI review.
    Condition 1 fails → leave both (Stage 4b handles normally).
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
                similarity = _jaccard_similarity(a.description, b.description)
                if similarity >= similarity_threshold:
                    # All three conditions met — structural duplicate: merge now.
                    merged = _merge_two_candidates(a, b, merged_description=None)
                    _mr = MergeRecord(
                        surviving_ci_id="(pending)",
                        original_descriptions=[a.description, b.description],
                        merged_signal_refs=merged.signal_refs,
                    )
                    merge_records.append(_mr)
                    # Carry forward pending MRs from both legs so the chain
                    # resolves to the final survivor after Step 5.
                    merged._pending_mrs = (  # type: ignore[attr-defined]
                        getattr(a, "_pending_mrs", [])
                        + getattr(b, "_pending_mrs", [])
                        + [_mr]
                    )
                    active[i] = merged
                    active.pop(j)
                    merged_this_round = True
                else:
                    # Conditions 1+2 only — descriptions differ; route to Stage 4b.
                    j += 1
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
    """Apply merge rule to two new candidates. Returns a single merged CandidateCCI."""
    if a.confidence >= b.confidence:
        higher, lower = a, b
    else:
        higher, lower = b, a

    description = merged_description if merged_description else higher.description
    signal_refs = sorted(set(a.signal_refs) | set(b.signal_refs))

    trigger = higher.trigger_condition or lower.trigger_condition
    if higher.trigger_condition and lower.trigger_condition:
        trigger = higher.trigger_condition

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
    cell_id: str,
    project_id: str,
) -> list[CellContentItemModel]:
    """
    Read committed CCIs for a cell using a fresh, immediately-closed session.

    Retries up to 3 times with exponential backoff on connection/SSL failures.
    Raises the last exception if all retries are exhausted — caller records
    step4_read_failure and falls back to an empty existing-CCI set.
    """
    last_exc: Exception | None = None
    delays = [0.0] + _RETRY_DELAYS

    for attempt, delay in enumerate(delays):
        if delay > 0:
            time.sleep(delay)
        session = get_session()
        try:
            result = (
                session.query(CellContentItemModel)
                .filter(
                    CellContentItemModel.cell_id == cell_id,
                    CellContentItemModel.project_id == project_id,
                )
                .order_by(CellContentItemModel.ci_id)
                .all()
            )
            return result
        except (sqlalchemy.exc.OperationalError, Exception) as exc:
            last_exc = exc
        finally:
            session.close()

    raise last_exc  # type: ignore[misc]


def _ai_cluster_review(
    *,
    cell_id: str,
    column: str,
    row_ref: int,
    candidates: list[CandidateCCI],
    project_id: str,
    client,
    pass_data: dict[str, Any],
    merge_records: list[MergeRecord],
    execution_warnings: list[ExecutionWarning],
) -> tuple[list[CandidateCCI], list[ExistingCCIUpdate]]:
    """
    Stage 4b: read existing CCIs, apply NoneType guard, group by classification_type,
    call AI per group (with sub-group splitting if > GROUP_SIZE_CAP), then execute
    Stage 4c merge/ambiguity resolution.
    """
    existing_updates: list[ExistingCCIUpdate] = []

    if not candidates:
        return candidates, existing_updates

    column_interrogative = COLUMN_INTERROGATIVES[row_ref][column]

    # ------------------------------------------------------------------ #
    # Read existing CCIs with SSL retry                                   #
    # ------------------------------------------------------------------ #
    try:
        raw_existing = _read_existing_ccis(cell_id=cell_id, project_id=project_id)
    except Exception:
        raw_existing = []
        execution_warnings.append(ExecutionWarning(
            warning_type="step4_read_failure",
            detail={"cell_id": cell_id},
        ))

    # ------------------------------------------------------------------ #
    # NoneType guard — validate every item before cluster review          #
    # ------------------------------------------------------------------ #
    existing_ccis: list[CellContentItemModel] = []
    for item in raw_existing:
        if item is None or not hasattr(item, "confidence"):
            execution_warnings.append(ExecutionWarning(
                warning_type="step4_nonetype_excluded",
                detail={
                    "cell_id": cell_id,
                    "ci_id_or_ref": getattr(item, "ci_id", repr(item)),
                },
            ))
        else:
            existing_ccis.append(item)

    # Guard on candidates too (defensive)
    valid_candidates: list[CandidateCCI] = []
    for cand in candidates:
        if cand is None or not hasattr(cand, "confidence"):
            execution_warnings.append(ExecutionWarning(
                warning_type="step4_nonetype_excluded",
                detail={"cell_id": cell_id, "ci_id_or_ref": repr(cand)},
            ))
        else:
            valid_candidates.append(cand)
    candidates = valid_candidates

    if not candidates and not existing_ccis:
        return candidates, existing_updates

    # ------------------------------------------------------------------ #
    # Build combined pool grouped by classification_type                  #
    # ------------------------------------------------------------------ #
    type_groups: dict[str, list[dict]] = {}

    for idx, cand in enumerate(candidates):
        ref = f"new_{idx}"
        type_groups.setdefault(cand.classification_type, []).append({
            "source": "new_candidate",
            "ref": ref,
            "description": cand.description,
            "signal_refs": cand.signal_refs,
            "confidence": cand.confidence,
            "is_named_instance": cand.is_named_instance,
            "_candidate_idx": idx,
        })

    for cci in existing_ccis:
        type_groups.setdefault(cci.classification_type, []).append({
            "source": "existing_cci",
            "ref": cci.ci_id,
            "description": cci.description,
            "signal_refs": list(cci.signal_refs),
            "confidence": cci.confidence,
            "_ci_id": cci.ci_id,
            "_cci": cci,
        })

    surviving_candidates = list(candidates)
    merged_into_existing: set[int] = set()

    for classification_type, group_items in type_groups.items():
        if len(group_items) <= 1:
            continue

        # ------------------------------------------------------------------ #
        # Named-instance bypass (DM) — per spec v0.9 §4.4                   #
        # If every new candidate in the group carries is_named_instance=True, #
        # treat the whole group as Distinct without an AI call.              #
        # ------------------------------------------------------------------ #
        new_items_in_group = [
            it for it in group_items if it["source"] == "new_candidate"
        ]
        # Named-instance bypass only applies when all new candidates in the
        # group share a SINGLE common signal source.  If candidates originate
        # from different Signals they were independently derived and are not
        # a named-instance group — they must go through normal AI review.
        _new_signal_sets = [frozenset(it["signal_refs"]) for it in new_items_in_group]
        _all_same_signal = len(set(_new_signal_sets)) == 1 if _new_signal_sets else False
        if new_items_in_group and _all_same_signal and all(
            it.get("is_named_instance", False) for it in new_items_in_group
        ):
            execution_warnings.append(ExecutionWarning(
                warning_type="stage4b_named_instance_bypass",
                detail={
                    "cell_id": cell_id,
                    "classification_type": classification_type,
                    "member_count": len(group_items),
                },
            ))
            continue

        # ------------------------------------------------------------------ #
        # Group-size cap: split into sub-groups if > _GROUP_SIZE_CAP        #
        # ------------------------------------------------------------------ #
        if len(group_items) > _GROUP_SIZE_CAP:
            sub_groups = [
                group_items[i: i + _GROUP_SIZE_CAP]
                for i in range(0, len(group_items), _GROUP_SIZE_CAP)
            ]
            execution_warnings.append(ExecutionWarning(
                warning_type="step4_sub_group_split",
                detail={
                    "cell_id": cell_id,
                    "classification_type": classification_type,
                    "group_size": len(group_items),
                    "sub_group_count": len(sub_groups),
                },
            ))
        else:
            sub_groups = [group_items]

        # Collect all cluster/ambiguous results across sub-groups
        all_cluster_entries = []
        all_ambiguous_entries = []

        for sub_group in sub_groups:
            if len(sub_group) <= 1:
                continue

            member_list = [
                {
                    "ref": item["ref"],
                    "source": item["source"],
                    "description": item["description"],
                    "signal_refs": item["signal_refs"],
                    "confidence": item["confidence"],
                }
                for item in sub_group
            ]

            prompt = build_cluster_review_prompt(
                cell_id=cell_id,
                column=column,
                column_interrogative=column_interrogative,
                members=member_list,
            )

            raw_response = _invoke_with_retry(
                client=client,
                prompt=prompt,
                label=f"{cell_id} {classification_type}",
            )

            if raw_response is None:
                pass_data.setdefault("_dedup_failures", []).append(
                    {"cell_id": cell_id, "classification_type": classification_type}
                )
                continue

            model_fingerprint = raw_response.get("model", MODEL)
            pass_data.setdefault("ai_model_fingerprints", []).append(
                f"{model_fingerprint} (dedup {cell_id})"
            )

            cluster_response, _ = parse_cluster_review_response(
                raw_response.get("content", {})
            )

            if cluster_response is None:
                continue

            all_cluster_entries.extend(cluster_response.clusters)
            all_ambiguous_entries.extend(cluster_response.ambiguous)

        # ------------------------------------------------------------------ #
        # Stage 4c — Merge execution across all sub-group results            #
        # ------------------------------------------------------------------ #
        ref_to_item: dict[str, dict] = {item["ref"]: item for item in group_items}

        for cluster in all_cluster_entries:
            _apply_duplicate_cluster(
                cluster_refs=cluster.member_refs,
                representative_description=cluster.representative_description,
                ref_to_item=ref_to_item,
                surviving_candidates=surviving_candidates,
                existing_updates=existing_updates,
                merged_into_existing=merged_into_existing,
                merge_records=merge_records,
            )

        for ambiguous in all_ambiguous_entries:
            _apply_ambiguous_cluster(
                member_refs=ambiguous.member_refs,
                ref_to_item=ref_to_item,
                surviving_candidates=surviving_candidates,
            )

    # Filter out candidates merged into existing CCIs (marked None sentinel)
    final_survivors = [
        cand
        for idx, cand in enumerate(surviving_candidates)
        if idx not in merged_into_existing and cand is not None
    ]

    return final_survivors, existing_updates


# --------------------------------------------------------------------------- #
# Stage 4c helpers                                                             #
# --------------------------------------------------------------------------- #

def _apply_duplicate_cluster(
    *,
    cluster_refs: list[str],
    representative_description: str,
    ref_to_item: dict[str, dict],
    surviving_candidates: list[CandidateCCI],
    existing_updates: list[ExistingCCIUpdate],
    merged_into_existing: set[int],
    merge_records: list[MergeRecord],
) -> None:
    """Stage 4c: handle a Duplicate cluster of N members."""
    members = [ref_to_item[ref] for ref in cluster_refs if ref in ref_to_item]
    if len(members) < 2:
        return

    existing_members = [m for m in members if m["source"] == "existing_cci"]
    new_members = [m for m in members if m["source"] == "new_candidate"]

    # Union all signal_refs across all cluster members
    all_signal_refs: set[str] = set()
    for m in members:
        all_signal_refs.update(m["signal_refs"])
    merged_refs = sorted(all_signal_refs)

    # Max confidence across all cluster members
    merged_conf = max(m["confidence"] for m in members)

    all_descriptions = [m["description"] for m in members]

    if existing_members:
        # Retain the existing CCI with highest confidence as the surviving entity
        surviving_existing = max(existing_members, key=lambda m: m["confidence"])
        cci = surviving_existing["_cci"]
        ci_id = surviving_existing["_ci_id"]

        existing_updates.append(
            ExistingCCIUpdate(
                ci_id=ci_id,
                cell_id=cci.cell_id,
                merged_signal_refs=merged_refs,
                merged_confidence=merged_conf,
                merged_description=representative_description or cci.description,
                original_descriptions=all_descriptions,
            )
        )
        merge_records.append(
            MergeRecord(
                surviving_ci_id=ci_id,
                original_descriptions=all_descriptions,
                merged_signal_refs=merged_refs,
            )
        )

        # Discard all new candidates in the cluster
        for nm in new_members:
            idx = nm.get("_candidate_idx")
            if idx is not None:
                merged_into_existing.add(idx)
                surviving_candidates[idx] = None  # type: ignore[assignment]

    else:
        # All new candidates — commit the highest-confidence one as a new CCI.
        # Per spec v0.8 §4.4: do NOT discard all candidates; exactly one merged
        # candidate must survive per duplicate cluster.
        if not new_members:
            return

        # Find the first viable base: highest-confidence new candidate whose
        # slot in surviving_candidates is still live (not already consumed by a
        # prior overlapping cluster within this group).  Iterating in descending
        # confidence order ensures we always pick the best available option.
        base_cand: CandidateCCI | None = None
        base_idx: int | None = None
        for nm in sorted(new_members, key=lambda m: m["confidence"], reverse=True):
            idx = nm.get("_candidate_idx")
            if idx is None:
                continue
            cand = surviving_candidates[idx]
            if cand is not None:
                base_idx = idx
                base_cand = cand
                break

        if base_cand is None or base_idx is None:
            # Every member was already consumed by a prior overlapping cluster.
            # Leave any still-live members intact rather than silently losing data.
            return

        # Gather justifications from the CandidateCCI structs (group_items dicts
        # do not carry justification — it lives on the CandidateCCI objects).
        cluster_justifications = [
            surviving_candidates[m["_candidate_idx"]].justification
            for m in new_members
            if m.get("_candidate_idx") is not None
            and surviving_candidates[m["_candidate_idx"]] is not None
        ]

        merged_candidate = CandidateCCI(
            cell_id=base_cand.cell_id,
            column=base_cand.column,
            classification_type=base_cand.classification_type,
            description=representative_description or base_cand.description,
            signal_refs=merged_refs,
            confidence=merged_conf,
            trigger_condition=base_cand.trigger_condition,
            justification=_merge_justifications(cluster_justifications),
        )

        _mr = MergeRecord(
            surviving_ci_id="(pending)",
            original_descriptions=all_descriptions,
            merged_signal_refs=merged_refs,
        )
        merge_records.append(_mr)

        # Gather any pending MRs already attached to the consumed candidates
        # (e.g. from Stage 4a chain merges) and transfer them to the new
        # merged_candidate so the entire chain resolves after Step 5.
        _inherited_mrs: list[MergeRecord] = []
        for nm in new_members:
            _idx = nm.get("_candidate_idx")
            if _idx is not None:
                _c = surviving_candidates[_idx]
                if _c is not None:
                    _inherited_mrs.extend(getattr(_c, "_pending_mrs", []))
        merged_candidate._pending_mrs = _inherited_mrs + [_mr]  # type: ignore[attr-defined]

        # Install merged candidate at base slot; discard all other members.
        surviving_candidates[base_idx] = merged_candidate
        for nm in new_members:
            idx = nm.get("_candidate_idx")
            if idx is not None and idx != base_idx:
                surviving_candidates[idx] = None  # type: ignore[assignment]


def _merge_justifications(justifications: list[str | None]) -> str | None:
    """Concatenate non-null justifications with ' | ' separator."""
    non_null = [j for j in justifications if j]
    if not non_null:
        return None
    return " | ".join(non_null)


def _apply_ambiguous_cluster(
    *,
    member_refs: list[str],
    ref_to_item: dict[str, dict],
    surviving_candidates: list[CandidateCCI],
) -> None:
    """
    Stage 4c: handle an Ambiguous entry — all members survive with confidence -0.1.
    Applies to both new candidates and existing CCIs in the combined set.
    """
    for ref in member_refs:
        item = ref_to_item.get(ref)
        if item is None:
            continue
        if item["source"] == "new_candidate":
            idx = item.get("_candidate_idx")
            if idx is not None and surviving_candidates[idx] is not None:
                cand = surviving_candidates[idx]
                cand.confidence = max(0.0, round(cand.confidence - 0.1, 10))


# --------------------------------------------------------------------------- #
# AI invocation helper                                                         #
# --------------------------------------------------------------------------- #

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
