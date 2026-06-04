"""
Confidence-band gating constants for the Data Dictionary service.

Per Data Dictionary Mechanism Spec v0.1 §4.3 and §3.2 (D-dd-2).

RESOLUTION_CONFIDENCE_BAND = 0.85 — provisional; expected to be revisited
against the first real resolution-confidence distributions. Change here
in one place when data arrives; promote to ProjectProfile parameter only if
observed distributions show projects need different bands.

MULTI_CANDIDATE_MARGIN = 0.05 — two canonicals within this margin of the top
score → ambiguous, regardless of absolute confidence (D-dd-2).
"""

RESOLUTION_CONFIDENCE_BAND: float = 0.85
MULTI_CANDIDATE_MARGIN: float = 0.05
