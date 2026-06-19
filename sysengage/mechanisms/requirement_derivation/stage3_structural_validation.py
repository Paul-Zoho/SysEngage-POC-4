"""
Stage 3 — Structural Validation (DM, with conditional IM repair).

Per Requirement Derivation Mechanism Spec v0.28 §4.3:
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
  CHK-3d-09  Typed-slot atomicity check (decidable, HARD; realises F88 + F98 v0.24).
             Calls core.slots.check_atomicity per proposal. Hard violations:
               decompose_eligible set — conjoined_predicate, compound_object,
                 compound_constraint_rule (F98 option A): all are separable by the
                 detector's own logic (inseparable-single-concept is the soft PLB-3d-01
                 edge, never reaches hard). → in-place decompose repair via
                 _run_conjoined_decompose. If decompose succeeds, atomic children
                 replace the compound in surviving proposals. execution_warnings:
                 conjoined_predicate_hard_reject (at detection), chk3d09_decompose_performed
                 (on success). compound_condition excluded — condition complexity is not
                 obligation duplication; orphan pool → _run_repair is correct there.
               All other hard violations (e.g. compound_condition, missing_shall):
                 CCIs return to orphan pool → second CHK-3d-05 repair attempt.
               Soft violations log advisory.
  ADVC-3d-01 Requirement-per-Domain soft bounds advisory.
  ADVC-3d-02 Interrogative slot-completeness advisory (v0.6). Warns when a surviving
             proposal may be missing a type-required slot (Functional: Subject/Action/
             Object; Constraint: Subject/Rule; Structural: Entity/structural-assertion).
             Logs interrogative_completeness_advisory in execution_warnings only.
             Does NOT reject the Requirement.
  ADVC-3d-03 Concern-atomicity over-bundling signal (v0.12). Records requirements
             whose cci_refs span ≥2 classification types across ≥2 Zachman columns
             into concern_atomicity_flags in Stage3Result. No execution_warning, no
             reject — mechanism_data recording only (soft advisory).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from core.ai_client import MODEL, get_ai_client
from core.class_model_validity import validate_class_model
from core.slots import check_atomicity, violation_summary
from core.structural_data_assertion import is_data_asserting
from mechanisms.requirement_derivation.prompts.requirement_conjoined_decompose_prompt import (
    build_conjoined_decompose_prompt,
)
from mechanisms.requirement_derivation.prompts.requirement_refinement_prompt import (
    build_requirement_refinement_prompt,
)
from mechanisms.requirement_derivation.prompts.requirement_repair_prompt import (
    build_requirement_repair_prompt,
)
from mechanisms.requirement_derivation.schemas.requirement_refinement_response_schema import (
    RefinementProposal,
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
    _resolve_source_domain_id,
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
    concern_atomicity_flags: list[dict[str, Any]] = field(default_factory=list)
    ai_model_fingerprints: list[dict[str, Any]] = field(default_factory=list)
    execution_warnings: list[dict[str, Any]] = field(default_factory=list)
    concern_entities: list[dict[str, Any]] = field(default_factory=list)
    elaboration_gaps: list[str] = field(default_factory=list)
    seed_coverage: dict[str, Any] = field(default_factory=dict)
    extinction_failure: bool = False
    status: str = "ok"
    failure_reason: str | None = None
    class_model_binding: dict[str, Any] = field(default_factory=dict)


def _call_repair_ai(prompt: str, *, max_tokens: int = 8192) -> tuple[Any, dict[str, Any]]:
    client = get_ai_client()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
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
    """All-or-nothing parse for CHK-3d-05 orphan-repair responses."""
    try:
        data = json.loads(_strip_code_fence(text_))
        if not isinstance(data, list):
            return None
        return [RepairRequirementProposal.model_validate(item) for item in data]
    except Exception:
        return None


def _parse_decompose_response(
    text_: str,
    *,
    source_domain_id: str,
    result: Stage3Result,
) -> list[RepairRequirementProposal] | None:
    """
    Item-level resilient parse for CHK-3d-09 decompose responses (F106, v0.28).

    Each child in the AI's array is validated independently.  A malformed child
    is logged as decompose_child_discarded (with its index and validation error)
    and discarded — the valid siblings are kept.  Returns None only when the raw
    JSON cannot be parsed, the top-level value is not a list, or zero valid
    children survive after per-item validation.

    The CHK-3d-05 _parse_repair_response path is NOT changed by F106 — it stays
    all-or-nothing because a partial orphan-repair response could leave orphans
    uncovered while the re-check believes them covered.
    """
    try:
        data = json.loads(_strip_code_fence(text_))
    except Exception:
        return None
    if not isinstance(data, list):
        return None

    valid: list[RepairRequirementProposal] = []
    for idx, item in enumerate(data):
        try:
            valid.append(RepairRequirementProposal.model_validate(item))
        except Exception as exc:
            result.execution_warnings.append({
                "type": "decompose_child_discarded",
                "source_domain_id": source_domain_id,
                "child_index": idx,
                "validation_error": str(exc),
            })
            _log.warning(
                "CHK-3d-09 decompose: child %d discarded (validation error): %s",
                idx, exc,
            )

    return valid if valid else None


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
                refines_refs=[],
                rationale=rp.rationale,
                fit_criteria=rp.fit_criteria,
                verification_method=rp.verification_method,
                priority=rp.priority,
                confidence=rp.confidence,
            )
        )
    return repair_proposals


def _run_conjoined_decompose(
    proposal: TaggedProposal,
    *,
    result: Stage3Result,
    row_ref: int,
) -> list[TaggedProposal]:
    """
    F98 CHK-3d-09 in-place decompose repair for conjoined-predicate violations (v0.28).

    Re-expresses one compound statement (two distinct finite verb phrases under one
    'shall') as N≥2 atomic statements, each carrying a single obligation. Any
    inter-half dependency is expressed as a Condition slot on the dependent statement.

    This is NOT the orphan-pool / CHK-3d-05 path — the decompose replaces the
    compound in-place so no CCI is dropped.

    F106 (v0.28) executor discipline:
      - Uses _parse_decompose_response (item-level resilient) instead of
        _parse_repair_response (all-or-nothing). A malformed child is discarded
        individually (decompose_child_discarded warning); valid siblings are kept.
        Returns [] only when zero valid children survive or the AI call fails.
      - cci_refs inheritance: any child whose cci_refs is empty after parse is
        assigned the parent compound's full cci_refs. This pairs with the schema
        relaxation that dropped cci_refs_not_empty — the schema accepts empty;
        the executor corrects it before building the TaggedProposal.
      - confidence normalisation: a None confidence (schema Optional/defaulted)
        is mapped to 0.85 before building the TaggedProposal.

    Returns TaggedProposal list (may be empty on AI failure; caller then falls through
    to the standard orphan-pool detection for the unrecovered CCIs).
    Mutates result.ai_model_fingerprints and result.execution_warnings.
    """
    decompose_prompt = build_conjoined_decompose_prompt(
        row_ref=row_ref,
        compound_statement=proposal.statement,
        requirement_type=proposal.requirement_type,
        cci_refs=proposal.cci_refs,
        rationale=proposal.rationale,
        fit_criteria=proposal.fit_criteria,
        verification_method=proposal.verification_method,
        priority=proposal.priority,
        confidence=proposal.confidence,
    )

    parsed_decompose: list[RepairRequirementProposal] | None = None
    try:
        msg, fp = _call_repair_ai(decompose_prompt, max_tokens=4096)
        fp["stage"] = "stage3_chk3d09_decompose"
        result.ai_model_fingerprints.append(fp)
        # F106(1): item-level resilient parse — malformed children are discarded
        # individually, valid siblings returned. _parse_repair_response (all-or-
        # nothing) is kept for the CHK-3d-05 orphan-repair path unchanged.
        parsed_decompose = _parse_decompose_response(
            msg.content[0].text,
            source_domain_id=proposal.source_domain_id,
            result=result,
        )
    except Exception as exc:
        _log.warning("CHK-3d-09 decompose AI call failed: %s", exc)
        result.execution_warnings.append({
            "type": "conjoined_predicate_decompose_failed",
            "source_domain_id": proposal.source_domain_id,
            # F100 every-path sweep (F104 v0.27): guard against empty/None statement
            # so the preview is always non-empty in the warning record.
            "statement_preview": (proposal.statement or "(no statement)")[:80],
            "detail": str(exc),
        })
        return []  # early return — avoids double-emit and cross-call suppression below

    if not parsed_decompose:
        # Zero valid children after per-item validation — emit failure once per call.
        result.execution_warnings.append({
            "type": "conjoined_predicate_decompose_failed",
            "source_domain_id": proposal.source_domain_id,
            # F100 every-path sweep (F104 v0.27): guard against empty/None statement.
            "statement_preview": (proposal.statement or "(no statement)")[:80],
        })
        return []

    children: list[TaggedProposal] = []
    for rp in parsed_decompose:
        # F106(2): inherit parent cci_refs for any child with empty cci_refs.
        # The schema no longer rejects empty cci_refs at parse time; the executor
        # corrects it here so every surviving child is fully referenced.
        child_cci_refs = list(rp.cci_refs) if rp.cci_refs else list(proposal.cci_refs)
        # F106(2): confidence is Optional/defaulted in the schema; normalise None.
        child_confidence = rp.confidence if rp.confidence is not None else 0.85
        children.append(
            TaggedProposal(
                source_domain_id=proposal.source_domain_id,
                statement=rp.statement,
                requirement_type=rp.requirement_type,
                cci_refs=child_cci_refs,
                refines_refs=list(proposal.refines_refs),
                rationale=rp.rationale,
                fit_criteria=rp.fit_criteria,
                verification_method=rp.verification_method,
                priority=rp.priority,
                confidence=child_confidence,
            )
        )
    return children


# ---------------------------------------------------------------------------
# CHK-3d-13 helpers — data-asserting Structural without class_model [E] v0.36
# ---------------------------------------------------------------------------

def _run_chk3d13_judge(statement: str, result: "Stage3Result") -> bool | None:
    """
    IM judge for genuinely ambiguous CHK-3d-13 cases.

    Returns True=data-asserting, False=not-data-asserting, None=judge failed.
    Fingerprint: stage3_chk3d13_judge.
    """
    prompt = (
        "You are a systems engineering data analyst.\n\n"
        "A *data-asserting* Structural requirement names a data entity and "
        "asserts its composition — it uses a have/comprise/define/contain/"
        "consist-of/be-associated-with predicate over attributes, "
        "relationships, keys, or domain values.\n\n"
        "A *constraint/policy* Structural requirement expresses a retention "
        "rule, auditability obligation, cross-entity policy, or other "
        "structural constraint that does NOT define an entity's data "
        "composition.\n\n"
        f'Statement: "{statement}"\n\n'
        'Respond with a single JSON object: {"is_data_asserting": true} or '
        '{"is_data_asserting": false}. No other text.'
    )
    try:
        client = get_ai_client()
        msg = client.messages.create(
            model=MODEL,
            max_tokens=64,
            messages=[{"role": "user", "content": prompt}],
        )
        result.ai_model_fingerprints.append({
            "stage": "stage3_chk3d13_judge",
            "model": msg.model,
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens,
        })
        raw = _strip_code_fence(msg.content[0].text if msg.content else "")
        data = json.loads(raw)
        return bool(data.get("is_data_asserting"))
    except Exception as exc:
        _log.warning("CHK-3d-13 judge failed: %s", exc)
        return None


def _run_chk3d13_repair(
    proposal: "TaggedProposal",
    *,
    row_ref: int,
    result: "Stage3Result",
) -> dict | None:
    """
    IM repair for CHK-3d-13: re-derive the data-asserting Structural as a
    class_model (§4.4.3c derivation path, one call per failing Structural).

    Returns the class_model dict on success, None if the call fails or the
    response cannot be parsed into a valid class_model.
    Fingerprint: stage3_chk3d13_repair.
    """
    prompt = (
        "You are a systems engineering analyst performing CHK-3d-13 repair. "
        "A data-asserting Structural requirement that lacks a class_model must "
        "be re-derived as one.\n\n"
        f"Row: {row_ref}\n"
        f'Statement: "{proposal.statement}"\n\n'
        "From this statement, identify:\n"
        "  1. The primary ENTITY being described (e.g. Task, Payment, Child).\n"
        "  2. Each ATTRIBUTE of that entity mentioned in the statement.\n\n"
        "CRITICAL field rules:\n"
        "  - `name`: a snake_case identifier derived from the attribute concept "
        "(e.g. 'monetary_value', 'availability_status', 'completion_date'). "
        "NEVER use 'attr_name' literally. NEVER leave it null.\n"
        "  - `semantic_type`: a semantic CATEGORY noun (e.g. 'money', 'identifier', "
        "'lifecycle_state', 'name', 'date', 'quantity', 'code', 'reference', "
        "'flag', 'amount', 'label'). "
        "Do NOT use POS tags ('Noun', 'Verb', 'Qualifier') — those are wrong.\n"
        "  - `origin`: 'refines' | 'realises' | 'introduced'\n"
        "  - `description`: one-line description of the attribute.\n\n"
        "Row 2 ONLY: do NOT include 'type', 'key', 'domain', or 'target_ref'.\n\n"
        "Example for 'Each task shall have an associated monetary value':\n"
        '{"entity":"Task","tier":2,"refinement_kind":"identity",'
        '"attributes":[{"name":"monetary_value","semantic_type":"money",'
        '"origin":"introduced","description":"Monetary value associated with the task"}],'
        '"relationships":[]}\n\n'
        "Now produce the class_model for the statement above. "
        "Return ONLY a JSON object — no other text."
    )
    try:
        client = get_ai_client()
        msg = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        result.ai_model_fingerprints.append({
            "stage": "stage3_chk3d13_repair",
            "model": msg.model,
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens,
        })
        raw = _strip_code_fence(msg.content[0].text if msg.content else "")
        cm = json.loads(raw)
        if not isinstance(cm, dict):
            return None
        if not cm.get("entity") or not cm.get("attributes"):
            return None
        return cm
    except Exception as exc:
        _log.warning("CHK-3d-13 repair failed: %s", exc)
        return None


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
    # CHK-3d-02 — Reject only when BOTH cci_refs AND refines_refs are empty.
    # v0.13 relaxation: Path R proposals may have empty cci_refs when
    # refines_refs is set; they pass this check.
    # -------------------------------------------------------------------------
    surviving = []
    for p in proposals:
        if not p.cci_refs and not p.refines_refs:
            result.validation_failures.append(
                {
                    "check_id": "CHK-3d-02",
                    "source_domain_id": p.source_domain_id,
                    "detail": "empty cci_refs AND empty refines_refs",
                }
            )
        else:
            surviving.append(p)
    proposals = surviving

    # -------------------------------------------------------------------------
    # CHK-3d-03 — cci_refs resolve to source Domain's eligible membership.
    # v0.13: proposals with empty cci_refs but non-empty refines_refs skip the
    # membership check (they are Path R proposals; cci_refs populated later).
    # -------------------------------------------------------------------------
    cleaned: list[TaggedProposal] = []
    for p in proposals:
        if not p.cci_refs and p.refines_refs:
            cleaned.append(p)
            continue

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

        if not valid_refs and not p.refines_refs:
            result.validation_failures.append(
                {
                    "check_id": "CHK-3d-02",
                    "source_domain_id": p.source_domain_id,
                    "detail": "empty cci_refs after stripping out-of-Domain refs (CHK-3d-03) and refines_refs also empty",
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
    # CHK-3d-11 — Class-model structural validity (F105 / v0.33)
    # Runs only on Structural proposals that carry a class_model dict.
    # Hard violations exclude the proposal; soft violations log an advisory.
    # -------------------------------------------------------------------------
    # Collect class_model_binding audit stats (§4.4.3b / §7)
    _cm_structural_count: int = sum(
        1 for p in proposals if p.requirement_type == "Structural"
    )
    _cm_with_class_model: int = sum(
        1 for p in proposals if p.requirement_type == "Structural" and p.class_model
    )
    _cm_by_tier: dict[str, int] = {}
    _cm_by_refinement_kind: dict[str, int] = {}
    _cm_invalid: list[dict[str, Any]] = []
    _TIER_NAMES: dict[int, str] = {
        1: "scope", 2: "conceptual", 3: "logical", 4: "physical", 5: "detailed"
    }
    for p in proposals:
        if p.requirement_type == "Structural" and p.class_model:
            tier_raw = p.class_model.get("tier")
            tier_key = _TIER_NAMES.get(tier_raw, f"tier{tier_raw}" if tier_raw is not None else "unknown")
            _cm_by_tier[tier_key] = _cm_by_tier.get(tier_key, 0) + 1
            rk = p.class_model.get("refinement_kind", "unknown")
            _cm_by_refinement_kind[rk] = _cm_by_refinement_kind.get(rk, 0) + 1

    surviving_11: list[TaggedProposal] = []
    for p in proposals:
        if p.requirement_type != "Structural" or not p.class_model:
            surviving_11.append(p)
            continue
        viols = validate_class_model(p.class_model, row_ref)
        hard_viols = [v for v in viols if v["severity"] == "hard"]
        soft_viols = [v for v in viols if v["severity"] == "soft"]
        if hard_viols:
            for v in hard_viols:
                result.validation_failures.append(
                    {
                        "check_id": "CHK-3d-11",
                        "source_domain_id": p.source_domain_id,
                        "detail": v["detail"],
                        "statement_preview": p.statement[:80],
                    }
                )
                _cm_invalid.append({
                    "source_domain_id": p.source_domain_id,
                    "entity": p.class_model.get("entity", "?"),
                    "detail": v["detail"],
                })
            _log.info(
                "CHK-3d-11 HARD: domain=%s entity=%r — %d violation(s) → excluded",
                p.source_domain_id,
                p.class_model.get("entity", "?"),
                len(hard_viols),
            )
        else:
            for sv in soft_viols:
                result.execution_warnings.append(
                    {
                        "type": "class_model_soft_violation",
                        "advisory_id": "CHK-3d-11",
                        "source_domain_id": p.source_domain_id,
                        "detail": sv["detail"],
                        "entity": p.class_model.get("entity", "?"),
                    }
                )
            surviving_11.append(p)
    proposals = surviving_11

    # -------------------------------------------------------------------------
    # CHK-3d-11 uniqueness — one class_model per (entity, row) [B] v0.36
    # A second Structural for the same entity at the same row_ref is a hard
    # error: only the first occurrence is kept; duplicates are rejected with
    # detail "duplicate_entity_model".
    # -------------------------------------------------------------------------
    entity_seen: dict[str, int] = {}  # normalised entity name → index in surviving_11_unique
    surviving_11_unique: list[TaggedProposal] = []
    for p in proposals:
        if p.requirement_type != "Structural" or not p.class_model:
            surviving_11_unique.append(p)
            continue
        entity_norm = (p.class_model.get("entity") or "").strip().lower()
        if entity_norm and entity_norm in entity_seen:
            result.validation_failures.append({
                "check_id": "CHK-3d-11",
                "source_domain_id": p.source_domain_id,
                "detail": "duplicate_entity_model",
                "entity": p.class_model.get("entity", "?"),
                "statement_preview": (p.statement or "")[:80],
            })
            result.execution_warnings.append({
                "type": "class_model_invalid",
                "source_domain_id": p.source_domain_id,
                "entity": p.class_model.get("entity", "?"),
                "detail": "duplicate_entity_model",
            })
            _log.info(
                "CHK-3d-11 [B] HARD: duplicate class_model for entity=%r at row %d — excluded",
                p.class_model.get("entity", "?"),
                row_ref,
            )
        else:
            if entity_norm:
                entity_seen[entity_norm] = len(surviving_11_unique)
            surviving_11_unique.append(p)
    proposals = surviving_11_unique

    result.class_model_binding = {
        "structural_count": _cm_structural_count,
        "with_class_model": _cm_with_class_model,
        "by_tier": _cm_by_tier,
        "by_refinement_kind": _cm_by_refinement_kind,
        "invalid": _cm_invalid,
    }

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
    # CHK-3d-09 — Typed-slot atomicity (decidable, HARD; realises F88 + F98)
    #
    # F98 (v0.24) conjoined-predicate branch: when the ONLY hard violation is
    # conjoined_predicate (two distinct finite verb phrases under one 'shall'),
    # attempt in-place decompose repair via _run_conjoined_decompose instead of
    # routing to the orphan pool. If decompose succeeds the atomic children
    # replace the compound in surviving_09. If decompose fails, the proposal is
    # absent from surviving_09 and its CCIs are detected as new_orphans_09 by
    # the post-loop computation, which then falls back to the standard
    # _run_repair path.
    #
    # All other hard violations still route to the orphan pool as before.
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
            decompose_eligible = all(
                v.rule in {"conjoined_predicate", "compound_object", "compound_constraint_rule"}
                for v in hard_viols
            )
            if decompose_eligible:
                # F98 (A): in-place decompose repair for any hard compound form
                # (conjoined_predicate, compound_object, compound_constraint_rule).
                # compound_condition stays on orphan path — it's condition complexity,
                # not obligation duplication, so a split of the action side is wrong.
                result.execution_warnings.append({
                    "type": "conjoined_predicate_hard_reject",
                    "source_domain_id": p.source_domain_id,
                    "statement_preview": p.statement[:80],
                })
                decomposed = _run_conjoined_decompose(p, result=result, row_ref=row_ref)
                if decomposed:
                    result.execution_warnings.append({
                        "type": "chk3d09_decompose_performed",
                        "source_domain_id": p.source_domain_id,
                        "original_statement_preview": p.statement[:80],
                        "decomposed_count": len(decomposed),
                    })
                    surviving_09.extend(decomposed)
                else:
                    # F102 (v0.26): retain-on-failure — a compound-but-present obligation
                    # beats an atomic-but-absent one. When decompose yields no atomic
                    # children, keep the original in surviving_09. The
                    # conjoined_predicate_decompose_failed warning was already recorded
                    # inside _run_conjoined_decompose. CHK-3d-05 orphan recovery is not
                    # a sufficient fallback where CCIs are coarse (Non-Loss).
                    result.execution_warnings.append({
                        "type": "chk3d09_decompose_failed_retained",
                        "source_domain_id": p.source_domain_id,
                        "statement_preview": p.statement[:80],
                    })
                    surviving_09.append(p)
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

    # -------------------------------------------------------------------------
    # ADVC-3d-03 — Concern-atomicity over-bundling signal (soft, v0.12)
    # Records requirements whose cci_refs span ≥2 classification types across
    # ≥2 Zachman columns. No execution_warning, no reject — mechanism_data only.
    # -------------------------------------------------------------------------
    _cci_meta: dict[str, dict[str, str]] = {
        cci.ci_id: {
            "column": cci.column,
            "classification_type": cci.classification_type,
        }
        for cci in stage1.eligible_ccis
    }
    for idx, p in enumerate(proposals):
        if not p.cci_refs:
            continue
        cols = {_cci_meta[r]["column"] for r in p.cci_refs if r in _cci_meta}
        types = {_cci_meta[r]["classification_type"] for r in p.cci_refs if r in _cci_meta}
        if len(cols) >= 2 and len(types) >= 2:
            placeholder = f"proposal_{idx + 1}:{p.statement[:40].rstrip()}"
            result.concern_atomicity_flags.append(
                {
                    "requirement_id_placeholder": placeholder,
                    "cci_refs": list(p.cci_refs),
                    "classification_types": sorted(types),
                    "columns": sorted(cols),
                }
            )
            _log.info(
                "ADVC-3d-03: %s spans %d classification types across %d columns — "
                "concern-atomicity over-bundling signal",
                placeholder, len(types), len(cols),
            )

    # -------------------------------------------------------------------------
    # CHK-3d-13 — data-asserting Structural MUST carry class_model [E] v0.36
    #
    # A Structural without class_model is examined:
    #   1. DM detector → "yes" | "no" | "ambiguous"
    #   2. "ambiguous" → IM judge (fingerprint stage3_chk3d13_judge)
    #   3. data-asserting → IM repair (fingerprint stage3_chk3d13_repair)
    #   4. Repair success + entity not yet modelled → proposal gets class_model, survives
    #      Repair success + entity ALREADY modelled → excluded as redundant ([B] interaction)
    #   5. Repair failure / persistent → HARD validation_failure, excluded
    #   6. "no" (constraint/policy) → chk3d13_constraint_exempt, kept as prose
    # -------------------------------------------------------------------------
    # Seed entity_modelled from proposals that already carry a class_model.
    # This set grows as successful repairs mint new models so that each entity
    # is modelled at most once across the whole CHK-3d-13 pass ([B] interaction).
    entity_modelled: set[str] = {
        (p.class_model.get("entity") or "").strip().lower()
        for p in proposals
        if p.requirement_type == "Structural" and p.class_model
        if (p.class_model.get("entity") or "").strip()
    }

    surviving_13: list[TaggedProposal] = []
    for p in proposals:
        if p.requirement_type != "Structural" or p.class_model is not None:
            surviving_13.append(p)
            continue

        stmt = p.statement or ""
        placeholder_13 = f"proposal:{stmt[:40].rstrip()}"
        decidability = is_data_asserting(stmt)

        if decidability == "no":
            result.execution_warnings.append({
                "type": "chk3d13_constraint_exempt",
                "statement_preview": stmt[:80],
            })
            surviving_13.append(p)
            continue

        if decidability == "ambiguous":
            judge_result = _run_chk3d13_judge(stmt, result)
            if judge_result is False:
                result.execution_warnings.append({
                    "type": "chk3d13_constraint_exempt",
                    "statement_preview": stmt[:80],
                })
                surviving_13.append(p)
                continue
            # judge_result is True or None (AI failure → conservative: treat as asserting)

        # data-asserting — attempt IM repair
        result.execution_warnings.append({
            "type": "chk3d13_repair_performed",
            "statement_preview": stmt[:80],
        })
        repaired_cm = _run_chk3d13_repair(p, row_ref=row_ref, result=result)

        if repaired_cm is not None:
            repaired_entity_norm = (repaired_cm.get("entity") or "").strip().lower()

            # [B] interaction: if this entity is already modelled by a prior surviving
            # proposal (original or repaired), exclude this prose Structural as redundant.
            if repaired_entity_norm and repaired_entity_norm in entity_modelled:
                result.execution_warnings.append({
                    "type": "chk3d13_entity_already_modelled",
                    "entity": repaired_cm.get("entity"),
                    "statement_preview": stmt[:80],
                })
                _log.info(
                    "CHK-3d-13 repair: entity=%r already modelled — "
                    "prose Structural excluded as redundant",
                    repaired_cm.get("entity"),
                )
                continue  # excluded — entity already has a class_model

            hard_viols = [
                v for v in validate_class_model(repaired_cm, row_ref)
                if v["severity"] == "hard"
            ]
            if not hard_viols:
                p.class_model = repaired_cm
                entity_modelled.add(repaired_entity_norm)
                if not p.statement:
                    try:
                        from core.class_model_projection import project_class_model
                        p.statement = project_class_model(repaired_cm)
                    except Exception:
                        pass
                surviving_13.append(p)
                _log.info(
                    "CHK-3d-13 repair success: entity=%r statement=%.60s",
                    repaired_cm.get("entity"),
                    stmt,
                )
                continue
            _log.warning(
                "CHK-3d-13 repaired class_model failed CHK-3d-11: %s",
                [v["detail"] for v in hard_viols],
            )

        # Persistent failure → HARD, excluded
        result.validation_failures.append({
            "check_id": "CHK-3d-13",
            "requirement_id": placeholder_13,
            "detail": "data_assertion_without_class_model",
            "statement_preview": stmt[:80],
        })
        result.execution_warnings.append({
            "type": "chk3d13_data_assertion_unmodelled",
            "statement_preview": stmt[:80],
        })
        _log.info(
            "CHK-3d-13 HARD: data-asserting Structural without class_model — excluded: %.60s",
            stmt,
        )
    proposals = surviving_13

    # -------------------------------------------------------------------------
    # VER-3d-21 — Seed-set provenance guard (v0.14).
    # Asserts that the seed set loaded by Stage 2 equals the independent
    # count of surviving row n-1 requirements.  A mismatch means a
    # provenance filter (e.g. filtering by cci_refs/refines_refs) has crept
    # into _load_seeds, silently excluding row-native Path-N seeds.
    # Only runs when Stage 2 recorded a non-zero surviving_count (i.e. a
    # fresh FirstRun/FullRerun at row >= 2; not IdempotentRerun/Row 1).
    # -------------------------------------------------------------------------
    if stage2.seed_set_surviving_count > 0:
        if len(stage2.seed_set) != stage2.seed_set_surviving_count:
            _log.warning(
                "VER-3d-21 FAIL: seed_set size=%d but surviving row n-1 "
                "requirement count=%d — provenance filter suspected in _load_seeds",
                len(stage2.seed_set),
                stage2.seed_set_surviving_count,
            )
            result.execution_warnings.append(
                {
                    "type": "ver3d21_seed_set_size_mismatch",
                    "seed_set_count": len(stage2.seed_set),
                    "surviving_count": stage2.seed_set_surviving_count,
                }
            )
        else:
            _log.info(
                "VER-3d-21 OK: seed_set size=%d matches surviving count",
                len(stage2.seed_set),
            )

    # -------------------------------------------------------------------------
    # CHK-3d-10 — Downward Non-Loss: every row n-1 seed is refined by ≥1
    # surviving proposal (v0.13).
    # Only applies when stage2.seed_set is non-empty (rows >= 2, Path R ran).
    # Unrefined seeds → one re-prompt elaboration attempt;
    # persistent → elaboration_gaps in mechanism_data + warning.
    # -------------------------------------------------------------------------
    seed_set = stage2.seed_set
    if seed_set:
        all_seed_ids = {s["requirement_id"] for s in seed_set}
        refined_seed_ids = {ref for p in proposals for ref in p.refines_refs}
        unrefined_seed_ids = all_seed_ids - refined_seed_ids

        result.seed_coverage = {
            "total_seeds": len(all_seed_ids),
            "refined_count": len(refined_seed_ids & all_seed_ids),
            "unrefined_count": len(unrefined_seed_ids),
            "unrefined_seed_ids": sorted(unrefined_seed_ids),
        }

        if unrefined_seed_ids:
            _log.info(
                "CHK-3d-10: %d unrefined seed(s) — attempting elaboration repair: %s",
                len(unrefined_seed_ids), sorted(unrefined_seed_ids),
            )
            result.execution_warnings.append(
                {
                    "type": "chk3d10_repair_performed",
                    "unrefined_count": len(unrefined_seed_ids),
                    "unrefined_seed_ids": sorted(unrefined_seed_ids),
                }
            )

            unrefined_seeds = [
                s for s in seed_set if s["requirement_id"] in unrefined_seed_ids
            ]
            domains_context = [
                {
                    "domain_id": d.domain_id,
                    "name": d.name,
                    "description": d.description,
                    "cell_content_items": [
                        {
                            "ci_id": c.ci_id,
                            "column": c.column,
                            "classification_type": c.classification_type,
                            "description": c.description,
                        }
                        for c in stage1.eligible_ccis
                        if c.ci_id in set(d.cell_content_item_refs)
                    ],
                }
                for d in stage1.active_domains
            ]
            repair_prompt = build_requirement_refinement_prompt(
                row_ref=row_ref,
                seeds=unrefined_seeds,
                domains=domains_context,
            )

            chk10_proposals: list[TaggedProposal] = []
            try:
                client = get_ai_client()
                msg = client.messages.create(
                    model=MODEL,
                    max_tokens=8192,
                    messages=[{"role": "user", "content": repair_prompt}],
                )
                fp = {
                    "stage": "stage3_chk3d10_repair",
                    "model": msg.model,
                    "input_tokens": msg.usage.input_tokens,
                    "output_tokens": msg.usage.output_tokens,
                }
                result.ai_model_fingerprints.append(fp)
                raw_text = msg.content[0].text if msg.content else ""
                try:
                    import json as _json
                    _raw = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw_text, re.DOTALL)
                    _stripped = _raw.group(1).strip() if _raw else raw_text.strip()
                    _parsed_items = _json.loads(_stripped)
                    if isinstance(_parsed_items, list):
                        for item in _parsed_items:
                            rp = RefinementProposal.model_validate(item)
                            if rp.refines_refs and rp.refines_refs[0] in unrefined_seed_ids:
                                src_did = _resolve_source_domain_id(list(rp.cci_refs), stage1)
                                chk10_proposals.append(
                                    TaggedProposal(
                                        source_domain_id=src_did,
                                        statement=rp.statement,
                                        requirement_type=rp.requirement_type,
                                        cci_refs=list(rp.cci_refs),
                                        refines_refs=list(rp.refines_refs),
                                        rationale=rp.rationale,
                                        fit_criteria=rp.fit_criteria,
                                        verification_method=rp.verification_method,
                                        priority=rp.priority,
                                        confidence=rp.confidence,
                                    )
                                )
                except Exception as parse_exc:
                    _log.warning("CHK-3d-10 repair response parse failed: %s", parse_exc)
                    result.execution_warnings.append(
                        {"type": "chk3d10_repair_failed", "detail": str(parse_exc)}
                    )
            except Exception as exc:
                _log.warning("CHK-3d-10 repair AI call failed: %s", exc)
                result.execution_warnings.append(
                    {"type": "chk3d10_repair_failed", "detail": str(exc)}
                )

            if chk10_proposals:
                proposals.extend(chk10_proposals)
                _log.info(
                    "CHK-3d-10 repair: %d proposals recovered", len(chk10_proposals)
                )
                refined_seed_ids_after = {
                    ref for p in proposals for ref in p.refines_refs
                }
                unrefined_seed_ids = all_seed_ids - refined_seed_ids_after
                result.seed_coverage["refined_count"] = len(refined_seed_ids_after & all_seed_ids)
                result.seed_coverage["unrefined_count"] = len(unrefined_seed_ids)
                result.seed_coverage["unrefined_seed_ids"] = sorted(unrefined_seed_ids)

            if unrefined_seed_ids:
                result.elaboration_gaps = sorted(unrefined_seed_ids)
                result.extinction_failure = True
                if result.status != "failed":
                    result.status = "ok_with_warnings"
                result.execution_warnings.append(
                    {
                        "type": "chk3d10_seed_extinct",
                        "elaboration_gap_count": len(unrefined_seed_ids),
                        "elaboration_gaps": sorted(unrefined_seed_ids),
                    }
                )
                _log.warning(
                    "CHK-3d-10: %d seed(s) remain unrefined after repair — "
                    "elaboration_gaps recorded: %s",
                    len(unrefined_seed_ids), sorted(unrefined_seed_ids),
                )

    result.proposals = proposals
    return result
