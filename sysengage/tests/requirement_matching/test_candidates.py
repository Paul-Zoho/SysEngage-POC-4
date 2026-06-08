"""
Unit tests for mechanisms/requirement_matching/candidates.py

Tests verify that get_candidates():
  - uses canonical_ids from data_dictionary_entry.provenance_ref (not object_term)
  - correctly defers DD-flagged children (not_yet_matchable=True)
  - falls back to full pool when DD has no binding for child
  - applies coverage-gap fallback when anchor filter yields no hits
  - filters pool by entity anchor intersection (canonical + related ids)
  - handles pool members with no DD binding (excluded from filter, present in fallback)
  - D-rm-5 (VER-rm-11): filters siblings to child's own subject class
  - D-rm-5 v0.5 ext: structural_entity class correctly detected ("Each X shall…")
  - D-rm-7 (VER-rm-13): filters siblings to child's own requirement_type;
    Functional / Structural / Constraint siblings are never duplicate-eligible
    against a child of a different type

All tests use unittest.mock.patch to avoid real DB calls.
Per project convention: run tests individually, not as a full suite.

Individual test run examples:
  pytest "tests/requirement_matching/test_candidates.py::TestDDFlaggedDeferred::test_flagged_child_not_yet_matchable" -v
  pytest "tests/requirement_matching/test_candidates.py::TestEntityAnchorFilter::test_pool_members_with_matching_canonical_id" -v
  pytest "tests/requirement_matching/test_candidates.py::TestRequirementTypeFilter::test_cross_type_sibling_excluded" -v
  pytest "tests/requirement_matching/test_candidates.py::TestStructuralEntitySubjectClass::test_each_entity_classified_structural" -v
"""

from __future__ import annotations

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Ensure sysengage/ is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _req(
    req_id: str,
    row: int = 2,
    statement: str = "stmt",
    requirement_type: str = "Functional",
) -> dict:
    return {
        "requirement_id": req_id,
        "row_target": str(row),
        "statement": statement,
        "requirement_type": requirement_type,
    }


# Pool for most tests: 2 row-1 requirements + 2 row-2 siblings
POOL = [
    _req("R001", row=1),
    _req("R002", row=1),
    _req("R011", row=2),
    _req("R012", row=2),
]

CHILD = _req("R021", row=3)


# ---------------------------------------------------------------------------
# TestNoDDBinding — child has no DD entries and resolution log is empty
# ---------------------------------------------------------------------------

class TestNoDDBinding(unittest.TestCase):
    """
    When get_canonical_ids_by_provenance_refs returns [] for child AND
    has_flagged_dd_resolution returns False, the pre-filter has nothing to
    anchor against — fall back to full pool for parent row and sibling row.
    """

    def _run(self, child, pool):
        # All requirements return empty canonical_id lists
        empty_map = {r["requirement_id"]: [] for r in pool}
        empty_map[child["requirement_id"]] = []
        with patch(
            "mechanisms.requirement_matching.candidates._get_canonical_ids_batch",
            return_value=empty_map,
        ), patch(
            "mechanisms.requirement_matching.candidates._is_dd_flagged",
            return_value=False,
        ):
            from mechanisms.requirement_matching.candidates import get_candidates
            return get_candidates(child=child, pool=pool)

    def test_full_pool_fallback_for_parents_and_siblings(self):
        pool = [
            _req("P001", row=1),
            _req("P002", row=1),
            _req("S001", row=2),
            _req("S002", row=2),
        ]
        child = _req("C001", row=2)
        parents, siblings, not_yet = self._run(child, pool)

        self.assertFalse(not_yet)
        self.assertEqual(
            {r["requirement_id"] for r in parents}, {"P001", "P002"},
            "All row-1 requirements returned as parents in fallback",
        )
        self.assertEqual(
            {r["requirement_id"] for r in siblings}, {"S001", "S002"},
            "All row-2 siblings returned in fallback",
        )

    def test_child_excluded_from_sibling_list(self):
        pool = [_req("S001", row=2), _req("S002", row=2)]
        child = _req("C001", row=2)
        _, siblings, _ = self._run(child, pool)
        sibling_ids = {r["requirement_id"] for r in siblings}
        self.assertNotIn("C001", sibling_ids)

    def test_row1_child_has_no_parents(self):
        """Row-1 child has no parent row."""
        pool = [_req("S001", row=1), _req("S002", row=1)]
        child = _req("C001", row=1)
        parents, siblings, not_yet = self._run(child, pool)
        self.assertFalse(not_yet)
        self.assertEqual(parents, [])
        self.assertEqual({r["requirement_id"] for r in siblings}, {"S001", "S002"})


