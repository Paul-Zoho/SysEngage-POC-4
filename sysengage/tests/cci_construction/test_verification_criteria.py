"""
CCI Construction verification criteria tests — spec v0.2 §8.

Each test targets one or more decidable verification criteria.

Criteria tested:
  VER-3b-01 — cell_id format: ZC-R{N}-C-{col} for each committed cell
  VER-3b-02 — ci_id format: CCI-ROW{N}-C-{col}-{seq} for each CCI
  VER-3b-03 — classification_type in permitted column vocabulary
  VER-3b-04 — signal_refs non-empty for each CCI
  VER-3b-05 — signal_refs resolve to committed Signals in the working set
  VER-3b-06 — All six ZachmanCells upserted per row on each run
  VER-3b-07 — AnalysisPass mechanism = "CCIConstruction"
  VER-3b-08 — execution_status ∈ {Completed, CompletedWithWarnings}
  VER-3b-09 — mode_active = "DM" on AnalysisPass
  VER-3b-10 — cci_data has all required fields (none null or missing)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from core.db import get_session
from mechanisms.cci_construction.prompts.column_vocabulary import (
    COLUMN_VOCABULARY,
    COLUMNS,
)
from models import AnalysisPassModel, SignalModel
from models.cell_content_item import CellContentItemModel
from models.zachman_cell import ZachmanCellModel
from tests.cci_construction.conftest import (
    PROJECT_ID,
    PRACTITIONER_ID,
    ROW_REF,
    _commit,
    build_mock_message,
    make_derivation_response,
    make_dedup_response,
)

CELL_ID_RE = re.compile(
    r"^ZC-R[1-6]-C-(What|How|Where|Who|When|Why)$"
)
CI_ID_RE = re.compile(
    r"^CCI-ROW[1-6]-C-(What|How|Where|Who|When|Why)-\d{3}$"
)
VALID_STATUSES = {"Completed", "CompletedWithWarnings"}
REQUIRED_CCI_DATA_KEYS = {
    "row_ref",
    "batches_processed",
    "batches_failed",
    "cells_populated",
    "cells_empty",
    "ccis_created",
    "ccis_merged",
    "candidates_rejected",
    "merges",
    "consolidation_flags",
    "integrity_violations",
}


def _run_mechanism(row_ref: int = ROW_REF) -> dict:
    from mechanisms.cci_construction import run
    return run(
        project_id=PROJECT_ID,
        practitioner_id=PRACTITIONER_ID,
        row_ref=row_ref,
    )


def _get_ccis(project_id: str) -> list[CellContentItemModel]:
    session = get_session()
    try:
        return (
            session.query(CellContentItemModel)
            .filter(CellContentItemModel.project_id == project_id)
            .all()
        )
    finally:
        session.close()


def _get_zachman_cells(project_id: str, row_ref: int) -> list[ZachmanCellModel]:
    session = get_session()
    try:
        return (
            session.query(ZachmanCellModel)
            .filter(
                ZachmanCellModel.project_id == project_id,
                ZachmanCellModel.row_target == str(row_ref),
            )
            .all()
        )
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


def _make_standard_derivation_response(signal_ids: list[str]) -> str:
    """Build a derivation response that assigns one CCI per signal across different columns."""
    columns = ["What", "How", "When"]
    items = []
    for i, sig_id in enumerate(signal_ids):
        col = columns[i % len(columns)]
        vocab = COLUMN_VOCABULARY[col]
        items.append({
            "column": col,
            "classification_type": vocab[0],
            "description": f"Derived classified content for {sig_id} in {col} column.",
            "signal_refs": [sig_id],
            "confidence": 0.85,
            "trigger_condition": None,
            "justification": f"Classified as {vocab[0]} within {col}.",
        })
    return make_derivation_response(items)


class TestZachmanCellCriteria:
    """VER-3b-01, VER-3b-06 — ZachmanCell format and completeness."""

    def test_ver_3b_01_cell_id_format(
        self, signals_3, project_profile, mock_ai_client
    ):
        """VER-3b-01: Every zachman_cell.cell_id matches ZC-R{N}-C-{col} format."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            _make_standard_derivation_response(["SG901", "SG902", "SG903"])
        )
        _run_mechanism(row_ref=ROW_REF)
        cells = _get_zachman_cells(PROJECT_ID, ROW_REF)
        for cell in cells:
            assert CELL_ID_RE.match(cell.cell_id), (
                f"VER-3b-01: cell_id '{cell.cell_id}' must match ZC-R{{N}}-C-{{col}}"
            )

    def test_ver_3b_06_all_six_cells_upserted(
        self, signals_3, project_profile, mock_ai_client
    ):
        """VER-3b-06: All six ZachmanCells (one per column) exist after a run."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            _make_standard_derivation_response(["SG901", "SG902", "SG903"])
        )
        _run_mechanism(row_ref=ROW_REF)
        cells = _get_zachman_cells(PROJECT_ID, ROW_REF)
        actual_columns = {cell.column for cell in cells}
        expected_columns = set(COLUMNS)
        assert actual_columns == expected_columns, (
            f"VER-3b-06: Expected all six columns {expected_columns}, "
            f"got {actual_columns}"
        )

    def test_ver_3b_06_idempotent_on_rerun(
        self, signals_3, project_profile, mock_ai_client
    ):
        """VER-3b-06: Re-running the mechanism does not create duplicate ZachmanCells."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            _make_standard_derivation_response(["SG901", "SG902", "SG903"])
        )
        _run_mechanism(row_ref=ROW_REF)
        _run_mechanism(row_ref=ROW_REF)
        cells = _get_zachman_cells(PROJECT_ID, ROW_REF)
        assert len(cells) == 6, (
            f"VER-3b-06: Expected exactly 6 ZachmanCells on re-run, got {len(cells)}"
        )


