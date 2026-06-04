"""
Type confirmation (classify.confirm) for Phase 4 Requirement Quality Analysis.

Per RQA Spec v0.1 §4.1.

Confirms the carried requirement_type against the F89 triad classification table
via a single IM model call (batched with other IM-judged checks per D-q-1).

If the content indicates a different type, records type_reclassification {from, to}
in the result. Does NOT write the change back to the requirement (D-q-3: read-and-
score, reclassification recorded not written back).
"""

from __future__ import annotations

import json
import logging
import re

from core.ai_client import MODEL, get_ai_client

_log = logging.getLogger(__name__)

_CLASSIFY_SYSTEM = """\
You are a systems engineering requirements classifier.
Respond ONLY with valid JSON. No markdown, no explanation outside the JSON.
"""

_CLASSIFY_TEMPLATE = """\
Requirement statement: {statement}
Carried type: {req_type}

Classify this requirement against the F89 type triad:
  Functional   — what the subject shall DO (action + object obligation)
  Constraint   — a restriction, rule, or governance obligation the subject shall comply with
                 (may have a measurable criterion → verification_method="Measurement")
  Structural   — a composition, membership, or relationship structure the subject shall HAVE

Is the carried type correct, or does the content indicate a different type?

Respond with a JSON object:
{{
  "effective_type": "Functional" | "Constraint" | "Structural",
  "reclassified": <true|false>,
  "rationale": "<one sentence>"
}}
"""


def _strip_code_fence(text_: str) -> str:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text_, re.DOTALL)
    return m.group(1).strip() if m else text_.strip()


def confirm(
    *,
    statement: str,
    requirement_type: str,
) -> dict:
    """
    Confirm or correct the requirement_type.

    Returns
    -------
    dict with keys:
      effective_type    : str (Functional | Constraint | Structural)
      reclassified      : bool
      rationale         : str
      _classify_failed  : bool (True on AI failure → not_assessed, manual review)
    """
    client = get_ai_client()
    prompt = _CLASSIFY_TEMPLATE.format(
        statement=statement,
        req_type=requirement_type,
    )

    def _call() -> dict:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=256,
            system=_CLASSIFY_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(_strip_code_fence(msg.content[0].text))
        if data.get("effective_type") not in ("Functional", "Constraint", "Structural"):
            raise ValueError(f"effective_type {data.get('effective_type')!r} not in triad")
        return data

    try:
        return _call()
    except Exception as exc1:
        _log.warning("classify.confirm first attempt failed: %s", exc1)
        try:
            return _call()
        except Exception as exc2:
            _log.error("classify.confirm persistent failure: %s", exc2)
            return {
                "effective_type": requirement_type,
                "reclassified": False,
                "rationale": f"AI classify failed: {exc2}",
                "_classify_failed": True,
            }