# ---------------------------------------------------------------------------
# TestDDFlaggedDeferred — child has been explicitly flagged by DD
# ---------------------------------------------------------------------------

class TestDDFlaggedDeferred(unittest.TestCase):
    """
    When the child has no canonical_ids AND has_flagged_dd_resolution returns True,
    the child is not-yet-matchable → ([], [], True).
    """

    def _run(self, child, pool):
        empty_map = {r["requirement_id"]: [] for r in pool}
        empty_map[child["requirement_id"]] = []
        with patch(
            "mechanisms.requirement_matching.candidates._get_canonical_ids_batch",
            return_value=empty_map,
        ), patch(
            "mechanisms.requirement_matching.candidates._is_dd_flagged",
            return_value=True,
        ):
            from mechanisms.requirement_matching.candidates import get_candidates
            return get_candidates(child=child, pool=pool)

    def test_flagged_child_not_yet_matchable(self):
        pool = [_req("P001", row=1), _req("S001", row=2)]
        child = _req("C001", row=2)
        parents, siblings, not_yet = self._run(child, pool)
        self.assertTrue(not_yet)
        self.assertEqual(parents, [])
        self.assertEqual(siblings, [])

    def test_flagged_child_row1_also_deferred(self):
        child = _req("C001", row=1)
        parents, siblings, not_yet = self._run(child, [_req("S001", row=1)])
        self.assertTrue(not_yet)
        self.assertEqual(parents, [])
        self.assertEqual(siblings, [])

    def test_flagged_check_not_called_when_canonical_ids_present(self):
        """If child has canonical_ids, _is_dd_flagged must never be called."""
        child = _req("C001", row=2)
        pool = [_req("P001", row=1)]
        canonical_map = {
            "C001": ["DD001"],
            "P001": ["DD001"],
        }
        mock_flagged = MagicMock(return_value=True)
        with patch(
            "mechanisms.requirement_matching.candidates._get_canonical_ids_batch",
            return_value=canonical_map,
        ), patch(
            "mechanisms.requirement_matching.candidates._relationships_of",
            return_value=[],
        ), patch(
            "mechanisms.requirement_matching.candidates._is_dd_flagged",
            mock_flagged,
        ):
            from mechanisms.requirement_matching.candidates import get_candidates
            get_candidates(child=child, pool=pool)
        mock_flagged.assert_not_called()


# ---------------------------------------------------------------------------
# TestEntityAnchorFilter — child has canonical_ids; pool filtered by intersection
# ---------------------------------------------------------------------------

