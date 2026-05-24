"""
Step 3 — Per-Batch CCI Construction.

Mode: DM (Stage 3a-pre) + IM (Stage 3a) + DM (Stage 3b, 3c). Per-batch iteration.
No ledger write — all output held in memory until Step 5.

Per CCI Construction Mechanism Spec v0.14 §4.3:
  Stage 3a-pre — Named-item enumeration pre-processor (DM): scan each Signal for
    comma/conjunction lists of named entities; split qualifying Signals into virtual
    sub-signals (one per named item) before the AI call.  All five criteria must hold:
    1. Enumeration pattern detected (comma/conjunction list, items 1–4 words each)
    2. Items are proper nouns or named entities (capitalisation + vocabulary)
    3. Category homogeneity (all items same semantic class)
    4. Column affinity supports named instances (Where, Who, or What)
    5. List length 2–10
  Stage 3a — AI derivation: one Claude call per (expanded) batch; all six column
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
import re
import time
from dataclasses import dataclass
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

# Columns for which named-instance splitting is appropriate (Criterion 4).
_NAMED_INSTANCE_COLUMNS = frozenset({"Where", "Who", "What"})

# Common English words that must not be treated as named entities even when
# they appear capitalised at the start of a sentence or segment.
_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "to", "in", "on", "at",
    "of", "for", "with", "by", "from", "that", "this", "these", "those",
    "it", "its", "be", "been", "being", "have", "has", "had",
    "and", "or", "but", "not", "no", "any", "all", "each", "both",
    "will", "would", "could", "should", "may", "might",
    "we", "our", "they", "their", "he", "she", "i", "you",
    "when", "where", "who", "what", "why", "how",
    "if", "then", "else", "so", "as", "than", "also",
})

# Separators used to normalise comma/conjunction lists before splitting.
# Order matters: longer patterns must be replaced before shorter ones.
_SEP_COMMA_CONJ = re.compile(r",\s*(?:and|or)\s+", re.IGNORECASE)
_SEP_CONJ_ONLY = re.compile(r"\s+(?:and|or)\s+", re.IGNORECASE)
_SEP_COMMA_ONLY = re.compile(r",\s*")


# ---------------------------------------------------------------------------
# Internal types
# ---------------------------------------------------------------------------


@dataclass
class VirtualSubSignal:
    """
    Lightweight stand-in for a SignalModel used only within Stage 3a-pre.

    Carries the original signal_id so that Stage 3c cross-field validation
    still passes (the original signal_id IS in eligible_signal_ids).
    The description is scoped to the single named item extracted from the
    original Signal's list.
    """

    signal_id: str
    description: str
    signal_type: str
    confidence: float


@dataclass
class EnumerationSplitRecord:
    """
    Audit record produced by Stage 3a-pre when a Signal is split into virtual
    sub-signals.  Stored in the enumeration_splits buffer and included in
    AnalysisPass outputs.cci_data per spec v0.14 §4.6.
    """

    original_signal_id: str
    item_count: int
    items: list[str]

    def to_dict(self) -> dict:
        return {
            "original_signal_id": self.original_signal_id,
            "item_count": self.item_count,
            "items": self.items,
        }


# ---------------------------------------------------------------------------
# Stage 3a-pre — named-item enumeration pre-processor (DM)
# ---------------------------------------------------------------------------


def _qualifies_as_named_entity(phrase: str, vocab_lookup: dict) -> bool:
    """
    Criterion 2: return True if phrase is a proper noun or a known named entity.

    Accepts:
    - Phrases whose first word starts with a capital letter and is not a
      common English stopword (handles Android, Windows, AWS …)
    - Phrases whose lowercase form appears in the named-entity vocabulary
      (handles iOS, macOS, eBay …)
    """
    s = phrase.strip()
    if not s:
        return False
    words = s.split()
    if not words or len(words) > 4:
        return False
    # Vocabulary check (covers lowercase-starting terms like iOS, macOS)
    if s.lower() in vocab_lookup:
        return True
    # Capitalisation check — first char must be uppercase, first word not a stopword
    return s[0].isupper() and words[0].lower() not in _STOPWORDS


def _extract_item_from_segment(segment: str, vocab_lookup: dict) -> str | None:
    """
    Extract a named entity from a single segment (text between list separators).

    Handles three forms that occur in prose:
    - Bare item:          "Android"          → "Android"
    - Prose + item:       "deploys to iOS"   → "iOS"
    - Item + prose:       "Windows platforms"→ "Windows"

    Strategy
    --------
    1. Vocabulary-first scan (highest priority): find the rightmost vocabulary
       term in the segment, respecting word boundaries.  This handles items
       whose first character is lowercase (iOS, macOS) and items buried after
       prose (e.g. "Deployed to AWS" → "AWS").  Longer vocabulary terms take
       precedence over shorter ones (avoids "windows" matching inside
       "windows server").

    2. Capitalisation fallback (no vocabulary match): try the shortest
       qualifying leading phrase (catches "Windows platforms" → "Windows"),
       then the shortest qualifying trailing phrase (catches "Server B" when
       leading words fail).
    """
    seg = segment.strip()
    if not seg:
        return None

    seg_lower = seg.lower()

    # ------------------------------------------------------------------ #
    # Priority 1: vocabulary scan                                          #
    # ------------------------------------------------------------------ #
    # Collect all vocabulary matches, prefer longer terms, then rightmost.
    best_match: tuple[int, int, str] | None = None  # (start, end, original_text)

    for term in sorted(vocab_lookup, key=len, reverse=True):
        pos = seg_lower.find(term)
        while pos != -1:
            end = pos + len(term)
            # Word-boundary guards: character before and after must not be alpha
            before_ok = pos == 0 or not seg_lower[pos - 1].isalpha()
            after_ok = end == len(seg_lower) or not seg_lower[end].isalpha()
            if before_ok and after_ok:
                if best_match is None or pos > best_match[0]:
                    best_match = (pos, end, seg[pos:end])
                break
            pos = seg_lower.find(term, pos + 1)

    if best_match is not None:
        return best_match[2]

    # ------------------------------------------------------------------ #
    # Priority 2: capitalisation fallback for unknown proper nouns         #
    # ------------------------------------------------------------------ #
    stripped_words = [
        w.strip(".,;:()[]\"'") for w in seg.split()
        if w.strip(".,;:()[]\"'")
    ]
    if not stripped_words:
        return None

    # Try prefix: shortest qualifying leading phrase (catches "Windows platforms" → "Windows")
    for length in range(1, min(5, len(stripped_words) + 1)):
        phrase = " ".join(stripped_words[:length])
        if _qualifies_as_named_entity(phrase, vocab_lookup):
            return phrase

    # Try suffix: shortest qualifying trailing phrase
    for length in range(1, min(5, len(stripped_words) + 1)):
        phrase = " ".join(stripped_words[-length:])
        if _qualifies_as_named_entity(phrase, vocab_lookup):
            return phrase

    return None


def _detect_named_enumeration(description: str) -> list[str]:
    """
    Detect a comma/conjunction-separated list of named items in description.

    Returns the list of item strings if all five criteria are satisfied,
    or an empty list if the signal should not be split.

    Criteria evaluated here:
      1. Enumeration pattern detected (at least one separator found, items 1–4 words)
      2. Items are proper nouns or named entities
      3. Category homogeneity
      4. Column affinity in {Where, Who, What}
      5. List length 2–10
    """
    from mechanisms.cci_construction.prompts.named_entity_vocabulary import (
        NAMED_ENTITY_CATEGORIES,
        NAMED_ENTITY_LOOKUP,
    )

    # Normalise: collapse ", and"/" or" into "|", then "and/or" and bare ","
    normalised = _SEP_COMMA_CONJ.sub("|", description)
    normalised = _SEP_CONJ_ONLY.sub("|", normalised)
    normalised = _SEP_COMMA_ONLY.sub("|", normalised)

    parts = [p for p in normalised.split("|") if p.strip()]

    # Criterion 1: need at least 2 separators → at least 2 candidate parts
    if len(parts) < 2:
        return []

    # Extract a named entity from each consecutive part; stop at the first
    # part that does not yield a named item (breaks the enumeration run)
    extracted: list[str] = []
    for part in parts:
        item = _extract_item_from_segment(part, NAMED_ENTITY_LOOKUP)
        if item is None:
            break
        extracted.append(item)

    # Criterion 5: list length 2–10
    if not (2 <= len(extracted) <= 10):
        return []

    # Criterion 1 (item-level): each item must be 1–4 words
    if not all(1 <= len(item.split()) <= 4 for item in extracted):
        return []

    # Criterion 3: category homogeneity — look up each item in the vocabulary
    categories: set[str] = set()
    for item in extracted:
        cat = NAMED_ENTITY_LOOKUP.get(item.lower())
        if cat:
            categories.add(cat)

    # If multiple distinct categories → not homogeneous → do not split
    if len(categories) > 1:
        return []

    # Criterion 4: column affinity must support named instances
    if categories:
        # All items are in vocabulary → derive column affinity
        affinity = NAMED_ENTITY_CATEGORIES[next(iter(categories))]["column_affinity"]
        if affinity not in _NAMED_INSTANCE_COLUMNS:
            return []
    # else: all items are unknown proper nouns (not in vocabulary).
    # Cannot determine column affinity — fail criterion 4 conservatively.
    else:
        return []

    return extracted


def _run_stage3a_pre(
    batch: list[SignalModel],
    row_ref: int,
) -> tuple[list, list[EnumerationSplitRecord]]:
    """
    Stage 3a-pre: scan each Signal in the batch for named enumerations and
    replace qualifying Signals with N virtual sub-signals (one per named item).

    Returns
    -------
    (expanded_batch, enumeration_splits)
      expanded_batch     : list[SignalModel | VirtualSubSignal] — the batch
                           to pass to Stage 3a; split Signals are replaced.
      enumeration_splits : list[EnumerationSplitRecord] — audit records for
                           each split performed.
    """
    expanded: list = []
    splits: list[EnumerationSplitRecord] = []

    for sig in batch:
        items = _detect_named_enumeration(sig.description)
        if not items:
            expanded.append(sig)
            continue

        # All five criteria satisfied — replace with N virtual sub-signals.
        for item in items:
            expanded.append(
                VirtualSubSignal(
                    signal_id=sig.signal_id,
                    description=f"[{item}] {sig.description}",
                    signal_type=sig.signal_type,
                    confidence=sig.confidence,
                )
            )

        record = EnumerationSplitRecord(
            original_signal_id=sig.signal_id,
            item_count=len(items),
            items=items,
        )
        splits.append(record)
        print(
            f"[step3/3a-pre] {sig.signal_id} → {len(items)} virtual sub-signals:"
            f" {items}",
            flush=True,
        )

    return expanded, splits


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def derive_ccis_for_batches(
    *,
    batches: list[list[SignalModel]],
    row_ref: int,
    project_id: str,
    eligible_signal_ids: set[str],
    pass_data: dict[str, Any],
) -> tuple[list[CandidateCCI], int, int, int, list[EnumerationSplitRecord]]:
    """
    Stage 3 — process every batch through Stage 3a-pre + AI derivation + entity production.

    Parameters
    ----------
    batches            : ordered list of Signal batches from Step 2b
    row_ref            : Zachman row number (1-6)
    project_id         : project scope
    eligible_signal_ids: set of signal_ids in the Step 1 working set (for Stage 3c)
    pass_data          : mutable pass dict (ai_model_fingerprints, confidences)

    Returns
    -------
    (all_candidates, candidates_rejected_count, batches_processed, batches_failed,
     enumeration_splits)
    """
    all_candidates: list[CandidateCCI] = []
    candidates_rejected_count = 0
    batches_processed = 0
    batches_failed = 0
    all_enumeration_splits: list[EnumerationSplitRecord] = []

    if not batches:
        return (
            all_candidates,
            candidates_rejected_count,
            batches_processed,
            batches_failed,
            all_enumeration_splits,
        )

    client = get_ai_client()
    valid_cell_ids = {f"ZC-R{row_ref}-C-{col}" for col in VALID_COLUMNS}

    total_batches = len(batches)
    for batch_idx, batch in enumerate(batches):
        batch_label = f"batch-{batch_idx + 1}"

        # ------------------------------------------------------------------ #
        # Stage 3a-pre — named-item enumeration pre-processor (DM)           #
        # ------------------------------------------------------------------ #
        expanded_batch, batch_splits = _run_stage3a_pre(batch, row_ref)
        all_enumeration_splits.extend(batch_splits)

        print(
            f"[step3] R{row_ref} {batch_label}/{total_batches}"
            f"  signals_in={len(batch)}"
            f"  signals_expanded={len(expanded_batch)}"
            f"  splits={len(batch_splits)}",
            flush=True,
        )

        # ------------------------------------------------------------------ #
        # Stage 3a — AI derivation (IM)                                       #
        # ------------------------------------------------------------------ #
        prompt = build_cci_derivation_prompt(row_ref=row_ref, signals=expanded_batch)
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

    return (
        all_candidates,
        candidates_rejected_count,
        batches_processed,
        batches_failed,
        all_enumeration_splits,
    )


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
