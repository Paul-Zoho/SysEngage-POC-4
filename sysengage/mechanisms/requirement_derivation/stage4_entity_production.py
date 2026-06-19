"""
Stage 4 — Entity Production and Ledger Commit (DM + IM for §4.4.3a).

Per Requirement Derivation Mechanism Spec v0.33 §4.4:
  4.4.1  requirement_id allocation (global per-project R###, includes retired).
  4.4.2  domain_refs DM-derivation (MD-2): intersect cci_refs with active Domain
         memberships; assert ≥1 domain_ref. Fail-closed if empty.
  4.4.3  Requirement entity construction (all spec §5.1 columns).
  4.4.3a DD Object-slot binding (v0.8, IM + DM):
         Step 1 — IM entity extraction: batched AI call reduces Object/Entity/Subject
         slots to entity-grade noun phrases; fingerprinted as
         'stage4_dd_entity_extraction'. Replaces the v0.7 verbatim DM slot copy.
         Step 2 — DD service resolve/relationship/value calls (DM).
         Step 3 — bind / flag; zero-term Functional/Structural → dd_unresolved.
         VER-3d-19 violations recorded in dd_binding audit block.
  4.4.4  FullRerun retirement (retired_at = now() on prior active Requirements).
  4.4.5  downstream_rerun_required: check Phase 5/6/8 AnalysisPasses.
  4.4.6  Single transaction: retire (FullRerun), insert Requirements, DD binding
         (own sessions), replace RequirementRegister.member_ids (project-wide),
         write AnalysisPass.

Note: F80 disposition — domain_refs are derived by domain_id, never by name.
Cross-row Domain name duplication (NQPS "Quality Governance" at Row 1 and Row 2)
is harmless to derivation. F80 left Open per D5.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.ai_client import MODEL, get_ai_client
from core.db import format_identifier, get_next_sequence_value, get_session, refresh_engine_pool
from core.slots import extract_slot_terms
from core.class_model_coverage import check_concept_coverage
from core.object_refs_resolver import resolve_object_refs
from mechanisms.data_dictionary.service import resolve_and_record
from mechanisms.requirement_derivation.prompts.requirement_dd_extraction_prompt import (
    build_dd_extraction_prompt,
)
from mechanisms.requirement_derivation.schemas.requirement_dd_extraction_response_schema import (
    EntityExtractionItem,
    StateQualifier,
)
from mechanisms.requirement_derivation.stage1_preflight import ActiveDomain, Stage1Result
from mechanisms.requirement_derivation.stage2_ai_derivation import Stage2Result
from mechanisms.requirement_derivation.stage3_structural_validation import Stage3Result, TaggedProposal
from models.concern import ConcernModel

_log = logging.getLogger(__name__)

_JACCARD_THRESHOLD = 0.50
_MIN_TERM_LEN = 2

# VER-3d-19 heuristic bounds
_VER19_MAX_WORDS = 8
_VER19_SENTENCE_PUNCT = re.compile(r"[.?!]\s*$")


@dataclass
class Stage4Result:
    requirement_count_produced: int = 0
    requirement_count_retired: int = 0
    requirements_produced: list[dict[str, Any]] = field(default_factory=list)
    requirement_type_distribution: dict[str, int] = field(default_factory=dict)
    retirement_mapping: list[dict[str, Any]] = field(default_factory=list)
    downstream_rerun_required: bool = False
    dd_binding: dict[str, Any] = field(default_factory=dict)
    ai_model_fingerprints: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    failure_reason: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _jaccard_overlap(stmt_a: str, stmt_b: str) -> float:
    tokens_a = set(stmt_a.lower().split())
    tokens_b = set(stmt_b.lower().split())
    if not tokens_a and not tokens_b:
        return 1.0
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


def _strip_code_fence(text_: str) -> str:
    """Strip markdown ```json ... ``` or ``` ... ``` code fences if present."""
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text_, re.DOTALL)
    return m.group(1).strip() if m else text_.strip()


def _raw_slot_description(slots: dict, requirement_type: str) -> str:
    """
    Format the slot parse output into a human-readable hint for the extraction prompt.
    The AI uses this as the anchor for reduction, not as the term itself.
    """
    if requirement_type == "Functional":
        obj = slots.get("object") or ""
        return obj
    elif requirement_type == "Structural":
        entity = slots.get("entity") or ""
        assertion = slots.get("assertion") or ""
        if entity and assertion:
            return f"{entity} / {assertion}"
        return entity or assertion
    elif requirement_type == "Constraint":
        # F99 (v0.24): pass the Constraint-Rule (post-shall predicate), not the Subject.
        # A Constraint has no Object slot; the DD entity terms are the domain concepts
        # the Rule governs, extracted from the rule predicate text.
        return slots.get("rule") or ""
    return ""


# ---------------------------------------------------------------------------
# §4.4.3a Step 1 — IM entity extraction (v0.25 / F101 batched)
# ---------------------------------------------------------------------------

# F101 (v0.25): extraction is batched and ceiling-bounded like Stage 2 Path-R.
# Each item's JSON output is ~15-25 tokens ({idx, terms:[...], state_qualifiers:[...]}).
# At 40 items/batch × 25 tokens/item ≈ 1 000 output tokens — 8× headroom under the
# 8 192 ceiling. Previously one unbatched call for the whole row overflowed the old
# 2 048 ceiling when decompose enlarged the batch (R3_Run8: output_tokens == 2 048
# exactly → truncated JSON → all proposals → dd_zero_term, silently).
_EXTRACTION_BATCH_SIZE = 40
_EXTRACTION_MAX_TOKENS = 8192


def _extract_entity_terms_ai(
    proposals: list[TaggedProposal],
    req_ids: list[str],
    pass_data: dict[str, Any],
    row_ref: int,
) -> tuple[dict[str, list[str]], dict[str, list[StateQualifier]], list[dict[str, Any]]]:
    """
    Batched IM entity extraction for §4.4.3a Step 1 (v0.25 / F101).

    Replaces the single-call architecture (v0.11) that could overflow the token
    ceiling when decompose enlarged the proposal set. Proposals are processed in
    batches of _EXTRACTION_BATCH_SIZE; each batch produces one fingerprint named
    'stage4_dd_entity_extraction_batch<N>'.

    Per-item slot-parse guard: extract_slot_terms exceptions degrade that proposal
    to raw_slot='' (slot_parse_failed warning) rather than crashing the stage.

    Truncation is a loud hard failure: if a batch's output_tokens hits the ceiling,
    dd_extraction_batch_truncated is recorded — never swallowed silently.

    Returns:
      entity_terms        — dict mapping req_id → list of bare entity-grade term strings
      state_qualifier_map — dict mapping req_id → list of StateQualifier (entity, state)
      fingerprints        — list of per-batch fingerprint dicts
    """
    entity_terms: dict[str, list[str]] = {req_id: [] for req_id in req_ids}
    state_qualifier_map: dict[str, list[StateQualifier]] = {req_id: [] for req_id in req_ids}
    fingerprints: list[dict[str, Any]] = []

    batches = [
        (proposals[i: i + _EXTRACTION_BATCH_SIZE], req_ids[i: i + _EXTRACTION_BATCH_SIZE])
        for i in range(0, len(proposals), _EXTRACTION_BATCH_SIZE)
    ]
    total_batches = len(batches)
    _log.info(
        "Stage 4 DD extraction: %d proposals in %d batch(es) of ≤%d (row %s)",
        len(proposals), total_batches, _EXTRACTION_BATCH_SIZE, row_ref,
    )

    for batch_num, (batch_proposals, batch_req_ids) in enumerate(batches, start=1):
        # --- per-item slot-parse guard ---
        items: list[dict[str, Any]] = []
        for i, (proposal, req_id) in enumerate(zip(batch_proposals, batch_req_ids)):
            try:
                slots = extract_slot_terms(proposal.statement, proposal.requirement_type)
                raw_slot = _raw_slot_description(slots, proposal.requirement_type)
            except Exception as slot_exc:
                _log.warning(
                    "Slot parse failed for req %s in batch %d: %s",
                    req_id, batch_num, slot_exc,
                )
                pass_data.setdefault("execution_warnings_stage4", []).append({
                    "type": "slot_parse_failed",
                    "batch": batch_num,
                    "requirement_id": req_id,
                    "error": str(slot_exc),
                })
                raw_slot = ""  # degrade gracefully — AI returns empty terms; lands in dd_zero_term
            items.append({
                "idx": i,
                "statement": proposal.statement,
                "requirement_type": proposal.requirement_type,
                "raw_slot": raw_slot,
            })

        prompt = build_dd_extraction_prompt(items)

        # --- AI call ---
        try:
            client = get_ai_client()
            msg = client.messages.create(
                model=MODEL,
                max_tokens=_EXTRACTION_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            fp: dict[str, Any] = {
                "stage": f"stage4_dd_entity_extraction_batch{batch_num}",
                "model": msg.model,
                "input_tokens": msg.usage.input_tokens,
                "output_tokens": msg.usage.output_tokens,
                "batch_size": len(items),
            }
            raw_text = msg.content[0].text if msg.content else ""

            # --- truncation detection (loud hard failure, never silent) ---
            if msg.usage.output_tokens >= _EXTRACTION_MAX_TOKENS:
                _log.warning(
                    "DD extraction batch %d/%d hit token ceiling (%d); "
                    "batch proposals recorded as empty (dd_extraction_batch_truncated)",
                    batch_num, total_batches, _EXTRACTION_MAX_TOKENS,
                )
                pass_data.setdefault("execution_warnings_stage4", []).append({
                    "type": "dd_extraction_batch_truncated",
                    "batch": batch_num,
                    "batch_size": len(items),
                    "output_tokens": msg.usage.output_tokens,
                    "max_tokens": _EXTRACTION_MAX_TOKENS,
                    "detail": "output_tokens == max_tokens; JSON likely truncated; batch proposals → empty",
                })
                fp["token_ceiling_hit"] = True
                fingerprints.append(fp)
                continue  # batch_req_ids already initialised to [] in entity_terms

        except Exception as exc:
            _log.warning(
                "DD extraction batch %d/%d AI call failed: %s — batch proposals → empty",
                batch_num, total_batches, exc,
            )
            pass_data.setdefault("execution_warnings_stage4", []).append({
                "type": "dd_entity_extraction_ai_error",
                "batch": batch_num,
                "error": str(exc),
            })
            fingerprints.append({
                "stage": f"stage4_dd_entity_extraction_batch{batch_num}",
                "model": MODEL,
                "input_tokens": 0,
                "output_tokens": 0,
                "batch_size": len(items),
                "error": str(exc),
            })
            continue

        # --- parse response (idx within batch → batch_req_ids) ---
        batch_terms, batch_sq = _parse_extraction_response(raw_text, batch_req_ids, pass_data)
        for req_id in batch_req_ids:
            entity_terms[req_id] = batch_terms.get(req_id, [])
            state_qualifier_map[req_id] = batch_sq.get(req_id, [])
        fingerprints.append(fp)

    if not any(entity_terms.values()):
        pass_data.setdefault("execution_warnings_stage4", []).append({
            "type": "dd_entity_extraction_all_empty",
            "detail": "AI entity extraction returned no terms for any proposal across all batches",
        })

    return entity_terms, state_qualifier_map, fingerprints


def _parse_extraction_response(
    raw_text: str,
    req_ids: list[str],
    pass_data: dict[str, Any] | None = None,
) -> tuple[dict[str, list[str]], dict[str, list[StateQualifier]]]:
    """
    Parse AI extraction response into a req_id → terms mapping and a
    req_id → state_qualifiers mapping (v0.11 §4.4.3a state-reduction).
    Falls back to empty dicts on parse failure.

    pass_data: if provided, parse failures emit a 'dd_entity_extraction_parse_error'
    execution_warning so the failure is visible in the output record (not only in logs).
    """
    try:
        data = json.loads(_strip_code_fence(raw_text))
        if not isinstance(data, list):
            raise ValueError(f"Expected JSON list, got {type(data).__name__}")
        items = [EntityExtractionItem.model_validate(item) for item in data]
        by_idx: dict[int, list[str]] = {item.idx: item.terms for item in items}
        sq_by_idx: dict[int, list[StateQualifier]] = {
            item.idx: item.state_qualifiers for item in items
        }
        terms_map = {req_ids[i]: by_idx.get(i, []) for i in range(len(req_ids))}
        sq_map = {req_ids[i]: sq_by_idx.get(i, []) for i in range(len(req_ids))}
        return terms_map, sq_map
    except Exception as exc:
        _log.warning(
            "DD entity extraction response parse failed: %s — falling back to empty terms",
            exc,
        )
        if pass_data is not None:
            pass_data.setdefault("execution_warnings_stage4", []).append({
                "type": "dd_entity_extraction_parse_error",
                "error": str(exc),
                "detail": "JSON parse of AI extraction response failed; all proposals → empty terms",
            })
        empty_sq: dict[str, list[StateQualifier]] = {req_id: [] for req_id in req_ids}
        return {req_id: [] for req_id in req_ids}, empty_sq


# ---------------------------------------------------------------------------
# §4.4.3a Step 2 — Build DD ops from extracted terms
# ---------------------------------------------------------------------------

def _check_ver19(term: str, req_id: str) -> dict[str, Any] | None:
    """
    VER-3d-19: entity-grade term heuristic.
    Returns a violation dict or None if the term passes.
    """
    word_count = len(term.split())
    if word_count > _VER19_MAX_WORDS:
        return {
            "requirement_id": req_id,
            "term": term,
            "reason": f"word_count_{word_count}_exceeds_{_VER19_MAX_WORDS}",
        }
    if _VER19_SENTENCE_PUNCT.search(term):
        return {
            "requirement_id": req_id,
            "term": term,
            "reason": "sentence_terminal_punctuation",
        }
    return None


def _build_dd_ops_from_terms(
    proposals: list[TaggedProposal],
    req_ids: list[str],
    entity_terms: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Build DD service resolve ops from AI-extracted entity terms (v0.33 / F107 names-only).

    Post-F107: relationship-record and value-record operations removed.
    Only 'resolve' ops are emitted for all requirement types.
    Called only for the non-cm_structural proposal batch in _run_dd_binding.

    Returns:
      ops                  — list of resolve-op dicts
      zero_term_unresolved — entries where extraction was empty or VER-3d-19 rejected
                             all terms.
    """
    ops: list[dict[str, Any]] = []
    zero_term_unresolved: list[dict[str, Any]] = []

    for proposal, req_id in zip(proposals, req_ids):
        terms = entity_terms.get(req_id, [])
        stmt = proposal.statement

        # VER-3d-19 pre-presentation reject: filter clause-grade terms
        clean_terms: list[str] = []
        for term in terms:
            violation = _check_ver19(term, req_id)
            if violation:
                zero_term_unresolved.append({
                    "requirement_id": req_id,
                    "term": term,
                    "reason": f"ver_3d_19_rejected:{violation['reason']}",
                    "warning_type": "ver_3d_19_term_rejected",
                })
            else:
                clean_terms.append(term)
        terms = clean_terms

        if not terms:
            zero_term_unresolved.append({
                "requirement_id": req_id,
                "term": None,
                "reason": "entity_extraction_empty",
            })
            continue

        for term in terms:
            if len(term) > _MIN_TERM_LEN:
                ops.append({
                    "op": "resolve",
                    "term": term,
                    "context": stmt,
                    "provenance_ref": req_id,
                })

    return ops, zero_term_unresolved


