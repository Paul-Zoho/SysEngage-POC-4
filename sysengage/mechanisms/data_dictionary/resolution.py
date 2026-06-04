"""
IM resolution-judgement act for the Data Dictionary service.

Per Data Dictionary Spec v0.1 §4.2 (D-dd-1).

judge() compares a candidate surface term (with its requirement context) against
the existing canonical entries' names + descriptions + existing synonyms and
returns best-match canonical id(s), a confidence in 0.0..1.0, and a
multi-candidate flag.

The judgement is a semantic same-entity judgement ("does this term denote an
entity already in this set, and if so which one?"), not a lexical one. One retry
on malformed model output; persistent failure → outcome=flagged (fail-safe to
human, never auto-merge on error, per D-dd-1).

Design note: embedding similarity MAY pre-rank candidates to bound the comparison
set, but the same/new/ambiguous judgement is model-made, not threshold-on-cosine
(a cosine threshold would re-introduce the string-matching failure F90 identified).
"""

from __future__ import annotations

import json
import logging
import re

from core.ai_client import MODEL, get_ai_client
from mechanisms.data_dictionary.gating import MULTI_CANDIDATE_MARGIN

_log = logging.getLogger(__name__)

_JUDGE_SYSTEM = """\
You are a semantic vocabulary analyst for a systems engineering data dictionary.
Your role is to judge whether a candidate term refers to the same entity as one
of the existing canonical dictionary entries, strictly on semantic/conceptual grounds
— not surface-form or lexical grounds.

Respond ONLY with valid JSON. No markdown, no explanation outside the JSON.
"""

_JUDGE_TEMPLATE = """\
Candidate term: {surface_term}
Requirement context (statement + row level): {context}

Existing canonical entries (name | description | known synonyms):
{canonical_text}

Task: does the candidate term refer to the same entity as one of these canonical
entries? Answer with a JSON object:
{{
  "best_canonical_ids": ["<dd_id>", ...],   // top matching canonical id(s); empty list if no adequate match
  "confidence": <0.0–1.0>,                  // confidence in the best match(es)
  "is_multi_candidate": <true|false>,       // true if two+ entries are within {margin} of the top score
  "rationale": "<one sentence>"
}}

Rules:
- If the candidate clearly refers to the same concept as a canonical entry, include that entry in best_canonical_ids.
- If the candidate clearly refers to a NEW concept not in the set, best_canonical_ids = [] and confidence should be high (you are confident it's new).
- If you are uncertain (two entries are equally plausible, or you can't tell), set is_multi_candidate=true.
- The judgement is about conceptual identity, not name similarity. "chore" and "task" may be synonyms; "worker" and "task" are different entities.
"""


def _strip_code_fence(text_: str) -> str:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text_, re.DOTALL)
    return m.group(1).strip() if m else text_.strip()


def _build_canonical_text(canonical_entries: list[dict]) -> str:
    """
    Format canonical entries for the prompt.
    Each entry: {dd_id, name, description, synonyms: [surface_term, ...]}
    """
    lines: list[str] = []
    for entry in canonical_entries:
        syn_text = ", ".join(entry.get("synonyms", [])) or "(none)"
        lines.append(
            f"  [{entry['dd_id']}] {entry['name']} — {entry.get('description', '')} "
            f"| synonyms: {syn_text}"
        )
    return "\n".join(lines) if lines else "  (empty dictionary — no canonical entries yet)"


def judge(
    *,
    surface_term: str,
    context: str,
    canonical_entries: list[dict],
) -> dict:
    """
    IM judgement: does surface_term denote an entity already in canonical_entries?

    Parameters
    ----------
    surface_term      : the candidate term to resolve
    context           : requirement statement + row context string
    canonical_entries : list of {dd_id, name, description, synonyms:[str]}

    Returns
    -------
    dict with keys:
      best_canonical_ids : list[str]  — empty if no adequate match (new canonical)
      confidence         : float
      is_multi_candidate : bool
      rationale          : str
    """
    client = get_ai_client()
    canonical_text = _build_canonical_text(canonical_entries)

    prompt = _JUDGE_TEMPLATE.format(
        surface_term=surface_term,
        context=context,
        canonical_text=canonical_text,
        margin=MULTI_CANDIDATE_MARGIN,
    )

    def _call() -> dict:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=_JUDGE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
        return json.loads(_strip_code_fence(raw))

    # One retry on malformed output; persistent failure → flagged (D-dd-1 fail-safe)
    try:
        result = _call()
        _validate_judge_output(result)
        return result
    except Exception as exc1:
        _log.warning("DD resolution judge first attempt failed: %s", exc1)
        try:
            result = _call()
            _validate_judge_output(result)
            return result
        except Exception as exc2:
            _log.error("DD resolution judge persistent failure: %s", exc2)
            return {
                "best_canonical_ids": [],
                "confidence": 0.0,
                "is_multi_candidate": False,
                "rationale": f"AI judge failed after retry: {exc2}",
                "_judge_failed": True,
            }


def _validate_judge_output(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Judge output is not a dict")
    if "best_canonical_ids" not in data:
        raise ValueError("Missing best_canonical_ids")
    if "confidence" not in data:
        raise ValueError("Missing confidence")
    conf = float(data["confidence"])
    if not (0.0 <= conf <= 1.0):
        raise ValueError(f"confidence {conf} out of range")
