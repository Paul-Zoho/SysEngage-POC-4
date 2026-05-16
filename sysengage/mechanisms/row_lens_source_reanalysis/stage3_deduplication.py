"""
Stage 3 — Cross-Chunk Deduplication + Conflict Flagging.

Mode: DM. No AI involvement. Fully deterministic.

Per spec §4.3:
- Sources appearing in multiple chunks may receive different classifications.
- Deduplication rules (by precedence):
  1. All OutOfScope → deduplicate to one OutOfScope entry.
  2. All Signal, same signal_type → keep highest-confidence Signal; discard others.
  3. All Signal, different signal_types → cross-chunk conflict flag; retain all.
  4. Mix Signal + Concern → cross-chunk conflict flag; retain all.
  5. All Concern → keep highest-confidence Concern; discard others.
  6. Any non-OutOfScope + OutOfScope → non-OutOfScope wins; discard OutOfScope.
- Residual results are merged in without deduplication (each Source appears once).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DeduplicationResult:
    """Output of Stage 3 deduplication."""

    signals: list[dict]
    concerns: list[dict]
    out_of_scope_refs: list[str]
    conflicts: list[dict]


def deduplicate(
    *,
    chunk_results: list[dict],
    residual_results: dict,
    chunk_assignment: dict[str, list[str]],
) -> DeduplicationResult:
    """
    Merge chunk and residual results; deduplicate cross-chunk items.

    Returns DeduplicationResult with deduplicated Signals, Concerns,
    OutOfScope refs, and unresolved cross-chunk conflicts for Stage 4.
    """
    # --- Collect all per-source classifications from chunks ---
    # source_classifications: {source_id: [{domain_id, classification, signal_type, confidence, raw}]}
    source_classifications: dict[str, list[dict]] = {}

    # Index raw entities from chunk results by source_id
    for chunk in chunk_results:
        domain_id = chunk["domain_id"]

        for raw_signal in chunk["signals"]:
            for src_id in raw_signal["source_refs"]:
                source_classifications.setdefault(src_id, []).append(
                    {
                        "domain_id": domain_id,
                        "classification": "Signal",
                        "signal_type": raw_signal.get("signal_type"),
                        "confidence": raw_signal["confidence"],
                        "raw": raw_signal,
                    }
                )

        for raw_concern in chunk["concerns"]:
            for src_id in raw_concern["source_refs"]:
                source_classifications.setdefault(src_id, []).append(
                    {
                        "domain_id": domain_id,
                        "classification": "Concern",
                        "signal_type": None,
                        "confidence": raw_concern["confidence"],
                        "raw": raw_concern,
                    }
                )

        for src_id in chunk["out_of_scope_refs"]:
            source_classifications.setdefault(src_id, []).append(
                {
                    "domain_id": domain_id,
                    "classification": "OutOfScope",
                    "signal_type": None,
                    "confidence": 0.0,
                    "raw": None,
                }
            )

    # --- Deduplicate per source_id ---
    final_signals: list[dict] = []
    final_concerns: list[dict] = []
    final_oos_refs: list[str] = []
    conflicts: list[dict] = []

    for source_id, cls_list in source_classifications.items():
        if len(cls_list) == 1:
            # Only one classification — no deduplication needed
            entry = cls_list[0]
            _add_single(entry, source_id, final_signals, final_concerns, final_oos_refs)
            continue

        # Multiple classifications for this source_id
        non_oos = [c for c in cls_list if c["classification"] != "OutOfScope"]
        oos_only = [c for c in cls_list if c["classification"] == "OutOfScope"]

        if not non_oos:
            # All OutOfScope
            if source_id not in final_oos_refs:
                final_oos_refs.append(source_id)
            continue

        # At least one non-OutOfScope classification: OutOfScope entries discarded
        signal_entries = [c for c in non_oos if c["classification"] == "Signal"]
        concern_entries = [c for c in non_oos if c["classification"] == "Concern"]

        if signal_entries and concern_entries:
            # Mix Signal + Concern → conflict
            conflicts.append(
                {
                    "source_id": source_id,
                    "classifications_by_chunk": [
                        {
                            "domain_id": c["domain_id"],
                            "classification": c["classification"],
                            "signal_type": c.get("signal_type"),
                            "confidence": c["confidence"],
                        }
                        for c in non_oos
                    ],
                }
            )
            # Retain all for Stage 4 processing
            for entry in signal_entries:
                final_signals.append(_clone_raw(entry["raw"], source_id))
            for entry in concern_entries:
                final_concerns.append(_clone_raw(entry["raw"], source_id))

        elif signal_entries:
            signal_types = {c["signal_type"] for c in signal_entries}
            if len(signal_types) > 1:
                # Different signal_types → conflict
                conflicts.append(
                    {
                        "source_id": source_id,
                        "classifications_by_chunk": [
                            {
                                "domain_id": c["domain_id"],
                                "classification": c["classification"],
                                "signal_type": c.get("signal_type"),
                                "confidence": c["confidence"],
                            }
                            for c in signal_entries
                        ],
                    }
                )
                # Retain all (per spec: do not discard)
                for entry in signal_entries:
                    final_signals.append(_clone_raw(entry["raw"], source_id))
            else:
                # Same signal_type → keep highest-confidence
                best = max(signal_entries, key=lambda c: c["confidence"])
                final_signals.append(_clone_raw(best["raw"], source_id))

        else:
            # All Concern → keep highest-confidence
            best = max(concern_entries, key=lambda c: c["confidence"])
            final_concerns.append(_clone_raw(best["raw"], source_id))

    # --- Merge residual results (each source appears only once) ---
    residual_source_ids_seen = set()
    for raw_signal in residual_results.get("signals", []):
        for src_id in raw_signal["source_refs"]:
            if src_id not in residual_source_ids_seen:
                final_signals.append(dict(raw_signal))
                residual_source_ids_seen.add(src_id)

    for raw_concern in residual_results.get("concerns", []):
        for src_id in raw_concern["source_refs"]:
            if src_id not in residual_source_ids_seen:
                final_concerns.append(dict(raw_concern))
                residual_source_ids_seen.add(src_id)

    for src_id in residual_results.get("out_of_scope_refs", []):
        if src_id not in residual_source_ids_seen:
            final_oos_refs.append(src_id)
            residual_source_ids_seen.add(src_id)

    return DeduplicationResult(
        signals=final_signals,
        concerns=final_concerns,
        out_of_scope_refs=final_oos_refs,
        conflicts=conflicts,
    )


def _add_single(
    entry: dict,
    source_id: str,
    signals: list[dict],
    concerns: list[dict],
    oos_refs: list[str],
) -> None:
    """Add a single-classification entry to the appropriate output list."""
    cls = entry["classification"]
    if cls == "OutOfScope":
        if source_id not in oos_refs:
            oos_refs.append(source_id)
    elif cls == "Signal":
        signals.append(_clone_raw(entry["raw"], source_id))
    else:
        concerns.append(_clone_raw(entry["raw"], source_id))


def _clone_raw(raw: dict, source_id: str) -> dict:
    """Return a shallow copy of a raw entity dict, ensuring source_refs contains source_id."""
    clone = dict(raw)
    if source_id not in clone.get("source_refs", []):
        clone["source_refs"] = [source_id]
    return clone
