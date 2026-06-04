"""
Requirement Matching Service — cross-row standalone service (F85, F82, F93).

Per Requirement Matching Service Spec (Row 4 Physical) v0.1.
Reads ledger v2.13 (Requirement.refines_refs); writes refines_refs, gap records,
and the matching log.

Public API:
  from mechanisms.requirement_matching.service import (
      match_requirement, match_row, match_set,
  )
"""
