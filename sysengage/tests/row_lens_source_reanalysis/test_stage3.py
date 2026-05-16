"""
Stage 3 deduplication unit tests.

Tests all deduplication rules from spec §4.3:
- All OutOfScope → single OOS entry
- All Signal, same type → keep highest confidence
- All Signal, different types → conflict
- Mix Signal + Concern → conflict
- All Concern → keep highest confidence
- Non-OOS + OOS → non-OOS wins
- Residual results merged without duplication
"""

from __future__ import annotations

import pytest
from mechanisms.row_lens_source_reanalysis.stage3_deduplication import deduplicate


def _make_signal(source_id: str, signal_type: str = "Normative", confidence: float = 0.8) -> dict:
    return {
        "source_refs": [source_id],
        "signal_type": signal_type,
        "description": f"Signal about {source_id}",
        "confidence": confidence,
        "sourceatom_refs": [],
        "derived_from_concern_id": None,
    }


def _make_concern(source_id: str, confidence: float = 0.5) -> dict:
    return {
        "source_refs": [source_id],
        "description": f"Concern about {source_id}",
        "confidence": confidence,
    }


def _make_chunk_result(
    domain_id: str,
    signals: list[dict] | None = None,
    concerns: list[dict] | None = None,
    oos: list[str] | None = None,
) -> dict:
    return {
        "domain_id": domain_id,
        "signals": signals or [],
        "concerns": concerns or [],
        "out_of_scope_refs": oos or [],
        "failures": [],
    }


def _empty_residual():
    return {"signals": [], "concerns": [], "out_of_scope_refs": [], "failures": []}


class TestAllOutOfScope:
    def test_all_oos_deduped_to_one(self):
        chunk_results = [
            _make_chunk_result("D1", oos=["S001"]),
            _make_chunk_result("D2", oos=["S001"]),
        ]
        result = deduplicate(
            chunk_results=chunk_results,
            residual_results=_empty_residual(),
            chunk_assignment={"S001": ["D1", "D2"]},
        )
        assert "S001" in result.out_of_scope_refs
        assert result.out_of_scope_refs.count("S001") == 1
        assert result.signals == []
        assert result.concerns == []
        assert result.conflicts == []


class TestAllSignalSameType:
    def test_keeps_highest_confidence(self):
        chunk_results = [
            _make_chunk_result("D1", signals=[_make_signal("S002", confidence=0.9)]),
            _make_chunk_result("D2", signals=[_make_signal("S002", confidence=0.7)]),
        ]
        result = deduplicate(
            chunk_results=chunk_results,
            residual_results=_empty_residual(),
            chunk_assignment={"S002": ["D1", "D2"]},
        )
        assert len(result.signals) == 1
        assert result.signals[0]["confidence"] == 0.9
        assert result.concerns == []
        assert result.conflicts == []

    def test_source_refs_preserved(self):
        chunk_results = [
            _make_chunk_result("D1", signals=[_make_signal("S003", confidence=0.85)]),
            _make_chunk_result("D2", signals=[_make_signal("S003", confidence=0.75)]),
        ]
        result = deduplicate(
            chunk_results=chunk_results,
            residual_results=_empty_residual(),
            chunk_assignment={"S003": ["D1", "D2"]},
        )
        assert "S003" in result.signals[0]["source_refs"]


class TestAllSignalDifferentTypes:
    def test_different_types_flagged_as_conflict(self):
        chunk_results = [
            _make_chunk_result("D1", signals=[_make_signal("S004", signal_type="Normative", confidence=0.9)]),
            _make_chunk_result("D2", signals=[_make_signal("S004", signal_type="Intent", confidence=0.8)]),
        ]
        result = deduplicate(
            chunk_results=chunk_results,
            residual_results=_empty_residual(),
            chunk_assignment={"S004": ["D1", "D2"]},
        )
        assert len(result.conflicts) == 1
        assert result.conflicts[0]["source_id"] == "S004"
        # All signals retained per spec
        assert len(result.signals) == 2

    def test_conflict_has_classifications_by_chunk(self):
        chunk_results = [
            _make_chunk_result("D1", signals=[_make_signal("S005", signal_type="Actor")]),
            _make_chunk_result("D2", signals=[_make_signal("S005", signal_type="Quality")]),
        ]
        result = deduplicate(
            chunk_results=chunk_results,
            residual_results=_empty_residual(),
            chunk_assignment={"S005": ["D1", "D2"]},
        )
        conflict = result.conflicts[0]
        assert "classifications_by_chunk" in conflict
        domain_ids = [c["domain_id"] for c in conflict["classifications_by_chunk"]]
        assert "D1" in domain_ids
        assert "D2" in domain_ids


