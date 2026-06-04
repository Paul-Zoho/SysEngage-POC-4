"""
Requirement Quality Analysis — Phase 4 mechanism (F88, F89, F90).

Per Requirement Quality Analysis Spec (Row 4 Physical) v0.1.
Read-and-score: does NOT modify requirements. Writes requirement_quality_result
side-table records.

Public API:
  from mechanisms.requirement_quality.service import (
      score_requirement, score_set, aggregate,
  )
"""
