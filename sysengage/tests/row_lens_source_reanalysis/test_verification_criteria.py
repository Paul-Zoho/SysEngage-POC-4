"""
All 17 decidable verification criteria — spec §8.1.

These tests use mock AI responses to avoid real API calls.
Each test verifies one or more decidable criteria against the full mechanism run.

Criteria tested:
  CN-1 — Concern identifier format ^CN\d{3,}$
  CN-2 — Concern source_refs non-empty
  CN-3 — Concern referential integrity (tested via entity_production tests)
  CN-4 — Concern upstream row constraint (tested via entity_production tests)
  CN-5 — Concern state = "Open" at production
  CN-6 — Concern produced_in_row = str(row_ref)
  SG-1 — Signal referential integrity (tested via entity_production tests)
  SG-2 — Signal upstream row constraint (tested via entity_production tests)
  SG-3 — Signal row_target = str(row_ref)
  ME-1 — No source_id in both Signal and Concern source_refs
  OS-1 — OutOfScope items in out_of_scope_refs
  OS-2 — OutOfScope source_ids not in Signal/Concern source_refs
  INV-1 — Invariant: stream1 + stream2 = signals + concerns + oos
  R1-1 — Row 1: stream2_requirement_count=0, stream2_domain_count=0
  AP-1 — AnalysisPass with mechanism="RowLensSourceReanalysis" exists
  AP-2 — execution_status ∈ {Completed, CompletedWithWarnings}
  AP-3 — mode_active="IM"; "LPM" ∈ declared_transformation_modes
"""

from __future__ import annotations

import re
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from tests.row_lens_source_reanalysis.conftest import (
    PROJECT_ID,
    PRACTITIONER_ID,
    make_classification_response,
    make_conflict_sweep_response,
    build_mock_message,
    _commit,
)
from models import SignalModel, ConcernModel, AnalysisPassModel
from core.db import get_session
from sqlalchemy import select


SIGNAL_ID_RE = re.compile(r"^SG\d{3,}$")
CONCERN_ID_RE = re.compile(r"^CN\d{3,}$")

VALID_EXECUTION_STATUSES = {"Completed", "CompletedWithWarnings"}


def _run_mechanism(row_ref: int = 1) -> dict:
    from mechanisms.row_lens_source_reanalysis import run
    return run(
        project_id=PROJECT_ID,
        practitioner_id=PRACTITIONER_ID,
        row_ref=row_ref,
    )


def _get_signals_for_run(project_id: str, pass_id: str) -> list[SignalModel]:
    session = get_session()
    try:
        return session.execute(
            select(SignalModel).where(SignalModel.project_id == project_id)
        ).scalars().all()
    finally:
        session.close()


def _get_concerns_for_run(project_id: str) -> list[ConcernModel]:
    session = get_session()
    try:
        return session.execute(
            select(ConcernModel).where(ConcernModel.project_id == project_id)
        ).scalars().all()
    finally:
        session.close()


def _get_analysis_pass(pass_id: str) -> AnalysisPassModel | None:
    session = get_session()
    try:
        return session.execute(
            select(AnalysisPassModel).where(AnalysisPassModel.pass_id == pass_id)
        ).scalar_one_or_none()
    finally:
        session.close()