class TestCCIFormatCriteria:
    """VER-3b-02, VER-3b-03, VER-3b-04, VER-3b-05 — CCI content correctness."""

    def test_ver_3b_02_ci_id_format(
        self, signals_3, project_profile, mock_ai_client
    ):
        """VER-3b-02: Every ci_id matches CCI-ROW{N}-C-{col}-{seq} format."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            _make_standard_derivation_response(["SG901", "SG902", "SG903"])
        )
        _run_mechanism(row_ref=ROW_REF)
        ccis = _get_ccis(PROJECT_ID)
        for cci in ccis:
            assert CI_ID_RE.match(cci.ci_id), (
                f"VER-3b-02: ci_id '{cci.ci_id}' must match CCI-ROW{{N}}-C-{{col}}-{{seq}}"
            )

    def test_ver_3b_03_classification_type_in_vocabulary(
        self, signals_3, project_profile, mock_ai_client
    ):
        """VER-3b-03: Every CCI.classification_type is in the permitted column vocabulary."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            _make_standard_derivation_response(["SG901", "SG902", "SG903"])
        )
        _run_mechanism(row_ref=ROW_REF)
        ccis = _get_ccis(PROJECT_ID)
        for cci in ccis:
            cell_col = cci.cell_id.split("-C-")[1]
            permitted = COLUMN_VOCABULARY.get(cell_col, [])
            assert cci.classification_type in permitted, (
                f"VER-3b-03: CCI '{cci.ci_id}' classification_type "
                f"'{cci.classification_type}' not in {permitted} for column '{cell_col}'"
            )

    def test_ver_3b_04_signal_refs_non_empty(
        self, signals_3, project_profile, mock_ai_client
    ):
        """VER-3b-04: Every CCI.signal_refs has ≥ 1 entry."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            _make_standard_derivation_response(["SG901", "SG902", "SG903"])
        )
        _run_mechanism(row_ref=ROW_REF)
        ccis = _get_ccis(PROJECT_ID)
        for cci in ccis:
            assert len(cci.signal_refs) >= 1, (
                f"VER-3b-04: CCI '{cci.ci_id}' must have non-empty signal_refs"
            )

    def test_ver_3b_05_signal_refs_resolve_to_committed_signals(
        self, signals_3, project_profile, mock_ai_client
    ):
        """VER-3b-05: Every signal_ref in every CCI resolves to a committed Signal."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            _make_standard_derivation_response(["SG901", "SG902", "SG903"])
        )
        _run_mechanism(row_ref=ROW_REF)

        # Collect committed signal IDs for this project
        session = get_session()
        try:
            committed_signal_ids = {
                row.signal_id
                for row in session.query(SignalModel.signal_id)
                .filter(SignalModel.project_id == PROJECT_ID)
                .all()
            }
        finally:
            session.close()

        ccis = _get_ccis(PROJECT_ID)
        for cci in ccis:
            for ref in cci.signal_refs:
                assert ref in committed_signal_ids, (
                    f"VER-3b-05: CCI '{cci.ci_id}' signal_ref '{ref}' "
                    "does not resolve to a committed Signal"
                )


