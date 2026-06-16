"""
VER-3d-24: CHK-3d-09 detector precision (F104 v0.27).

Pure unit tests for core/slots.py check_atomicity(). No DB, no AI stub.
Run individually or as the full class — no external dependencies.

Usage:
    pytest sysengage/tests/requirement_derivation/test_slots.py -v
    pytest "sysengage/tests/requirement_derivation/test_slots.py::TestDetectorPrecision::test_genuine_conjoined_predicate_still_hard" -v
"""

import pytest

from sysengage.core.slots import AtomicityViolation, check_atomicity


class TestDetectorPrecision:
    """
    VER-3d-24: the four non-separable forms introduced by F104 (v0.27) do NOT
    hard-flag; a genuine conjoined predicate still does.
    """

    # ------------------------------------------------------------------
    # P1 — conjunction only, never disjunction
    # ------------------------------------------------------------------

    def test_p1_or_in_predicate_no_hard_flag(self):
        """P1: 'or' in predicate is a single-obligation choice/hedge — no hard violation."""
        stmt = "The system shall expose the resource via a REST endpoint or an equivalent protocol."
        viols = check_atomicity(stmt, "Functional")
        hard = [v for v in viols if v.is_hard]
        assert hard == [], (
            f"Expected no hard violations for OR-in-predicate, got: {hard}"
        )

    def test_p1_or_in_predicate_no_conjunct_split(self):
        """P1: OR in predicate is preserved whole — no split occurs (no conjoined_predicate or compound_object hard)."""
        stmt = "The system shall process a batch request or a real-time event."
        viols = check_atomicity(stmt, "Functional")
        hard_rules = {v.rule for v in viols if v.is_hard}
        assert "conjoined_predicate" not in hard_rules, (
            f"OR in predicate must not trigger conjoined_predicate. Got rules: {hard_rules}"
        )
        assert "compound_object" not in hard_rules, (
            f"OR in predicate must not trigger compound_object hard. Got rules: {hard_rules}"
        )

    def test_p1_condition_or_still_flags_compound_condition(self):
        """P1 slot-sensitivity: 'or' joining two condition openers still fires compound_condition (unchanged)."""
        stmt = (
            "When the request is authenticated or when the fallback token is active, "
            "the system shall log the access event."
        )
        viols = check_atomicity(stmt, "Functional")
        hard_rules = [v.rule for v in viols if v.is_hard]
        assert "compound_condition" in hard_rules, (
            f"Expected compound_condition hard for OR-joining-conditions. Got: {viols}"
        )

    # ------------------------------------------------------------------
    # P2 — main-predicate scope (conjunction inside relative clause)
    # ------------------------------------------------------------------

    def test_p2_conjunction_inside_relative_clause_no_hard_flag(self):
        """P2: 'and' inside a relative clause is not a conjoined obligation."""
        stmt = (
            "The system shall implement a service that evaluates eligibility "
            "and transitions the workflow state."
        )
        viols = check_atomicity(stmt, "Functional")
        hard = [v for v in viols if v.is_hard]
        assert hard == [], (
            f"Expected no hard violations for AND inside relative clause, got: {hard}"
        )

    def test_p2_relative_clause_and_which_variant_no_hard_flag(self):
        """P2 / retained carve-out: 'and which' continuation is not a conjoined predicate."""
        stmt = (
            "The system shall produce a consolidated report and which is formatted "
            "according to the standard template."
        )
        viols = check_atomicity(stmt, "Functional")
        hard_rules = {v.rule for v in viols if v.is_hard}
        assert "conjoined_predicate" not in hard_rules, (
            f"'and which' must not trigger conjoined_predicate. Got rules: {hard_rules}"
        )

    # ------------------------------------------------------------------
    # P3 — operation/privilege lists under one governing verb
    # ------------------------------------------------------------------

    def test_p3_operation_list_revoke_no_hard_flag(self):
        """P3: privilege list under 'revoke' is a soft PLB-3d-01 advisory, not a hard reject."""
        stmt = "The system shall revoke UPDATE and DELETE permissions on the archive schema."
        viols = check_atomicity(stmt, "Functional")
        hard = [v for v in viols if v.is_hard]
        assert hard == [], (
            f"Expected no hard violations for operation list under revoke, got: {hard}"
        )
        soft = [v for v in viols if not v.is_hard]
        assert any(v.rule == "compound_object" for v in soft), (
            f"Expected soft compound_object (PLB-3d-01 advisory), got soft viols: {soft}"
        )

    def test_p3_operation_list_grant_no_hard_flag(self):
        """P3: privilege list under 'grant' is soft PLB-3d-01, not a hard reject."""
        stmt = "The system shall grant SELECT and INSERT privileges to the reporting role."
        viols = check_atomicity(stmt, "Functional")
        hard = [v for v in viols if v.is_hard]
        assert hard == [], (
            f"Expected no hard violations for operation list under grant, got: {hard}"
        )

    def test_p3_member_list_include_no_hard_flag(self):
        """P3 / F103: member-list verb 'include' with conjunction is soft PLB-3d-01."""
        stmt = "The system shall include the transaction reference and the timestamp in the audit log."
        viols = check_atomicity(stmt, "Functional")
        hard = [v for v in viols if v.is_hard]
        assert hard == [], (
            f"Expected no hard violations for member list under include, got: {hard}"
        )

    # ------------------------------------------------------------------
    # P4 — temporal/sequencing subordinators
    # ------------------------------------------------------------------

    def test_p4_and_then_no_hard_flag(self):
        """P4: 'and then' between clauses is a temporal sequence, not a conjoined obligation."""
        stmt = "The system shall capture the transaction record and then process the payment."
        viols = check_atomicity(stmt, "Functional")
        hard = [v for v in viols if v.is_hard]
        assert hard == [], (
            f"Expected no hard violations for 'and then' temporal sequence, got: {hard}"
        )

    def test_p4_and_before_no_hard_flag(self):
        """P4: 'and before' is a temporal qualifier, not a second independent obligation."""
        stmt = "The system shall validate the input and before storing it, apply the sanitisation rules."
        viols = check_atomicity(stmt, "Functional")
        hard = [v for v in viols if v.is_hard]
        assert hard == [], (
            f"Expected no hard violations for 'and before' temporal qualifier, got: {hard}"
        )

    def test_p4_and_prior_to_no_hard_flag(self):
        """P4: 'and prior to' is a temporal qualifier, not a conjoined obligation."""
        stmt = "The system shall insert the new transaction rows and prior to committing, verify the checksum."
        viols = check_atomicity(stmt, "Functional")
        hard = [v for v in viols if v.is_hard]
        assert hard == [], (
            f"Expected no hard violations for 'and prior to' temporal qualifier, got: {hard}"
        )

    # ------------------------------------------------------------------
    # Control — genuine conjoined predicate still hard-flags
    # ------------------------------------------------------------------

    def test_genuine_conjoined_predicate_still_hard(self):
        """Control: two parallel independent obligations under one 'shall' still fires conjoined_predicate hard."""
        stmt = "The system shall enforce access controls and delete all expired session records."
        viols = check_atomicity(stmt, "Functional")
        hard_rules = [v.rule for v in viols if v.is_hard]
        assert "conjoined_predicate" in hard_rules, (
            f"Expected conjoined_predicate hard for genuine dual-obligation. Got violations: {viols}"
        )

    def test_genuine_conjoined_predicate_constraint_still_hard(self):
        """Control (Constraint): two distinct constraint rules under one 'shall' still fires conjoined_predicate hard."""
        stmt = "The system shall restrict write access and audit all read operations on the compliance table."
        viols = check_atomicity(stmt, "Constraint")
        hard_rules = [v.rule for v in viols if v.is_hard]
        assert "conjoined_predicate" in hard_rules, (
            f"Expected conjoined_predicate hard for Constraint dual-rule. Got violations: {viols}"
        )
