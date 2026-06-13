"""
Stage 4 — Entity Production and Ledger Commit (DM + IM for §4.4.3a).

Per Requirement Derivation Mechanism Spec v0.20 §4.4:
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
from core.db import format_identifier, get_next_sequence_value
from core.slots import extract_slot_terms
from mechanisms.data_dictionary.service import (
    record_relationship,
    record_value,
    resolve_and_record,
)
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
# §4.4.3a Step 1 — IM entity extraction (v0.11)
# ---------------------------------------------------------------------------

def _extract_entity_terms_ai(
    proposals: list[TaggedProposal],
    req_ids: list[str],
    pass_data: dict[str, Any],
    row_ref: int,
) -> tuple[dict[str, list[str]], dict[str, list[StateQualifier]], list[dict[str, Any]]]:
    """
    Batch IM entity extraction for §4.4.3a Step 1 (v0.11).

    Replaces the v0.7 verbatim DM slot copy. One AI call for all surviving
    proposals; the model reduces each Object/Entity/Subject slot to its
    bare entity-grade noun head(s) and returns any lifecycle state qualifiers
    for attribute recording (v0.11 state-reduction rule).

    Returns:
      entity_terms       — dict mapping req_id → list of bare entity-grade term strings
      state_qualifier_map — dict mapping req_id → list of StateQualifier (entity, state)
      fingerprints       — list containing one fingerprint dict (stage4_dd_entity_extraction)

    On AI or parse failure, falls back to empty terms for all proposals and
    logs a warning; does not abort the run.
    """
    items = []
    for i, (proposal, req_id) in enumerate(zip(proposals, req_ids)):
        slots = extract_slot_terms(proposal.statement, proposal.requirement_type)
        raw_slot = _raw_slot_description(slots, proposal.requirement_type)
        items.append({
            "idx": i,
            "statement": proposal.statement,
            "requirement_type": proposal.requirement_type,
            "raw_slot": raw_slot,
        })

    prompt = build_dd_extraction_prompt(items)

    try:
        client = get_ai_client()
        msg = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        fingerprint = {
            "stage": "stage4_dd_entity_extraction",
            "model": msg.model,
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens,
        }
        raw_text = msg.content[0].text if msg.content else ""
    except Exception as exc:
        _log.warning("DD entity extraction AI call failed: %s — using empty terms", exc)
        pass_data.setdefault("execution_warnings_stage4", []).append({
            "type": "dd_entity_extraction_ai_error",
            "error": str(exc),
        })
        fingerprint = {
            "stage": "stage4_dd_entity_extraction",
            "model": MODEL,
            "input_tokens": 0,
            "output_tokens": 0,
            "error": str(exc),
        }
        return {req_id: [] for req_id in req_ids}, {req_id: [] for req_id in req_ids}, [fingerprint]

    entity_terms, state_qualifier_map = _parse_extraction_response(raw_text, req_ids)
    if not any(entity_terms.values()):
        pass_data.setdefault("execution_warnings_stage4", []).append({
            "type": "dd_entity_extraction_all_empty",
            "detail": "AI entity extraction returned no terms for any proposal",
        })

    return entity_terms, state_qualifier_map, [fingerprint]


def _parse_extraction_response(
    raw_text: str,
    req_ids: list[str],
) -> tuple[dict[str, list[str]], dict[str, list[StateQualifier]]]:
    """
    Parse AI extraction response into a req_id → terms mapping and a
    req_id → state_qualifiers mapping (v0.11 §4.4.3a state-reduction).
    Falls back to empty dicts on parse failure.
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
    state_qualifier_map: dict[str, list[StateQualifier]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Build DD service operation list from AI-extracted entity terms (v0.8 / F99 v0.24).

    Returns:
      ops                  — list of DD service op dicts
      zero_term_unresolved — dd_zero_term entries: extraction-empty OR VER-3d-19
                             pre-presentation rejects (F99 v0.24).
                             Distinguished by reason prefix:
                               "entity_extraction_empty" — no terms from AI
                               "ver_3d_19_rejected:<reason>" — clause-grade term
                             Entries also carry warning_type="ver_3d_19_term_rejected"
                             for the VER-3d-19 rejects.

    VER-3d-19 (F99 v0.24): promoted from post-commit warn to enforcing pre-presentation
    reject. Clause-grade terms (exceeds word-count heuristic or sentence punctuation)
    are skipped here — they never reach the DD service. The standalone _check_ver19
    predicate is unchanged; this is a routing change.
    """
    ops: list[dict[str, Any]] = []
    zero_term_unresolved: list[dict[str, Any]] = []

    for proposal, req_id in zip(proposals, req_ids):
        rtype = proposal.requirement_type
        terms = entity_terms.get(req_id, [])
        stmt = proposal.statement

        # VER-3d-19 pre-presentation reject (F99 v0.24): filter clause-grade terms
        # before building ops. Rejected terms → dd_zero_term; NOT presented to DD.
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

        if rtype in ("Functional", "Structural"):
            if not terms:
                # Zero-term for a type that should have an entity
                zero_term_unresolved.append({
                    "requirement_id": req_id,
                    "term": None,
                    "reason": "entity_extraction_empty",
                })
                continue

            if rtype == "Structural":
                # Check if statement asserts a relationship (DM slot parse for
                # is_relationship flag only — not for the terms themselves)
                slots = extract_slot_terms(stmt, rtype)
                is_rel = slots.get("is_relationship", False)
                if is_rel and len(terms) >= 2:
                    ops.append({
                        "op": "relationship",
                        "from_term": terms[0],
                        "to_term": terms[1],
                        "cardinality": "unspecified",
                        "provenance_ref": req_id,
                    })
                    for term in terms[2:]:
                        if len(term) > _MIN_TERM_LEN:
                            ops.append({
                                "op": "resolve",
                                "term": term,
                                "context": stmt,
                                "provenance_ref": req_id,
                            })
                else:
                    for term in terms:
                        if len(term) > _MIN_TERM_LEN:
                            ops.append({
                                "op": "resolve",
                                "term": term,
                                "context": stmt,
                                "provenance_ref": req_id,
                            })
            else:
                for term in terms:
                    if len(term) > _MIN_TERM_LEN:
                        ops.append({
                            "op": "resolve",
                            "term": term,
                            "context": stmt,
                            "provenance_ref": req_id,
                        })

        elif rtype == "Constraint":
            if not terms:
                # F99 (v0.24): no stmt[:60] fallback — empty Constraint extraction
                # → dd_zero_term; no DD term presented. Non-Loss preserved by the
                # produced Requirement; the DD simply gains no entry.
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
            # Named value from fit_criteria; terms is guaranteed non-empty here.
            if proposal.fit_criteria and proposal.fit_criteria.strip():
                ops.append({
                    "op": "value",
                    "canonical_term": terms[0],
                    "attr_name": "constraint_value",
                    "value": proposal.fit_criteria.strip(),
                    "provenance_ref": req_id,
                })

    # State qualifier recording (v0.11 §4.4.3a): lifecycle states recorded as entity
    # attribute values on the DD entry — one record_value() call per qualifier.
    if state_qualifier_map:
        for req_id in req_ids:
            for qualifier in state_qualifier_map.get(req_id, []):
                if qualifier.entity and qualifier.state:
                    ops.append({
                        "op": "value",
                        "canonical_term": qualifier.entity,
                        "attr_name": "lifecycle_state",
                        "value": qualifier.state,
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
    Execute §4.4.3a DD Object-slot binding (v0.8):
      Step 1 — IM entity extraction (AI call).
      Step 2 — DD service calls (resolve / relationship / value).
      Step 3 — bind / flag.

    dd_unresolved   — DD service flagged entries (terms_presented but not resolved);
                      counted in VER-3d-17 accounting.
    dd_zero_term    — Functional/Structural proposals where entity extraction returned
                      no terms; NOT counted in terms_presented (no resolve op was made).
    VER-3d-17:  terms_presented == resolved + len(dd_unresolved)  ← excludes dd_zero_term.
    VER-3d-19:  entity-grade heuristic violations logged in ver_3d_19_violations.

    Returns:
      dd_binding   — audit block dict for mechanism_data §4.4.3b
      fingerprints — list containing the stage4_dd_entity_extraction fingerprint
    """
    # Step 1: IM entity extraction
    entity_terms, state_qualifier_map, fingerprints = _extract_entity_terms_ai(
        proposals, req_ids, pass_data, row_ref
    )

    # Step 2: Build ops from AI-extracted entity terms (VER-3d-19 reject is inside)
    ops, zero_term_entries = _build_dd_ops_from_terms(
        proposals, req_ids, entity_terms, state_qualifier_map
    )

    terms_presented: int = 0
    resolved: int = 0
    new_canonical: int = 0
    synonyms_recorded: int = 0
    relationships_recorded: int = 0
    values_recorded: int = 0
    # dd_unresolved: DD service flagged entries only (VER-3d-17 scope)
    dd_unresolved: list[dict[str, Any]] = []

    for op in ops:
        try:
            if op["op"] == "resolve":
                terms_presented += 1
                result = resolve_and_record(op["term"], op["context"], op["provenance_ref"])
                outcome = result.get("outcome", "flagged")
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

            elif op["op"] == "relationship":
                rel_result = record_relationship(
                    op["from_term"],
                    op["to_term"],
                    op["cardinality"],
                    op["provenance_ref"],
                )
                if rel_result.get("status") == "recorded":
                    relationships_recorded += 1

            elif op["op"] == "value":
                val_result = record_value(
                    op["canonical_term"],
                    op["attr_name"],
                    op["value"],
                    op["provenance_ref"],
                )
                if val_result.get("status") == "recorded":
                    values_recorded += 1

        except Exception as exc:
            _log.warning(
                "DD binding op failed for term=%r req=%s: %s",
                op.get("term") or op.get("from_term", "?"),
                op.get("provenance_ref", "?"),
                exc,
            )
            pass_data.setdefault("execution_warnings_stage4", []).append({
                "type": "dd_binding_op_error",
                "term": op.get("term") or op.get("from_term", "?"),
                "provenance_ref": op.get("provenance_ref", "?"),
                "error": str(exc),
            })

    audit: dict[str, Any] = {
        "terms_presented": terms_presented,
        "resolved": resolved,
        "new_canonical": new_canonical,
        "synonyms_recorded": synonyms_recorded,
        "relationships_recorded": relationships_recorded,
        "values_recorded": values_recorded,
        # DD service flagged entries — counted in terms_presented (VER-3d-17 scope)
        "dd_unresolved": dd_unresolved,
        # Zero-term and VER-3d-19 pre-presentation rejects — NOT in terms_presented.
        # Entries with warning_type="ver_3d_19_term_rejected" are the F99 rejects;
        # entries with reason="entity_extraction_empty" are empty-extraction cases.
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

    # --- §4.4.3a DD entity extraction (IM, v0.8) — outside the ledger transaction ---
    # The extraction AI call happens before the transaction so that failures
    # do not roll back the ledger write. On extraction failure, empty terms are
    # used and zero_term_unresolved entries are recorded.
    dd_binding, dd_fingerprints = _run_dd_binding(proposals, new_ids, pass_data, row_ref)
    result.ai_model_fingerprints = dd_fingerprints

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

        # Step 2: INSERT new Requirement entities
        for proposal, req_id in zip(proposals, new_ids):
            domain_refs = getattr(proposal, "_domain_refs", [])
            session.execute(
                text(
                    "INSERT INTO requirement "
                    "(requirement_id, project_id, statement, requirement_type, "
                    " row_target, rationale, cci_refs, domain_refs, fit_criteria, "
                    " verification_method, priority, answer_refs, refines_refs, "
                    " confidence, retired_at, created_at) "
                    "VALUES (:rid, :pid, :stmt, :rtype, :row, :rationale, "
                    "        CAST(:cci_refs AS jsonb), CAST(:domain_refs AS jsonb), "
                    "        :fit_criteria, :verification_method, :priority, "
                    "        CAST(:answer_refs AS jsonb), CAST(:refines_refs AS jsonb), "
                    "        :confidence, NULL, :now)"
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
