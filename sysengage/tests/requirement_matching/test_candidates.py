"""
Unit tests for mechanisms/requirement_matching/candidates.py

Tests verify that get_candidates():
  - uses canonical_ids from data_dictionary_entry.provenance_ref (not object_term)
  - correctly defers DD-flagged children (not_yet_matchable=True)
  - falls back to full pool when DD has no binding for child
  - applies coverage-gap fallback when anchor filter yields no hits
  - filters pool by entity anchor intersection (canonical + related ids)
  - handles pool members with no DD binding (excluded from filter, present in fallback)

All tests use unittest.mock.patch to avoid real DB calls.
Per project convention: run tests individually, not as a full suite.

Individual test run examples:
  pytest "tests/requirement_matching/test_candidates.py::TestDDFlaggedDeferred::test_flagged_child_not_yet_matchable" -v
  pytest "tests/requirement_matching/test_candidates.py::TestEntityAnchorFilter::test_pool_members_with_matching_canonical_id" -v
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

def _req(req_id: str, row: int = 2, statement: str = "stmt") -> dict:
    return {"requirement_id": req_id, "row_target": str(row), "statement": statement}


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

    def test_pool_member_no_dd_binding_skipped_by_filter(self):
        """Pool member with [] canonical_ids is skipped in entity filter."""
        child = _req("C001", row=2)
        pool = [_req("P001", row=1)]
        canonical_map = {"C001": ["DD001"], "P001": []}
        parents, siblings, _ = self._run(child, pool, canonical_map)
        # P001 has no DD binding → excluded from entity filter → fallback fires
        self.assertIn("P001", {r["requirement_id"] for r in parents})


# ---------------------------------------------------------------------------
# TestCoverageGapFallback — entity filter yields nothing → full-row fallback
# ---------------------------------------------------------------------------

class TestCoverageGapFallback(unittest.TestCase):
    """
    When child has canonical_ids but none of the pool members share the entity
    (coverage gap), the full row is returned rather than an empty candidate set.
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

    def test_no_matching_parents_triggers_full_parent_row(self):
        child = _req("C001", row=2)
        pool = [_req("P001", row=1), _req("P002", row=1)]
        canonical_map = {
            "C001": ["DD001"],
            "P001": ["DD999"],   # different entity
            "P002": ["DD999"],
        }
        parents, siblings, not_yet = self._run(child, pool, canonical_map)
        self.assertFalse(not_yet)
        self.assertEqual(
            {r["requirement_id"] for r in parents}, {"P001", "P002"},
            "Full parent row returned when entity filter finds nothing",
        )

    def test_no_matching_siblings_triggers_full_sibling_row(self):
        child = _req("C001", row=2)
        pool = [_req("S001", row=2), _req("S002", row=2)]
        canonical_map = {
            "C001": ["DD001"],
            "S001": ["DD999"],
            "S002": ["DD999"],
        }
        _, siblings, _ = self._run(child, pool, canonical_map)
        self.assertEqual(
            {r["requirement_id"] for r in siblings}, {"S001", "S002"},
            "Full sibling row returned when entity filter finds nothing",
        )

    def test_fallback_excludes_child_from_siblings(self):
        child = _req("C001", row=2)
        pool = [_req("S001", row=2), _req("S002", row=2)]
        canonical_map = {"C001": ["DD001"], "S001": ["DD999"], "S002": ["DD999"]}
        _, siblings, _ = self._run(child, pool, canonical_map)
        self.assertNotIn("C001", {r["requirement_id"] for r in siblings})


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


if __name__ == "__main__":
    unittest.main()