class TestEntityAnchorFilter(unittest.TestCase):
    """
    When child has canonical_ids, only pool members whose canonical_ids
    intersect the anchor set are returned as candidates.
    """

    def _run(self, child, pool, canonical_map, related_ids=None):
        """
        related_ids: dict[canonical_id → [related_id, ...]] (default: no relationships)
        """
        def fake_relationships_of(cid):
            return (related_ids or {}).get(cid, [])

        with patch(
            "mechanisms.requirement_matching.candidates._get_canonical_ids_batch",
            return_value=canonical_map,
        ), patch(
            "mechanisms.requirement_matching.candidates._relationships_of",
            side_effect=fake_relationships_of,
        ):
            from mechanisms.requirement_matching.candidates import get_candidates
            return get_candidates(child=child, pool=pool)

    def test_pool_members_with_matching_canonical_id(self):
        child = _req("C001", row=2)
        pool = [
            _req("P001", row=1),
            _req("P002", row=1),
            _req("S001", row=2),
            _req("S002", row=2),
        ]
        canonical_map = {
            "C001": ["DD001"],
            "P001": ["DD001"],   # matches
            "P002": ["DD002"],   # different entity — should NOT match
            "S001": ["DD001"],   # matches
            "S002": [],          # no DD binding — excluded from filter
        }
        parents, siblings, not_yet = self._run(child, pool, canonical_map)

        self.assertFalse(not_yet)
        self.assertEqual({r["requirement_id"] for r in parents}, {"P001"})
        self.assertEqual({r["requirement_id"] for r in siblings}, {"S001"})

    def test_child_excluded_from_own_candidates(self):
        child = _req("C001", row=2)
        pool = [_req("C001", row=2), _req("P001", row=1)]
        canonical_map = {"C001": ["DD001"], "P001": ["DD001"]}
        parents, siblings, _ = self._run(child, pool, canonical_map)
        sibling_ids = {r["requirement_id"] for r in siblings}
        self.assertNotIn("C001", sibling_ids)
        self.assertIn("P001", {r["requirement_id"] for r in parents})

    def test_related_entity_included_via_dd_relationship(self):
        """A pool member whose canonical_id is related to child's canonical_id is included."""
        child = _req("C001", row=2)
        pool = [_req("P001", row=1)]
        canonical_map = {
            "C001": ["DD001"],
            "P001": ["DD002"],   # different canonical, but DD001 → DD002 relationship
        }
        # DD001 relates to DD002
        related_ids = {"DD001": ["DD002"]}
        parents, siblings, not_yet = self._run(child, pool, canonical_map, related_ids)
        self.assertFalse(not_yet)
        self.assertIn("P001", {r["requirement_id"] for r in parents})

    def test_multi_canonical_child_anchor_union(self):
        """Child with multiple canonical_ids — anchor = union of all."""
        child = _req("C001", row=2)
        pool = [_req("P001", row=1), _req("P002", row=1)]
        canonical_map = {
            "C001": ["DD001", "DD003"],
            "P001": ["DD001"],    # matches via DD001
            "P002": ["DD003"],    # matches via DD003
        }
        parents, siblings, _ = self._run(child, pool, canonical_map)
        self.assertEqual(
            {r["requirement_id"] for r in parents}, {"P001", "P002"}
        )

    def test_pool_member_no_dd_binding_excluded_no_fallback(self):
        """
        Pool member with [] canonical_ids is skipped in entity filter.
        Because the *child* is DD-bound, no fallback fires — the pool member
        simply doesn't participate in entity-anchored matching.
        """
        child = _req("C001", row=2)
        pool = [_req("P001", row=1)]
        canonical_map = {"C001": ["DD001"], "P001": []}
        parents, siblings, not_yet = self._run(child, pool, canonical_map)
        # Child is DD-bound → no coverage-gap fallback; P001 has no binding → excluded
        self.assertFalse(not_yet)
        self.assertEqual(parents, [], "P001 excluded from entity filter; child is DD-bound so no fallback")


# ---------------------------------------------------------------------------
# TestEntityAnchorNoFallback — DD-bound child with no pool match → empty sets
# ---------------------------------------------------------------------------