class TestMixSignalAndConcern:
    def test_mix_produces_conflict(self):
        chunk_results = [
            _make_chunk_result("D1", signals=[_make_signal("S006")]),
            _make_chunk_result("D2", concerns=[_make_concern("S006")]),
        ]
        result = deduplicate(
            chunk_results=chunk_results,
            residual_results=_empty_residual(),
            chunk_assignment={"S006": ["D1", "D2"]},
        )
        assert len(result.conflicts) == 1
        assert result.conflicts[0]["source_id"] == "S006"
        # Both retained
        assert len(result.signals) >= 1
        assert len(result.concerns) >= 1


class TestAllConcern:
    def test_all_concern_keeps_highest_confidence(self):
        chunk_results = [
            _make_chunk_result("D1", concerns=[_make_concern("S007", confidence=0.6)]),
            _make_chunk_result("D2", concerns=[_make_concern("S007", confidence=0.4)]),
        ]
        result = deduplicate(
            chunk_results=chunk_results,
            residual_results=_empty_residual(),
            chunk_assignment={"S007": ["D1", "D2"]},
        )
        assert len(result.concerns) == 1
        assert result.concerns[0]["confidence"] == 0.6
        assert result.signals == []
        assert result.conflicts == []


class TestOosWithNonOos:
    def test_non_oos_wins_over_oos(self):
        chunk_results = [
            _make_chunk_result("D1", signals=[_make_signal("S008")]),
            _make_chunk_result("D2", oos=["S008"]),
        ]
        result = deduplicate(
            chunk_results=chunk_results,
            residual_results=_empty_residual(),
            chunk_assignment={"S008": ["D1", "D2"]},
        )
        assert "S008" not in result.out_of_scope_refs
        assert any("S008" in s["source_refs"] for s in result.signals)


class TestResidualMerge:
    def test_residuals_merged_without_dedup(self):
        residual_results = {
            "signals": [_make_signal("S_RES1"), _make_signal("S_RES2")],
            "concerns": [_make_concern("S_RES3")],
            "out_of_scope_refs": ["S_RES4"],
            "failures": [],
        }
        result = deduplicate(
            chunk_results=[],
            residual_results=residual_results,
            chunk_assignment={},
        )
        signal_ids = [s["source_refs"][0] for s in result.signals]
        assert "S_RES1" in signal_ids
        assert "S_RES2" in signal_ids
        assert "S_RES3" in result.concerns[0]["source_refs"]
        assert "S_RES4" in result.out_of_scope_refs

    def test_residuals_not_duplicated_from_chunks(self):
        chunk_results = [
            _make_chunk_result("D1", signals=[_make_signal("S009")]),
        ]
        residual_results = {
            "signals": [],
            "concerns": [],
            "out_of_scope_refs": [],
            "failures": [],
        }
        result = deduplicate(
            chunk_results=chunk_results,
            residual_results=residual_results,
            chunk_assignment={"S009": ["D1"]},
        )
        s009_count = sum(
            1 for s in result.signals if "S009" in s["source_refs"]
        )
        assert s009_count == 1


class TestSingleClassification:
    def test_single_signal_passes_through(self):
        chunk_results = [
            _make_chunk_result("D1", signals=[_make_signal("S010")]),
        ]
        result = deduplicate(
            chunk_results=chunk_results,
            residual_results=_empty_residual(),
            chunk_assignment={"S010": ["D1"]},
        )
        assert len(result.signals) == 1
        assert result.signals[0]["source_refs"] == ["S010"]

    def test_single_concern_passes_through(self):
        chunk_results = [
            _make_chunk_result("D1", concerns=[_make_concern("S011")]),
        ]
        result = deduplicate(
            chunk_results=chunk_results,
            residual_results=_empty_residual(),
            chunk_assignment={"S011": ["D1"]},
        )
        assert len(result.concerns) == 1

    def test_single_oos_passes_through(self):
        chunk_results = [
            _make_chunk_result("D1", oos=["S012"]),
        ]
        result = deduplicate(
            chunk_results=chunk_results,
            residual_results=_empty_residual(),
            chunk_assignment={"S012": ["D1"]},
        )
        assert "S012" in result.out_of_scope_refs
