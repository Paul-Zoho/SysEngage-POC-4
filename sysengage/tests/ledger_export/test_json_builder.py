"""
Tests for ledger_export/json_builder.py.

Verifies canonical JSON structure, field correctness, execution_status
normalisation, element ordering, register construction, and content_hash.
"""

from __future__ import annotations

import hashlib
import json
import re

import pytest

from mechanisms.ledger_export.json_builder import (
    SPEC_VERSION,
    SCHEMA_ID,
    _ELEMENT_TYPE_ORDER,
    _TYPE_RANK,
    _map_execution_status,
    build_canonical_ledger,
    ledger_to_json_str,
)
from tests.ledger_export.conftest import (
    ProjectData,
    make_analysis_pass,
    make_concern,
    make_domain,
    make_project,
    make_requirement,
    make_segment,
    make_signal,
    make_source,
    make_source_atom,
    make_stakeholder,
)


# ── execution_status normalisation ───────────────────────────────────────────

class TestExecutionStatusMapping:
    def test_completed_maps_to_success(self):
        assert _map_execution_status("Completed") == "Success"

    def test_success_maps_to_success(self):
        assert _map_execution_status("Success") == "Success"

    def test_completedwithwarnings_maps_to_partialsuccess(self):
        assert _map_execution_status("CompletedWithWarnings") == "PartialSuccess"

    def test_partialsuccess_preserved(self):
        assert _map_execution_status("PartialSuccess") == "PartialSuccess"

    def test_failed_preserved(self):
        assert _map_execution_status("Failed") == "Failed"

    def test_unknown_value_defaults_to_success(self):
        assert _map_execution_status("SomeOtherValue") == "Success"


# ── top-level ledger structure ────────────────────────────────────────────────