class TestEntityAnchorNoFallback(unittest.TestCase):
    """
    When child has canonical_ids but no pool members share the entity anchor,
    get_candidates must return empty candidate lists and not_yet_matchable=False.

    The full-pool fallback is intentionally NOT applied here: the child is
    DD-bound, so an empty candidate set is the correct signal (no match). Applying
    a fallback would silently defeat the entity-anchored tractability guarantee
    (Matching Spec §4.1 / D-rm-1).
    """

    def _run(self, child, pool, canonical_map):
        with patch(
            "mechanisms.requirement_matching.candidates._get_canonical_ids_batch",
            return_value=canonical_map,
        ), patch(
            "mechanisms.requirement_matching.candidates._relationships_of",
            return_value=[],
        ):
            from mechanisms.requirement_matching.candidates import get_candidates
            return get_candidates(child=child, pool=pool)

    def test_no_matching_parents_returns_empty(self):
        """DD-bound child with no entity-matching parents → empty parents, not full row."""
        child = _req("C001", row=2)
        pool = [_req("P001", row=1), _req("P002", row=1)]
        canonical_map = {
            "C001": ["DD001"],
            "P001": ["DD999"],   # different entity — no match
            "P002": ["DD999"],
        }
        parents, siblings, not_yet = self._run(child, pool, canonical_map)
        self.assertFalse(not_yet)
        self.assertEqual(parents, [], "Empty parents expected — no coverage-gap fallback")
        self.assertEqual(siblings, [])

    def test_no_matching_siblings_returns_empty(self):
        """DD-bound child with no entity-matching siblings → empty siblings, not full row."""
        child = _req("C001", row=2)
        pool = [_req("S001", row=2), _req("S002", row=2)]
        canonical_map = {
            "C001": ["DD001"],
            "S001": ["DD999"],
            "S002": ["DD999"],
        }
        _, siblings, not_yet = self._run(child, pool, canonical_map)
        self.assertFalse(not_yet)
        self.assertEqual(siblings, [], "Empty siblings expected — no coverage-gap fallback")

    def test_not_yet_matchable_false_when_anchor_present_but_no_hits(self):
        """not_yet_matchable must be False even when candidate sets are empty."""
        child = _req("C001", row=2)
        pool = [_req("P001", row=1)]
        canonical_map = {"C001": ["DD001"], "P001": ["DD999"]}
        parents, siblings, not_yet = self._run(child, pool, canonical_map)
        self.assertFalse(not_yet)

    def test_full_pool_fallback_only_fires_for_zero_dd_binding(self):
        """
        Confirm the full-pool fallback fires for a child with NO dd bindings,
        but NOT for a child that has bindings with no pool overlap.
        """
        pool = [_req("P001", row=1), _req("S001", row=2)]
        child = _req("C001", row=2)

        # Child with zero bindings → fallback expected
        empty_map = {"C001": [], "P001": [], "S001": []}
        with patch(
            "mechanisms.requirement_matching.candidates._get_canonical_ids_batch",
            return_value=empty_map,
        ), patch(
            "mechanisms.requirement_matching.candidates._is_dd_flagged",
            return_value=False,
        ):
            from mechanisms.requirement_matching.candidates import get_candidates
            parents, siblings, not_yet = get_candidates(child=child, pool=pool)
        self.assertFalse(not_yet)
        self.assertIn("P001", {r["requirement_id"] for r in parents})

        # Same child with a binding but no pool overlap → no fallback
        bound_map = {"C001": ["DD001"], "P001": ["DD999"], "S001": ["DD999"]}
        with patch(
            "mechanisms.requirement_matching.candidates._get_canonical_ids_batch",
            return_value=bound_map,
        ), patch(
            "mechanisms.requirement_matching.candidates._relationships_of",
            return_value=[],
        ):
            parents2, siblings2, not_yet2 = get_candidates(child=child, pool=pool)
        self.assertFalse(not_yet2)
        self.assertEqual(parents2, [], "No fallback when child has DD binding but no entity overlap")


# ---------------------------------------------------------------------------
# TestBatchQueryCalled — verify the batch function is called once per get_candidates
# ---------------------------------------------------------------------------

class TestBatchQueryCalled(unittest.TestCase):
    """
    get_candidates must call _get_canonical_ids_batch exactly once,
    with child + all pool member ids, regardless of DD coverage.
    """

    def test_batch_called_once_with_all_ids(self):
        child = _req("C001", row=2)
        pool = [_req("P001", row=1), _req("S001", row=2)]
        all_ids = {"C001", "P001", "S001"}

        captured = {}

        def fake_batch(ids):
            captured["ids"] = set(ids)
            return {i: [] for i in ids}

        with patch(
            "mechanisms.requirement_matching.candidates._get_canonical_ids_batch",
            side_effect=fake_batch,
        ), patch(
            "mechanisms.requirement_matching.candidates._is_dd_flagged",
            return_value=False,
        ):
            from mechanisms.requirement_matching.candidates import get_candidates
            get_candidates(child=child, pool=pool)

        self.assertEqual(captured["ids"], all_ids)

    def test_empty_pool_only_child_id_in_batch(self):
        child = _req("C001", row=2)
        captured = {}

        def fake_batch(ids):
            captured["ids"] = set(ids)
            return {"C001": []}

        with patch(
            "mechanisms.requirement_matching.candidates._get_canonical_ids_batch",
            side_effect=fake_batch,
        ), patch(
            "mechanisms.requirement_matching.candidates._is_dd_flagged",
            return_value=False,
        ):
            from mechanisms.requirement_matching.candidates import get_candidates
            get_candidates(child=child, pool=[])

        self.assertEqual(captured["ids"], {"C001"})


