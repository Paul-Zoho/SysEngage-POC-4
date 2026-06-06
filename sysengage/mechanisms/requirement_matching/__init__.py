"""
Requirement Matching Service — cross-row standalone service (F85, F82, F93).

Per Requirement Matching Service Spec (Row 4 Physical) v0.2.
Reads ledger v2.15 (Requirement.refines_refs); writes refines_refs and
one AnalysisPass per execution (provenance — D-rm-4 reversed in v0.2).

Public API:
  from mechanisms.requirement_matching.service import (
      match_requirement, match_row, match_set,
  )
"""
