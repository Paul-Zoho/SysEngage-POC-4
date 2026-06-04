"""
Confidence-band gating constants for the Requirement Matching service.

Per Requirement Matching Service Spec v0.1 §4.4.

MATCH_CONFIDENCE_BAND = 0.85 — provisional; expected to be revisited against
real match-confidence data. Change here in one place. Promote to ProjectProfile
only if distributions show projects need different bands. Until validated,
the band can be set conservatively high to favour Practitioner review.

MULTI_PARENT_MARGIN = 0.05 — parents within this margin of the top confidence
score are collectively ambiguous (multi-parent flag → outcome=flagged).
"""

MATCH_CONFIDENCE_BAND: float = 0.85
MULTI_PARENT_MARGIN: float = 0.05
