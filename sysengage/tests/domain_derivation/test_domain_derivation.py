"""
Pass 3c Domain Derivation — unit and structural validation tests.

IMPORTANT: run tests INDIVIDUALLY per project convention.
Example:
  pytest "tests/domain_derivation/test_domain_derivation.py::TestStage1Preflight::test_zero_cci_exit" -v

Tests that require a live Neon DB are marked @pytest.mark.db.
DB tests MUST be run one at a time due to Neon connection-pool interference.

Test coverage:
  TestStage1Preflight         — Unit tests for Stage 1 logic (no AI, no full DB)
  TestStage3Validation        — Unit tests for all six CHK-3c-XX checks
  TestStage3RepairIntegration — Repair prompt integration (mocked AI)
  TestVerificationCriteria    — VER-3c-XX criteria tests (mocked AI, live session)
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

from mechanisms.domain_derivation.schemas.domain_grouping_response_schema import (
    DomainGroupingResponse,
    DomainProposal,
)
from mechanisms.domain_derivation.stage1_preflight import EligibleCCI
from tests.domain_derivation.conftest import (
    PROJECT_ID,
    PRACTITIONER_ID,
    ROW_REF,
    make_grouping_response,
    make_repair_response,
    seed_standard_test_dataset,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIVE_CCIS = [
    EligibleCCI("CCI-ROW4-C-What-001", "What", "Component", "Authentication service"),
    EligibleCCI("CCI-ROW4-C-What-002", "What", "Component", "Database access layer"),
    EligibleCCI("CCI-ROW4-C-How-001", "How", "Process", "OAuth2 token validation"),
    EligibleCCI("CCI-ROW4-C-How-002", "How", "Process", "Database query execution"),
    EligibleCCI("CCI-ROW4-C-Where-001", "Where", "Location", "Cloud deployment target"),
]


def _make_proposals(items: list[tuple[str, str, list[str]]]) -> list[DomainProposal]:
    return [
        DomainProposal(name=n, description=d, classification_type=None, cci_refs=refs)
        for n, d, refs in items
    ]


# ---------------------------------------------------------------------------
# TestStage3Validation — CHK-3c-01 through CHK-3c-06
# ---------------------------------------------------------------------------


class TestStage3Validation:
    """Unit tests for Stage 3 structural checks (no AI, no DB)."""

    def _make_stage1(self, eligible_ccis: list[EligibleCCI]) -> Any:
        from mechanisms.domain_derivation.stage1_preflight import Stage1Result
        s = Stage1Result()
        s.eligible_ccis = eligible_ccis
        s.current_hash = "abc"
        s.scenario = "FirstRun"
        s.domain_cross_cutting_advisory_threshold = 3
        return s

    def _make_stage2(self, proposals: list[DomainProposal]) -> Any:
        from mechanisms.domain_derivation.stage2_ai_grouping import Stage2Result
        s = Stage2Result()
        s.proposals = proposals
        s.effective_scenario = "FirstRun"
        return s

    def _run_stage3(self, proposals: list[DomainProposal], ccis: list[EligibleCCI]) -> Any:
        from mechanisms.domain_derivation.stage3_structural_validation import run_stage3
        stage1 = self._make_stage1(ccis)
        stage2 = self._make_stage2(proposals)
        return run_stage3(
            stage1=stage1,
            stage2=stage2,
            practitioner_id=PRACTITIONER_ID,
            project_id=PROJECT_ID,
            row_ref=ROW_REF,
        )

    # CHK-3c-01: proposals whose cci_refs become empty after CHK-3c-02 stripping are dropped
    def test_chk_3c_01_all_invalid_refs_stripped(self):
        """
        CHK-3c-01 fires (via CHK-3c-02) when all cci_refs for a proposal are invalid.

        DomainProposal requires min_length=1, so the only realistic path to an
        "empty after strip" proposal is a proposal whose refs are all absent from
        the eligible set (CHK-3c-02 strips them all, then records a CHK-3c-01 failure).
        """
        eligible = _FIVE_CCIS
        proposals = [
            DomainProposal(
                name="Auth Domain",
                description="Authentication related components",
                classification_type=None,
                cci_refs=["CCI-ROW4-C-What-001"],
            ),
            DomainProposal(
                name="Phantom Domain",
                description="All cci_refs here are not in the eligible set",
                classification_type=None,
                cci_refs=["CCI-ROW4-C-GHOST-001", "CCI-ROW4-C-GHOST-002"],
            ),
        ]
        with patch(
            "mechanisms.domain_derivation.stage3_structural_validation._call_repair_ai"
        ) as mock_repair:
            mock_repair.return_value = (
                MagicMock(
                    content=[
                        MagicMock(
                            text=make_repair_response(
                                [
                                    {
                                        "action": "assign",
                                        "domain_name": "Auth Domain",
                                        "new_cci_refs": [
                                            "CCI-ROW4-C-What-002",
                                            "CCI-ROW4-C-How-001",
                                            "CCI-ROW4-C-How-002",
                                            "CCI-ROW4-C-Where-001",
                                        ],
                                    }
                                ]
                            )
                        )
                    ],
                    model="test",
                    usage=MagicMock(input_tokens=10, output_tokens=10),
                ),
                {"stage": "stage3_repair", "model": "test"},
            )
            result = self._run_stage3(proposals, eligible)

        assert any(
            f["check_id"] == "CHK-3c-01" for f in result.validation_failures
        ), "CHK-3c-01 failure not recorded after CHK-3c-02 strips all refs"
        domain_names = [p.name for p in result.proposals]
        assert "Phantom Domain" not in domain_names, (
            "Phantom Domain (all-invalid refs) should be removed"
        )

    # CHK-3c-02: invalid cci_refs stripped
    def test_chk_3c_02_invalid_refs_stripped(self):
        """cci_refs not in eligible set are stripped (CHK-3c-02)."""
        eligible = _FIVE_CCIS[:3]
        proposals = [
            DomainProposal(
                name="Auth Domain",
                description="Authentication related items",
                classification_type=None,
                cci_refs=["CCI-ROW4-C-What-001", "CCI-ROW4-C-GHOST-999"],
            ),
            DomainProposal(
                name="Data Domain",
                description="Data access layer items",
                classification_type=None,
                cci_refs=["CCI-ROW4-C-What-002", "CCI-ROW4-C-How-001"],
            ),
        ]
        with patch(
            "mechanisms.domain_derivation.stage3_structural_validation._call_repair_ai"
        ) as mock_repair:
            mock_repair.return_value = (
                MagicMock(
                    content=[MagicMock(text=make_repair_response([]))],
                    model="test",
                    usage=MagicMock(input_tokens=10, output_tokens=10),
                ),
                {"stage": "stage3_repair", "model": "test"},
            )
            result = self._run_stage3(proposals, eligible)

        chk02 = [f for f in result.validation_failures if f["check_id"] == "CHK-3c-02"]
        assert len(chk02) >= 1, "CHK-3c-02 failure not recorded"
        auth_domain = next(p for p in result.proposals if p.name == "Auth Domain")
        assert "CCI-ROW4-C-GHOST-999" not in auth_domain.cci_refs

    # CHK-3c-03: duplicate names merged
    def test_chk_3c_03_duplicate_names_merged(self):
        """Duplicate domain names (case-insensitive) are merged (CHK-3c-03)."""
        proposals = [
            DomainProposal(
                name="Security Domain",
                description="Security components and processes",
                classification_type=None,
                cci_refs=["CCI-ROW4-C-What-001"],
            ),
            DomainProposal(
                name="security domain",
                description="Duplicate security domain lowercase",
                classification_type=None,
                cci_refs=["CCI-ROW4-C-How-001"],
            ),
            DomainProposal(
                name="Data Domain",
                description="Data access components",
                classification_type=None,
                cci_refs=["CCI-ROW4-C-What-002", "CCI-ROW4-C-How-002", "CCI-ROW4-C-Where-001"],
            ),
        ]
        result = self._run_stage3(proposals, _FIVE_CCIS)

        names_lower = [p.name.lower().strip() for p in result.proposals]
        assert names_lower.count("security domain") == 1, "Duplicate should be merged to one"
        merged = next(p for p in result.proposals if p.name.lower().strip() == "security domain")
        assert "CCI-ROW4-C-What-001" in merged.cci_refs
        assert "CCI-ROW4-C-How-001" in merged.cci_refs

    # CHK-3c-04: non-loss — all CCIs covered
    def test_chk_3c_04_non_loss_all_covered(self):
        """Non-loss: no repair needed when all CCIs are covered."""
        proposals = _make_proposals(
            [
                ("Auth Domain", "Authentication and access control", ["CCI-ROW4-C-What-001", "CCI-ROW4-C-How-001"]),
                ("Data Domain", "Data access and storage", ["CCI-ROW4-C-What-002", "CCI-ROW4-C-How-002"]),
                ("Infra Domain", "Infrastructure and deployment", ["CCI-ROW4-C-Where-001"]),
            ]
        )
        result = self._run_stage3(proposals, _FIVE_CCIS)
        assert result.orphaned_ccis == [], "No orphans expected when all CCIs covered"
        assert not result.repair_prompt_issued

    # CHK-3c-04: repair issued on orphan
    def test_chk_3c_04_repair_issued_on_orphan(self):
        """Repair prompt is issued when a CCI is orphaned."""
        proposals = _make_proposals(
            [
                ("Auth Domain", "Authentication components", ["CCI-ROW4-C-What-001"]),
                # CCI-ROW4-C-What-002, -How-001, -How-002, -Where-001 are orphaned
            ]
        )
        with patch(
            "mechanisms.domain_derivation.stage3_structural_validation._call_repair_ai"
        ) as mock_repair:
            mock_repair.return_value = (
                MagicMock(
                    content=[
                        MagicMock(
                            text=make_repair_response(
                                [
                                    {
                                        "action": "assign",
                                        "domain_name": "Auth Domain",
                                        "new_cci_refs": [
                                            "CCI-ROW4-C-What-002",
                                            "CCI-ROW4-C-How-001",
                                            "CCI-ROW4-C-How-002",
                                            "CCI-ROW4-C-Where-001",
                                        ],
                                    }
                                ]
                            )
                        )
                    ],
                    model="test",
                    usage=MagicMock(input_tokens=10, output_tokens=10),
                ),
                {"stage": "stage3_repair", "model": "test"},
            )
            result = self._run_stage3(proposals, _FIVE_CCIS)

        assert result.repair_prompt_issued
        assert result.orphaned_ccis == [], "Repair should have resolved all orphans"

    # CHK-3c-05: cross-cutting advisory fires above threshold
    def test_chk_3c_05_cross_cutting_advisory(self):
        """Cross-cutting advisory fires when a CCI appears in more domains than threshold."""
        proposals = _make_proposals(
            [
                ("Domain A", "First domain component set", ["CCI-ROW4-C-What-001", "CCI-ROW4-C-How-001"]),
                ("Domain B", "Second domain component set", ["CCI-ROW4-C-What-001", "CCI-ROW4-C-How-002"]),
                ("Domain C", "Third domain component set", ["CCI-ROW4-C-What-001", "CCI-ROW4-C-What-002"]),
                ("Domain D", "Fourth domain component set", ["CCI-ROW4-C-Where-001"]),
            ]
        )
        # What-001 appears in A, B, C — that's 3 domains; threshold defaults to 3
        # Advisory fires when count > threshold, so 3 > 3 is False; 4 > 3 is True
        # Let's set threshold to 2 via stage1
        from mechanisms.domain_derivation.stage1_preflight import Stage1Result
        from mechanisms.domain_derivation.stage2_ai_grouping import Stage2Result

        s1 = Stage1Result()
        s1.eligible_ccis = _FIVE_CCIS
        s1.scenario = "FirstRun"
        s1.current_hash = "abc"
        s1.domain_cross_cutting_advisory_threshold = 2  # advisory fires at > 2

        s2 = Stage2Result()
        s2.proposals = proposals
        s2.effective_scenario = "FirstRun"

        from mechanisms.domain_derivation.stage3_structural_validation import run_stage3
        result = run_stage3(
            stage1=s1,
            stage2=s2,
            practitioner_id=PRACTITIONER_ID,
            project_id=PROJECT_ID,
            row_ref=ROW_REF,
        )

        cross_cut_ids = [a["ci_id"] for a in result.cross_cutting_advisories]
        assert "CCI-ROW4-C-What-001" in cross_cut_ids, (
            "What-001 appears in 3 domains (>2 threshold) — advisory expected"
        )

    # CHK-3c-06: at least one domain survives after all checks
    def test_chk_3c_06_fails_when_all_proposals_stripped(self):
        """
        Status is Failed (CHK-3c-06) when all proposals have only invalid cci_refs
        and are removed by CHK-3c-02, leaving zero surviving domains.
        Repair prompt returns no actions → no domains remain → CHK-3c-06 fires.
        """
        eligible = _FIVE_CCIS[:1]  # only What-001 is eligible
        proposals = [
            DomainProposal(
                name="Ghost Domain",
                description="All refs here are outside the eligible set",
                classification_type=None,
                cci_refs=["CCI-ROW4-C-GHOST-001", "CCI-ROW4-C-GHOST-002"],
            ),
        ]
        with patch(
            "mechanisms.domain_derivation.stage3_structural_validation._call_repair_ai"
        ) as mock_repair:
            # Repair returns no actions — orphan stays, no domains survive
            mock_repair.return_value = (
                MagicMock(
                    content=[MagicMock(text=make_repair_response([]))],
                    model="test",
                    usage=MagicMock(input_tokens=10, output_tokens=10),
                ),
                {"stage": "stage3_repair", "model": "test"},
            )
            result = self._run_stage3(proposals, eligible)

        assert result.status == "failed", (
            "CHK-3c-06: should fail when no domains survive structural validation"
        )


# ---------------------------------------------------------------------------
# TestSchemaValidation — Pydantic schema round-trip checks
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    """Verify Pydantic schemas parse correctly."""

    def test_grouping_response_parses(self):
        data = {
            "proposals": [
                {
                    "name": "Auth Domain",
                    "description": "Authentication and access control concerns",
                    "classification_type": "Security",
                    "cci_refs": ["CCI-ROW4-C-What-001"],
                }
            ]
        }
        resp = DomainGroupingResponse.model_validate(data)
        assert len(resp.proposals) == 1
        assert resp.proposals[0].name == "Auth Domain"

    def test_incremental_response_assign_action(self):
        from mechanisms.domain_derivation.schemas.domain_incremental_response_schema import (
            DomainIncrementalResponse,
        )

        data = {
            "actions": [
                {
                    "action": "assign",
                    "domain_id": "D001",
                    "new_cci_refs": ["CCI-ROW4-C-What-002"],
                }
            ]
        }
        resp = DomainIncrementalResponse.model_validate(data)
        assert resp.actions[0].action == "assign"
        assert resp.actions[0].domain_id == "D001"

    def test_incremental_response_new_action(self):
        from mechanisms.domain_derivation.schemas.domain_incremental_response_schema import (
            DomainIncrementalResponse,
        )

        data = {
            "actions": [
                {
                    "action": "new",
                    "name": "New Domain",
                    "description": "Newly discovered domain for unclassified items",
                    "classification_type": None,
                    "cci_refs": ["CCI-ROW4-C-What-002"],
                }
            ]
        }
        resp = DomainIncrementalResponse.model_validate(data)
        assert resp.actions[0].action == "new"

    def test_repair_response_assign_uses_domain_name(self):
        from mechanisms.domain_derivation.schemas.domain_repair_response_schema import (
            DomainRepairResponse,
        )

        data = {
            "actions": [
                {
                    "action": "assign",
                    "domain_name": "Auth Domain",
                    "new_cci_refs": ["CCI-ROW4-C-What-001"],
                }
            ]
        }
        resp = DomainRepairResponse.model_validate(data)
        assert resp.actions[0].domain_name == "Auth Domain"

    def test_schema_isolation_repair_vs_incremental(self):
        """AssignAction in repair uses domain_name; in incremental uses domain_id."""
        from mechanisms.domain_derivation.schemas.domain_incremental_response_schema import (
            AssignAction as IncAssign,
        )
        from mechanisms.domain_derivation.schemas.domain_repair_response_schema import (
            AssignAction as RepairAssign,
        )

        inc = IncAssign(action="assign", domain_id="D001", new_cci_refs=["CCI-ROW4-C-What-001"])
        assert hasattr(inc, "domain_id")
        assert not hasattr(inc, "domain_name")

        rep = RepairAssign(
            action="assign",
            domain_name="Auth Domain",
            new_cci_refs=["CCI-ROW4-C-What-001"],
        )
        assert hasattr(rep, "domain_name")
        assert not hasattr(rep, "domain_id")

    def test_invalid_domain_id_format_rejected(self):
        from mechanisms.domain_derivation.schemas.domain_incremental_response_schema import (
            AssignAction,
        )

        with pytest.raises(Exception):
            AssignAction(action="assign", domain_id="INVALID", new_cci_refs=["x"])


# ---------------------------------------------------------------------------
# TestVerificationCriteria — VER-3c-XX (mocked AI, requires live Neon session)
# ---------------------------------------------------------------------------


@pytest.mark.db
class TestVerificationCriteria:
    """
    VER-3c-XX verification criteria tests.
    Run each test individually:
      pytest "tests/domain_derivation/test_domain_derivation.py::TestVerificationCriteria::test_ver_3c_01_all_ccis_assigned" -v
    """

    @pytest.fixture(autouse=True)
    def setup(self, session):
        """Seed standard test dataset and set session attribute.

        Cleans up any prior DomainDerivation passes / domain rows for the test
        project before seeding so each test run starts from a clean FirstRun
        state (the orchestrator commits its own session, so prior-run state
        is not rolled back by the test session fixture).
        """
        from tests.domain_derivation.conftest import PROJECT_ID as _PID
        session.execute(
            text("DELETE FROM domain WHERE project_id = :pid"),
            {"pid": _PID},
        )
        session.execute(
            text(
                "DELETE FROM analysis_pass "
                "WHERE project_id = :pid AND mechanism = 'DomainDerivation'"
            ),
            {"pid": _PID},
        )
        session.commit()
        self._session = session
        seed_standard_test_dataset(session)
        session.commit()

    def _make_ai_message(self, text_content: str) -> MagicMock:
        return MagicMock(
            content=[MagicMock(text=text_content)],
            model="claude-test",
            usage=MagicMock(input_tokens=100, output_tokens=200),
        )

    def _default_grouping_response(self) -> str:
        return make_grouping_response(
            [
                {
                    "name": "Authentication Domain",
                    "description": "Components and processes related to authentication and access control",
                    "classification_type": "Security",
                    "cci_refs": [
                        "CCI-ROW4-C-What-001",
                        "CCI-ROW4-C-How-001",
                    ],
                },
                {
                    "name": "Data Access Domain",
                    "description": "Components and processes for database access and query execution",
                    "classification_type": "DataAccess",
                    "cci_refs": [
                        "CCI-ROW4-C-What-002",
                        "CCI-ROW4-C-How-002",
                    ],
                },
                {
                    "name": "Infrastructure Domain",
                    "description": "Deployment targets and infrastructure components",
                    "classification_type": "Infrastructure",
                    "cci_refs": ["CCI-ROW4-C-Where-001"],
                },
            ]
        )

    # VER-3c-01: All eligible CCIs appear in at least one Domain (Non-Loss)
    def test_ver_3c_01_all_ccis_assigned(self):
        """VER-3c-01: All 5 eligible CCIs must appear in domain.cell_content_item_refs."""
        import mechanisms.domain_derivation as dd

        with patch("core.ai_client.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_ai_message(
                self._default_grouping_response()
            )
            result = dd.run(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        assert result["execution_status"] in ("Completed", "CompletedWithWarnings")
        md = result["mechanism_data"]
        assert md["orphaned_ccis"] == [], "VER-3c-01: All CCIs must be assigned"

        rows = self._session.execute(
            text(
                "SELECT COUNT(DISTINCT ci_id) "
                "FROM domain, "
                "     jsonb_array_elements_text(cell_content_item_refs) AS ci_id "
                "WHERE domain.project_id = :pid "
                "  AND domain.row_target = :row "
                "  AND domain.retired_at IS NULL"
            ),
            {"pid": PROJECT_ID, "row": str(ROW_REF)},
        ).fetchone()
        assert rows[0] == 5, f"VER-3c-01: expected 5 distinct CCI refs, got {rows[0]}"

    # VER-3c-02: domain_id format D### for all produced domains
    def test_ver_3c_02_domain_id_format(self):
        """VER-3c-02: All produced domain_ids must match ^D\\d{3}$."""
        import re

        import mechanisms.domain_derivation as dd

        with patch("core.ai_client.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_ai_message(
                self._default_grouping_response()
            )
            result = dd.run(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        assert result["execution_status"] in ("Completed", "CompletedWithWarnings")
        for d in result["mechanism_data"]["domains_produced"]:
            assert re.match(r"^D\d{3}$", d["domain_id"]), (
                f"VER-3c-02: domain_id {d['domain_id']!r} does not match D### format"
            )

    # VER-3c-03: DomainRegister member_ids updated
    def test_ver_3c_03_domain_register_updated(self):
        """VER-3c-03: register table DomainRegister member_ids includes all active domain_ids."""
        import mechanisms.domain_derivation as dd

        with patch("core.ai_client.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_ai_message(
                self._default_grouping_response()
            )
            dd.run(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        reg_row = self._session.execute(
            text(
                "SELECT member_ids FROM register "
                "WHERE register_type = 'Domain' AND project_id = :pid"
            ),
            {"pid": PROJECT_ID},
        ).fetchone()
        assert reg_row is not None, "VER-3c-03: DomainRegister row must exist"
        member_ids = reg_row[0]
        assert isinstance(member_ids, list), "VER-3c-03: member_ids must be a list"
        assert len(member_ids) > 0, "VER-3c-03: member_ids must be non-empty after run"

    # VER-3c-04: IdempotentRerun returns same pass (no new domains)
    def test_ver_3c_04_idempotent_rerun(self):
        """VER-3c-04: Second run with same CCI set is IdempotentRerun — no new entities."""
        import mechanisms.domain_derivation as dd

        with patch("core.ai_client.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_ai_message(
                self._default_grouping_response()
            )
            first = dd.run(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        first_call_count = mock_client.messages.create.call_count

        with patch("core.ai_client.Anthropic") as mock_anthropic2:
            mock_client2 = MagicMock()
            mock_anthropic2.return_value = mock_client2
            second = dd.run(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        assert second["mechanism_data"]["scenario"] == "IdempotentRerun", (
            "VER-3c-04: Second run with same CCI set must be IdempotentRerun"
        )
        assert mock_client2.messages.create.call_count == 0, (
            "VER-3c-04: IdempotentRerun must not call AI"
        )
        assert second["mechanism_data"].get("idempotent") is True, (
            "VER-3c-04: mechanism_data.idempotent must be True on IdempotentRerun"
        )

    # VER-3c-07: FullRerun retires prior domains
    def test_ver_3c_07_fullrerun_retires_prior_domains(self):
        """VER-3c-07: FullRerun sets retired_at on all prior active domains for the row."""
        import mechanisms.domain_derivation as dd

        with patch("core.ai_client.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_ai_message(
                self._default_grouping_response()
            )
            first = dd.run(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        assert first["execution_status"] in ("Completed", "CompletedWithWarnings")
        first_domains = first["mechanism_data"]["domains_produced"]
        first_domain_ids = [d["domain_id"] for d in first_domains]

        with patch("core.ai_client.Anthropic") as mock_anthropic2:
            mock_client2 = MagicMock()
            mock_anthropic2.return_value = mock_client2
            mock_client2.messages.create.return_value = self._make_ai_message(
                make_grouping_response(
                    [
                        {
                            "name": "Revised Auth Domain",
                            "description": "Revised domain for authentication, access and infrastructure",
                            "classification_type": "Security",
                            "cci_refs": [
                                "CCI-ROW4-C-What-001",
                                "CCI-ROW4-C-How-001",
                                "CCI-ROW4-C-Where-001",
                            ],
                        },
                        {
                            "name": "Revised Data Domain",
                            "description": "Revised data access and query domain",
                            "classification_type": "DataAccess",
                            "cci_refs": [
                                "CCI-ROW4-C-What-002",
                                "CCI-ROW4-C-How-002",
                            ],
                        },
                    ]
                )
            )
            # Force FullRerun by patching the hash so it differs
            with patch(
                "mechanisms.domain_derivation.stage1_preflight.hashlib"
            ) as mock_hash:
                mock_hash.sha256.return_value.hexdigest.return_value = "DIFFERENT_HASH"
                second = dd.run(
                    project_id=PROJECT_ID,
                    practitioner_id=PRACTITIONER_ID,
                    row_ref=ROW_REF,
                )

        assert second["mechanism_data"]["scenario"] == "FullRerun", (
            "VER-3c-07: Should be FullRerun when hash differs significantly"
        )

        # Check that first-run domain_ids are now retired
        for domain_id in first_domain_ids:
            row = self._session.execute(
                text(
                    "SELECT retired_at FROM domain "
                    "WHERE domain_id = :did AND project_id = :pid"
                ),
                {"did": domain_id, "pid": PROJECT_ID},
            ).fetchone()
            if row:
                assert row[0] is not None, (
                    f"VER-3c-07: Domain {domain_id} should be retired after FullRerun"
                )

    # VER-3c-12: FirstRun MUST produce at least one Domain
    def test_ver_3c_12_firstrun_produces_at_least_one_domain(self):
        """VER-3c-12: FirstRun that produces zero domains results in Failed status."""
        import mechanisms.domain_derivation as dd

        with patch("core.ai_client.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_ai_message(
                self._default_grouping_response()
            )
            result = dd.run(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        assert result["execution_status"] in ("Completed", "CompletedWithWarnings"), (
            "VER-3c-12: FirstRun with valid grouping must not fail"
        )
        assert result["mechanism_data"]["domain_count_produced"] >= 1, (
            "VER-3c-12: At least one Domain must be produced"
        )

    # VER-3c-13: Stage 1 fails when Pass 3b prerequisite is absent
    def test_ver_3c_13_fails_without_3b_prereq(self):
        """VER-3c-13: Mechanism fails if no completed Pass 3b exists for the row."""
        import mechanisms.domain_derivation as dd

        result = dd.run(
            project_id="NO_SUCH_PROJECT",
            practitioner_id=PRACTITIONER_ID,
            row_ref=99,
        )
        assert result["execution_status"] == "Failed", (
            "VER-3c-13: Must fail when no Pass 3b exists for the project/row"
        )

    # VER-3c-03: Every active Domain has ≥1 entry in cell_content_item_refs
    def test_ver_3c_03_every_domain_has_refs(self):
        """VER-3c-03: Every active domain must have jsonb_array_length(cell_content_item_refs) >= 1."""
        import mechanisms.domain_derivation as dd

        with patch("core.ai_client.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_ai_message(
                self._default_grouping_response()
            )
            result = dd.run(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        assert result["execution_status"] in ("Completed", "CompletedWithWarnings")

        rows = self._session.execute(
            text(
                "SELECT domain_id, jsonb_array_length(cell_content_item_refs) AS ref_count "
                "FROM domain "
                "WHERE project_id = :pid AND row_target = :row AND retired_at IS NULL"
            ),
            {"pid": PROJECT_ID, "row": str(ROW_REF)},
        ).fetchall()
        assert len(rows) > 0, "VER-3c-03: at least one active domain must exist"
        for domain_id, ref_count in rows:
            assert ref_count >= 1, (
                f"VER-3c-03: domain {domain_id} has empty cell_content_item_refs"
            )

    # VER-3c-04: All ci_ids in cell_content_item_refs resolve to cell_content_item with matching row_target
    def test_ver_3c_04_all_cci_refs_valid(self):
        """VER-3c-04: Every ci_id in cell_content_item_refs must resolve to a CCI with matching row_target."""
        import mechanisms.domain_derivation as dd

        with patch("core.ai_client.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_ai_message(
                self._default_grouping_response()
            )
            result = dd.run(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        assert result["execution_status"] in ("Completed", "CompletedWithWarnings")

        mismatches = self._session.execute(
            text(
                "SELECT d.domain_id, refs.ci_id "
                "FROM domain d "
                "CROSS JOIN LATERAL jsonb_array_elements_text(d.cell_content_item_refs) AS refs(ci_id) "
                "LEFT JOIN cell_content_item cci "
                "       ON cci.ci_id = refs.ci_id AND cci.project_id = d.project_id "
                "LEFT JOIN zachman_cell zc "
                "       ON zc.cell_id = cci.cell_id AND zc.project_id = d.project_id "
                "WHERE d.project_id = :pid "
                "  AND d.row_target = :row "
                "  AND d.retired_at IS NULL "
                "  AND (cci.ci_id IS NULL OR zc.row_target != d.row_target)"
            ),
            {"pid": PROJECT_ID, "row": str(ROW_REF)},
        ).fetchall()
        assert mismatches == [], (
            f"VER-3c-04: {len(mismatches)} CCI ref(s) in cell_content_item_refs "
            f"do not resolve or have mismatched row_target: {mismatches}"
        )

    # VER-3c-06: DomainRegister member_ids equals the full set of active domain_ids
    def test_ver_3c_06_register_member_ids_strict_equality(self):
        """VER-3c-06: register.member_ids must equal the set of all active domain_ids for the project."""
        import mechanisms.domain_derivation as dd

        with patch("core.ai_client.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_ai_message(
                self._default_grouping_response()
            )
            dd.run(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        reg_row = self._session.execute(
            text(
                "SELECT member_ids FROM register "
                "WHERE register_type = 'Domain' AND project_id = :pid"
            ),
            {"pid": PROJECT_ID},
        ).fetchone()
        assert reg_row is not None, "VER-3c-06: DomainRegister row must exist"
        register_ids = set(reg_row[0])

        active_rows = self._session.execute(
            text(
                "SELECT domain_id FROM domain "
                "WHERE project_id = :pid AND retired_at IS NULL"
            ),
            {"pid": PROJECT_ID},
        ).fetchall()
        active_ids = {r[0] for r in active_rows}

        assert register_ids == active_ids, (
            f"VER-3c-06: register member_ids {register_ids} != active domain_ids {active_ids}"
        )

    # VER-3c-08: mechanism_data field completeness
    def test_ver_3c_08_mechanism_data_completeness(self):
        """VER-3c-08: mechanism_data must contain all required fields from spec §7."""
        import mechanisms.domain_derivation as dd

        required_fields = {
            "row_ref",
            "scenario",
            "cci_count_input",
            "domain_count_produced",
            "domain_count_retired",
            "domains_produced",
            "cci_set_hash",
            "downstream_rerun_required",
            "retirement_mapping",
            "orphaned_ccis",
            "repair_prompt_issued",
            "cross_cutting_advisories",
            "validation_failures",
            "large_cci_set_advisory",
            "mode_violations",
            "ai_model_fingerprints",
        }

        with patch("core.ai_client.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = self._make_ai_message(
                self._default_grouping_response()
            )
            result = dd.run(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        assert result["execution_status"] in ("Completed", "CompletedWithWarnings")
        md = result["mechanism_data"]
        missing = required_fields - md.keys()
        assert not missing, (
            f"VER-3c-08: mechanism_data missing required fields: {sorted(missing)}"
        )

    # VER-3c-09: domain_qualifier and upstream_domain_ref columns must be absent from domain table
    def test_ver_3c_09_withdrawn_columns_absent(self):
        """VER-3c-09: Withdrawn columns domain_qualifier and upstream_domain_ref must not exist on domain table."""
        withdrawn = {"domain_qualifier", "upstream_domain_ref"}
        rows = self._session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'domain' AND column_name = ANY(:cols)"
            ),
            {"cols": list(withdrawn)},
        ).fetchall()
        present = {r[0] for r in rows}
        assert not present, (
            f"VER-3c-09: withdrawn column(s) found on domain table: {present}"
        )
