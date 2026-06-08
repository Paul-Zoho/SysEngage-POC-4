"""
IM matching judgement for the Requirement Matching service.

Per Requirement Matching Service Spec v0.5 §4.2 (D-rm-1, D-rm-2).

judge_refine / judge_duplicate decide for each child requirement:
  - Against cross-row candidate_parents (row n-1): refine vs none.
  - Against same-row candidate_siblings: duplicate vs none.

The row dimension pre-separates the two cases (D-rm-2, decidable).
Judgement is abstraction-level reasoning anchored on the shared DD entity.

One retry on malformed output; persistent failure → flagged (D-rm-3 fail-safe,
never auto-link on error).

v0.2: each call returns a _fingerprint dict (model, type, called_at) so the
ProvAccumulator can record ai_model_fingerprints in the AnalysisPass.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from core.ai_client import MODEL, get_ai_client
from mechanisms.requirement_matching.gating import MULTI_PARENT_MARGIN

_log = logging.getLogger(__name__)

_JUDGE_SYSTEM = """\
You are a systems engineering requirements analyst.
Your role is to judge abstraction-level relationships between requirements.
Respond ONLY with valid JSON. No markdown, no explanation outside the JSON.
"""

_REFINE_TEMPLATE = """\
Child requirement (row {child_row}):
  [{child_id}] {child_stmt}

Candidate parent requirements (row {parent_row} = child row − 1):
{parent_text}

Task: for each candidate parent, judge whether the child REFINES that parent
(same obligation, one level more concrete) or has NO relationship.

"Refine" means: the child is a more-specific, more-physically-concrete realisation
of the parent obligation. Both must address the same obligation at different
abstraction levels. Do NOT judge refine for topical overlap without abstraction-level
subordination.

Respond with a JSON object:
{{
  "outcome": "refine" | "no_match",
  "matched_parent_ids": ["<req_id>", ...],  // non-empty only when outcome=refine
  "confidence": <0.0–1.0>,
  "is_multi_parent": <true|false>,  // true if two+ parents within {margin} of top score
  "rationale": "<one sentence>"
}}
"""

_DUPLICATE_TEMPLATE = """\
Child requirement (row {child_row}):
  [{child_id}] {child_stmt}

Candidate sibling requirements (same row {child_row}):
{sibling_text}

Task: does the child state the SAME OBLIGATION as one of the siblings
(i.e. a duplicate at the same abstraction level)?

A duplicate must express the same normative obligation, not merely the same topic.
"The enterprise shall maintain records" and "The enterprise shall retain records
of all transactions" are candidates; judge carefully.

