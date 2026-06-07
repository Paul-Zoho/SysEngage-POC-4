"""
Stage 3 — Structural Validation (DM, with conditional IM repair).

Per Requirement Derivation Mechanism Spec v0.6 §4.3:
  All checks run in sequence on the accumulated proposal set. Pure in-memory
  operations except the Non-Loss repair prompt (IM conditional sub-act).

  CHK-3d-01  No empty statement.
  CHK-3d-02  No empty cci_refs.
  CHK-3d-03  cci_refs resolve to source Domain's eligible membership (strip out-of-Domain).
  CHK-3d-04  fit_criteria integrity (strip present-but-empty; advisory for Measurement
             without fit_criteria). v2.13: Performance replaced by Measurement (F89).
  CHK-3d-05  Non-Loss: every eligible CCI covered by ≥1 Requirement; repair prompt
             if orphans. Persistent orphan → CompletedWithWarnings + Concern raised.
  CHK-3d-06  Failure if all proposals rejected and repair produced nothing.
  CHK-3d-07  Exact-duplicate collapse (same statement + cci_refs set).
  CHK-3d-08  Row-appropriate statement subject (decidable; soft severity). Tests the
             statement's grammatical subject against the row's permitted subject set
             from REQUIREMENT_ROW_GUIDANCE §5.4(a). v0.9: Row 2 widened to four-class
             taxonomy (actor / system-affordance / business / named-role) — only "the
             enterprise" (Row 1 scope escape) is a mismatch at Row 2; system-subject
             at Row 2 is now legitimate. Mismatch logs subject_vocabulary_mismatch in
             execution_warnings and records the flag in subject_vocabulary_flags.
             Does NOT reject the Requirement or block production.
  CHK-3d-09  Typed-slot atomicity check (decidable, HARD; realises F88).
             Calls core.slots.check_atomicity per proposal. Hard violations reject
             the proposal; its CCIs return to orphan pool and are re-covered via a
             second CHK-3d-05 repair attempt (repair prompt instructs atomic
             single-obligation statements). Soft violations log advisory.
  ADVC-3d-01 Requirement-per-Domain soft bounds advisory.
  ADVC-3d-02 Interrogative slot-completeness advisory (v0.6). Warns when a surviving
             proposal may be missing a type-required slot (Functional: Subject/Action/
             Object; Constraint: Subject/Rule; Structural: Entity/structural-assertion).
             Logs interrogative_completeness_advisory in execution_warnings only.
             Does NOT reject the Requirement.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from core.ai_client import MODEL, get_ai_client
from core.slots import check_atomicity, violation_summary
from mechanisms.requirement_derivation.prompts.requirement_repair_prompt import (
    build_requirement_repair_prompt,
)
from mechanisms.requirement_derivation.schemas.requirement_repair_response_schema import (
    RepairRequirementProposal,
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

_log = logging.getLogger(__name__)


@dataclass
class Stage3Result:
    proposals: list[TaggedProposal] = field(default_factory=list)
    repair_prompt_issued: bool = False
    orphaned_ccis: list[str] = field(default_factory=list)
    validation_failures: list[dict[str, Any]] = field(default_factory=list)
    duplicate_requirements_collapsed: list[dict[str, Any]] = field(default_factory=list)
    subject_vocabulary_flags: list[dict[str, Any]] = field(default_factory=list)
    ai_model_fingerprints: list[dict[str, Any]] = field(default_factory=list)
    execution_warnings: list[dict[str, Any]] = field(default_factory=list)
    concern_entities: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    failure_reason: str | None = None


def _call_repair_ai(prompt: str) -> tuple[Any, dict[str, Any]]:
    client = get_ai_client()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    fingerprint = {
        "stage": "stage3_repair",
        "model": msg.model,
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
    }
    return msg, fingerprint


def _strip_code_fence(text_: str) -> str:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text_, re.DOTALL)
    return m.group(1).strip() if m else text_.strip()


def _parse_repair_response(text_: str) -> list[RepairRequirementProposal] | None:
    try:
        data = json.loads(_strip_code_fence(text_))
        if not isinstance(data, list):
            return None
        return [RepairRequirementProposal.model_validate(item) for item in data]
    except Exception:
        return None


def _run_repair(
    *,
    orphan_ci_ids: set[str],
    cci_by_id: dict[str, EligibleCCI],
    active_domains: list[ActiveDomain],
    row_ref: int,
    result: Stage3Result,
    warning_type: str,
) -> list[TaggedProposal]:
    """
    Run one CHK-3d-05-style repair AI call for the given orphaned CCI set.
    Returns TaggedProposal list (may be empty on AI failure).
    Mutates result.ai_model_fingerprints and result.execution_warnings.
    """
    cci_dicts: list[dict[str, Any]] = []
    for ci_id in sorted(orphan_ci_ids):
        cci = cci_by_id.get(ci_id)
        if cci is None:
            continue
        owning_domain: ActiveDomain | None = next(
            (d for d in active_domains if ci_id in set(d.cell_content_item_refs)),
            active_domains[0] if active_domains else None,
        )
        if owning_domain is None:
            continue
        cci_dicts.append(
            {
                "ci_id": ci_id,
                "column": cci.column,
                "classification_type": cci.classification_type,
                "description": cci.description,
                "owning_domain_id": owning_domain.domain_id,
                "owning_domain_name": owning_domain.name,
            }
        )

    if not cci_dicts:
        return []

    repair_prompt = build_requirement_repair_prompt(
        row_ref=row_ref, orphaned_ccis=cci_dicts
    )
    parsed_repair: list[RepairRequirementProposal] | None = None
    try:
        msg, fp = _call_repair_ai(repair_prompt)
        result.ai_model_fingerprints.append(fp)
        parsed_repair = _parse_repair_response(msg.content[0].text)
    except Exception as exc:
        _log.warning("%s repair AI call failed: %s", warning_type, exc)
        result.execution_warnings.append(
            {"type": f"{warning_type}_repair_failed", "detail": str(exc)}
        )

    if not parsed_repair:
        result.execution_warnings.append({"type": f"{warning_type}_repair_failed"})
        return []

    repair_proposals: list[TaggedProposal] = []
    for rp in parsed_repair:
        owning_did = cci_dicts[0]["owning_domain_id"]
        for cci_dict in cci_dicts:
            if cci_dict["ci_id"] in rp.cci_refs:
                owning_did = cci_dict["owning_domain_id"]
                break
        repair_proposals.append(
            TaggedProposal(
                source_domain_id=owning_did,
                statement=rp.statement,
                requirement_type=rp.requirement_type,
                cci_refs=list(rp.cci_refs),
                rationale=rp.rationale,
                fit_criteria=rp.fit_criteria,
                verification_method=rp.verification_method,
                priority=rp.priority,
                confidence=rp.confidence,
            )
        )
    return repair_proposals


def run_stage3(
    *,
    stage1: Stage1Result,
    stage2: Stage2Result,
    practitioner_id: str,
    project_id: str,
    row_ref: int,
) -> Stage3Result:
    """
    Run Stage 3 structural validation.

    Returns Stage3Result with validated proposals, validation_failures,
    orphaned_ccis, concern_entities, and execution_warnings.
    """
    result = Stage3Result()

    eligible_ci_ids: set[str] = {c.ci_id for c in stage1.eligible_ccis}
    cci_by_id: dict[str, EligibleCCI] = {c.ci_id: c for c in stage1.eligible_ccis}
    domain_by_id: dict[str, ActiveDomain] = {
        d.domain_id: d for d in stage1.active_domains
    }

    proposals: list[TaggedProposal] = list(stage2.proposals)

    # -------------------------------------------------------------------------
    # CHK-3d-01 — No empty statement
    # -------------------------------------------------------------------------
    surviving: list[TaggedProposal] = []
    for p in proposals:
        if not p.statement or not p.statement.strip():
            result.validation_failures.append(
                {
                    "check_id": "CHK-3d-01",
                    "source_domain_id": p.source_domain_id,
                    "detail": "empty statement",
                }
            )
        else:
            surviving.append(p)
    proposals = surviving

    # -------------------------------------------------------------------------
    # CHK-3d-02 — No empty cci_refs
    # -------------------------------------------------------------------------
    surviving = []
    for p in proposals:
        if not p.cci_refs:
            result.validation_failures.append(
                {
                    "check_id": "CHK-3d-02",
                    "source_domain_id": p.source_domain_id,
                    "detail": "empty cci_refs",
                }
            )
        else:
            surviving.append(p)
    proposals = surviving

    # -------------------------------------------------------------------------
    # CHK-3d-03 — cci_refs resolve to source Domain's eligible membership
    # -------------------------------------------------------------------------
    cleaned: list[TaggedProposal] = []
    for p in proposals:
        domain = domain_by_id.get(p.source_domain_id)
        if domain is None:
            result.validation_failures.append(
                {
                    "check_id": "CHK-3d-03",
                    "source_domain_id": p.source_domain_id,
                    "detail": "source_domain_id not found in active domains",
                }
            )
            continue

        domain_member_ids: set[str] = set(domain.cell_content_item_refs)
        valid_refs = [r for r in p.cci_refs if r in domain_member_ids]
        invalid_refs = [r for r in p.cci_refs if r not in domain_member_ids]
        for ref in invalid_refs:
            result.validation_failures.append(
                {
                    "check_id": "CHK-3d-03",
                    "source_domain_id": p.source_domain_id,
                    "detail": f"cci_ref {ref!r} not in source Domain membership — stripped",
                }
            )

        if not valid_refs:
            result.validation_failures.append(
                {
                    "check_id": "CHK-3d-02",
                    "source_domain_id": p.source_domain_id,
                    "detail": "empty cci_refs after stripping out-of-Domain refs (CHK-3d-03)",
                }
            )
        else:
            p.cci_refs = valid_refs
            cleaned.append(p)
    proposals = cleaned

    # -------------------------------------------------------------------------
    # CHK-3d-04 — fit_criteria integrity
    # v2.13: advisory for Measurement (verification_method) without fit_criteria
    # -------------------------------------------------------------------------
    for p in proposals:
        if p.fit_criteria is not None and not p.fit_criteria.strip():
            p.fit_criteria = None
            result.execution_warnings.append(
                {
                    "type": "fit_criteria_empty_stripped",
                    "source_domain_id": p.source_domain_id,
                }
            )
        if p.verification_method == "Measurement" and p.fit_criteria is None:
            result.execution_warnings.append(
                {
                    "type": "measurement_missing_fit_criteria",
                    "source_domain_id": p.source_domain_id,
                    "statement_preview": p.statement[:80],
                }
            )

    # -------------------------------------------------------------------------
    # CHK-3d-05 — Non-Loss: every eligible CCI covered by ≥1 Requirement
    # -------------------------------------------------------------------------
    covered = {ref for p in proposals for ref in p.cci_refs}
    orphaned = eligible_ci_ids - covered

    if orphaned:
        result.repair_prompt_issued = True
        result.execution_warnings.append(
            {"type": "chk3d05_repair_performed", "orphan_count": len(orphaned)}
        )

        repair_proposals = _run_repair(
            orphan_ci_ids=orphaned,
            cci_by_id=cci_by_id,
            active_domains=stage1.active_domains,
            row_ref=row_ref,
            result=result,
            warning_type="chk3d05",
        )
        proposals.extend(repair_proposals)

        # Re-compute orphaned after repair
        covered = {ref for p in proposals for ref in p.cci_refs}
        orphaned = eligible_ci_ids - covered

    if orphaned:
        result.orphaned_ccis = sorted(orphaned)
        result.status = "ok_with_warnings"
        result.concern_entities.append(
            {
                "description": (
                    f"Pass 3d Requirement Derivation: {len(orphaned)} CCI(s) could not be "
                    f"covered by any Requirement after repair attempt. Practitioner review "
                    f"required. Orphaned ci_ids: {sorted(orphaned)}"
                ),
                "source_refs": sorted(orphaned),
                "practitioner_id": practitioner_id,
                "project_id": project_id,
                "produced_in_row": str(row_ref),
            }
        )

    # -------------------------------------------------------------------------
    # CHK-3d-06 — Failure if all proposals rejected
    # -------------------------------------------------------------------------
    if not proposals:
        result.status = "failed"
        result.failure_reason = "No valid Requirement proposals survived validation"
        return result

    # -------------------------------------------------------------------------
    # CHK-3d-07 — Exact-duplicate collapse (same statement + cci_refs set)
    # -------------------------------------------------------------------------
    seen_keys: dict[tuple, int] = {}
    deduped: list[TaggedProposal] = []
    for p in proposals:
        key = (p.statement.lower().strip(), frozenset(p.cci_refs))
        if key in seen_keys:
            result.execution_warnings.append(
                {"type": "duplicate_requirement_collapsed"}
            )
            result.duplicate_requirements_collapsed.append(
                {
                    "kept_statement": deduped[seen_keys[key]].statement,
                    "collapsed_count": 1,
                }
            )
        else:
            seen_keys[key] = len(deduped)
            deduped.append(p)
    proposals = deduped

    # -------------------------------------------------------------------------
    # CHK-3d-08 — Row-appropriate statement subject (decidable; soft severity)
    # Realises Mechanism Spec v0.6 §4.3 / closes F81 detection.
    #
    # For each surviving Requirement, test the grammatical subject of the
    # statement against the row's required subject per REQUIREMENT_ROW_GUIDANCE
    # §5.4(a). Row 1 requires "The enterprise shall…"; a "The system shall…"
    # (or other system/component subject) at Row 1 is a mismatch.
    #
    # Severity: soft — mismatch records a flag in subject_vocabulary_flags
    # and logs subject_vocabulary_mismatch in execution_warnings; it does NOT
    # reject the Requirement or change execution_status.
    # -------------------------------------------------------------------------
    _SYSTEM_SUBJECT_PATTERN = re.compile(
        r"^the\s+(?:system|software|application|component|platform|tool|service|"
        r"database|module|interface|api|app)\b",
        re.IGNORECASE,
    )
    _ENTERPRISE_SUBJECT_PATTERN = re.compile(
        r"^the\s+enterprise\b",
        re.IGNORECASE,
    )

    _ROW1_REQUIRES_ENTERPRISE = "1"
    _ROW2_FOUR_CLASS = "2"

    for idx, p in enumerate(proposals):
        stmt_stripped = p.statement.strip()
        # Determine mismatch per row:
        #   Row 1 — subject must be "the enterprise"; any system/component subject is a mismatch.
        #   Row 2 — four-class taxonomy (actor / system-affordance / business / named-role) are
        #            all legitimate; only "the enterprise" (Row 1 scope escape) is a mismatch.
        #   Rows 3–5 — no decidable subject check at v0.1 (guidance carries the discipline).
        detected_subject: str | None = None
        if str(row_ref) == _ROW1_REQUIRES_ENTERPRISE:
            if _SYSTEM_SUBJECT_PATTERN.match(stmt_stripped):
                words = stmt_stripped.split()
                detected_subject = " ".join(words[:2]) if len(words) >= 2 else stmt_stripped[:30]
        elif str(row_ref) == _ROW2_FOUR_CLASS:
            if _ENTERPRISE_SUBJECT_PATTERN.match(stmt_stripped):
                words = stmt_stripped.split()
                detected_subject = " ".join(words[:2]) if len(words) >= 2 else stmt_stripped[:30]

        if detected_subject is not None:
            placeholder = f"proposal_{idx + 1}:{stmt_stripped[:40].rstrip()}"
            result.subject_vocabulary_flags.append(
                {
                    "requirement_id_placeholder": placeholder,
                    "row": row_ref,
                    "detected_subject": detected_subject,
                }
            )
            result.execution_warnings.append(
                {
                    "type": "subject_vocabulary_mismatch",
                    "row": row_ref,
                    "detected_subject": detected_subject,
                    "statement_preview": stmt_stripped[:80],
                }
            )
            _log.info(
                "CHK-3d-08: Row %s subject mismatch — detected %r in %r",
                row_ref, detected_subject, stmt_stripped[:60],
            )

    # -------------------------------------------------------------------------
    # CHK-3d-09 — Typed-slot atomicity (decidable, HARD; realises F88)
    # -------------------------------------------------------------------------
    pre_09_count = len(proposals)
    surviving_09: list[TaggedProposal] = []
    for p in proposals:
        violations = check_atomicity(p.statement, p.requirement_type)
        hard_viols = [v for v in violations if v.is_hard]
        soft_viols = [v for v in violations if not v.is_hard]
        if hard_viols:
            result.validation_failures.append(
                {
                    "check_id": "CHK-3d-09",
                    "source_domain_id": p.source_domain_id,
                    "violation": violation_summary(hard_viols),
                    "statement_preview": p.statement[:80],
                }
            )
        else:
            for sv in soft_viols:
                result.execution_warnings.append(
                    {
                        "type": "atomicity_possible_exception",
                        "rule": sv.rule,
                        "detail": sv.detail,
                        "statement_preview": p.statement[:80],
                    }
                )
            surviving_09.append(p)
    proposals = surviving_09

    # If CHK-3d-09 rejections created new orphans, attempt one repair
    if len(proposals) < pre_09_count:
        covered_after_09 = {ref for p in proposals for ref in p.cci_refs}
        existing_orphan_ids = set(result.orphaned_ccis)
        new_orphans_09 = eligible_ci_ids - covered_after_09 - existing_orphan_ids
        if new_orphans_09:
            result.execution_warnings.append(
                {
                    "type": "chk3d09_new_orphans",
                    "orphan_count": len(new_orphans_09),
                    "orphan_ids": sorted(new_orphans_09),
                }
            )
            repair_proposals_09 = _run_repair(
                orphan_ci_ids=new_orphans_09,
                cci_by_id=cci_by_id,
                active_domains=stage1.active_domains,
                row_ref=row_ref,
                result=result,
                warning_type="chk3d09",
            )
            # Repair proposals added WITHOUT re-applying CHK-3d-09 (one-level repair)
            proposals.extend(repair_proposals_09)
            covered_after_repair = {ref for p in proposals for ref in p.cci_refs}
            persistent_09_orphans = new_orphans_09 - covered_after_repair
            if persistent_09_orphans:
                result.orphaned_ccis.extend(sorted(persistent_09_orphans))
                if result.status != "failed":
                    result.status = "ok_with_warnings"
                result.concern_entities.append(
                    {
                        "description": (
                            f"Pass 3d CHK-3d-09 atomicity: {len(persistent_09_orphans)} CCI(s) "
                            f"orphaned after atomicity rejection and one repair attempt. "
                            f"Orphaned ci_ids: {sorted(persistent_09_orphans)}"
                        ),
                        "source_refs": sorted(persistent_09_orphans),
                        "practitioner_id": practitioner_id,
                        "project_id": project_id,
                        "produced_in_row": str(row_ref),
                    }
                )

    # -------------------------------------------------------------------------
    # ADVC-3d-01 — Requirement-per-Domain soft bounds
    # -------------------------------------------------------------------------
    for domain in stage1.active_domains:
        domain_proposals = [p for p in proposals if p.source_domain_id == domain.domain_id]
        req_count = len(domain_proposals)
        cci_count = len(domain.cell_content_item_refs)
        if req_count > cci_count:
            result.execution_warnings.append(
                {
                    "type": "requirement_count_advisory",
                    "domain_id": domain.domain_id,
                    "requirement_count": req_count,
                    "cci_count": cci_count,
                }
            )
            _log.info(
                "ADVC-3d-01: domain=%s produced %d Requirements for %d CCIs — "
                "possible over-decomposition",
                domain.domain_id, req_count, cci_count,
            )

    # -------------------------------------------------------------------------
    # ADVC-3d-02 — Interrogative slot-completeness (soft advisory, v0.6)
    # Warns when a surviving proposal may be missing a type-required slot.
    # Does NOT reject or change execution_status.
    # -------------------------------------------------------------------------
    _STRUCTURAL_MARKERS = (
        "comprise", "consist", "contain", "include",
        "belong", "associate", "relate to", "have a",
        "component", "member", "part of", "made of",
        "composed", "structured",
    )

    for p in proposals:
        stmt_lower = p.statement.lower().strip()
        rtype = p.requirement_type

        if rtype == "Functional":
            if " shall " not in stmt_lower:
                result.execution_warnings.append(
                    {
                        "type": "interrogative_completeness_advisory",
                        "advisory_id": "ADVC-3d-02",
                        "requirement_type": "Functional",
                        "detail": "Functional proposal missing normative 'shall' — possible incomplete Action slot",
                        "statement_preview": p.statement[:80],
                    }
                )

        elif rtype == "Constraint":
            # A Constraint should have a rule — 'shall' is present but should constrain
            if "shall" not in stmt_lower:
                result.execution_warnings.append(
                    {
                        "type": "interrogative_completeness_advisory",
                        "advisory_id": "ADVC-3d-02",
                        "requirement_type": "Constraint",
                        "detail": "Constraint proposal missing 'shall' — Rule slot may be incomplete",
                        "statement_preview": p.statement[:80],
                    }
                )

        elif rtype == "Structural":
            if not any(marker in stmt_lower for marker in _STRUCTURAL_MARKERS):
                if "shall " not in stmt_lower:
                    result.execution_warnings.append(
                        {
                            "type": "interrogative_completeness_advisory",
                            "advisory_id": "ADVC-3d-02",
                            "requirement_type": "Structural",
                            "detail": "Structural proposal may lack explicit structural-assertion slot",
                            "statement_preview": p.statement[:80],
                        }
                    )

    result.proposals = proposals
    return result