# ---------------------------------------------------------------------------
# §4.4.3a — Top-level DD binding orchestrator
# ---------------------------------------------------------------------------

def _run_dd_binding(
    proposals: list[TaggedProposal],
    req_ids: list[str],
    pass_data: dict[str, Any],
    row_ref: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Execute §4.4.3a DD Object-slot binding (v0.33 / F107 names-only).

    Structural proposals with class_model set — Sub-pass 1:
      Entity name and relationship target names extracted directly from class_model;
      no AI extraction call.  entity_ref is set in-place on class_model after
      successful resolution.

    Other proposals (Functional, Constraint, Structural-without-cm):
      Step 1 — IM entity extraction (AI call, F101 batched).
      Step 2 — DD resolve calls (names-only; relationship/value ops removed F107).

    dd_unresolved   — DD service flagged entries (terms_presented but not resolved).
    dd_zero_term    — proposals where no term was presented to the DD service.
    VER-3d-17:  terms_presented == resolved + len(dd_unresolved)
    VER-3d-23:  three-clause completeness invariant.

    Returns:
      dd_binding   — audit block dict for mechanism_data §4.4.3b
      fingerprints — list of per-batch AI-extraction fingerprint dicts
    """
    # Split: Structural proposals with class_model vs. everything else
    cm_struct_proposals: list[TaggedProposal] = []
    cm_struct_ids: list[str] = []
    other_proposals: list[TaggedProposal] = []
    other_ids: list[str] = []

    for p, rid in zip(proposals, req_ids):
        if p.requirement_type == "Structural" and p.class_model:
            cm_struct_proposals.append(p)
            cm_struct_ids.append(rid)
        else:
            other_proposals.append(p)
            other_ids.append(rid)

    terms_presented: int = 0
    resolved: int = 0
    new_canonical: int = 0
    synonyms_recorded: int = 0
    dd_unresolved: list[dict[str, Any]] = []
    zero_term_entries: list[dict[str, Any]] = []
    reqs_with_terms: set[str] = set()
    fingerprints: list[dict[str, Any]] = []

    # -----------------------------------------------------------------------
    # Sub-pass 1: Structural-with-class_model — resolve names, set entity_ref
    # -----------------------------------------------------------------------
    for proposal, req_id in zip(cm_struct_proposals, cm_struct_ids):
        cm = proposal.class_model  # type: ignore[index]
        entity = (cm.get("entity") or "").strip()
        if not entity or len(entity) <= _MIN_TERM_LEN:
            zero_term_entries.append({
                "requirement_id": req_id,
                "term": None,
                "reason": "class_model_entity_empty_or_trivial",
            })
            continue

        # Resolve primary entity name; set entity_ref on class_model if resolved
        try:
            res = resolve_and_record(entity, proposal.statement, req_id)
            terms_presented += 1
            reqs_with_terms.add(req_id)
            outcome = res.get("outcome", "flagged")
            if outcome == "flagged":
                dd_unresolved.append({
                    "requirement_id": req_id,
                    "term": entity,
                    "reason": "flagged_ambiguous",
                })
            else:
                resolved += 1
                if outcome == "canonical":
                    new_canonical += 1
                elif outcome == "synonym":
                    synonyms_recorded += 1
                dd_id = res.get("dd_id")
                if dd_id:
                    cm["entity_ref"] = dd_id
        except Exception as exc:
            _log.warning("DD resolve failed for entity=%r req=%s: %s", entity, req_id, exc)
            pass_data.setdefault("execution_warnings_stage4", []).append({
                "type": "dd_binding_op_error",
                "term": entity,
                "provenance_ref": req_id,
                "error": str(exc),
            })

        # Resolve relationship target names (names-only; no record_relationship)
        for rel in cm.get("relationships") or []:
            if not isinstance(rel, dict):
                continue
            target = (rel.get("target") or "").strip()
            if not target or len(target) <= _MIN_TERM_LEN:
                continue
            viol = _check_ver19(target, req_id)
            if viol:
                zero_term_entries.append({
                    "requirement_id": req_id,
                    "term": target,
                    "reason": f"ver_3d_19_rejected:{viol['reason']}",
                    "warning_type": "ver_3d_19_term_rejected",
                })
                continue
            try:
                res = resolve_and_record(target, proposal.statement, req_id)
                terms_presented += 1
                reqs_with_terms.add(req_id)
                outcome = res.get("outcome", "flagged")
                if outcome == "flagged":
                    dd_unresolved.append({
                        "requirement_id": req_id,
                        "term": target,
                        "reason": "flagged_ambiguous",
                    })
                else:
                    resolved += 1
                    if outcome == "canonical":
                        new_canonical += 1
                    elif outcome == "synonym":
                        synonyms_recorded += 1
            except Exception as exc:
                _log.warning(
                    "DD resolve failed for rel-target=%r req=%s: %s", target, req_id, exc
                )
                pass_data.setdefault("execution_warnings_stage4", []).append({
                    "type": "dd_binding_op_error",
                    "term": target,
                    "provenance_ref": req_id,
                    "error": str(exc),
                })

    # -----------------------------------------------------------------------
    # Other proposals — AI extraction (F101 batched) + resolve ops
    # -----------------------------------------------------------------------
    if other_proposals:
        entity_terms, _sq_map, ext_fps = _extract_entity_terms_ai(
            other_proposals, other_ids, pass_data, row_ref
        )
        fingerprints.extend(ext_fps)

        ops, other_zero = _build_dd_ops_from_terms(
            other_proposals, other_ids, entity_terms
        )
        zero_term_entries.extend(other_zero)

        for op in ops:
            if op["op"] != "resolve":
                continue
            try:
                terms_presented += 1
                reqs_with_terms.add(op["provenance_ref"])
                op_result = resolve_and_record(
                    op["term"], op["context"], op["provenance_ref"]
                )
                outcome = op_result.get("outcome", "flagged")
                if outcome == "flagged":
                    dd_unresolved.append({
                        "requirement_id": op["provenance_ref"],
                        "term": op["term"],
                        "reason": "flagged_ambiguous",
                    })
                else:
                    resolved += 1
                    if outcome == "canonical":
                        new_canonical += 1
                    elif outcome == "synonym":
                        synonyms_recorded += 1
            except Exception as exc:
                _log.warning(
                    "DD binding op failed for term=%r req=%s: %s",
                    op.get("term", "?"), op.get("provenance_ref", "?"), exc,
                )
                pass_data.setdefault("execution_warnings_stage4", []).append({
                    "type": "dd_binding_op_error",
                    "term": op.get("term", "?"),
                    "provenance_ref": op.get("provenance_ref", "?"),
                    "error": str(exc),
                })

    # --- VER-3d-23: three-clause completeness invariant -----------------------
    zero_term_req_ids: set[str] = {e["requirement_id"] for e in zero_term_entries}
    reqs_accounted: int = len(reqs_with_terms) + len(zero_term_req_ids)
    row_req_count: int = len(req_ids)
    ver23_c1_ok: bool = reqs_accounted == row_req_count
    ver23_c2_ok: bool = terms_presented == resolved + len(dd_unresolved)
    truncation_batches = [
        w for w in pass_data.get("execution_warnings_stage4", [])
        if w.get("type") == "dd_extraction_batch_truncated"
    ]
    ver23_c3_ok: bool = len(truncation_batches) == 0

    if not (ver23_c1_ok and ver23_c2_ok and ver23_c3_ok):
        ver23_detail: dict[str, Any] = {}
        if not ver23_c1_ok:
            ver23_detail["clause1_req_completeness"] = {
                "reqs_with_terms": len(reqs_with_terms),
                "dd_zero_term_unique_reqs": len(zero_term_req_ids),
                "accounted": reqs_accounted,
                "row_req_count": row_req_count,
                "gap": row_req_count - reqs_accounted,
            }
        if not ver23_c2_ok:
            ver23_detail["clause2_term_consistency"] = {
                "terms_presented": terms_presented,
                "resolved": resolved,
                "dd_unresolved_count": len(dd_unresolved),
                "delta": terms_presented - (resolved + len(dd_unresolved)),
            }
        if not ver23_c3_ok:
            ver23_detail["clause3_no_truncation"] = {
                "truncated_batch_count": len(truncation_batches),
            }
        _log.warning("VER-3d-23 failed: %s", ver23_detail)
        pass_data.setdefault("execution_warnings_stage4", []).append({
            "type": "ver_3d_23_fail",
            "detail": ver23_detail,
        })

    audit: dict[str, Any] = {
        "terms_presented": terms_presented,
        "resolved": resolved,
        "new_canonical": new_canonical,
        "synonyms_recorded": synonyms_recorded,
        "dd_unresolved": dd_unresolved,
        "dd_zero_term": zero_term_entries,
    }

    return audit, fingerprints


# ---------------------------------------------------------------------------
# Stage 4 ledger helpers (unchanged from v0.7)
# ---------------------------------------------------------------------------

def _allocate_requirement_ids(
    session: Session, project_id: str, count: int
) -> list[str]:
    """
    Allocate `count` new requirement_ids (R001, R002, …).
    MAX query includes retired Requirements — ids are never reused per spec §4.4.1.
    """
    row = session.execute(
        text(
            "SELECT MAX(CAST(SUBSTRING(requirement_id FROM 2) AS INTEGER)) "
            "FROM requirement WHERE project_id = :pid"
        ),
        {"pid": project_id},
    ).fetchone()
    next_seq = 1 if row[0] is None else row[0] + 1

    if next_seq + count > 800:
        _log.warning(
            "requirement_id ceiling advisory: next_seq=%d count=%d for project=%s — "
            "approaching R999 limit; raise tracker finding for 4-digit extension",
            next_seq, count, project_id,
        )

    return [f"R{str(i).zfill(3)}" for i in range(next_seq, next_seq + count)]


def _query_active_requirements_for_row(
    session: Session, project_id: str, row_ref: int
) -> list[dict[str, Any]]:
    rows = session.execute(
        text(
            "SELECT requirement_id, statement FROM requirement "
            "WHERE project_id = :pid "
            "  AND row_target = :row "
            "  AND retired_at IS NULL"
        ),
        {"pid": project_id, "row": str(row_ref)},
    ).fetchall()
    return [{"requirement_id": r[0], "statement": r[1]} for r in rows]


def _query_all_active_requirement_ids(
    session: Session, project_id: str
) -> list[str]:
    """Project-wide active requirement_ids — no row_target filter."""
    rows = session.execute(
        text(
            "SELECT requirement_id FROM requirement "
            "WHERE project_id = :pid AND retired_at IS NULL"
        ),
        {"pid": project_id},
    ).fetchall()
    return [r[0] for r in rows]


def _check_downstream_rerun_required(
    session: Session, project_id: str, row_ref: int
) -> bool:
    """Check if Phase 5, Phase 6, or Phase 8 AnalysisPasses exist for this row/project."""
    row = session.execute(
        text(
            "SELECT pass_id FROM analysis_pass "
            "WHERE project_id = :pid "
            "  AND mechanism IN ('CellQuality', 'CoverageAnalysis', 'CoverageAnalysis8') "
            "  AND execution_status IN ('Completed', 'CompletedWithWarnings', 'Success', 'PartialSuccess') "
            "  AND outputs->'mechanism_data'->>'row_ref' = :row "
            "LIMIT 1"
        ),
        {"pid": project_id, "row": str(row_ref)},
    ).fetchone()
    return row is not None


def _compute_retirement_mapping(
    prior_active: list[dict[str, Any]],
    new_proposals: list[TaggedProposal],
    new_ids: list[str],
) -> list[dict[str, Any]]:
    """
    For each retiring Requirement, find the new Requirement with highest Jaccard
    statement overlap. Per spec §4.4.4: threshold 0.50.
    """
    mapping = []
    for old in prior_active:
        best_score = 0.0
        best_new_idx = None
        for i, prop in enumerate(new_proposals):
            score = _jaccard_overlap(old["statement"], prop.statement)
            if score > best_score:
                best_score = score
                best_new_idx = i
        inferred_successor = (
            new_ids[best_new_idx]
            if best_new_idx is not None and best_score >= _JACCARD_THRESHOLD
            else None
        )
        mapping.append(
            {
                "old_requirement_id": old["requirement_id"],
                "inferred_successor_requirement_id": inferred_successor,
            }
        )
    return mapping


def _derive_domain_refs(
    proposal: TaggedProposal,
    active_domains: list[ActiveDomain],
) -> list[str]:
    """
    MD-2: DM-derived domain_refs — set of domain_ids whose cell_content_item_refs
    intersect proposal.cci_refs. Never AI-proposed.

    v0.13: For Path R proposals with empty cci_refs but non-empty refines_refs,
    fall back to [source_domain_id] so the proposal passes the MD-2 assert.
    """
    if proposal.cci_refs:
        proposal_ci_ids = set(proposal.cci_refs)
        domain_refs = sorted(
            d.domain_id
            for d in active_domains
            if proposal_ci_ids & set(d.cell_content_item_refs)
        )
        return domain_refs

    if proposal.refines_refs and proposal.source_domain_id:
        active_domain_ids = {d.domain_id for d in active_domains}
        if proposal.source_domain_id in active_domain_ids:
            return [proposal.source_domain_id]
        if active_domains:
            return [active_domains[0].domain_id]

    return []


# ---------------------------------------------------------------------------
# run_stage4 — main entry point
# ---------------------------------------------------------------------------

def run_stage4(
    *,
    stage1: Stage1Result,
    stage2: Stage2Result,
    stage3: Stage3Result,
    project_id: str,
    row_ref: int,
    practitioner_id: str,
    pass_data: dict[str, Any],
    session: Session,
) -> Stage4Result:
    """
    Run Stage 4 entity production and ledger commit.

    pass_data: mutable pass record built by orchestrator (mutated in place).
    Returns Stage4Result.
    """
    result = Stage4Result()
    effective_scenario = stage2.effective_scenario
    proposals = stage3.proposals

    # --- 4.4.5 downstream_rerun_required (check before transaction) ---
    if effective_scenario in ("FullRerun", "IncrementalRerun"):
        result.downstream_rerun_required = _check_downstream_rerun_required(
            session, project_id, row_ref
        )

    # --- 4.4.4 Retirement mapping (BEFORE opening transaction) ---
    prior_active: list[dict[str, Any]] = []
    if effective_scenario == "FullRerun":
        prior_active = _query_active_requirements_for_row(session, project_id, row_ref)
        result.requirement_count_retired = len(prior_active)

    # --- 4.4.2 domain_refs DM-derivation; reject empty (MD-2 fail-closed) ---
    valid_proposals: list[TaggedProposal] = []
    for proposal in proposals:
        domain_refs = _derive_domain_refs(proposal, stage1.active_domains)
        if not domain_refs:
            stage3.validation_failures.append(
                {
                    "check_id": "MD-2",
                    "source_domain_id": proposal.source_domain_id,
                    "detail": "domain_refs derivation empty — proposal excluded",
                }
            )
            _log.warning(
                "MD-2 fail-closed: empty domain_refs for proposal from domain=%s; excluded",
                proposal.source_domain_id,
            )
            continue
        proposal._domain_refs = domain_refs  # type: ignore[attr-defined]
        valid_proposals.append(proposal)

    excluded_count = len(proposals) - len(valid_proposals)
    if excluded_count > 0:
        pass_data.setdefault("execution_warnings_stage4", []).append(
            {"type": "md2_domain_refs_empty_excluded", "count": excluded_count}
        )

    proposals = valid_proposals

    # --- 4.4.1 requirement_id allocation ---
    new_ids = _allocate_requirement_ids(session, project_id, len(proposals))

    # Retirement mapping (now that new_ids are known)
    if effective_scenario == "FullRerun" and prior_active:
        result.retirement_mapping = _compute_retirement_mapping(
            prior_active, proposals, new_ids
        )

    # --- §4.4.3a DD entity extraction (IM, v0.33) — outside the ledger transaction ---
    # The extraction AI call happens before the transaction so that failures
    # do not roll back the ledger write. On extraction failure, empty terms are
    # used and zero_term_unresolved entries are recorded.
    # F107: _run_dd_binding also sets entity_ref on class_model dicts in-place.
    dd_binding, dd_fingerprints = _run_dd_binding(proposals, new_ids, pass_data, row_ref)
    result.ai_model_fingerprints = dd_fingerprints

    # --- §4.4.3a Step 4: Object-refs materialisation (F107 / v0.33) -------
    # Build working set from resolved class_models (entity_ref now set).
    # Materialise behavioural proposals' candidate object_refs paths.
    # Row-1 gate: if no Structural proposals produced class_models in this row
    # (e.g. Row 1 — no Structural requirements), the working set is empty and
    # every path would dangle.  Skip the resolver entirely in that case and
    # record no dangling warnings — the absence of class_models is expected, not
    # an error.
    class_models_by_entity: dict[str, dict] = {}
    for p in proposals:
        if p.class_model and p.class_model.get("entity"):
            class_models_by_entity[p.class_model["entity"]] = p.class_model

    proposal_object_refs: list[list[str]] = []
    for proposal, req_id in zip(proposals, new_ids):
        if proposal.requirement_type not in ("Functional", "Constraint"):
            proposal_object_refs.append([])
            continue
        if not proposal.object_refs:
            proposal_object_refs.append([])
            continue
        if not class_models_by_entity:
            proposal_object_refs.append([])
            continue
        try:
            resolved_paths, dangling = resolve_object_refs(
                proposal.object_refs, class_models_by_entity, req_id
            )
            proposal_object_refs.append(resolved_paths)
            if dangling:
                pass_data.setdefault("execution_warnings_stage4", []).append({
                    "type": "object_refs_dangling",
                    "provenance_ref": req_id,
                    "dangling_count": len(dangling),
                    "dangling": dangling,
                })
        except Exception as exc:
            _log.warning(
                "object_refs materialisation failed for req=%s: %s", req_id, exc
            )
            pass_data.setdefault("execution_warnings_stage4", []).append({
                "type": "object_refs_materialisation_error",
                "provenance_ref": req_id,
                "error": str(exc),
            })
            proposal_object_refs.append([])

    # Build object_refs_binding audit block (§4.4.3b / §7)
    _orb_formed: int = sum(1 for paths in proposal_object_refs if paths)
    _orb_dangling: list[dict[str, Any]] = []
    for w in pass_data.get("execution_warnings_stage4", []):
        if w.get("type") == "object_refs_dangling":
            for d in w.get("dangling", []):
                _orb_dangling.append({
                    "provenance_ref": w.get("provenance_ref"),
                    "path": d.get("path"),
                    "reason": d.get("reason"),
                })
    pass_data.setdefault("mechanism_data_stage4", {})["object_refs_binding"] = {
        "formed": _orb_formed,
        "dangling": _orb_dangling,
    }

    # Refresh the DB pool before the ledger transaction — second guard point.
    # _run_dd_binding's AI extraction batches (F101 v0.25) idle the main session
    # for the duration of the extraction calls (~30 s/batch × N batches); the DD
    # binding service calls open their own sessions internally, so the main
    # session receives no keepalive traffic during that window.  Neon can
    # suspend and tear down the SSL session, causing the subsequent INSERT to
    # fail (observed: R3_Run9, psycopg2.OperationalError SSL connection closed).
    # This mirrors the pre-stage4 refresh in __init__.py but guards the
    # stage4-internal AI window rather than the stage1–3 window.
    session.invalidate()
    refresh_engine_pool()
    session = get_session()

    # --- 4.4.6 Ledger transaction ---
    now = datetime.now(timezone.utc)
    try:
        # Step 1: FullRerun retirement UPDATE
        if effective_scenario == "FullRerun":
            session.execute(
                text(
                    "UPDATE requirement SET retired_at = :now "
                    "WHERE project_id = :pid "
                    "  AND row_target = :row "
                    "  AND retired_at IS NULL"
                ),
                {"now": now, "pid": project_id, "row": str(row_ref)},
            )

        # Step 2: INSERT new Requirement entities (F105 + F107: class_model, object_refs)
        for idx, (proposal, req_id) in enumerate(zip(proposals, new_ids)):
            domain_refs = getattr(proposal, "_domain_refs", [])
            obj_refs = proposal_object_refs[idx] if idx < len(proposal_object_refs) else []
            cm_json: str | None = (
                json.dumps(proposal.class_model) if proposal.class_model else None
            )
            session.execute(
                text(
                    "INSERT INTO requirement "
                    "(requirement_id, project_id, statement, requirement_type, "
                    " row_target, rationale, cci_refs, domain_refs, fit_criteria, "
                    " verification_method, priority, answer_refs, refines_refs, "
                    " confidence, retired_at, created_at, class_model, object_refs) "
                    "VALUES (:rid, :pid, :stmt, :rtype, :row, :rationale, "
                    "        CAST(:cci_refs AS jsonb), CAST(:domain_refs AS jsonb), "
                    "        :fit_criteria, :verification_method, :priority, "
                    "        CAST(:answer_refs AS jsonb), CAST(:refines_refs AS jsonb), "
                    "        :confidence, NULL, :now, "
                    "        CAST(:class_model AS jsonb), CAST(:object_refs AS jsonb))"
                ),
                {
                    "rid": req_id,
                    "pid": project_id,
                    "stmt": proposal.statement,
                    "rtype": proposal.requirement_type,
                    "row": str(row_ref),
                    "rationale": proposal.rationale,
                    "cci_refs": json.dumps(sorted(proposal.cci_refs)),
                    "domain_refs": json.dumps(domain_refs),
                    "fit_criteria": proposal.fit_criteria,
                    "verification_method": proposal.verification_method,
                    "priority": proposal.priority,
                    "answer_refs": json.dumps([]),
                    "refines_refs": json.dumps(sorted(proposal.refines_refs)),
                    "confidence": proposal.confidence,
                    "now": now,
                    "class_model": cm_json,
                    "object_refs": json.dumps(obj_refs),
                },
            )

        # DD binding already run above (pre-transaction); store audit result
        result.dd_binding = dd_binding

        # Step 3: Insert Concern entities for persistent orphans
        for concern_data in stage3.concern_entities:
            seq_val = get_next_sequence_value(session, "cn_id_seq")
            concern_id = format_identifier("CN", seq_val)
            session.add(
                ConcernModel(
                    concern_id=concern_id,
                    source_refs=concern_data["source_refs"],
                    description=concern_data["description"],
                    state="Open",
                    produced_in_row=concern_data["produced_in_row"],
                    practitioner_id=concern_data["practitioner_id"],
                    confidence=1.0,
                    project_id=concern_data["project_id"],
                    created_at=now,
                )
            )

        # Step 4: UPDATE RequirementRegister — project-wide, no row_target filter
        active_ids_rows = session.execute(
            text(
                "SELECT requirement_id FROM requirement "
                "WHERE project_id = :pid AND retired_at IS NULL"
            ),
            {"pid": project_id},
        ).fetchall()
        all_active_ids = sorted(r[0] for r in active_ids_rows)

        update_count = session.execute(
            text(
                "UPDATE register SET member_ids = :mi "
                "WHERE register_type = 'Requirement' AND project_id = :pid"
            ),
            {"mi": json.dumps(all_active_ids), "pid": project_id},
        ).rowcount

        if update_count == 0:
            raise RuntimeError(
                "RequirementRegister not found — migration may not have run"
            )

        session.commit()

    except Exception as exc:
        session.rollback()
        result.status = "failed"
        result.failure_reason = f"Ledger transaction rolled back: {exc}"
        return result

    # --- CHK-3d-12: Concept-coverage check (F107 / v0.33, soft advisory) -----
    # Row-level check: every prior-row entity should be covered by ≥1 current-row
    # class_model with refinement_kind != 'introduce'. Advisory only — does not
    # change execution_status. Result recorded in mechanism_data.
    try:
        current_row_cms = [
            p.class_model
            for p in proposals
            if p.requirement_type == "Structural" and p.class_model
        ]
        coverage = check_concept_coverage(
            project_id=project_id,
            row_ref=row_ref,
            current_row_class_models=current_row_cms,
            session=session,
        )
        pass_data.setdefault("mechanism_data_stage4", {})["chk3d12"] = coverage
        if coverage.get("status") not in ("ok",):
            _log.info(
                "CHK-3d-12 %s: %d uncovered entity(ies) out of %d at row %d",
                coverage.get("status"),
                len(coverage.get("uncovered_entities", [])),
                coverage.get("prior_entity_count", 0),
                row_ref,
            )
            pass_data.setdefault("execution_warnings_stage4", []).append({
                "type": "chk3d12_concept_coverage_gap",
                "status": coverage.get("status"),
                "uncovered_entities": coverage.get("uncovered_entities", []),
                "hard_extinction": coverage.get("hard_extinction", False),
            })
    except Exception as exc:
        _log.warning("CHK-3d-12 failed: %s", exc)

    # Build result summary
    type_dist: dict[str, int] = {
        "Functional": 0,
        "Constraint": 0,
        "Structural": 0,
    }
    reqs_produced = []
    for proposal, req_id in zip(proposals, new_ids):
        type_dist[proposal.requirement_type] = (
            type_dist.get(proposal.requirement_type, 0) + 1
        )
        domain_refs = getattr(proposal, "_domain_refs", [])
        reqs_produced.append(
            {
                "requirement_id": req_id,
                "requirement_type": proposal.requirement_type,
                "cci_ref_count": len(proposal.cci_refs),
                "domain_refs": domain_refs,
            }
        )

    result.requirement_count_produced = len(proposals)
    result.requirement_type_distribution = type_dist
    result.requirements_produced = reqs_produced
    return result