class TestRow1EmptyStream2:
    """
    Fixture 2: Row 1 with no prior Requirements (stream 2 empty by design).
    All Sources processed as residual using mock AI.
    Tests: R1-1, INV-1, AP-1, AP-2, AP-3.
    """

    def test_r1_1_stream2_empty(self, sources_3, project_profile, mock_ai_client):
        """R1-1: At row_ref=1, stream2_requirement_count=0, stream2_domain_count=0."""
        # Mock residual classification: all 3 sources as Signal
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "Signal", "signal_type": "Normative", "confidence": 0.9, "description": "Children save pocket money."},
                {"item_id": "RLS902", "classification": "Signal", "signal_type": "Actor", "confidence": 0.85, "description": "Parents approve spending."},
                {"item_id": "RLS903", "classification": "Signal", "signal_type": "Normative", "confidence": 0.8, "description": "System sends email summaries."},
            ])
        )
        result = _run_mechanism(row_ref=1)
        rld = result["row_lens_data"]
        assert rld["stream2_requirement_count"] == 0, "R1-1: stream2_requirement_count must be 0"
        assert rld["stream2_domain_count"] == 0, "R1-1: stream2_domain_count must be 0"

    def test_inv1_row1(self, sources_3, project_profile, mock_ai_client):
        """INV-1: stream1 + stream2 = signals + concerns + oos."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "Signal", "signal_type": "Normative", "confidence": 0.9, "description": "d1"},
                {"item_id": "RLS902", "classification": "Concern", "signal_type": None, "confidence": 0.4, "description": "d2"},
                {"item_id": "RLS903", "classification": "OutOfScope", "signal_type": None, "confidence": 0.1, "description": "d3"},
            ])
        )
        result = _run_mechanism(row_ref=1)
        rld = result["row_lens_data"]
        total_in = rld["stream1_source_count"] + rld["stream2_requirement_count"]
        total_out = rld["signal_count_produced"] + rld["concern_count_produced"] + rld["out_of_scope_count"]
        assert total_in == total_out, f"INV-1 violated: {total_in} != {total_out}"

    def test_ap1_analysis_pass_exists(self, sources_3, project_profile, mock_ai_client):
        """AP-1: AnalysisPass with mechanism='RowLensSourceReanalysis' exists."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "Signal", "signal_type": "Normative", "confidence": 0.9, "description": "d1"},
                {"item_id": "RLS902", "classification": "Signal", "signal_type": "Normative", "confidence": 0.85, "description": "d2"},
                {"item_id": "RLS903", "classification": "Signal", "signal_type": "Normative", "confidence": 0.8, "description": "d3"},
            ])
        )
        result = _run_mechanism(row_ref=1)
        pass_record = _get_analysis_pass(result["pass_id"])
        assert pass_record is not None, "AP-1: AnalysisPass must exist"
        assert pass_record.mechanism == "RowLensSourceReanalysis"

    def test_ap2_execution_status(self, sources_3, project_profile, mock_ai_client):
        """AP-2: execution_status ∈ {Completed, CompletedWithWarnings}."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "Signal", "signal_type": "Normative", "confidence": 0.9, "description": "d1"},
                {"item_id": "RLS902", "classification": "Signal", "signal_type": "Normative", "confidence": 0.85, "description": "d2"},
                {"item_id": "RLS903", "classification": "Signal", "signal_type": "Normative", "confidence": 0.8, "description": "d3"},
            ])
        )
        result = _run_mechanism(row_ref=1)
        assert result["execution_status"] in VALID_EXECUTION_STATUSES, (
            f"AP-2: execution_status must be in {VALID_EXECUTION_STATUSES}. Got: {result['execution_status']}"
        )

    def test_ap3_mode_declarations(self, sources_3, project_profile, mock_ai_client):
        """AP-3: mode_active='IM'; 'LPM' ∈ declared_transformation_modes."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "Signal", "signal_type": "Normative", "confidence": 0.9, "description": "d1"},
                {"item_id": "RLS902", "classification": "Signal", "signal_type": "Normative", "confidence": 0.85, "description": "d2"},
                {"item_id": "RLS903", "classification": "Signal", "signal_type": "Normative", "confidence": 0.8, "description": "d3"},
            ])
        )
        result = _run_mechanism(row_ref=1)
        pass_record = _get_analysis_pass(result["pass_id"])
        assert pass_record.mode_active == "IM", "AP-3: mode_active must be 'IM'"
        assert "LPM" in pass_record.declared_transformation_modes, (
            "AP-3: 'LPM' must be in declared_transformation_modes"
        )