class TestAnalysisPassCriteria:
    """VER-3b-07, VER-3b-08, VER-3b-09, VER-3b-10 — AnalysisPass correctness."""

    def test_ver_3b_07_mechanism_name(
        self, signals_3, project_profile, mock_ai_client
    ):
        """VER-3b-07: AnalysisPass.mechanism = 'CCIConstruction'."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            _make_standard_derivation_response(["SG901", "SG902", "SG903"])
        )
        result = _run_mechanism(row_ref=ROW_REF)
        pass_record = _get_analysis_pass(result["pass_id"])
        assert pass_record is not None, "VER-3b-07: AnalysisPass must exist"
        assert pass_record.mechanism == "CCIConstruction", (
            f"VER-3b-07: mechanism must be 'CCIConstruction', got '{pass_record.mechanism}'"
        )

    def test_ver_3b_08_execution_status(
        self, signals_3, project_profile, mock_ai_client
    ):
        """VER-3b-08: execution_status ∈ {Completed, CompletedWithWarnings}."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            _make_standard_derivation_response(["SG901", "SG902", "SG903"])
        )
        result = _run_mechanism(row_ref=ROW_REF)
        assert result["execution_status"] in VALID_STATUSES, (
            f"VER-3b-08: execution_status '{result['execution_status']}' "
            f"must be in {VALID_STATUSES}"
        )

    def test_ver_3b_09_mode_active(
        self, signals_3, project_profile, mock_ai_client
    ):
        """VER-3b-09: AnalysisPass.mode_active = 'DM'."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            _make_standard_derivation_response(["SG901", "SG902", "SG903"])
        )
        result = _run_mechanism(row_ref=ROW_REF)
        pass_record = _get_analysis_pass(result["pass_id"])
        assert pass_record.mode_active == "DM", (
            f"VER-3b-09: mode_active must be 'DM', got '{pass_record.mode_active}'"
        )

    def test_ver_3b_10_cci_data_required_fields(
        self, signals_3, project_profile, mock_ai_client
    ):
        """VER-3b-10: cci_data has all required fields, none null or absent."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            _make_standard_derivation_response(["SG901", "SG902", "SG903"])
        )
        result = _run_mechanism(row_ref=ROW_REF)
        cci_data = result["cci_data"]
        for key in REQUIRED_CCI_DATA_KEYS:
            assert key in cci_data, (
                f"VER-3b-10: cci_data missing required field '{key}'"
            )
            assert cci_data[key] is not None, (
                f"VER-3b-10: cci_data['{key}'] must not be null"
            )