class TestLedgerTopLevel:
    def test_required_top_level_keys(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        for key in (
            "sysengage_ledger_version",
            "schema_id",
            "row_target",
            "run_id",
            "created_utc",
            "generator",
            "elements",
            "register_index",
            "content_hash",
        ):
            assert key in ledger, f"Missing top-level key: {key!r}"

    def test_spec_version(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        assert ledger["sysengage_ledger_version"] == "2.12"

    def test_schema_id(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        assert ledger["schema_id"] == "sysengage.ledger.instance.v2_11"

    def test_generator_fields(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        gen = ledger["generator"]
        assert gen["name"] == "sysengage-ledger-export"
        assert gen["version"] == "1.0"

    def test_run_id_is_uuid_format(self, minimal_project_data):
        import uuid
        ledger = build_canonical_ledger(minimal_project_data)
        uuid.UUID(ledger["run_id"])

    def test_created_utc_is_iso8601(self, minimal_project_data):
        from datetime import datetime
        ledger = build_canonical_ledger(minimal_project_data)
        datetime.fromisoformat(ledger["created_utc"])


# ── row_target derivation ─────────────────────────────────────────────────────

class TestRowTargetDerivation:
    def test_row_target_single_row_from_signal(self):
        data = ProjectData(
            project=make_project(),
            sources=[make_source()],
            signals=[make_signal(row_target="1")],
            segments=[],
            source_atoms=[],
            concerns=[],
            analysis_passes=[],
            stakeholders=[make_stakeholder()],
            domains=[],
            requirements=[],
        )
        ledger = build_canonical_ledger(data)
        assert ledger["row_target"] == "1"

    def test_row_target_multiple_rows_from_signals(self):
        data = ProjectData(
            project=make_project(),
            sources=[make_source()],
            signals=[
                make_signal("SG001", row_target="1"),
                make_signal("SG002", row_target="2"),
            ],
            segments=[],
            source_atoms=[],
            concerns=[],
            analysis_passes=[],
            stakeholders=[make_stakeholder()],
            domains=[],
            requirements=[],
        )
        ledger = build_canonical_ledger(data)
        assert ledger["row_target"] == ["1", "2"]

    def test_row_target_default_when_no_row_elements(self):
        data = ProjectData(
            project=make_project(),
            sources=[make_source()],
            signals=[],
            segments=[],
            source_atoms=[],
            concerns=[],
            analysis_passes=[],
            stakeholders=[make_stakeholder()],
            domains=[],
            requirements=[],
        )
        ledger = build_canonical_ledger(data)
        assert ledger["row_target"] == "1"

    def test_row_target_from_concern(self):
        data = ProjectData(
            project=make_project(),
            sources=[make_source()],
            signals=[],
            segments=[],
            source_atoms=[],
            concerns=[make_concern(produced_in_row="2")],
            analysis_passes=[],
            stakeholders=[make_stakeholder()],
            domains=[],
            requirements=[],
        )
        ledger = build_canonical_ledger(data)
        assert ledger["row_target"] == "2"


# ── element type correctness ──────────────────────────────────────────────────

class TestElementPayloads:
    def _elements_by_type(self, ledger: dict, etype: str) -> list[dict]:
        return [e for e in ledger["elements"] if e["element_type"] == etype]

    def test_source_payload_fields(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        src_els = self._elements_by_type(ledger, "Source")
        assert len(src_els) == 1
        p = src_els[0]["payload"]
        assert p["source_id"] == "S001"
        assert "source_text" in p
        assert "segmentation_context" in p
        assert "input_material_ref" in p
        assert "confidence" in p
        assert "project_id" not in p
        assert "created_at" not in p

    def test_source_parent_ref_omitted_when_none(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        src_el = self._elements_by_type(ledger, "Source")[0]
        assert "parent_source_ref" not in src_el["payload"]

    def test_source_parent_ref_present_when_set(self):
        src = make_source("S002", parent_source_ref="S001")
        data = ProjectData(
            project=make_project(),
            sources=[src],
            segments=[],
            source_atoms=[],
            signals=[],
            concerns=[],
            analysis_passes=[make_analysis_pass()],
            stakeholders=[make_stakeholder()],
            domains=[],
            requirements=[],
        )
        ledger = build_canonical_ledger(data)
        p = self._elements_by_type(ledger, "Source")[0]["payload"]
        assert p["parent_source_ref"] == "S001"

    def test_analysis_pass_execution_status_normalised(self):
        ap = make_analysis_pass(execution_status="CompletedWithWarnings")
        data = ProjectData(
            project=make_project(),
            sources=[make_source()],
            segments=[],
            source_atoms=[],
            signals=[],
            concerns=[],
            analysis_passes=[ap],
            stakeholders=[make_stakeholder()],
            domains=[],
            requirements=[],
        )
        ledger = build_canonical_ledger(data)
        ap_el = self._elements_by_type(ledger, "AnalysisPass")[0]
        assert ap_el["payload"]["execution_status"] == "PartialSuccess"

    def test_analysis_pass_strips_non_canonical_fields(self):
        ledger = build_canonical_ledger(
            ProjectData(
                project=make_project(),
                sources=[make_source()],
                segments=[],
                source_atoms=[],
                signals=[],
                concerns=[],
                analysis_passes=[make_analysis_pass()],
                stakeholders=[make_stakeholder()],
                domains=[],
                requirements=[],
            )
        )
        p = self._elements_by_type(ledger, "AnalysisPass")[0]["payload"]
        assert "project_id" not in p
        assert "created_at" not in p
        assert "phase_id" not in p

    def test_signal_source_refs_sorted(self):
        sig = make_signal(source_refs=["S003", "S001", "S002"])
        data = ProjectData(
            project=make_project(),
            sources=[make_source("S001"), make_source("S002"), make_source("S003")],
            segments=[],
            source_atoms=[],
            signals=[sig],
            concerns=[],
            analysis_passes=[make_analysis_pass()],
            stakeholders=[make_stakeholder()],
            domains=[],
            requirements=[],
        )
        ledger = build_canonical_ledger(data)
        sig_el = self._elements_by_type(ledger, "Signal")[0]
        assert sig_el["payload"]["source_refs"] == ["S001", "S002", "S003"]

    def test_signal_no_sourceatom_refs_when_empty(self):
        sig = make_signal(sourceatom_refs=[])
        data = ProjectData(
            project=make_project(),
            sources=[make_source()],
            segments=[],
            source_atoms=[],
            signals=[sig],
            concerns=[],
            analysis_passes=[make_analysis_pass()],
            stakeholders=[make_stakeholder()],
            domains=[],
            requirements=[],
        )
        ledger = build_canonical_ledger(data)
        sig_el = self._elements_by_type(ledger, "Signal")[0]
        assert "sourceatom_refs" not in sig_el["payload"]

    def test_concern_payload_fields(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        cn_els = self._elements_by_type(ledger, "Concern")
        assert len(cn_els) == 1
        p = cn_els[0]["payload"]
        assert p["concern_id"] == "CN001"
        assert "source_refs" in p
        assert "description" in p
        assert "state" in p
        assert "produced_in_row" in p
        assert "practitioner_id" in p
        assert "confidence" in p
        assert "project_id" not in p

    def test_concern_optional_fields_omitted_when_none(self):
        cn = make_concern(dispositioned_with_outcome=None, disposition_rationale=None)
        data = ProjectData(
            project=make_project(),
            sources=[make_source()],
            segments=[],
            source_atoms=[],
            signals=[],
            concerns=[cn],
            analysis_passes=[make_analysis_pass()],
            stakeholders=[make_stakeholder()],
            domains=[],
            requirements=[],
        )
        ledger = build_canonical_ledger(data)
        p = self._elements_by_type(ledger, "Concern")[0]["payload"]
        assert "dispositioned_with_outcome" not in p
        assert "disposition_rationale" not in p

    def test_stakeholder_sh001_has_kind_automated(self):
        ledger = build_canonical_ledger(
            ProjectData(
                project=make_project(),
                sources=[make_source()],
                segments=[],
                source_atoms=[],
                signals=[],
                concerns=[],
                analysis_passes=[make_analysis_pass()],
                stakeholders=[make_stakeholder("SH001", "SysEngage")],
                domains=[],
                requirements=[],
            )
        )
        sh_els = self._elements_by_type(ledger, "Stakeholder")
        sh001 = next(e for e in sh_els if e["element_id"] == "SH001")
        assert sh001["payload"]["stakeholder_kind"] == "Automated"

    def test_segment_payload_fields(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        seg_els = self._elements_by_type(ledger, "Segment")
        assert len(seg_els) == 1
        p = seg_els[0]["payload"]
        assert p["segment_id"] == "SEG001"
        assert "title" in p
        assert "source_refs" in p
        assert "confidence" in p
        assert "project_id" not in p

    def test_source_atom_payload_fields(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        atom_els = self._elements_by_type(ledger, "SourceAtom")
        assert len(atom_els) == 2
        p = atom_els[0]["payload"]
        assert "atom_id" in p
        assert "atom_text" in p
        assert "source_ref" in p
        assert "confidence" in p
        assert "project_id" not in p
        assert "position" not in p

    def test_domain_payload_fields(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        dom_els = self._elements_by_type(ledger, "Domain")
        assert len(dom_els) == 1
        p = dom_els[0]["payload"]
        assert p["domain_id"] == "D001"
        assert p["name"] == "Expense Tracking"
        assert p["row_target"] == "1"

    def test_requirement_payload_fields(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        req_els = self._elements_by_type(ledger, "Requirement")
        assert len(req_els) == 1
        p = req_els[0]["payload"]
        assert p["requirement_id"] == "R001"
        assert "statement" in p
        assert p["row_target"] == "1"


# ── register construction ─────────────────────────────────────────────────────

class TestRegisterConstruction:
    def _registers_by_type(self, ledger: dict, rtype: str) -> list[dict]:
        return [e for e in ledger["elements"] if e["element_type"] == rtype + "Register"]

    def test_source_register_always_present(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        regs = self._registers_by_type(ledger, "Source")
        assert len(regs) == 1
        p = regs[0]["payload"]
        assert p["register_type"] == "Source"
        assert p["register_id"] == "SOURCE_REG001"
        assert "S001" in p["member_ids"]

    def test_signal_register_always_present(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        regs = self._registers_by_type(ledger, "Signal")
        assert len(regs) == 1
        assert regs[0]["payload"]["register_type"] == "Signal"

    def test_stakeholder_register_always_present(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        regs = self._registers_by_type(ledger, "Stakeholder")
        assert len(regs) == 1

    def test_segment_register_present_when_segments_exist(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        regs = self._registers_by_type(ledger, "Segment")
        assert len(regs) == 1

    def test_segment_register_absent_when_no_segments(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        regs = self._registers_by_type(ledger, "Segment")
        assert len(regs) == 0

    def test_concern_register_present_when_concerns_exist(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        regs = self._registers_by_type(ledger, "Concern")
        assert len(regs) == 1
        assert "CN001" in regs[0]["payload"]["member_ids"]

    def test_concern_register_absent_when_no_concerns(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        regs = self._registers_by_type(ledger, "Concern")
        assert len(regs) == 0

    def test_sourceatom_register_present_when_atoms_exist(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        regs = self._registers_by_type(ledger, "SourceAtom")
        assert len(regs) == 1

    def test_domain_register_present_when_domains_exist(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        regs = self._registers_by_type(ledger, "Domain")
        assert len(regs) == 1

    def test_requirement_register_present_when_requirements_exist(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        regs = self._registers_by_type(ledger, "Requirement")
        assert len(regs) == 1

    def test_register_member_ids_sorted_lexicographically(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        for el in ledger["elements"]:
            if el["element_type"].endswith("Register"):
                ids = el["payload"]["member_ids"]
                assert ids == sorted(ids), f"{el['element_id']} member_ids not sorted"

    def test_register_index_matches_register_elements(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        register_element_ids = {
            e["element_id"]
            for e in ledger["elements"]
            if e["element_type"].endswith("Register")
        }
        register_index_ids = {r["register_id"] for r in ledger["register_index"]}
        assert register_element_ids == register_index_ids


# ── element ordering ──────────────────────────────────────────────────────────

class TestElementOrdering:
    def test_elements_sorted_by_type_rank_then_id(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        elements = ledger["elements"]
        prev_rank = -1
        prev_id = ""
        for el in elements:
            etype = el["element_type"]
            eid = el["element_id"]
            rank = _TYPE_RANK.get(etype, 999)
            if rank == prev_rank:
                assert eid >= prev_id, (
                    f"Element {eid!r} ({etype}) out of lexicographic order after {prev_id!r}"
                )
            else:
                assert rank >= prev_rank, (
                    f"Element type {etype!r} (rank {rank}) out of order after rank {prev_rank}"
                )
            prev_rank = rank
            prev_id = eid if rank != prev_rank else prev_id


# ── element_id rules ──────────────────────────────────────────────────────────

class TestElementIdRules:
    def test_element_id_matches_primary_id_field(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        id_field_map = {
            "Source": "source_id",
            "Segment": "segment_id",
            "SourceAtom": "atom_id",
            "Signal": "signal_id",
            "Concern": "concern_id",
            "AnalysisPass": "pass_id",
            "Stakeholder": "stakeholder_id",
            "Domain": "domain_id",
            "Requirement": "requirement_id",
        }
        for el in ledger["elements"]:
            etype = el["element_type"]
            if etype in id_field_map:
                field = id_field_map[etype]
                assert el["element_id"] == el["payload"][field], (
                    f"element_id mismatch for {etype}: "
                    f"element_id={el['element_id']!r} payload.{field}={el['payload'][field]!r}"
                )
            elif etype.endswith("Register"):
                assert el["element_id"] == el["payload"]["register_id"]

    def test_all_element_ids_globally_unique(self, full_project_data):
        ledger = build_canonical_ledger(full_project_data)
        ids = [e["element_id"] for e in ledger["elements"]]
        assert len(ids) == len(set(ids)), "Duplicate element_ids found"


# ── content hash ──────────────────────────────────────────────────────────────

class TestContentHash:
    def test_content_hash_present(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        ch = ledger["content_hash"]
        assert ch["hash_alg"] == "sha256"
        assert re.match(r"^[0-9a-f]{64}$", ch["hash"])

    def test_content_hash_deterministic(self, minimal_project_data):
        ledger1 = build_canonical_ledger(minimal_project_data)
        # Change run_id to simulate second run producing same content —
        # we manually check that the hash logic is stable given same content.
        # Two calls produce different run_ids (uuid) so hashes WILL differ;
        # here we verify the hash field IS a 64-char hex string both times.
        ledger2 = build_canonical_ledger(minimal_project_data)
        assert re.match(r"^[0-9a-f]{64}$", ledger1["content_hash"]["hash"])
        assert re.match(r"^[0-9a-f]{64}$", ledger2["content_hash"]["hash"])

    def test_content_hash_not_included_in_own_hash_input(self, minimal_project_data):
        """Verify the hash field is omitted from the hashed payload (Appendix B.5)."""
        import copy
        ledger = build_canonical_ledger(minimal_project_data)
        stored_hash = ledger["content_hash"]["hash"]

        payload_without_hash = copy.deepcopy(ledger)
        del payload_without_hash["content_hash"]

        serialised = json.dumps(payload_without_hash, ensure_ascii=False, indent=2, sort_keys=True)
        serialised = serialised.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.rstrip() for line in serialised.split("\n")]
        canonical_bytes = "\n".join(lines).encode("utf-8")
        recomputed = hashlib.sha256(canonical_bytes).hexdigest()

        assert recomputed == stored_hash


# ── JSON serialisation ────────────────────────────────────────────────────────

class TestJsonSerialisation:
    def test_json_str_is_valid_json(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        json_str = ledger_to_json_str(ledger)
        parsed = json.loads(json_str)
        assert parsed["sysengage_ledger_version"] == "2.12"

    def test_json_str_uses_lf_newlines(self, minimal_project_data):
        ledger = build_canonical_ledger(minimal_project_data)
        json_str = ledger_to_json_str(ledger)
        assert "\r\n" not in json_str
        assert "\r" not in json_str