# ---------------------------------------------------------------------------
# TestStructuralEntitySubjectClass — D-rm-5 v0.5 extension (VER-rm-11)
# ---------------------------------------------------------------------------

class TestStructuralEntitySubjectClass(unittest.TestCase):
    """
    _classify_subject must return "structural_entity" for "Each <X> shall…" /
    "Every <X> shall…" forms (v0.5 D-rm-5 extension), keeping them out of the
    "actor" catch-all so they are not mis-bucketed with actor-form statements.
    """

    def _classify(self, statement: str) -> str:
        from mechanisms.requirement_matching.candidates import _classify_subject
        return _classify_subject(statement)

    def test_each_entity_classified_structural(self):
        self.assertEqual(self._classify("Each task shall have a monetary value"), "structural_entity")

    def test_every_entity_classified_structural(self):
        self.assertEqual(self._classify("Every order shall be assigned a unique identifier"), "structural_entity")

    def test_case_insensitive(self):
        self.assertEqual(self._classify("EACH Task shall …"), "structural_entity")

    def test_system_not_reclassified(self):
        """'The system shall…' must still be system, not structural_entity."""
        self.assertEqual(self._classify("The system shall display tasks to the user"), "system")

    def test_actor_form_not_structural(self):
        """'A parent can define tasks' must still be actor."""
        self.assertEqual(self._classify("A parent can define tasks with monetary values"), "actor")

    def test_structural_sibling_excluded_from_actor_bucket(self):
        """
        A child with actor-form subject ("a parent can…") must not receive
        a structural_entity sibling ("Each task shall…") in its candidate set
        even when both share the same DD entity anchor.  (D-rm-5 / VER-rm-11)
        """
        child = _req("C001", row=2, statement="a parent can define tasks with values")
        structural_sibling = _req("S001", row=2, statement="Each task shall have a monetary value")
        pool = [child, structural_sibling]
        canonical_map = {
            "C001": ["DD001"],
            "S001": ["DD001"],
        }
        with patch(
            "mechanisms.requirement_matching.candidates._get_canonical_ids_batch",
            return_value=canonical_map,
        ), patch(
            "mechanisms.requirement_matching.candidates._relationships_of",
            return_value=[],
        ):
            from mechanisms.requirement_matching.candidates import get_candidates
            _, siblings, _ = get_candidates(child=child, pool=pool)
        sibling_ids = {r["requirement_id"] for r in siblings}
        self.assertNotIn(
            "S001", sibling_ids,
            "structural_entity sibling must be excluded from actor-class child's sibling set",
        )


# ---------------------------------------------------------------------------
# TestRequirementTypeFilter — D-rm-7 (VER-rm-13)
# ---------------------------------------------------------------------------