class TestSignalCriteria:
    """SG-1, SG-3 — Signal identifier format and row_target."""

    def test_sg3_signal_row_target(self, sources_3, project_profile, mock_ai_client):
        """SG-3: Every Signal.row_target = str(row_ref)."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "Signal", "signal_type": "Normative", "confidence": 0.9, "description": "d1"},
                {"item_id": "RLS902", "classification": "Signal", "signal_type": "Intent", "confidence": 0.85, "description": "d2"},
                {"item_id": "RLS903", "classification": "OutOfScope", "signal_type": None, "confidence": 0.1, "description": "d3"},
            ])
        )
        result = _run_mechanism(row_ref=1)
        signals = _get_signals_for_run(PROJECT_ID, result["pass_id"])
        for sig in signals:
            assert sig.row_target == "1", f"SG-3: Signal {sig.signal_id} row_target must be '1'"

    def test_signal_id_format(self, sources_3, project_profile, mock_ai_client):
        """Signal IDs must match ^SG\\d{3,}$."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "Signal", "signal_type": "Normative", "confidence": 0.9, "description": "d1"},
                {"item_id": "RLS902", "classification": "Signal", "signal_type": "Normative", "confidence": 0.8, "description": "d2"},
                {"item_id": "RLS903", "classification": "Signal", "signal_type": "Normative", "confidence": 0.75, "description": "d3"},
            ])
        )
        result = _run_mechanism(row_ref=1)
        signals = _get_signals_for_run(PROJECT_ID, result["pass_id"])
        for sig in signals:
            assert SIGNAL_ID_RE.match(sig.signal_id), (
                f"Signal ID {sig.signal_id!r} must match ^SG\\d{{3,}}$"
            )


class TestConcernCriteria:
    """CN-1, CN-2, CN-5, CN-6 — Concern format, non-empty refs, state, produced_in_row."""

    def test_cn1_concern_id_format(self, sources_3, project_profile, mock_ai_client):
        """CN-1: Every Concern.concern_id matches ^CN\\d{3,}$."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "Concern", "signal_type": None, "confidence": 0.4, "description": "ambiguous concern"},
                {"item_id": "RLS902", "classification": "Signal", "signal_type": "Normative", "confidence": 0.85, "description": "d2"},
                {"item_id": "RLS903", "classification": "OutOfScope", "signal_type": None, "confidence": 0.1, "description": "d3"},
            ])
        )
        result = _run_mechanism(row_ref=1)
        concerns = _get_concerns_for_run(PROJECT_ID)
        for c in concerns:
            assert CONCERN_ID_RE.match(c.concern_id), (
                f"CN-1: Concern ID {c.concern_id!r} must match ^CN\\d{{3,}}$"
            )

    def test_cn2_source_refs_non_empty(self, sources_3, project_profile, mock_ai_client):
        """CN-2: Every Concern.source_refs has ≥ 1 entry."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "Concern", "signal_type": None, "confidence": 0.4, "description": "concern 1"},
                {"item_id": "RLS902", "classification": "Concern", "signal_type": None, "confidence": 0.45, "description": "concern 2"},
                {"item_id": "RLS903", "classification": "Signal", "signal_type": "Normative", "confidence": 0.8, "description": "d3"},
            ])
        )
        result = _run_mechanism(row_ref=1)
        concerns = _get_concerns_for_run(PROJECT_ID)
        for c in concerns:
            assert len(c.source_refs) >= 1, f"CN-2: Concern {c.concern_id} must have non-empty source_refs"

    def test_cn5_concern_state_open(self, sources_3, project_profile, mock_ai_client):
        """CN-5: Every Concern.state = 'Open' at production."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "Concern", "signal_type": None, "confidence": 0.3, "description": "c1"},
                {"item_id": "RLS902", "classification": "Signal", "signal_type": "Normative", "confidence": 0.9, "description": "d2"},
                {"item_id": "RLS903", "classification": "OutOfScope", "signal_type": None, "confidence": 0.1, "description": "d3"},
            ])
        )
        result = _run_mechanism(row_ref=1)
        concerns = _get_concerns_for_run(PROJECT_ID)
        for c in concerns:
            assert c.state == "Open", f"CN-5: Concern {c.concern_id} must have state='Open'"

    def test_cn6_produced_in_row(self, sources_3, project_profile, mock_ai_client):
        """CN-6: Every Concern.produced_in_row = str(row_ref)."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "Concern", "signal_type": None, "confidence": 0.3, "description": "c1"},
                {"item_id": "RLS902", "classification": "Signal", "signal_type": "Normative", "confidence": 0.85, "description": "d2"},
                {"item_id": "RLS903", "classification": "Signal", "signal_type": "Intent", "confidence": 0.8, "description": "d3"},
            ])
        )
        result = _run_mechanism(row_ref=1)
        concerns = _get_concerns_for_run(PROJECT_ID)
        for c in concerns:
            assert c.produced_in_row == "1", (
                f"CN-6: Concern {c.concern_id} produced_in_row must be '1'"
            )


