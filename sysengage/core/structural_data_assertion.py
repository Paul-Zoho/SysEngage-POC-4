"""
CHK-3d-13 data-asserting Structural detector.

Per Requirement Derivation Spec v0.36 §4.3 CHK-3d-13.

A Structural is *data-asserting* iff its statement:
  (a) references a DD-canonical entity, AND
  (b) asserts composition of that entity via a have/comprise/define/contain/
      consist-of/associated-with/with-attribute predicate over an attribute,
      relationship, key, or domain.

The predicate+object test is DM-decidable; genuinely ambiguous statements
are settled by an IM judge in Stage 3 (fingerprint stage3_chk3d13_judge).

Returns: "yes" | "no" | "ambiguous"
  yes       — DM-decidable data assertion (strong composition predicate)
  no        — DM-decidable non-data constraint (retention/policy/rule)
  ambiguous — requires IM judge
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Composition predicates → "yes" (data-asserting)
# Matches: "shall have", "shall comprise", "shall contain", "shall consist of",
#          "shall define", "shall be composed of", "shall be structured",
#          "shall be made up of", "shall carry", "shall store", "shall record",
#          "shall hold", "shall maintain a[n]? <entity-attribute>".
# ---------------------------------------------------------------------------
_DATA_ASSERTING_RE = re.compile(
    r"shall\s+"
    r"(?:"
    r"have\b"
    r"|comprise\b"
    r"|consist\s+of\b"
    r"|contain\b"
    r"|define\b"
    r"|be\s+composed\s+of\b"
    r"|be\s+made\s+up\s+of\b"
    r"|be\s+structured\s+(?:to\s+)?(?:include|capture|store|hold)\b"
    r"|carry\b"
    r"|store\b"
    r"|record\b"
    r"|hold\b"
    r"|be\s+associated\s+with\b"
    r")",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Non-data constraint patterns → "no"
# These are retention, auditing, policy, prohibition, and availability rules
# that do NOT define entity composition.
# ---------------------------------------------------------------------------
_NON_DATA_RE = re.compile(
    r"shall\s+"
    r"(?:"
    r"be\s+retained\b"
    r"|be\s+archived\b"
    r"|be\s+audited\b"
    r"|be\s+auditable\b"
    r"|comply\b"
    r"|be\s+enforced\b"
    r"|be\s+protected\b"
    r"|be\s+encrypted\b"
    r"|be\s+secured\b"
    r"|not\b"
    r"|be\s+accessible\b"
    r"|be\s+maintained\s+for\b"
    r"|be\s+available\s+for\b"
    r"|be\s+preserved\b"
    r"|be\s+backed\s+up\b"
    r"|be\s+recoverable\b"
    r"|be\s+logged\b"
    r"|conform\b"
    r"|comply\s+with\b"
    r")",
    re.IGNORECASE,
)


def is_data_asserting(statement: str) -> str:
    """
    DM-decidable data-assertion classifier for CHK-3d-13.

    Returns
    -------
    "yes"       Strong composition predicate detected — data-asserting.
    "no"        Strong policy/constraint/retention language — non-data constraint.
    "ambiguous" Neither strong signal — IM judge required.
    """
    s = statement.strip()

    non_data_match = _NON_DATA_RE.search(s)
    data_assert_match = _DATA_ASSERTING_RE.search(s)

    if non_data_match and not data_assert_match:
        return "no"

    if data_assert_match and not non_data_match:
        return "yes"

    # Both patterns present (rare but possible) or neither → ambiguous
    return "ambiguous"