class TestRequirementTypeFilter(unittest.TestCase):
    """
    VER-rm-13: two requirements of different requirement_type (Functional /
    Structural / Constraint) must never appear together in the duplicate
    candidate set, regardless of shared entity or subject class.

    get_candidates() Step 6 (D-rm-7) drops cross-type siblings before they
    reach judge_duplicate.
    """

    def _run(self, child, pool, canonical_map):
        with patch(
            "mechanisms.requirement_matching.candidates._get_canonical_ids_batch",
            return_value=canonical_map,
        ), patch(
            "mechanisms.requirement_matching.candidates._relationships_of",
            return_value=[],
        ):
            from mechanisms.requirement_matching.candidates import get_candidates
            return get_candidates(child=child, pool=pool)

    def test_cross_type_sibling_excluded(self):
        """
        A Functional child must not receive a Structural sibling in its
        duplicate candidate set even when both share the same entity anchor.
        Mirrors the PMT R2 Run13 false merge: R030 (Functional) ↔ R014 (Structural).
        """
        child = _req("R030", row=2,
                     statement="a parent can define tasks with monetary values",
                     requirement_type="Functional")
        structural_sibling = _req("R014", row=2,
                                  statement="Each task shall have a monetary value",
                                  requirement_type="Structural")
        pool = [child, structural_sibling]
        canonical_map = {"R030": ["DD_TASK"], "R014": ["DD_TASK"]}

        _, siblings, _ = self._run(child, pool, canonical_map)
        self.assertNotIn(
            "R014",
            {r["requirement_id"] for r in siblings},
            "Structural sibling R014 must be excluded from Functional child R030's candidate set (D-rm-7)",
        )

    def test_cross_type_functional_constraint_excluded(self):
        """
        A Functional child must not receive a Constraint sibling.
        Mirrors R028 (Functional) ↔ R029 (Constraint) from PMT R2 Run13.
        """
        child = _req("R028", row=2,
                     statement="the system shall maintain a historical record of transactions",
                     requirement_type="Functional")
        constraint_sibling = _req("R029", row=2,
                                  statement="the system shall retain completion records for the required duration",
                                  requirement_type="Constraint")
        pool = [child, constraint_sibling]
        canonical_map = {"R028": ["DD_RECORD"], "R029": ["DD_RECORD"]}

        _, siblings, _ = self._run(child, pool, canonical_map)
        self.assertNotIn(
            "R029",
            {r["requirement_id"] for r in siblings},
            "Constraint sibling R029 must be excluded from Functional child R028's candidate set (D-rm-7)",
        )

    def test_same_type_sibling_retained(self):
        """
        Two Functional requirements sharing an entity anchor must BOTH appear
        in the candidate set — type filter must not over-exclude.
        """
        child = _req("R031", row=2,
                     statement="a parent can add tasks to a list",
                     requirement_type="Functional")
        same_type_sibling = _req("R032", row=2,
                                 statement="a parent can create new tasks in the system",
                                 requirement_type="Functional")
        pool = [child, same_type_sibling]
        canonical_map = {"R031": ["DD_TASK"], "R032": ["DD_TASK"]}

        _, siblings, _ = self._run(child, pool, canonical_map)
        self.assertIn(
            "R032",
            {r["requirement_id"] for r in siblings},
            "Same-type (Functional) sibling must be retained in the candidate set",
        )

    def test_no_requirement_type_field_allows_all(self):
        """
        When the child has no requirement_type (empty string), the type filter
        is skipped — no siblings are dropped on type grounds.
        """
        child = {
            "requirement_id": "C001",
            "row_target": "2",
            "statement": "a parent can view tasks",
            "requirement_type": "",
        }
        sibling = _req("S001", row=2, statement="a parent can see all tasks",
                       requirement_type="Functional")
        pool = [child, sibling]
        canonical_map = {"C001": ["DD_TASK"], "S001": ["DD_TASK"]}

        _, siblings, _ = self._run(child, pool, canonical_map)
        self.assertIn(
            "S001",
            {r["requirement_id"] for r in siblings},
            "Type filter must be skipped when child has no requirement_type",
        )

    def test_all_three_types_each_isolated(self):
        """
        Three same-entity siblings of three different types — each child sees
        only its own type in the sibling candidate set.
        """
        func = _req("F001", row=2, statement="a parent can add tasks", requirement_type="Functional")
        struct = _req("S001", row=2, statement="Each task shall have an id", requirement_type="Structural")
        constr = _req("C001", row=2, statement="the system shall retain tasks for 7 years", requirement_type="Constraint")
        pool = [func, struct, constr]
        canonical_map = {"F001": ["DD_TASK"], "S001": ["DD_TASK"], "C001": ["DD_TASK"]}

        for child, forbidden_pair in [
            (func, {"S001", "C001"}),
            (struct, {"F001", "C001"}),
            (constr, {"F001", "S001"}),
        ]:
            _, siblings, _ = self._run(child, pool, canonical_map)
            sibling_ids = {r["requirement_id"] for r in siblings}
            self.assertFalse(
                sibling_ids & forbidden_pair,
                f"Child {child['requirement_id']} ({child['requirement_type']}) must not see "
                f"cross-type siblings {forbidden_pair}; got {sibling_ids}",
            )


if __name__ == "__main__":
    unittest.main()
