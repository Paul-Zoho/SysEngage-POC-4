"""
Provenance accumulator for the Requirement Matching service.

Per Requirement Matching Service Spec v0.2 §3.1 and §5.3.

Replaces the v0.1 service-log tables (requirement_matching_log,
requirement_gap_record).  Assembles ONE AnalysisPass per match_row /
match_set execution; all per-requirement decisions live in
outputs.mechanism_data.match_records so that:
  - a no-match is distinguishable from a missed parent by ledger inspection
    (the rejected candidates_considered are recorded for every no-match).
  - the review path for RequirementMatching provenance is the same as every
    other mechanism — inspect the AnalysisPass, not a side table.

D-rm-4 (v0.2): the audit carrier is a per-execution AnalysisPass, NOT a
per-requirement service-log row.  One pass per match_row / match_set call.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from core.audit_trail import create_analysis_pass_record, persist_analysis_pass
from core.db import get_session

_log = logging.getLogger(__name__)

MECHANISM = "RequirementMatching"
PHASE_ID = "PH001"


class ProvAccumulator:
    """
    Accumulates per-requirement decisions during a single matching execution.
    Call write_pass(session) at the end of match_row / match_set to commit
    the AnalysisPass record alongside the other ledger writes.
    """

    def __init__(
        self,
        *,
        project_id: str,
        practitioner_id: str,
        row_n: int | None,
        parent_row_n: int | None,
    ) -> None:
        self.project_id = project_id
        self.practitioner_id = practitioner_id
        self.row_n = row_n
        self.parent_row_n = parent_row_n
        self.match_records: list[dict[str, Any]] = []
        self.gap_records: list[dict[str, Any]] = []
        self.merge_records: list[dict[str, Any]] = []
        self.ai_model_fingerprints: list[dict[str, Any]] = []
        self._pass_data = create_analysis_pass_record(
            project_id=project_id,
            practitioner_id=practitioner_id,
            phase_id=PHASE_ID,
            pass_type="Per-row",
            mechanism=MECHANISM,
            evaluated_scope=self._make_scope(),
        )

    # ------------------------------------------------------------------
    # Accumulation helpers
    # ------------------------------------------------------------------

    def add_match_record(
        self,
        *,
        requirement_id: str,
        outcome: str,
        confidence: float | None,
        candidates_considered: list[str],
        parent_ids: list[str] | None = None,
        duplicate_of: str | None = None,
        auto_recorded: bool,
        multi_parent_ambiguous: bool = False,
    ) -> None:
        self.match_records.append(
            {
                "requirement_id": requirement_id,
                "outcome": outcome,
                "confidence": confidence,
                "candidates_considered": candidates_considered,
                "parent_ids": parent_ids or [],
                "duplicate_of": duplicate_of,
                "auto_recorded": auto_recorded,
                "multi_parent_ambiguous": multi_parent_ambiguous,
            }
        )

    def add_gap_record(self, gap: dict[str, Any]) -> None:
        self.gap_records.append(gap)

    def add_merge_record(self, merge: dict[str, Any]) -> None:
        self.merge_records.append(merge)

    def add_fingerprints(self, fingerprints: list[dict[str, Any]]) -> None:
        self.ai_model_fingerprints.extend(fingerprints)

    # ------------------------------------------------------------------
    # Pass finalisation
    # ------------------------------------------------------------------

    def _make_scope(self) -> str:
        if self.row_n is not None and self.parent_row_n is not None:
            return f"Row {self.row_n} requirements matched against Row {self.parent_row_n}"
        return "Incremental re-match"

    def _compute_execution_status(self) -> str:
        # Ledger v2.15 enum: "Success" | "PartialSuccess" | "Failed"
        # PartialSuccess when judge failures were flagged or requirements were
        # deferred (execution completed but with partial-failure conditions).
        outcomes = [r["outcome"] for r in self.match_records]
        if not outcomes:
            return "Success"
        has_flagged = any(o == "flagged" for o in outcomes)
        has_deferred = any(o == "deferred" for o in outcomes)
        if has_flagged or has_deferred:
            return "PartialSuccess"
        return "Success"

    def _mean_confidence(self) -> float:
        confs = [r["confidence"] for r in self.match_records if r["confidence"] is not None]
        return round(sum(confs) / len(confs), 4) if confs else 1.0

    def _build_mechanism_data(self) -> dict[str, Any]:
        outcomes = [r["outcome"] for r in self.match_records]
        counts: dict[str, int] = {
            "processed": len(self.match_records),
            "refine_link": outcomes.count("refine"),
            "no_match": outcomes.count("no_match"),
            "no_candidates": outcomes.count("no_candidates"),
            "duplicate_merge": outcomes.count("duplicate"),
            "flagged": outcomes.count("flagged"),
            "deferred": outcomes.count("deferred"),
            "no_parents": outcomes.count("no_parents"),
        }
        return {
            "row_ref": self.row_n,
            "parent_row_ref": self.parent_row_n,
            "ai_model_fingerprints": self.ai_model_fingerprints,
            "counts": counts,
            "match_records": self.match_records,
            "gap_records": self.gap_records,
            "merge_records": self.merge_records,
            "mode_violations": [],
        }

    def write_pass(self, session) -> str:
        """
        Finalise and persist the AnalysisPass in the given session.
        Does NOT commit — caller is responsible.
        Returns the assigned pass_id.
        """
        elapsed = time.monotonic() - self._pass_data.pop("_start_monotonic")
        status = self._compute_execution_status()
        mechanism_data = self._build_mechanism_data()

        self._pass_data["execution_status"] = status
        self._pass_data["mode_active"] = "IM"
        self._pass_data["declared_transformation_modes"] = ["IM", "DM", "LPM"]
        self._pass_data["pass_completed_at"] = datetime.now(timezone.utc)
        self._pass_data["elapsed_ms"] = int(elapsed * 1000)
        self._pass_data["confidence"] = self._mean_confidence()
        self._pass_data["outputs"] = {
            "mechanism_data": mechanism_data,
            "mode_violations": [],
        }

        pass_id = persist_analysis_pass(session, self._pass_data)
        _log.info(
            "RequirementMatching AnalysisPass %s written — %s (row=%s, records=%d)",
            pass_id,
            status,
            self.row_n,
            len(self.match_records),
        )
        return pass_id

    def write_failure_pass(self, *, failure_reason: str) -> str:
        """
        Commit the AnalysisPass failure record in a SEPARATE transaction.
        Call this from an except block when the main transaction has rolled back.
        """
        try:
            self._pass_data.pop("_start_monotonic", None)
        except KeyError:
            pass
        self._pass_data["execution_status"] = "Failed"
        self._pass_data["mode_active"] = "IM"
        self._pass_data["declared_transformation_modes"] = ["IM", "DM", "LPM"]
        self._pass_data["pass_completed_at"] = datetime.now(timezone.utc)
        self._pass_data["elapsed_ms"] = None
        self._pass_data["confidence"] = 0.0
        self._pass_data["outputs"] = {
            "failure_reason": failure_reason,
            "mechanism_data": self._build_mechanism_data(),
            "mode_violations": [],
        }

        session = get_session()
        try:
            pass_id = persist_analysis_pass(session, self._pass_data)
            session.commit()
            _log.info("RequirementMatching failure AnalysisPass %s committed", pass_id)
            return pass_id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
