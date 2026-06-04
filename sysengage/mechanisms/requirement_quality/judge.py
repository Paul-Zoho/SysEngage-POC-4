"""
IM-judged quality checks for Phase 4 Requirement Quality Analysis.

Per RQA Spec v0.1 §4.4 (D-q-1).

One batched model call per requirement returns judgements for:
  - ambiguous_verb         (handle/manage/support/process)      → Low (5)
  - implied_design         (implementation detail below row)    → Low (5)
  - subjective_terms       (robust/sufficient/easy/quickly)     → Low (5)
  - behaviour_present      (Constraint carrying a behaviour →   → Medium (15)
                            misclassification signal)

One retry on malformed output; persistent failure → those IM checks recorded as
not_assessed (the decidable score still stands; the requirement is flagged for
manual quality review — fail-safe, never silently pass).
"""

from __future__ import annotations

import json
import logging
import re

from core.ai_client import MODEL, get_ai_client
from mechanisms.requirement_quality.scoring import SEVERITY_MEDIUM, SEVERITY_LOW

_log = logging.getLogger(__name__)

_JUDGE_SYSTEM = """\
You are a systems engineering requirements quality analyst.
Respond ONLY with valid JSON. No markdown, no explanation outside the JSON.
"""

_JUDGE_TEMPLATE = """\
Requirement:
  Statement: {statement}
  Type: {req_type}

Assess the following quality properties. For each, answer true/false and give a brief reason.

ambiguous_verb: Does the statement use an ambiguous verb (handle, manage, support, process)
  that obscures what the subject actually does?
implied_design: Does the statement imply a specific design or implementation choice that
  should be deferred to a lower row?
subjective_terms: Does the statement use unquantified subjective terms (robust, sufficient,
  easy, quickly, timely, adequate) without measurable acceptance criteria?
behaviour_present: If the type is Constraint, does the statement describe a behaviour
  (something the subject shall DO) rather than a restriction or governance rule?
  (Set false if type is Functional or Structural.)

Respond with:
{{
  "ambiguous_verb": {{"present": <true|false>, "reason": "<brief>"}},
  "implied_design": {{"present": <true|false>, "reason": "<brief>"}},
  "subjective_terms": {{"present": <true|false>, "reason": "<brief>"}},
  "behaviour_present": {{"present": <true|false>, "reason": "<brief>"}}
}}
"""


def _strip_code_fence(text_: str) -> str:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text_, re.DOTALL)
    return m.group(1).strip() if m else text_.strip()


# Violation specs for each IM check: (rule, severity, penalty)
_IM_CHECKS = {
    "ambiguous_verb": ("ambiguous_verb", "Low", SEVERITY_LOW),
    "implied_design": ("implied_design", "Low", SEVERITY_LOW),
    "subjective_terms": ("subjective_terms", "Low", SEVERITY_LOW),
    "behaviour_present": ("behaviour_misclassification", "Medium", SEVERITY_MEDIUM),
}


def run_im_checks(
    *,
    statement: str,
    requirement_type: str,
) -> tuple[list[dict], list[str], bool]:
    """
    Run all batched IM-judged quality checks for one requirement.

    Returns
    -------
    violations      : list of violation dicts that fired (present=True)
    not_assessed    : list of check names that could not be assessed (AI failure)
    manual_review   : True if any IM check failed and was not assessed
    """
    client = get_ai_client()
    prompt = _JUDGE_TEMPLATE.format(
        statement=statement,
        req_type=requirement_type,
    )

    def _call() -> dict:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=_JUDGE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(_strip_code_fence(msg.content[0].text))

    raw: dict | None = None
    try:
        raw = _call()
    except Exception as exc1:
        _log.warning("IM judge first attempt failed: %s", exc1)
        try:
            raw = _call()
        except Exception as exc2:
            _log.error("IM judge persistent failure: %s", exc2)
            return [], list(_IM_CHECKS.keys()), True

    violations: list[dict] = []
    not_assessed: list[str] = []

    for check_key, (rule, severity, penalty) in _IM_CHECKS.items():
        check_data = raw.get(check_key)
        if not isinstance(check_data, dict):
            not_assessed.append(check_key)
            continue
        if check_data.get("present") is True:
            violations.append({
                "rule": rule,
                "severity": severity,
                "penalty": penalty,
                "detail": check_data.get("reason", ""),
            })

    manual_review = bool(not_assessed)
    return violations, not_assessed, manual_review
