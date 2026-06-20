"""
Pass 3d Requirement Derivation — unit and structural validation tests.

IMPORTANT: run tests INDIVIDUALLY per project convention.
Example:
  pytest "tests/requirement_derivation/test_requirement_derivation.py::TestStage1Preflight::test_no_3c_pass_fails" -v

Tests that require a live Neon DB are marked @pytest.mark.db.
DB tests MUST be run one at a time due to Neon connection-pool interference.

Test coverage:
  TestStage1Preflight              — Unit / DB tests for Stage 1 logic
  TestStage3Validation             — Unit tests for CHK-3d-01 through CHK-3d-07
  TestStage2Routing                — Unit tests for scenario detection routing
  TestVerificationCriteria         — VER-3d-XX criteria (mocked AI, live session)
  TestCHK3d11AttributeWellFormed   — VER-3d-26: [G] attr_name + semantic_type shape/POS checks
  TestSemanticTypeRegistry         — Unit tests for the accreting semantic_type registry
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

from core.class_model_validity import validate_class_model
from core.semantic_type_registry import SemanticTypeRegistry
from mechanisms.requirement_derivation.schemas.requirement_derivation_response_schema import (
    RequirementProposal,
)
from mechanisms.requirement_derivation.stage1_preflight import (
    ActiveDomain,
    EligibleCCI,
    Stage1Result,
)
from mechanisms.requirement_derivation.stage2_ai_derivation import (
    Stage2Result,
    TaggedProposal,
)
from tests.requirement_derivation.conftest import (
    DOMAIN_A_CCIS,
    DOMAIN_A_ID,
    DOMAIN_B_CCIS,
    DOMAIN_B_ID,
    PRACTITIONER_ID,
    PROJECT_ID,
    ROW_REF,
    make_derivation_response,
    make_repair_response,
    seed_standard_test_dataset,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stage1(
    eligible_ccis: list[EligibleCCI],
    active_domains: list[ActiveDomain] | None = None,
    scenario: str = "FirstRun",
    current_hash: str = "abc123",
) -> Stage1Result:
    s = Stage1Result()
    s.eligible_ccis = eligible_ccis
    s.active_domains = active_domains or []
    s.scenario = scenario
    s.current_hash = current_hash
    s.requirement_rerun_threshold = 0.20
    s.requirement_large_cci_set_advisory_threshold = 80
    return s


def _make_stage2(proposals: list[TaggedProposal]) -> Stage2Result:
    s = Stage2Result()
    s.proposals = proposals
    s.effective_scenario = "FirstRun"
    return s


_FIVE_CCIS = [
    EligibleCCI("CCI-ROW4-C-What-001", "What", "Component", "Auth service component"),
    EligibleCCI("CCI-ROW4-C-What-002", "What", "Component", "DB access layer"),
    EligibleCCI("CCI-ROW4-C-How-001", "How", "Process", "OAuth2 token validation"),
    EligibleCCI("CCI-ROW4-C-How-002", "How", "Process", "DB query execution"),
    EligibleCCI("CCI-ROW4-C-Where-001", "Where", "Location", "Cloud deployment target"),
]

_DOMAIN_A = ActiveDomain(
    domain_id=DOMAIN_A_ID,
    name="Authentication Infrastructure",
    description="Physical auth components",
    cell_content_item_refs=DOMAIN_A_CCIS,
)
_DOMAIN_B = ActiveDomain(
    domain_id=DOMAIN_B_ID,
    name="Data Access and Deployment Platform",
    description="DB and deployment",
    cell_content_item_refs=DOMAIN_B_CCIS,
)


def _make_proposal(
    statement: str,
    cci_refs: list[str],
    source_domain_id: str = DOMAIN_A_ID,
    requirement_type: str = "Functional",
    confidence: float = 0.90,
) -> TaggedProposal:
    return TaggedProposal(
        source_domain_id=source_domain_id,
        statement=statement,
        requirement_type=requirement_type,
        cci_refs=cci_refs,
        rationale=None,
        fit_criteria=None,
        verification_method=None,
        priority=None,
        confidence=confidence,
    )


def _run_stage3(
    proposals: list[TaggedProposal],
    ccis: list[EligibleCCI],
    domains: list[ActiveDomain],
    scenario: str = "FirstRun",
) -> Any:
    from mechanisms.requirement_derivation.stage3_structural_validation import run_stage3
    stage1 = _make_stage1(ccis, domains, scenario)
    stage2 = _make_stage2(proposals)
    return run_stage3(
        stage1=stage1,
        stage2=stage2,
        practitioner_id=PRACTITIONER_ID,
        project_id=PROJECT_ID,
        row_ref=ROW_REF,
    )


# ---------------------------------------------------------------------------
# TestStage1Preflight — Unit tests
# ---------------------------------------------------------------------------


class TestStage1Preflight:
    """Unit and DB tests for Stage 1 logic."""

    def test_no_3c_pass_fails(self, session):
        """Stage 1 fails with correct failure_reason when no Pass 3c exists."""
        from mechanisms.requirement_derivation.stage1_preflight import run_stage1

        session.execute(
            text("DELETE FROM analysis_pass WHERE project_id = :pid AND mechanism = 'DomainDerivation'"),
            {"pid": PROJECT_ID},
        )

        result = run_stage1(
            project_id=PROJECT_ID,
            row_ref=ROW_REF,
            session=session,
        )
        session.rollback()

        assert result.status == "failed"
        assert "prerequisite" in result.failure_reason.lower()

    @pytest.mark.db
    def test_zero_cci_triggers_early_exit(self, session):
        """
        Stage 1 returns zero_cci_exit when no CCIs exist for the row.
        Seeds a 3c pass but no CCIs.
        """
        from mechanisms.requirement_derivation.stage1_preflight import run_stage1
        from tests.requirement_derivation.conftest import (
            seed_3c_pass,
            seed_project,
            seed_project_profile,
        )

        # Clean state
        session.execute(
            text("DELETE FROM analysis_pass WHERE project_id = :pid"), {"pid": PROJECT_ID}
        )
        session.execute(
            text("DELETE FROM cell_content_item WHERE project_id = :pid"), {"pid": PROJECT_ID}
        )
        session.flush()

        seed_project(session)
        seed_project_profile(session)
        seed_3c_pass(session)
        session.flush()

        result = run_stage1(
            project_id=PROJECT_ID,
            row_ref=ROW_REF,
            session=session,
        )
        session.rollback()

        assert result.status == "zero_cci_exit"
        assert any(w["type"] == "no_cci_input" for w in result.execution_warnings)

    @pytest.mark.db
    def test_first_run_scenario_with_domains(self, session):
        """
        Stage 1 returns FirstRun scenario with correct eligible_ccis and
        active_domains when no prior Pass 3d exists.
        """
        from mechanisms.requirement_derivation.stage1_preflight import run_stage1

        # Full clean
        session.execute(
            text(
                "DELETE FROM analysis_pass WHERE project_id = :pid "
                "AND mechanism = 'RequirementDerivation'"
            ),
            {"pid": PROJECT_ID},
        )
        session.execute(
            text("DELETE FROM requirement WHERE project_id = :pid"),
            {"pid": PROJECT_ID},
        )
        session.execute(
            text("DELETE FROM domain WHERE project_id = :pid"),
            {"pid": PROJECT_ID},
        )
        session.execute(
            text("DELETE FROM cell_content_item WHERE project_id = :pid"),
            {"pid": PROJECT_ID},
        )
        session.execute(
            text("DELETE FROM analysis_pass WHERE project_id = :pid"),
            {"pid": PROJECT_ID},
        )
        session.flush()

        seed_standard_test_dataset(session)
        session.flush()

        result = run_stage1(
            project_id=PROJECT_ID,
            row_ref=ROW_REF,
            session=session,
        )
        session.rollback()

        assert result.status == "continue"
        assert result.scenario == "FirstRun"
        assert len(result.eligible_ccis) == 5
        assert len(result.active_domains) == 2
        assert result.current_hash != ""

    @pytest.mark.db
    def test_idempotent_rerun_when_hash_unchanged(self, session):
        """
        Stage 1 returns IdempotentRerun when the two-part hash matches the prior pass.
        Seeds a prior RequirementDerivation pass with matching hash and domain_id_set.
        """
        from datetime import datetime, timezone

        from core.db import format_identifier, get_next_sequence_value
        from mechanisms.requirement_derivation.stage1_preflight import run_stage1

        session.execute(
            text(
                "DELETE FROM analysis_pass WHERE project_id = :pid "
                "AND mechanism = 'RequirementDerivation'"
            ),
            {"pid": PROJECT_ID},
        )
        session.execute(
            text("DELETE FROM domain WHERE project_id = :pid"),
            {"pid": PROJECT_ID},
        )
        session.execute(
            text("DELETE FROM cell_content_item WHERE project_id = :pid"),
            {"pid": PROJECT_ID},
        )
        session.execute(
            text("DELETE FROM analysis_pass WHERE project_id = :pid"),
            {"pid": PROJECT_ID},
        )
        session.flush()

        seed_standard_test_dataset(session)
        session.flush()

        # First pass — get actual hash from Stage 1
        probe = run_stage1(
            project_id=PROJECT_ID,
            row_ref=ROW_REF,
            session=session,
        )
        assert probe.status == "continue"
        actual_hash = probe.current_hash
        actual_domain_ids = sorted(d.domain_id for d in probe.active_domains)

        # Seed a prior RequirementDerivation pass with matching hash
        seq_val = get_next_sequence_value(session, "p_id_seq")
        pass_id = format_identifier("P", seq_val)
        now = datetime.now(timezone.utc)
        session.add(
            __import__("models", fromlist=["AnalysisPassModel"]).AnalysisPassModel(
                pass_id=pass_id,
                phase_id="PH003",
                pass_type="Universal",
                mechanism="RequirementDerivation",
                evaluated_scope=f"Row {ROW_REF} for {PROJECT_ID}",
                confidence=1.0,
                pass_started_at=now,
                pass_completed_at=now,
                execution_status="Completed",
                mode_active="IM",
                declared_transformation_modes=["IM", "DM"],
                elapsed_ms=100,
                practitioner_id=PRACTITIONER_ID,
                project_id=PROJECT_ID,
                outputs={
                    "mechanism_data": {
                        "row_ref": ROW_REF,
                        "requirement_input_hash": actual_hash,
                        "domain_id_set": actual_domain_ids,
                        "cci_count_input": 5,
                        "requirement_count_produced": 3,
                    }
                },
            )
        )
        session.flush()

        # Re-run Stage 1 — should detect Idempotent
        result = run_stage1(
            project_id=PROJECT_ID,
            row_ref=ROW_REF,
            session=session,
        )
        session.rollback()

        assert result.status == "idempotent_exit"
        assert result.scenario == "IdempotentRerun"


# ---------------------------------------------------------------------------
# TestStage3Validation — CHK-3d-01 through CHK-3d-07
# ---------------------------------------------------------------------------


class TestStage3Validation:
    """Unit tests for Stage 3 structural checks (no AI, no DB)."""

    def test_chk_3d_01_empty_statement_dropped(self):
        """CHK-3d-01: proposal with empty statement is rejected."""
        proposals = [
            _make_proposal("", ["CCI-ROW4-C-What-001"]),
            _make_proposal(
                "The system shall authenticate users via OAuth2.",
                ["CCI-ROW4-C-What-001"],
            ),
        ]
        result = _run_stage3(proposals, _FIVE_CCIS, [_DOMAIN_A, _DOMAIN_B])

        assert any(f["check_id"] == "CHK-3d-01" for f in result.validation_failures)
        surviving_stmts = [p.statement for p in result.proposals]
        assert "" not in surviving_stmts
        assert any("OAuth2" in s for s in surviving_stmts)

    def test_chk_3d_02_empty_cci_refs_dropped(self):
        """CHK-3d-02: proposal with empty cci_refs is rejected."""
        good = _make_proposal(
            "The system shall authenticate users via OAuth2.",
            ["CCI-ROW4-C-What-001"],
        )
        bad = TaggedProposal(
            source_domain_id=DOMAIN_A_ID,
            statement="A phantom requirement.",
            requirement_type="Functional",
            cci_refs=[],
            rationale=None,
            fit_criteria=None,
            verification_method=None,
            priority=None,
            confidence=0.5,
        )
        result = _run_stage3([good, bad], _FIVE_CCIS, [_DOMAIN_A, _DOMAIN_B])

        assert any(f["check_id"] == "CHK-3d-02" for f in result.validation_failures)
        assert len(result.proposals) >= 1

    def test_chk_3d_03_cci_ref_outside_domain_stripped(self):
        """CHK-3d-03: cci_ref not in source Domain membership is stripped."""
        # Domain A owns CCI-ROW4-C-What-001 and CCI-ROW4-C-How-001 only
        # Proposing a ref from Domain B's set is out-of-Domain
        proposal = _make_proposal(
            "The system shall execute DB queries for authentication.",
            ["CCI-ROW4-C-What-001", "CCI-ROW4-C-How-002"],  # How-002 is in Domain B
            source_domain_id=DOMAIN_A_ID,
        )
        result = _run_stage3([proposal], _FIVE_CCIS, [_DOMAIN_A, _DOMAIN_B])

        chk03_failures = [f for f in result.validation_failures if f["check_id"] == "CHK-3d-03"]
        assert chk03_failures, "CHK-3d-03 should have fired for out-of-Domain ref"
        # Valid refs survive — proposal kept with stripped refs
        surviving = [p for p in result.proposals if "The system shall execute" in p.statement]
        if surviving:
            assert "CCI-ROW4-C-How-002" not in surviving[0].cci_refs

    def test_chk_3d_04_fit_criteria_empty_stripped(self):
        """CHK-3d-04: present-but-empty fit_criteria is stripped to None."""
        proposal = TaggedProposal(
            source_domain_id=DOMAIN_A_ID,
            statement="The system shall authenticate users.",
            requirement_type="Functional",
            cci_refs=["CCI-ROW4-C-What-001"],
            rationale=None,
            fit_criteria="   ",
            verification_method=None,
            priority=None,
            confidence=0.85,
        )
        result = _run_stage3([proposal], _FIVE_CCIS, [_DOMAIN_A, _DOMAIN_B])

        assert any(
            w["type"] == "fit_criteria_empty_stripped"
            for w in result.execution_warnings
        )
        if result.proposals:
            assert result.proposals[0].fit_criteria is None

    def test_chk_3d_04_performance_without_fit_criteria_advisory(self):
        """CHK-3d-04: Performance requirement without fit_criteria triggers advisory."""
        proposal = TaggedProposal(
            source_domain_id=DOMAIN_A_ID,
            statement="The system shall respond within a threshold.",
            requirement_type="Performance",
            cci_refs=["CCI-ROW4-C-What-001"],
            rationale=None,
            fit_criteria=None,
            verification_method=None,
            priority=None,
            confidence=0.75,
        )
        result = _run_stage3([proposal], _FIVE_CCIS, [_DOMAIN_A, _DOMAIN_B])

        assert any(
            w["type"] == "performance_missing_fit_criteria"
            for w in result.execution_warnings
        )

    def test_chk_3d_07_exact_duplicate_collapsed(self):
        """CHK-3d-07: two proposals with same statement and same cci_refs are collapsed."""
        stmt = "The system shall authenticate users via OAuth2."
        p1 = _make_proposal(stmt, ["CCI-ROW4-C-What-001", "CCI-ROW4-C-How-001"])
        p2 = _make_proposal(stmt, ["CCI-ROW4-C-How-001", "CCI-ROW4-C-What-001"])

        result = _run_stage3([p1, p2], _FIVE_CCIS, [_DOMAIN_A, _DOMAIN_B])

        matching = [p for p in result.proposals if stmt in p.statement]
        assert len(matching) == 1, "Duplicate should be collapsed to one"
        assert result.duplicate_requirements_collapsed

    @patch("mechanisms.requirement_derivation.stage3_structural_validation._call_repair_ai")
    def test_chk_3d_05_non_loss_repair_called_on_orphan(self, mock_repair):
        """
        CHK-3d-05: when CCIs are orphaned, repair AI is called and proposals added.
        Domain A owns CCI-ROW4-C-What-001 and CCI-ROW4-C-How-001. If both are left
        uncovered, the repair prompt fires and the mock's proposal covers How-001.
        """
        repair_proposals = [
            {
                "statement": "The system shall perform OAuth2 token validation.",
                "requirement_type": "Functional",
                "cci_refs": ["CCI-ROW4-C-How-001"],
                "rationale": "Covers orphaned CCI",
                "fit_criteria": None,
                "verification_method": None,
                "priority": None,
                "confidence": 0.80,
            }
        ]
        mock_msg = MagicMock()
        mock_msg.content[0].text = json.dumps(repair_proposals)
        mock_msg.model = "claude-test"
        mock_msg.usage.input_tokens = 100
        mock_msg.usage.output_tokens = 50
        mock_repair.return_value = (mock_msg, {"stage": "stage3_repair", "model": "claude-test", "input_tokens": 100, "output_tokens": 50})

        # Only cover What-001; leave How-001 orphaned
        initial_proposals = [
            _make_proposal(
                "The system shall authenticate users.",
                ["CCI-ROW4-C-What-001"],
                source_domain_id=DOMAIN_A_ID,
            )
        ]

        result = _run_stage3(initial_proposals, _FIVE_CCIS, [_DOMAIN_A, _DOMAIN_B])

        assert result.repair_prompt_issued
        # After repair, How-001 should be covered
        all_covered = {ref for p in result.proposals for ref in p.cci_refs}
        assert "CCI-ROW4-C-How-001" in all_covered


# ---------------------------------------------------------------------------
# TestStage2Routing — unit tests for scenario routing
# ---------------------------------------------------------------------------


class TestStage2Routing:
    """Unit tests for Stage 2 scenario routing (mocked AI)."""

    @patch("mechanisms.requirement_derivation.stage2_ai_derivation._call_ai")
    def test_firstrun_produces_tagged_proposals(self, mock_call):
        """FirstRun path calls AI once per Domain and tags each proposal."""
        proposals_a = [
            {
                "statement": "The system shall authenticate users via OAuth2.",
                "requirement_type": "Functional",
                "cci_refs": ["CCI-ROW4-C-What-001"],
                "rationale": None,
                "fit_criteria": None,
                "verification_method": "Test",
                "priority": "High",
                "confidence": 0.90,
            }
        ]
        proposals_b = [
            {
                "statement": "The system shall execute DB queries against the data access layer.",
                "requirement_type": "Functional",
                "cci_refs": ["CCI-ROW4-C-What-002"],
                "rationale": None,
                "fit_criteria": None,
                "verification_method": None,
                "priority": None,
                "confidence": 0.85,
            }
        ]

        call_count = [0]

        def side_effect(prompt: str) -> tuple:
            idx = call_count[0]
            call_count[0] += 1
            body = proposals_a if idx == 0 else proposals_b
            msg = MagicMock()
            msg.content[0].text = json.dumps(body)
            msg.model = "claude-test"
            msg.usage.input_tokens = 100
            msg.usage.output_tokens = 50
            return msg, {
                "model": "claude-test",
                "input_tokens": 100,
                "output_tokens": 50,
            }

        mock_call.side_effect = side_effect

        from mechanisms.requirement_derivation.stage2_ai_derivation import run_stage2
        from sqlalchemy.orm import Session

        stage1 = _make_stage1(_FIVE_CCIS, [_DOMAIN_A, _DOMAIN_B], "FirstRun")
        stage2 = run_stage2(
            stage1=stage1,
            session=MagicMock(spec=Session),
            project_id=PROJECT_ID,
            row_ref=ROW_REF,
        )

        assert stage2.status == "ok"
        assert len(stage2.proposals) == 2
        domain_ids_produced = {p.source_domain_id for p in stage2.proposals}
        assert DOMAIN_A_ID in domain_ids_produced
        assert DOMAIN_B_ID in domain_ids_produced

    @patch("mechanisms.requirement_derivation.stage2_ai_derivation._call_ai")
    def test_parse_failure_all_domains_marks_failed(self, mock_call):
        """If all Domain AI calls fail to parse, stage2.status == 'failed'."""
        msg = MagicMock()
        msg.content[0].text = "INVALID JSON RESPONSE"
        mock_call.return_value = (
            msg,
            {"model": "claude-test", "input_tokens": 10, "output_tokens": 5},
        )

        from mechanisms.requirement_derivation.stage2_ai_derivation import run_stage2
        from sqlalchemy.orm import Session

        stage1 = _make_stage1(_FIVE_CCIS, [_DOMAIN_A, _DOMAIN_B], "FirstRun")
        stage2 = run_stage2(
            stage1=stage1,
            session=MagicMock(spec=Session),
            project_id=PROJECT_ID,
            row_ref=ROW_REF,
        )

        assert stage2.status == "failed"
        assert stage2.failure_reason is not None


# ---------------------------------------------------------------------------
# TestVerificationCriteria — VER-3d-XX (mocked AI, live session)
# ---------------------------------------------------------------------------


class TestVerificationCriteria:
    """
    Verification criteria tests for Pass 3d.
    Requires a live Neon session. Run individually.

    VER-3d-01  FirstRun: ≥1 Requirement produced per Domain.
    VER-3d-02  FullRerun: prior active Requirements retired.
    VER-3d-03  RequirementRegister.member_ids updated correctly after run.
    VER-3d-04  domain_refs DM-derived: each produced Requirement has ≥1 domain_ref.
    VER-3d-05  Non-Loss: every eligible CCI covered by ≥1 active Requirement.
               (Persistent orphan → CompletedWithWarnings, not Failed — VER-3d-05b.)
    VER-3d-06  Idempotent: second run with unchanged inputs returns IdempotentRerun.
    VER-3d-07  IncrementalRerun: new CCI below threshold → IncrementalRerun scenario.
    """

    def _make_mock_call_ai(self, per_domain_proposals: dict[str, list[dict]]) -> Any:
        """
        Build a mock _call_ai that dispatches proposals based on Domain keywords
        found in the prompt.
        """
        call_count = [0]

        def side_effect(prompt: str) -> tuple:
            idx = call_count[0]
            call_count[0] += 1
            # Inspect prompt for domain_id hint
            body = None
            for domain_id, proposals in per_domain_proposals.items():
                if domain_id in prompt:
                    body = proposals
                    break
            if body is None:
                body = list(per_domain_proposals.values())[idx % len(per_domain_proposals)]
            msg = MagicMock()
            msg.content[0].text = json.dumps(body)
            msg.model = "claude-test"
            msg.usage.input_tokens = 200
            msg.usage.output_tokens = 100
            return msg, {
                "model": "claude-test",
                "input_tokens": 200,
                "output_tokens": 100,
            }

        return side_effect

    def _full_clean(self, session) -> None:
        for tbl in [
            "requirement",
            "concern",
            "analysis_pass",
            "domain",
            "cell_content_item",
            "zachman_cell",
            "register",
            "project_profile",
        ]:
            session.execute(
                text(f"DELETE FROM {tbl} WHERE project_id = :pid"),
                {"pid": PROJECT_ID},
            )
        session.flush()

    @pytest.mark.db
    def test_ver_3d_01_first_run_requirement_per_domain(self, session):
        """
        VER-3d-01: FirstRun produces ≥1 Requirement per Domain.
        Mocked AI returns 1 proposal per Domain. Both Domains yield Requirements.
        """
        self._full_clean(session)
        seed_standard_test_dataset(session)
        session.commit()

        per_domain_proposals = {
            DOMAIN_A_ID: [
                {
                    "statement": "The system shall support OAuth2 token authentication.",
                    "requirement_type": "Functional",
                    "cci_refs": ["CCI-ROW4-C-What-001", "CCI-ROW4-C-How-001"],
                    "rationale": None,
                    "fit_criteria": None,
                    "verification_method": "Test",
                    "priority": "High",
                    "confidence": 0.92,
                }
            ],
            DOMAIN_B_ID: [
                {
                    "statement": "The system shall provide a database access layer for query execution.",
                    "requirement_type": "Functional",
                    "cci_refs": ["CCI-ROW4-C-What-002", "CCI-ROW4-C-How-002", "CCI-ROW4-C-Where-001"],
                    "rationale": None,
                    "fit_criteria": None,
                    "verification_method": None,
                    "priority": None,
                    "confidence": 0.88,
                }
            ],
        }

        with patch(
            "mechanisms.requirement_derivation.stage2_ai_derivation._call_ai",
            side_effect=self._make_mock_call_ai(per_domain_proposals),
        ):
            from mechanisms.requirement_derivation import run_requirement_derivation
            result = run_requirement_derivation(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        assert result["execution_status"] in ("Completed", "CompletedWithWarnings"), result
        assert result["requirement_count_produced"] >= 2

        # Verify: ≥1 Requirement per Domain
        req_rows = session.execute(
            text(
                "SELECT requirement_id, domain_refs FROM requirement "
                "WHERE project_id = :pid AND row_target = :row AND retired_at IS NULL"
            ),
            {"pid": PROJECT_ID, "row": str(ROW_REF)},
        ).fetchall()

        domains_with_reqs = set()
        for row in req_rows:
            for did in (row[1] or []):
                domains_with_reqs.add(did)

        assert DOMAIN_A_ID in domains_with_reqs, f"Domain A has no Requirements. domains_with_reqs={domains_with_reqs}"
        assert DOMAIN_B_ID in domains_with_reqs, f"Domain B has no Requirements. domains_with_reqs={domains_with_reqs}"

    @pytest.mark.db
    def test_ver_3d_03_requirement_register_updated(self, session):
        """
        VER-3d-03: RequirementRegister.member_ids is updated to match active
        Requirement ids after a successful run.
        """
        self._full_clean(session)
        seed_standard_test_dataset(session)
        session.commit()

        per_domain_proposals = {
            DOMAIN_A_ID: [
                {
                    "statement": "The system shall authenticate users.",
                    "requirement_type": "Functional",
                    "cci_refs": ["CCI-ROW4-C-What-001", "CCI-ROW4-C-How-001"],
                    "rationale": None,
                    "fit_criteria": None,
                    "verification_method": None,
                    "priority": None,
                    "confidence": 0.90,
                }
            ],
            DOMAIN_B_ID: [
                {
                    "statement": "The system shall manage DB access and deployment.",
                    "requirement_type": "Functional",
                    "cci_refs": ["CCI-ROW4-C-What-002", "CCI-ROW4-C-How-002", "CCI-ROW4-C-Where-001"],
                    "rationale": None,
                    "fit_criteria": None,
                    "verification_method": None,
                    "priority": None,
                    "confidence": 0.87,
                }
            ],
        }

        with patch(
            "mechanisms.requirement_derivation.stage2_ai_derivation._call_ai",
            side_effect=self._make_mock_call_ai(per_domain_proposals),
        ):
            from mechanisms.requirement_derivation import run_requirement_derivation
            result = run_requirement_derivation(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        assert result["execution_status"] in ("Completed", "CompletedWithWarnings")

        # Read back RequirementRegister
        reg_row = session.execute(
            text(
                "SELECT member_ids FROM register "
                "WHERE register_type = 'Requirement' AND project_id = :pid"
            ),
            {"pid": PROJECT_ID},
        ).fetchone()
        assert reg_row is not None, "RequirementRegister row missing"

        member_ids = reg_row[0] if isinstance(reg_row[0], list) else json.loads(reg_row[0])

        # Live requirement_ids
        active_rows = session.execute(
            text(
                "SELECT requirement_id FROM requirement "
                "WHERE project_id = :pid AND retired_at IS NULL"
            ),
            {"pid": PROJECT_ID},
        ).fetchall()
        active_ids = sorted(r[0] for r in active_rows)

        assert sorted(member_ids) == active_ids, (
            f"Register mismatch: member_ids={sorted(member_ids)} active={active_ids}"
        )

    @pytest.mark.db
    def test_ver_3d_04_domain_refs_dm_derived(self, session):
        """
        VER-3d-04: domain_refs on each produced Requirement are DM-derived
        (no ≤0 length; reference valid Domain ids that own at least one CCI
        in that Requirement's cci_refs).
        """
        self._full_clean(session)
        seed_standard_test_dataset(session)
        session.commit()

        per_domain_proposals = {
            DOMAIN_A_ID: [
                {
                    "statement": "The system shall validate OAuth2 tokens at the auth service boundary.",
                    "requirement_type": "Functional",
                    "cci_refs": ["CCI-ROW4-C-What-001", "CCI-ROW4-C-How-001"],
                    "rationale": None,
                    "fit_criteria": None,
                    "verification_method": "Test",
                    "priority": None,
                    "confidence": 0.93,
                }
            ],
            DOMAIN_B_ID: [
                {
                    "statement": "The system shall deploy the data access layer to the cloud platform.",
                    "requirement_type": "Functional",
                    "cci_refs": ["CCI-ROW4-C-What-002", "CCI-ROW4-C-How-002", "CCI-ROW4-C-Where-001"],
                    "rationale": None,
                    "fit_criteria": None,
                    "verification_method": None,
                    "priority": None,
                    "confidence": 0.89,
                }
            ],
        }

        with patch(
            "mechanisms.requirement_derivation.stage2_ai_derivation._call_ai",
            side_effect=self._make_mock_call_ai(per_domain_proposals),
        ):
            from mechanisms.requirement_derivation import run_requirement_derivation
            result = run_requirement_derivation(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        assert result["execution_status"] in ("Completed", "CompletedWithWarnings")

        req_rows = session.execute(
            text(
                "SELECT requirement_id, cci_refs, domain_refs FROM requirement "
                "WHERE project_id = :pid AND row_target = :row AND retired_at IS NULL"
            ),
            {"pid": PROJECT_ID, "row": str(ROW_REF)},
        ).fetchall()

        valid_domain_ids = {DOMAIN_A_ID, DOMAIN_B_ID}
        for row in req_rows:
            domain_refs = row[2] if isinstance(row[2], list) else json.loads(row[2])
            assert len(domain_refs) >= 1, f"{row[0]} has empty domain_refs"
            for did in domain_refs:
                assert did in valid_domain_ids, (
                    f"{row[0]} references unknown domain_id {did!r}"
                )

    @pytest.mark.db
    def test_ver_3d_06_idempotent_second_run(self, session):
        """
        VER-3d-06: running Pass 3d twice with identical inputs returns
        IdempotentRerun on the second run.
        """
        self._full_clean(session)
        seed_standard_test_dataset(session)
        session.commit()

        per_domain_proposals = {
            DOMAIN_A_ID: [
                {
                    "statement": "The system shall authenticate users.",
                    "requirement_type": "Functional",
                    "cci_refs": ["CCI-ROW4-C-What-001", "CCI-ROW4-C-How-001"],
                    "rationale": None,
                    "fit_criteria": None,
                    "verification_method": None,
                    "priority": None,
                    "confidence": 0.90,
                }
            ],
            DOMAIN_B_ID: [
                {
                    "statement": "The system shall manage DB access.",
                    "requirement_type": "Functional",
                    "cci_refs": ["CCI-ROW4-C-What-002", "CCI-ROW4-C-How-002", "CCI-ROW4-C-Where-001"],
                    "rationale": None,
                    "fit_criteria": None,
                    "verification_method": None,
                    "priority": None,
                    "confidence": 0.87,
                }
            ],
        }

        from mechanisms.requirement_derivation import run_requirement_derivation

        with patch(
            "mechanisms.requirement_derivation.stage2_ai_derivation._call_ai",
            side_effect=self._make_mock_call_ai(per_domain_proposals),
        ):
            first = run_requirement_derivation(
                project_id=PROJECT_ID,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW_REF,
            )

        assert first["execution_status"] in ("Completed", "CompletedWithWarnings")

        second = run_requirement_derivation(
            project_id=PROJECT_ID,
            practitioner_id=PRACTITIONER_ID,
            row_ref=ROW_REF,
        )

        assert second["execution_status"] in ("Completed", "CompletedWithWarnings")
        assert second.get("scenario") == "IdempotentRerun", (
            f"Expected IdempotentRerun on second run; got scenario={second.get('scenario')}"
        )


# ---------------------------------------------------------------------------
# VER-3d-26: CHK-3d-11 [G] attribute well-formedness (v0.37)
# ---------------------------------------------------------------------------


class TestCHK3d11AttributeWellFormed:
    """
    VER-3d-26: CHK-3d-11 [G] attribute well-formedness checks (v0.37).

    Hard checks added by [G]:
      attr_name_empty       — attribute.name is null/empty
      semantic_type_pos_tag — semantic_type is a universal POS tag (case-insensitive)
      semantic_type_malformed — semantic_type fails ^[a-z][a-z0-9_]*$ shape

    Run individually (no DB required):
      pytest "tests/requirement_derivation/test_requirement_derivation.py::TestCHK3d11AttributeWellFormed::test_attr_name_empty_is_hard_violation" -v
    """

    def _cm(self, attrs: list[dict], row_ref: int = 2) -> dict:
        return {
            "entity": "BloodPressure",
            "tier": row_ref,
            "refinement_kind": "introduce",
            "attributes": attrs,
        }

    def test_attr_name_empty_is_hard_violation(self):
        """attr_name null/empty → hard violation with detail 'attr_name_empty'."""
        cm = self._cm([
            {"name": "", "origin": "introduced", "semantic_type": "measurement"},
        ])
        violations = validate_class_model(cm, row_ref=2)
        details = [v["detail"] for v in violations]
        assert "attr_name_empty" in details, f"Expected attr_name_empty; got {details}"
        assert all(
            v["severity"] == "hard"
            for v in violations
            if v["detail"] == "attr_name_empty"
        )

    def test_attr_name_none_is_hard_violation(self):
        """attr_name=None → hard violation with detail 'attr_name_empty'."""
        cm = self._cm([
            {"name": None, "origin": "introduced", "semantic_type": "measurement"},
        ])
        violations = validate_class_model(cm, row_ref=2)
        details = [v["detail"] for v in violations]
        assert "attr_name_empty" in details, f"Expected attr_name_empty; got {details}"

    def test_semantic_type_pos_tag_capitalized(self):
        """semantic_type='Noun' → hard violation 'semantic_type_pos_tag' (POS check before shape)."""
        cm = self._cm([
            {"name": "systolic", "origin": "introduced", "semantic_type": "Noun"},
        ])
        violations = validate_class_model(cm, row_ref=2)
        details = [v["detail"] for v in violations]
        assert "semantic_type_pos_tag" in details, f"Expected semantic_type_pos_tag; got {details}"
        assert all(
            v["severity"] == "hard"
            for v in violations
            if v["detail"] == "semantic_type_pos_tag"
        )

    def test_semantic_type_pos_tag_lowercase(self):
        """semantic_type='noun' (lowercase) → hard violation 'semantic_type_pos_tag'."""
        cm = self._cm([
            {"name": "status", "origin": "introduced", "semantic_type": "noun"},
        ])
        violations = validate_class_model(cm, row_ref=2)
        details = [v["detail"] for v in violations]
        assert "semantic_type_pos_tag" in details, f"Expected semantic_type_pos_tag; got {details}"

    def test_semantic_type_pos_tag_verb(self):
        """semantic_type='verb' → hard violation 'semantic_type_pos_tag'."""
        cm = self._cm([
            {"name": "action", "origin": "introduced", "semantic_type": "verb"},
        ])
        violations = validate_class_model(cm, row_ref=2)
        details = [v["detail"] for v in violations]
        assert "semantic_type_pos_tag" in details, f"Expected semantic_type_pos_tag; got {details}"

    def test_semantic_type_malformed_physical_type(self):
        """semantic_type='VARCHAR(255)' → hard violation 'semantic_type_malformed'."""
        cm = self._cm([
            {"name": "bp_value", "origin": "introduced", "semantic_type": "VARCHAR(255)"},
        ], row_ref=3)
        violations = validate_class_model(cm, row_ref=3)
        details = [v["detail"] for v in violations]
        assert "semantic_type_malformed" in details, f"Expected semantic_type_malformed; got {details}"
        assert all(
            v["severity"] == "hard"
            for v in violations
            if v["detail"] == "semantic_type_malformed"
        )

    def test_semantic_type_malformed_uppercase_start(self):
        """semantic_type='BloodPressure' → hard violation 'semantic_type_malformed' (shape fails)."""
        cm = self._cm([
            {"name": "value", "origin": "introduced", "semantic_type": "BloodPressure"},
        ], row_ref=3)
        violations = validate_class_model(cm, row_ref=3)
        details = [v["detail"] for v in violations]
        assert "semantic_type_malformed" in details, f"Expected semantic_type_malformed; got {details}"

    def test_domain_specific_semantic_type_passes(self):
        """systolic_pressure is a novel domain term — shape-valid, not a POS tag → no [G] violation."""
        cm = self._cm([
            {"name": "value", "origin": "introduced", "semantic_type": "systolic_pressure"},
        ])
        violations = validate_class_model(cm, row_ref=2)
        g_violations = [
            v for v in violations
            if v["detail"] in ("attr_name_empty", "semantic_type_malformed", "semantic_type_pos_tag")
        ]
        assert not g_violations, f"Expected no [G] violations for 'systolic_pressure'; got {g_violations}"

    def test_identifier_semantic_type_passes(self):
        """semantic_type='identifier' is shape-valid and not a POS tag → passes [G]."""
        cm = self._cm([
            {"name": "id", "origin": "introduced", "semantic_type": "identifier"},
        ])
        violations = validate_class_model(cm, row_ref=2)
        g_violations = [
            v for v in violations
            if v["detail"] in ("attr_name_empty", "semantic_type_malformed", "semantic_type_pos_tag")
        ]
        assert not g_violations, f"Expected no [G] violations for 'identifier'; got {g_violations}"

    def test_semantic_type_absent_no_g_violation(self):
        """semantic_type absent (null) → no [G] shape/POS violations (field is optional)."""
        cm = self._cm([
            {"name": "quantity", "origin": "introduced", "semantic_type": None},
        ], row_ref=3)
        violations = validate_class_model(cm, row_ref=3)
        g_violations = [
            v for v in violations
            if v["detail"] in ("semantic_type_malformed", "semantic_type_pos_tag")
        ]
        assert not g_violations, f"Expected no [G] shape/POS violations when semantic_type=None; got {g_violations}"


# ---------------------------------------------------------------------------
# Semantic-type registry unit tests
# ---------------------------------------------------------------------------


class TestSemanticTypeRegistry:
    """
    Unit tests for SemanticTypeRegistry (core/semantic_type_registry.py).

    Run individually:
      pytest "tests/requirement_derivation/test_requirement_derivation.py::TestSemanticTypeRegistry::test_first_registration_is_minted" -v
    """

    def test_first_registration_is_minted(self):
        """First time a term is registered → outcome='minted'."""
        reg = SemanticTypeRegistry()
        result = reg.register("monetary_value")
        assert result["outcome"] == "minted"
        assert result["near_duplicates"] == []

    def test_second_registration_is_reused(self):
        """Same term registered twice → second call returns outcome='reused'."""
        reg = SemanticTypeRegistry()
        reg.register("monetary_value")
        result = reg.register("monetary_value")
        assert result["outcome"] == "reused"

    def test_summary_counts_correct(self):
        """Summary minted/reused counts match registration history."""
        reg = SemanticTypeRegistry()
        reg.register("amount")
        reg.register("quantity")
        reg.register("amount")
        reg.register("rate")
        summary = reg.summary()
        assert summary["minted"] == 3
        assert summary["reused"] == 1

    def test_near_duplicate_detected(self):
        """'monetary_value' and 'monetary_values' are near-duplicates (ratio ≥ 0.75)."""
        reg = SemanticTypeRegistry()
        reg.register("monetary_value")
        result = reg.register("monetary_values")
        assert result["near_duplicates"] == ["monetary_value"], (
            f"Expected near-dup 'monetary_value'; got {result['near_duplicates']}"
        )
        summary = reg.summary()
        assert len(summary["near_duplicates"]) == 1
        assert summary["near_duplicates"][0]["check_id"] == "PLB-3d-07"

    def test_distinct_terms_no_near_duplicate(self):
        """'identifier' and 'lifecycle_state' are not near-duplicates."""
        reg = SemanticTypeRegistry()
        reg.register("identifier")
        result = reg.register("lifecycle_state")
        assert result["near_duplicates"] == []

    def test_empty_string_does_not_crash(self):
        """Empty string is handled gracefully."""
        reg = SemanticTypeRegistry()
        result = reg.register("")
        assert result["outcome"] in ("minted", "reused")

    def test_registry_is_independent_per_instance(self):
        """Two SemanticTypeRegistry instances do not share state."""
        reg1 = SemanticTypeRegistry()
        reg2 = SemanticTypeRegistry()
        reg1.register("amount")
        result = reg2.register("amount")
        assert result["outcome"] == "minted"
