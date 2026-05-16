"""
Entity production unit tests.

Tests:
- build_signal_model produces valid SignalModel
- build_concern_model produces valid ConcernModel with state="Open"
- run_referential_integrity_checks: SG-1, SG-2, CN-3, CN-4
- run_mutual_exclusivity_check: ME-1 (Concern takes precedence)
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from mechanisms.row_lens_source_reanalysis.entity_production import (
    RowLensRunState,
    build_signal_model,
    build_concern_model,
    run_referential_integrity_checks,
    run_mutual_exclusivity_check,
)


def _make_source(source_id: str):
    s = MagicMock()
    s.source_id = source_id
    return s


def _make_requirement(req_id: str, row_target: str = "1"):
    r = MagicMock()
    r.requirement_id = req_id
    r.row_target = row_target
    return r


class TestBuildSignalModel:
    def test_signal_id_set(self):
        sm = build_signal_model(
            signal_id="SG001",
            raw={
                "source_refs": ["S001"],
                "signal_type": "Normative",
                "description": "A normative signal.",
                "confidence": 0.9,
                "sourceatom_refs": [],
                "derived_from_concern_id": None,
            },
            row_ref=2,
            project_id="P001",
        )
        assert sm.signal_id == "SG001"

    def test_row_target_set(self):
        sm = build_signal_model(
            signal_id="SG002",
            raw={
                "source_refs": ["S002"],
                "signal_type": "Intent",
                "description": "An intent signal.",
                "confidence": 0.85,
                "sourceatom_refs": [],
                "derived_from_concern_id": None,
            },
            row_ref=3,
            project_id="P001",
        )
        assert sm.row_target == "3"

    def test_state_not_present(self):
        sm = build_signal_model(
            signal_id="SG003",
            raw={
                "source_refs": ["S003"],
                "signal_type": "Actor",
                "description": "An actor signal.",
                "confidence": 0.8,
                "sourceatom_refs": [],
                "derived_from_concern_id": None,
            },
            row_ref=2,
            project_id="P001",
        )
        # Signal has no 'state' attribute; check it's a SignalModel instance
        from models.signal import SignalModel
        assert isinstance(sm, SignalModel)


class TestBuildConcernModel:
    def test_state_open(self):
        cm = build_concern_model(
            concern_id="CN001",
            raw={
                "source_refs": ["S001"],
                "description": "A concern.",
                "confidence": 0.45,
            },
            row_ref=2,
            project_id="P001",
            practitioner_id="SH001",
        )
        assert cm.state == "Open"  # CN-5 criterion

    def test_produced_in_row(self):
        cm = build_concern_model(
            concern_id="CN002",
            raw={
                "source_refs": ["S002"],
                "description": "Another concern.",
                "confidence": 0.3,
            },
            row_ref=3,
            project_id="P001",
            practitioner_id="SH001",
        )
        assert cm.produced_in_row == "3"  # CN-6 criterion

    def test_dispositioned_null_at_production(self):
        cm = build_concern_model(
            concern_id="CN003",
            raw={
                "source_refs": ["S003"],
                "description": "Concern at production.",
                "confidence": 0.5,
            },
            row_ref=2,
            project_id="P001",
            practitioner_id="SH001",
        )
        assert cm.dispositioned_with_outcome is None
        assert cm.disposition_rationale is None


class TestReferentialIntegrity:
    def _make_state(
        self,
        signal_refs: list[str] | None = None,
        concern_refs: list[str] | None = None,
    ) -> RowLensRunState:
        signals_raw = (
            [{"source_refs": signal_refs, "signal_type": "Normative", "description": "x", "confidence": 0.8}]
            if signal_refs
            else []
        )
        concerns_raw = (
            [{"source_refs": concern_refs, "description": "y", "confidence": 0.5}]
            if concern_refs
            else []
        )
        return RowLensRunState(
            signals_raw=signals_raw,
            concerns_raw=concerns_raw,
            out_of_scope_refs=[],
            stream1_source_count=1,
            stream2_requirement_count=0,
            stream2_domain_count=0,
            row_ref=2,
            practitioner_id="SH001",
        )

    def test_valid_source_ref_no_failures(self):
        state = self._make_state(signal_refs=["S001"])
        sources = {"S001": _make_source("S001")}
        failures = run_referential_integrity_checks(
            run_state=state,
            sources_by_id=sources,
            requirements_by_id={},
        )
        assert failures == []

    def test_missing_source_ref_sg1_failure(self):
        state = self._make_state(signal_refs=["S_MISSING"])
        failures = run_referential_integrity_checks(
            run_state=state,
            sources_by_id={},
            requirements_by_id={},
        )
        assert any("SG-1" in f["reason"] for f in failures)

    def test_requirement_upstream_ok(self):
        """Signal with requirement from row_target="1" at row_ref=2 → valid."""
        state = self._make_state(signal_refs=["R001"])
        reqs = {"R001": _make_requirement("R001", row_target="1")}
        failures = run_referential_integrity_checks(
            run_state=state,
            sources_by_id={},
            requirements_by_id=reqs,
        )
        assert failures == []

    def test_requirement_same_row_sg2_failure(self):
        """Signal referencing a Requirement with row_target >= row_ref → SG-2."""
        state = self._make_state(signal_refs=["R002"])
        reqs = {"R002": _make_requirement("R002", row_target="2")}
        failures = run_referential_integrity_checks(
            run_state=state,
            sources_by_id={},
            requirements_by_id=reqs,
        )
        assert any("SG-2" in f["reason"] for f in failures)

    def test_concern_missing_ref_cn3_failure(self):
        state = self._make_state(concern_refs=["S_MISSING"])
        failures = run_referential_integrity_checks(
            run_state=state,
            sources_by_id={},
            requirements_by_id={},
        )
        assert any("CN-3" in f["reason"] for f in failures)

    def test_concern_upstream_row_cn4_failure(self):
        state = self._make_state(concern_refs=["R_SAME"])
        reqs = {"R_SAME": _make_requirement("R_SAME", row_target="2")}
        failures = run_referential_integrity_checks(
            run_state=state,
            sources_by_id={},
            requirements_by_id=reqs,
        )
        assert any("CN-4" in f["reason"] for f in failures)


class TestMutualExclusivity:
    def test_no_overlap_no_failures(self):
        state = RowLensRunState(
            signals_raw=[{"source_refs": ["S001"], "signal_type": "Normative", "description": "x", "confidence": 0.8}],
            concerns_raw=[{"source_refs": ["S002"], "description": "y", "confidence": 0.5}],
            out_of_scope_refs=[],
            stream1_source_count=2,
            stream2_requirement_count=0,
            stream2_domain_count=0,
            row_ref=2,
            practitioner_id="SH001",
        )
        failures = run_mutual_exclusivity_check(run_state=state)
        assert failures == []

    def test_overlap_produces_me1_failure(self):
        state = RowLensRunState(
            signals_raw=[{"source_refs": ["S001"], "signal_type": "Normative", "description": "x", "confidence": 0.8}],
            concerns_raw=[{"source_refs": ["S001"], "description": "y", "confidence": 0.5}],
            out_of_scope_refs=[],
            stream1_source_count=1,
            stream2_requirement_count=0,
            stream2_domain_count=0,
            row_ref=2,
            practitioner_id="SH001",
        )
        failures = run_mutual_exclusivity_check(run_state=state)
        assert len(failures) == 1
        assert "ME-1" in failures[0]["reason"]