class TestEdgeCases:
    """Edge case and resilience tests."""

    def test_no_signals_returns_completed(self, test_project, project_profile, mock_ai_client):
        """With no Signals for the row, the mechanism completes with empty cci_data."""
        result = _run_mechanism(row_ref=ROW_REF)
        assert result["execution_status"] in VALID_STATUSES
        assert result["cci_data"]["ccis_created"] == 0
        assert result["cci_data"]["batches_processed"] == 0

    def test_invalid_classification_type_rejected(
        self, signals_3, project_profile, mock_ai_client
    ):
        """
        An AI response with an invalid classification_type is rejected at Stage 3b.
        Valid items from the same batch still survive.
        """
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_derivation_response([
                {
                    "column": "What",
                    "classification_type": "INVALID_TYPE",
                    "description": "This item has an invalid type.",
                    "signal_refs": ["SG901"],
                    "confidence": 0.8,
                    "trigger_condition": None,
                    "justification": None,
                },
                {
                    "column": "How",
                    "classification_type": "Process",
                    "description": "Parent approval process for spending.",
                    "signal_refs": ["SG902"],
                    "confidence": 0.85,
                    "trigger_condition": None,
                    "justification": None,
                },
            ])
        )
        result = _run_mechanism(row_ref=ROW_REF)
        # Invalid item rejected; mechanism completes
        assert result["execution_status"] in VALID_STATUSES
        assert result["cci_data"]["candidates_rejected"] >= 1

    def test_unknown_signal_ref_rejected(
        self, signals_3, project_profile, mock_ai_client
    ):
        """Stage 3c: a signal_ref not in the eligible working set is rejected."""
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_derivation_response([
                {
                    "column": "What",
                    "classification_type": "Entity",
                    "description": "Entity derived from a phantom signal.",
                    "signal_refs": ["PHANTOM_SG999"],
                    "confidence": 0.9,
                    "trigger_condition": None,
                    "justification": None,
                },
                {
                    "column": "How",
                    "classification_type": "Process",
                    "description": "Valid process classification.",
                    "signal_refs": ["SG901"],
                    "confidence": 0.85,
                    "trigger_condition": None,
                    "justification": None,
                },
            ])
        )
        result = _run_mechanism(row_ref=ROW_REF)
        assert result["cci_data"]["candidates_rejected"] >= 1
        ccis = _get_ccis(PROJECT_ID)
        for cci in ccis:
            assert "PHANTOM_SG999" not in cci.signal_refs, (
                "Unknown signal_ref must not appear in any committed CCI"
            )

    def test_structural_duplicate_merged(
        self, signals_3, project_profile, mock_ai_client
    ):
        """
        Stage 4a: two candidates with identical classification_type and signal_refs
        (same set) are merged into one CCI.
        """
        # Return two structurally identical items in the same cell
        mock_ai_client.messages.create.return_value = build_mock_message(
            make_derivation_response([
                {
                    "column": "What",
                    "classification_type": "Entity",
                    "description": "Child account entity — first derivation.",
                    "signal_refs": ["SG901"],
                    "confidence": 0.90,
                    "trigger_condition": None,
                    "justification": None,
                },
                {
                    "column": "What",
                    "classification_type": "Entity",
                    "description": "Child account entity — second derivation.",
                    "signal_refs": ["SG901"],
                    "confidence": 0.80,
                    "trigger_condition": None,
                    "justification": None,
                },
            ])
        )
        result = _run_mechanism(row_ref=ROW_REF)
        # Both map to ZC-R2-C-What — structural dedup should merge them into 1
        what_ccis = [
            c for c in _get_ccis(PROJECT_ID) if "What" in c.ci_id
        ]
        assert len(what_ccis) == 1, (
            f"Stage 4a: structural duplicates must merge into 1 CCI, got {len(what_ccis)}"
        )
        assert result["cci_data"]["ccis_created"] == 1

    def test_integrity_violation_excluded(self, test_project, project_profile, mock_ai_client):
        """
        Step 1: Signal with derived_from_concern_id referencing an Open Concern
        must be excluded from the working set and recorded in integrity_violations.
        """
        from models.concern import ConcernModel

        # Commit an Open Concern
        _commit(
            ConcernModel(
                concern_id="CN901",
                source_refs=["SRC_PHANTOM"],
                description="Open concern for test.",
                state="Open",
                produced_in_row="2",
                practitioner_id=PRACTITIONER_ID,
                confidence=0.5,
                project_id=PROJECT_ID,
                created_at=datetime.now(timezone.utc),
            )
        )
        # Commit a Signal that derived from the Open Concern
        _commit(
            SignalModel(
                signal_id="SG904",
                signal_type="Normative",
                row_target="2",
                description="This signal derived from an open concern.",
                source_refs=["SRC_SG904"],
                sourceatom_refs=[],
                confidence=0.85,
                derived_from_concern_id="CN901",
                project_id=PROJECT_ID,
                created_at=datetime.now(timezone.utc),
            )
        )

        mock_ai_client.messages.create.return_value = build_mock_message(
            make_derivation_response([])
        )
        result = _run_mechanism(row_ref=ROW_REF)
        violations = result["cci_data"]["integrity_violations"]
        violation_signal_ids = [v["signal_id"] for v in violations]
        assert "SG904" in violation_signal_ids, (
            "Step 1: Signal with Open Concern reference must appear in integrity_violations"
        )