class TestOutOfScopeCriteria:
    """OS-1, OS-2 — OutOfScope recording and mutual exclusivity."""

    def test_os1_oos_in_refs(self, sources_3, project_profile, mock_ai_client):
        """OS-1: Every OutOfScope item's id in out_of_scope_refs."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "OutOfScope", "signal_type": None, "confidence": 0.05, "description": "out"},
                {"item_id": "RLS902", "classification": "Signal", "signal_type": "Normative", "confidence": 0.9, "description": "d2"},
                {"item_id": "RLS903", "classification": "Signal", "signal_type": "Normative", "confidence": 0.8, "description": "d3"},
            ])
        )
        result = _run_mechanism(row_ref=1)
        oos_refs = result["row_lens_data"]["out_of_scope_refs"]
        assert "RLS901" in oos_refs, "OS-1: S901 classified OutOfScope must appear in out_of_scope_refs"

    def test_os2_oos_not_in_signal_or_concern(self, sources_3, project_profile, mock_ai_client):
        """OS-2: No id in out_of_scope_refs appears in any Signal/Concern source_refs."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "OutOfScope", "signal_type": None, "confidence": 0.05, "description": "out"},
                {"item_id": "RLS902", "classification": "Signal", "signal_type": "Normative", "confidence": 0.9, "description": "d2"},
                {"item_id": "RLS903", "classification": "Signal", "signal_type": "Normative", "confidence": 0.8, "description": "d3"},
            ])
        )
        result = _run_mechanism(row_ref=1)
        oos_refs = set(result["row_lens_data"]["out_of_scope_refs"])
        signals = _get_signals_for_run(PROJECT_ID, result["pass_id"])
        concerns = _get_concerns_for_run(PROJECT_ID)

        all_signal_refs = {ref for s in signals for ref in s.source_refs}
        all_concern_refs = {ref for c in concerns for ref in c.source_refs}

        overlap = oos_refs & (all_signal_refs | all_concern_refs)
        assert not overlap, f"OS-2: OOS refs {overlap} appear in Signal/Concern source_refs"


class TestMutualExclusivityEndToEnd:
    """ME-1 end-to-end: no source_id in both Signal and Concern source_refs."""

    def test_me1_no_source_in_both(self, sources_3, project_profile, mock_ai_client):
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_classification_response([
                {"item_id": "RLS901", "classification": "Signal", "signal_type": "Normative", "confidence": 0.9, "description": "d1"},
                {"item_id": "RLS902", "classification": "Concern", "signal_type": None, "confidence": 0.4, "description": "c2"},
                {"item_id": "RLS903", "classification": "OutOfScope", "signal_type": None, "confidence": 0.1, "description": "oos"},
            ])
        )
        result = _run_mechanism(row_ref=1)
        signals = _get_signals_for_run(PROJECT_ID, result["pass_id"])
        concerns = _get_concerns_for_run(PROJECT_ID)

        signal_source_ids = {ref for s in signals for ref in s.source_refs}
        concern_source_ids = {ref for c in concerns for ref in c.source_refs}

        overlap = signal_source_ids & concern_source_ids
        assert not overlap, f"ME-1: Source IDs {overlap} appear in both Signal and Concern source_refs"
