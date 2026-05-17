"""
Unit tests for step6_analysis_pass helper functions.

Covers:
  - _ci_id_to_cell_id: CI ID → cell ID parsing
  - build_cci_data: cells_populated / cells_empty in-memory computation,
    including first-run (no merges) and merge-only scenarios.
"""

from __future__ import annotations

import pytest

from mechanisms.cci_construction.step6_analysis_pass import (
    _ci_id_to_cell_id,
    build_cci_data,
)
from mechanisms.cci_construction.types import ConsolidationFlag, MergeRecord


class TestCiIdToCellId:
    def test_standard_format(self):
        assert _ci_id_to_cell_id("CCI-ROW1-C-What-001") == "ZC-R1-C-What"

    def test_row_6_why_column(self):
        assert _ci_id_to_cell_id("CCI-ROW6-C-Why-099") == "ZC-R6-C-Why"

    def test_all_columns(self):
        for col in ("What", "How", "Where", "Who", "When", "Why"):
            assert _ci_id_to_cell_id(f"CCI-ROW2-C-{col}-001") == f"ZC-R2-C-{col}"

    def test_unparseable_returns_empty(self):
        assert _ci_id_to_cell_id("INVALID") == ""
        assert _ci_id_to_cell_id("") == ""
        assert _ci_id_to_cell_id("ZC-R1-C-What") == ""

    def test_pending_sentinel_returns_empty(self):
        assert _ci_id_to_cell_id("(pending)") == ""


class TestBuildCciData:
    def _make_merge(self, surviving_ci_id: str) -> MergeRecord:
        return MergeRecord(
            surviving_ci_id=surviving_ci_id,
            merged_signal_refs=["SG001"],
            original_descriptions=["desc"],
        )

    def test_first_run_cells_populated_from_new_ci_ids(self):
        """First run: cells_populated comes entirely from new_ci_ids."""
        new_ci_ids = [
            "CCI-ROW1-C-What-001",
            "CCI-ROW1-C-What-002",
            "CCI-ROW1-C-How-001",
            "CCI-ROW1-C-Why-001",
        ]
        result = build_cci_data(
            row_ref=1,
            batches_processed=1,
            batches_failed=0,
            ccis_created=4,
            ccis_merged=0,
            candidates_rejected=0,
            new_ci_ids=new_ci_ids,
            merge_records=[],
            consolidation_flags=[],
            integrity_violations=[],
        )
        assert result["cells_populated"] == 3
        assert result["cells_empty"] == 3

    def test_rerun_cells_populated_from_merge_records(self):
        """Re-run with no new CCIs: cells_populated derived from surviving_ci_id."""
        merge_records = [
            self._make_merge("CCI-ROW1-C-What-001"),
            self._make_merge("CCI-ROW1-C-What-001"),
            self._make_merge("CCI-ROW1-C-How-001"),
        ]
        result = build_cci_data(
            row_ref=1,
            batches_processed=1,
            batches_failed=0,
            ccis_created=0,
            ccis_merged=2,
            candidates_rejected=0,
            new_ci_ids=[],
            merge_records=merge_records,
            consolidation_flags=[],
            integrity_violations=[],
        )
        assert result["cells_populated"] == 2
        assert result["cells_empty"] == 4

    def test_mixed_new_and_merges_deduplicates(self):
        """Same cell appearing in both new_ci_ids and merge_records counts once."""
        result = build_cci_data(
            row_ref=1,
            batches_processed=1,
            batches_failed=0,
            ccis_created=1,
            ccis_merged=1,
            candidates_rejected=0,
            new_ci_ids=["CCI-ROW1-C-What-002"],
            merge_records=[self._make_merge("CCI-ROW1-C-What-001")],
            consolidation_flags=[],
            integrity_violations=[],
        )
        assert result["cells_populated"] == 1
        assert result["cells_empty"] == 5

    def test_no_ccis_returns_zero(self):
        """No new CCIs and no merges → cells_populated = 0."""
        result = build_cci_data(
            row_ref=1,
            batches_processed=0,
            batches_failed=0,
            ccis_created=0,
            ccis_merged=0,
            candidates_rejected=0,
            new_ci_ids=[],
            merge_records=[],
            consolidation_flags=[],
            integrity_violations=[],
        )
        assert result["cells_populated"] == 0
        assert result["cells_empty"] == 6

    def test_pending_sentinel_not_counted(self):
        """MergeRecord with surviving_ci_id='(pending)' must not inflate count."""
        result = build_cci_data(
            row_ref=1,
            batches_processed=1,
            batches_failed=0,
            ccis_created=0,
            ccis_merged=1,
            candidates_rejected=0,
            new_ci_ids=[],
            merge_records=[self._make_merge("(pending)")],
            consolidation_flags=[],
            integrity_violations=[],
        )
        assert result["cells_populated"] == 0
        assert result["cells_empty"] == 6

    def test_required_fields_all_present(self):
        """build_cci_data always emits all required cci_data keys."""
        required = {
            "row_ref", "batches_processed", "batches_failed",
            "cells_populated", "cells_empty", "ccis_created",
            "ccis_merged", "candidates_rejected",
            "merges", "consolidation_flags", "integrity_violations",
        }
        result = build_cci_data(
            row_ref=2,
            batches_processed=1,
            batches_failed=0,
            ccis_created=1,
            ccis_merged=0,
            candidates_rejected=0,
            new_ci_ids=["CCI-ROW2-C-Where-001"],
            merge_records=[],
            consolidation_flags=[],
            integrity_violations=[],
        )
        for key in required:
            assert key in result, f"Missing required field: {key}"
            assert result[key] is not None, f"Field {key!r} must not be None"
