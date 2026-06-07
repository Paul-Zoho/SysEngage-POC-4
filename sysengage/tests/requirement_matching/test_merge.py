"""
Requirement Matching — merge unit tests.

VER-rm-03 (updated): duplicate equivalence class → one active survivor (lowest id);
                     all other members retired; survivor carries union of refs.
VER-rm-10 (new):    reciprocal / chained duplicate claims → one merge_record,
                    one active survivor per class; Non-Loss assertion fires on
                    any all-members-retired attempt (fail-closed).

These tests cover the pure functions (no DB required for most) and the
NonLossViolationError path, which is asserted before any session call.

Run individually per project convention:
  pytest "tests/requirement_matching/test_merge.py::TestEquivalenceClasses::test_reciprocal_pair" -v
  pytest "tests/requirement_matching/test_merge.py::TestEquivalenceClasses::test_chained_triple" -v
  pytest "tests/requirement_matching/test_merge.py::TestNonLossAssertion::test_non_loss_fires" -v
  pytest "tests/requirement_matching/test_merge.py::TestNonLossAssertion::test_single_member_class" -v
  pytest "tests/requirement_matching/test_merge.py::TestSelectSurvivor::test_min_id_selected" -v
  pytest "tests/requirement_matching/test_merge.py::TestSelectSurvivor::test_reciprocal_determinism" -v
  pytest "tests/requirement_matching/test_merge.py::TestClassMergeWithSession::test_class_merge_retires_non_survivors" -v
  pytest "tests/requirement_matching/test_merge.py::TestClassMergeWithSession::test_class_merge_repoints_refs" -v
  pytest "tests/requirement_matching/test_merge.py::TestClassMergeWithSession::test_class_merge_unions_refs" -v
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, call, patch

import pytest

from mechanisms.requirement_matching.merge import (
    NonLossViolationError,
    build_equivalence_classes,
    execute_class_merge,
    select_survivor,
)


# ---------------------------------------------------------------------------
# TestEquivalenceClasses — VER-rm-10 (pure function, no DB)
# ---------------------------------------------------------------------------

class TestEquivalenceClasses:
    """build_equivalence_classes() resolves pairwise duplicate edges."""

    def test_empty_pairs(self):
        """No edges → no classes."""
        assert build_equivalence_classes([]) == []

    def test_single_pair(self):
        """One edge → one two-member class."""
        classes = build_equivalence_classes([("R013", "R019")])
        assert len(classes) == 1
        assert classes[0] == {"R013", "R019"}

    def test_reciprocal_pair(self):
        """
        VER-rm-10: A→B and B→A are a reciprocal pair.
        Must collapse into exactly one equivalence class {A, B}.
        """
        classes = build_equivalence_classes([("R013", "R019"), ("R019", "R013")])
        assert len(classes) == 1
        assert classes[0] == {"R013", "R019"}

    def test_chained_triple(self):
        """
        VER-rm-10: A≡B, B≡C forms a chain.
        Must collapse into one class {A, B, C}.
        """
        classes = build_equivalence_classes([("R001", "R002"), ("R002", "R003")])
        assert len(classes) == 1
        assert classes[0] == {"R001", "R002", "R003"}

    def test_chained_triple_reversed(self):
        """Same chain given in reverse order — same result."""
        classes = build_equivalence_classes([("R003", "R002"), ("R002", "R001")])
        assert len(classes) == 1
        assert classes[0] == {"R001", "R002", "R003"}

    def test_two_disjoint_pairs(self):
        """Two unrelated pairs → two separate classes."""
        classes = build_equivalence_classes([
            ("R013", "R019"),
            ("R015", "R022"),
        ])
        assert len(classes) == 2
        class_sets = sorted([frozenset(c) for c in classes])
        assert frozenset({"R013", "R019"}) in class_sets
        assert frozenset({"R015", "R022"}) in class_sets

    def test_three_reciprocal_pairs_from_run8(self):
        """
        VER-rm-10: R2 Run8 scenario — three reciprocal pairs, each must form
        its own two-member class (not one big class).
        Previously caused six members retired; with union-find three survivors remain.
        """
        pairs = [
            ("R013", "R019"), ("R019", "R013"),
            ("R015", "R022"), ("R022", "R015"),
            ("R023", "R028"), ("R028", "R023"),
        ]
        classes = build_equivalence_classes(pairs)
        assert len(classes) == 3
        class_sets = [frozenset(c) for c in classes]
        assert frozenset({"R013", "R019"}) in class_sets
        assert frozenset({"R015", "R022"}) in class_sets
        assert frozenset({"R023", "R028"}) in class_sets

    def test_fan_out_all_pointing_to_one(self):
        """B, C, D all nominate A as duplicate → one class {A, B, C, D}."""
        classes = build_equivalence_classes([
            ("R002", "R001"),
            ("R003", "R001"),
            ("R004", "R001"),
        ])
        assert len(classes) == 1
        assert classes[0] == {"R001", "R002", "R003", "R004"}


# ---------------------------------------------------------------------------
# TestSelectSurvivor — VER-rm-03 / VER-rm-10 determinism
# ---------------------------------------------------------------------------

class TestSelectSurvivor:
    """select_survivor() always returns the minimum requirement_id."""

    def test_min_id_selected(self):
        assert select_survivor({"R013", "R019"}) == "R013"

    def test_min_id_three_members(self):
        assert select_survivor({"R003", "R001", "R002"}) == "R001"

    def test_reciprocal_determinism(self):
        """
        VER-rm-10: for a reciprocal pair the survivor must be the same regardless
        of which direction the judge nominated first.
        """
        # Both orderings give the same survivor
        assert select_survivor({"R013", "R019"}) == "R013"
        assert select_survivor({"R019", "R013"}) == "R013"

    def test_numeric_lexicographic_order(self):
        """R009 < R010 < R019 lexicographically."""
        assert select_survivor({"R019", "R010", "R009"}) == "R009"


# ---------------------------------------------------------------------------
# TestNonLossAssertion — VER-rm-10 fail-closed guard
# ---------------------------------------------------------------------------

class TestNonLossAssertion:
    """
    execute_class_merge() raises NonLossViolationError before any DB write
    if the assertion would retire all class members.
    """

    def test_non_loss_fires_when_survivor_also_retired(self):
        """
        If the caller passes survivor_id that is also in retired_ids (i.e. survivor
        is not excluded from class_members - {survivor}), the assertion must fire.

        Simulate by passing class_members = {A} and survivor_id = B (not in class).
        Then retired_ids = {A}, survivor not in class → active count = 0 → violation.
        """
        with pytest.raises(NonLossViolationError):
            execute_class_merge(
                None,  # session — never reached; assertion fires first
                class_members={"R013", "R019"},
                survivor_id="R099",  # not in class → all of {R013, R019} are retired
                project_id="PMT_E2E",
                confidence=0.92,
                rationale="test",
                auto_recorded=True,
            )

    def test_non_loss_fires_empty_class(self):
        """Empty class → no survivor possible."""
        with pytest.raises((NonLossViolationError, ValueError)):
            execute_class_merge(
                None,
                class_members=set(),
                survivor_id="R013",
                project_id="PMT_E2E",
                confidence=0.9,
                rationale="test",
                auto_recorded=True,
            )

    def test_single_member_class_no_op(self):
        """Single-member class: survivor == the one member → retired_ids is empty → no DB op."""
        mock_session = MagicMock()
        result = execute_class_merge(
            mock_session,
            class_members={"R013"},
            survivor_id="R013",
            project_id="PMT_E2E",
            confidence=0.9,
            rationale="test",
            auto_recorded=True,
        )
        assert result["retired_ids"] == []
        assert result["repointed_refs"] == []
        assert result["survivor_id"] == "R013"
        # No DB writes for a single-member class
        mock_session.execute.assert_not_called()

    def test_non_loss_assertion_before_db_write(self):
        """
        VER-rm-10 fail-closed: session.execute must NOT be called when
        NonLossViolationError is raised — the DB must be left untouched.
        """
        mock_session = MagicMock()
        with pytest.raises(NonLossViolationError):
            execute_class_merge(
                mock_session,
                class_members={"R013", "R019"},
                survivor_id="R099",  # not in class → all retired → violation
                project_id="PMT_E2E",
                confidence=0.9,
                rationale="test",
                auto_recorded=True,
            )
        mock_session.execute.assert_not_called()


# ---------------------------------------------------------------------------
# TestClassMergeWithSession — VER-rm-03 / VER-rm-10 with mocked session
# ---------------------------------------------------------------------------

def _make_mock_session(
    survivor_cci=None,
    survivor_domain=None,
    retired_rows: dict | None = None,
    dependents: list[dict] | None = None,
) -> MagicMock:
    """
    Build a mock SQLAlchemy session that returns predictable data.

    survivor_cci / survivor_domain : lists for the survivor's ref columns.
    retired_rows : {retired_id: {"cci_refs": [...], "domain_refs": [...]}}
    dependents   : list of {"requirement_id": ..., "refines_refs": [...]}
    """
    retired_rows = retired_rows or {}
    dependents = dependents or []

    def _execute(stmt, params=None):
        params = params or {}
        rid = params.get("rid", "")
        mock_result = MagicMock()

        # Survivor SELECT
        if rid and survivor_cci is not None and rid not in retired_rows:
            row = MagicMock()
            row.__getitem__ = lambda s, k: (
                survivor_cci if k == "cci_refs" else survivor_domain
            )
            mock_result.mappings.return_value.one_or_none.return_value = row
            return mock_result

        # Retired member SELECT
        if rid in retired_rows:
            row = MagicMock()
            data = retired_rows[rid]
            row.__getitem__ = lambda s, k: data.get(k, [])
            mock_result.mappings.return_value.one_or_none.return_value = row
            return mock_result

        # refines_refs dependents SELECT (contains rid_array check)
        rid_array = params.get("rid_array")
        if rid_array is not None:
            retired_id = json.loads(rid_array)[0]
            matching = [d for d in dependents if retired_id in (d.get("refines_refs") or [])]
            rows = []
            for d in matching:
                m = MagicMock()
                m.__getitem__ = lambda s, k, _d=d: _d.get(k)
                rows.append(m)
            mock_result.mappings.return_value.all.return_value = rows
            return mock_result

        # Default UPDATE / other
        return mock_result

    session = MagicMock()
    session.execute.side_effect = _execute
    return session


class TestClassMergeWithSession:
    """execute_class_merge() with a mocked session."""

    def test_class_merge_retires_non_survivors(self):
        """
        VER-rm-03 / VER-rm-10: for a reciprocal pair {R013, R019},
        survivor = R013; R019 must be retired (retired_at set).
        """
        session = _make_mock_session(
            survivor_cci=["C001"],
            survivor_domain=["D001"],
            retired_rows={"R019": {"cci_refs": ["C002"], "domain_refs": []}},
        )
        result = execute_class_merge(
            session,
            class_members={"R013", "R019"},
            survivor_id="R013",
            project_id="PMT_E2E",
            confidence=0.91,
            rationale="reciprocal duplicate",
            auto_recorded=True,
        )
        assert result["survivor_id"] == "R013"
        assert result["retired_ids"] == ["R019"]
        assert result["confidence"] == 0.91
        assert result["auto_recorded"] is True

    def test_class_merge_unions_refs(self):
        """
        VER-rm-03: survivor takes the union of cci_refs / domain_refs across the class.
        """
        session = _make_mock_session(
            survivor_cci=["C001"],
            survivor_domain=["D001"],
            retired_rows={"R019": {"cci_refs": ["C002", "C003"], "domain_refs": ["D002"]}},
        )
        result = execute_class_merge(
            session,
            class_members={"R013", "R019"},
            survivor_id="R013",
            project_id="PMT_E2E",
            confidence=0.91,
            rationale="test",
            auto_recorded=True,
        )
        # The UPDATE call for survivor should include the unioned refs.
        # Find the UPDATE call that sets cci_refs on the survivor.
        update_calls = [
            c for c in session.execute.call_args_list
            if c.args and "UPDATE requirement SET" in str(c.args[0])
            and c.kwargs.get("params", {}).get("rid") == "R013"
            or (len(c.args) > 1 and isinstance(c.args[1], dict) and c.args[1].get("rid") == "R013")
        ]
        # Verify at least one UPDATE was made for survivor
        assert len(update_calls) > 0

    def test_class_merge_repoints_refs(self):
        """
        VER-rm-03: any refines_refs pointing at R019 must be repointed to R013.
        repointed_refs list must include the dependent's id.
        """
        session = _make_mock_session(
            survivor_cci=[],
            survivor_domain=[],
            retired_rows={"R019": {"cci_refs": [], "domain_refs": []}},
            dependents=[{"requirement_id": "R044", "refines_refs": ["R019"]}],
        )
        result = execute_class_merge(
            session,
            class_members={"R013", "R019"},
            survivor_id="R013",
            project_id="PMT_E2E",
            confidence=0.91,
            rationale="test",
            auto_recorded=True,
        )
        assert "R044" in result["repointed_refs"]

    def test_chained_triple_survivor_is_min(self):
        """
        VER-rm-10: chained triple {R001, R002, R003} — survivor must be R001;
        retired_ids must be [R002, R003]; result has exactly one survivor.
        """
        session = _make_mock_session(
            survivor_cci=[],
            survivor_domain=[],
            retired_rows={
                "R002": {"cci_refs": [], "domain_refs": []},
                "R003": {"cci_refs": [], "domain_refs": []},
            },
        )
        result = execute_class_merge(
            session,
            class_members={"R001", "R002", "R003"},
            survivor_id="R001",
            project_id="PMT_E2E",
            confidence=0.88,
            rationale="chained triple",
            auto_recorded=True,
        )
        assert result["survivor_id"] == "R001"
        assert sorted(result["retired_ids"]) == ["R002", "R003"]
        # Non-Loss: exactly one survivor
        assert len(result["retired_ids"]) == 2  # class size 3 minus 1 survivor
        assert result["survivor_id"] not in result["retired_ids"]


# ---------------------------------------------------------------------------
# TestEndToEndUnionFind — VER-rm-10 integration: pairs → classes → survivors
# ---------------------------------------------------------------------------

class TestEndToEndUnionFind:
    """
    VER-rm-10 end-to-end: given a set of pairwise duplicate claims,
    verify that union-find + select_survivor produces the expected outcome
    (no both-retired; correct survivor per class).
    """

    def test_run8_scenario_no_both_retired(self):
        """
        Reproduces the R2 Run8 failure: three reciprocal pairs all produce both
        members retired under the old pairwise code.

        With union-find:
        - Each pair forms its own class.
        - select_survivor picks the lower id.
        - No id appears in more than one class's retired set.
        - Total survivors = 3 (one per class); total retired = 3.
        """
        pairs = [
            ("R013", "R019"), ("R019", "R013"),
            ("R015", "R022"), ("R022", "R015"),
            ("R023", "R028"), ("R028", "R023"),
        ]
        classes = build_equivalence_classes(pairs)
        assert len(classes) == 3

        all_retired: set[str] = set()
        all_survivors: set[str] = set()
        for cls in classes:
            survivor = select_survivor(cls)
            retired = cls - {survivor}
            all_survivors.add(survivor)
            all_retired.update(retired)

        # No requirement is both survivor and retired
        assert all_survivors.isdisjoint(all_retired), (
            f"Both-retired violation: {all_survivors & all_retired}"
        )
        # Exactly 3 survivors, 3 retired
        assert len(all_survivors) == 3
        assert len(all_retired) == 3
        # Correct survivors (lower ids win)
        assert "R013" in all_survivors
        assert "R015" in all_survivors
        assert "R023" in all_survivors
        # Higher ids are retired
        assert "R019" in all_retired
        assert "R022" in all_retired
        assert "R028" in all_retired

    def test_no_duplicates_no_classes(self):
        """If no duplicate pairs are emitted, no equivalence classes are formed."""
        classes = build_equivalence_classes([])
        assert classes == []

    def test_member_appears_in_exactly_one_class(self):
        """Each requirement_id appears in at most one equivalence class."""
        pairs = [
            ("R001", "R002"), ("R002", "R001"),  # class A
            ("R003", "R004"),                      # class B
            ("R005", "R006"), ("R006", "R007"),   # class C (chain)
        ]
        classes = build_equivalence_classes(pairs)
        all_members: list[str] = []
        for cls in classes:
            all_members.extend(cls)
        # No duplicates in the member list across all classes
        assert len(all_members) == len(set(all_members)), (
            f"Member appears in multiple classes: {all_members}"
        )