Respond with a JSON object:
{{
  "outcome": "duplicate" | "no_match",
  "duplicate_of": "<req_id>" | null,   // id of the surviving sibling if outcome=duplicate
  "confidence": <0.0–1.0>,
  "rationale": "<one sentence>"
}}
"""


def _strip_code_fence(text_: str) -> str:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text_, re.DOTALL)
    return m.group(1).strip() if m else text_.strip()


def _format_req_list(reqs: list[dict]) -> str:
    return "\n".join(
        f"  [{r['requirement_id']}] {r['statement']}" for r in reqs
    ) or "  (none)"


def _make_fingerprint(judge_type: str) -> dict[str, str]:
    return {
        "model": MODEL,
        "type": judge_type,
        "called_at": datetime.now(timezone.utc).isoformat(),
    }


def judge_refine(
    *,
    child: dict,
    candidate_parents: list[dict],
) -> dict[str, Any]:
    """
    Judge whether child refines one or more of candidate_parents.

    Returns dict with keys: outcome, matched_parent_ids, confidence,
    is_multi_parent, rationale, _fingerprints (list[dict]).
    May include _judge_failed=True on persistent AI failure.
    """
    if not candidate_parents:
        return {
            "outcome": "no_match",
            "matched_parent_ids": [],
            "confidence": 1.0,
            "is_multi_parent": False,
            "rationale": "No candidate parents to compare against",
            "_fingerprints": [],
        }

    client = get_ai_client()
    parent_row = str(int(child["row_target"]) - 1)
    prompt = _REFINE_TEMPLATE.format(
        child_id=child["requirement_id"],
        child_row=child["row_target"],
        child_stmt=child["statement"],
        parent_row=parent_row,
        parent_text=_format_req_list(candidate_parents),
        margin=MULTI_PARENT_MARGIN,
    )

    fingerprints: list[dict] = []

    def _call() -> dict:
        fp = _make_fingerprint("judge_refine")
        fingerprints.append(fp)
        msg = client.messages.create(
            model=MODEL,
            max_tokens=512,
            temperature=0,
            system=_JUDGE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(_strip_code_fence(msg.content[0].text))

    try:
        result = _call()
        _validate_refine_output(result)
        result["_fingerprints"] = fingerprints
        return result
    except Exception as exc1:
        _log.warning("judge_refine first attempt failed: %s", exc1)
        try:
            result = _call()
            _validate_refine_output(result)
            result["_fingerprints"] = fingerprints
            return result
        except Exception as exc2:
            _log.error("judge_refine persistent failure: %s", exc2)
            return {
                "outcome": "flagged",
                "matched_parent_ids": [],
                "confidence": 0.0,
                "is_multi_parent": False,
                "rationale": f"AI judge failed: {exc2}",
                "_fingerprints": fingerprints,
                "_judge_failed": True,
            }


def judge_duplicate(
    *,
    child: dict,
    candidate_siblings: list[dict],
) -> dict[str, Any]:
    """
    Judge whether child duplicates one of candidate_siblings.

    Returns dict with keys: outcome, duplicate_of, confidence,
    rationale, _fingerprints (list[dict]).
    May include _judge_failed=True on persistent AI failure.
    """
    if not candidate_siblings:
        return {
            "outcome": "no_match",
            "duplicate_of": None,
            "confidence": 1.0,
            "rationale": "No candidate siblings to compare against",
            "_fingerprints": [],
        }

    client = get_ai_client()
    prompt = _DUPLICATE_TEMPLATE.format(
        child_id=child["requirement_id"],
        child_row=child["row_target"],
        child_stmt=child["statement"],
        sibling_text=_format_req_list(candidate_siblings),
    )

    fingerprints: list[dict] = []

    def _call() -> dict:
        fp = _make_fingerprint("judge_duplicate")
        fingerprints.append(fp)
        msg = client.messages.create(
            model=MODEL,
            max_tokens=512,
            temperature=0,
            system=_JUDGE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(_strip_code_fence(msg.content[0].text))

    try:
        result = _call()
        _validate_duplicate_output(result)
        result["_fingerprints"] = fingerprints
        return result
    except Exception as exc1:
        _log.warning("judge_duplicate first attempt failed: %s", exc1)
        try:
            result = _call()
            _validate_duplicate_output(result)
            result["_fingerprints"] = fingerprints
            return result
        except Exception as exc2:
            _log.error("judge_duplicate persistent failure: %s", exc2)
            return {
                "outcome": "flagged",
                "duplicate_of": None,
                "confidence": 0.0,
                "rationale": f"AI judge failed: {exc2}",
                "_fingerprints": fingerprints,
                "_judge_failed": True,
            }


def _validate_refine_output(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Not a dict")
    if data.get("outcome") not in ("refine", "no_match"):
        raise ValueError(f"outcome must be refine|no_match, got {data.get('outcome')!r}")
    conf = float(data.get("confidence", -1))
    if not (0.0 <= conf <= 1.0):
        raise ValueError(f"confidence {conf} out of range")


def _validate_duplicate_output(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Not a dict")
    if data.get("outcome") not in ("duplicate", "no_match"):
        raise ValueError(f"outcome must be duplicate|no_match, got {data.get('outcome')!r}")
    conf = float(data.get("confidence", -1))
    if not (0.0 <= conf <= 1.0):
        raise ValueError(f"confidence {conf} out of range")
