"""
Ledger Export — Canonical JSON Builder.

Builds a spec-v2.17-conformant canonical JSON ledger dict from ProjectData.
Applies:
  - Non-canonical attribute stripping (project_id, created_at, phase_id, etc.)
  - execution_status normalisation (DB values → canonical enum)
  - Deterministic element ordering (per Appendix B.2)
  - Register construction for all element types present
  - content_hash computation (SHA-256 over canonicalised payload)
  - row_target derivation from live element data
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from mechanisms.ledger_export.db_reader import ProjectData

SPEC_VERSION = "2.17"
SCHEMA_ID = "sysengage.ledger.instance.v2_17"
GENERATOR_NAME = "sysengage-ledger-export"
GENERATOR_VERSION = "1.0"

_ELEMENT_TYPE_ORDER: list[str] = [
    "Source",
    "Register",
    "SourceRegister",
    "AnalysisPass",
    "Gap",
    "GapRegister",
    "ZachmanCell",
    "ZachmanCellRegister",
    "CellContentItem",
    "CellContentItemRegister",
    "Domain",
    "DomainRegister",
    "Requirement",
    "RequirementRegister",
    "DataDictionaryEntry",
    "DataDictionaryRegister",
    "Question",
    "QuestionRegister",
    "Answer",
    "AnswerRegister",
    "Suggestion",
    "SuggestionRegister",
    "CoverageItem",
    "CoverageRegister",
    "Segment",
    "SegmentRegister",
    "SourceAtom",
    "SourceAtomRegister",
    "Signal",
    "SignalRegister",
    "Risk",
    "RiskRegister",
    "Stakeholder",
    "StakeholderRegister",
    "Concern",
    "ConcernRegister",
]

_TYPE_RANK: dict[str, int] = {t: i for i, t in enumerate(_ELEMENT_TYPE_ORDER)}

_EXECUTION_STATUS_MAP: dict[str, str] = {
    "Success": "Success",
    "Completed": "Success",
    "PartialSuccess": "PartialSuccess",
    "CompletedWithWarnings": "PartialSuccess",
    "Failed": "Failed",
    "Aborted": "Failed",
}


def _map_execution_status(raw: str) -> str:
    return _EXECUTION_STATUS_MAP.get(raw, "Success")


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _sort_list(lst: list[str]) -> list[str]:
    return sorted(lst)


def _build_source_element(src) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_id": src.source_id,
        "source_text": src.source_text,
        "segmentation_context": src.segmentation_context,
        "input_material_ref": src.input_material_ref,
        "confidence": src.confidence,
    }
    if src.parent_source_ref is not None:
        payload["parent_source_ref"] = src.parent_source_ref
    return {"element_type": "Source", "element_id": src.source_id, "payload": payload}


def _build_segment_element(seg) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "segment_id": seg.segment_id,
        "title": seg.title,
        "source_refs": _sort_list(list(seg.source_refs or [])),
        "confidence": seg.confidence,
    }
    if seg.description is not None:
        payload["description"] = seg.description
    if seg.parent_segment_ref is not None:
        payload["parent_segment_ref"] = seg.parent_segment_ref
    return {
        "element_type": "Segment",
        "element_id": seg.segment_id,
        "payload": payload,
    }


def _build_source_atom_element(atom) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "atom_id": atom.atom_id,
        "atom_text": atom.atom_text,
        "source_ref": atom.source_ref,
        "confidence": atom.confidence,
    }
    if atom.segment_ref is not None:
        payload["segment_ref"] = atom.segment_ref
    if atom.parent_atom_ref is not None:
        payload["parent_atom_ref"] = atom.parent_atom_ref
    return {
        "element_type": "SourceAtom",
        "element_id": atom.atom_id,
        "payload": payload,
    }


def _build_signal_element(sig) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "signal_id": sig.signal_id,
        "signal_type": sig.signal_type,
        "row_target": sig.row_target,
        "description": sig.description,
        "source_refs": _sort_list(list(sig.source_refs or [])),
        "confidence": sig.confidence,
    }
    if sig.sourceatom_refs:
        payload["sourceatom_refs"] = _sort_list(list(sig.sourceatom_refs))
    if sig.derived_from_concern_id is not None:
        payload["derived_from_concern_id"] = sig.derived_from_concern_id
    return {
        "element_type": "Signal",
        "element_id": sig.signal_id,
        "payload": payload,
    }


def _build_concern_element(cn) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "concern_id": cn.concern_id,
        "source_refs": _sort_list(list(cn.source_refs or [])),
        "description": cn.description,
        "state": cn.state,
        "produced_in_row": cn.produced_in_row,
        "practitioner_id": cn.practitioner_id,
        "confidence": cn.confidence,
    }
    if cn.dispositioned_with_outcome is not None:
        payload["dispositioned_with_outcome"] = cn.dispositioned_with_outcome
    if cn.disposition_rationale is not None:
        payload["disposition_rationale"] = cn.disposition_rationale
    return {
        "element_type": "Concern",
        "element_id": cn.concern_id,
        "payload": payload,
    }


def _build_analysis_pass_element(ap) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "pass_id": ap.pass_id,
        "pass_type": ap.pass_type,
        "mechanism": ap.mechanism,
        "evaluated_scope": ap.evaluated_scope,
        "execution_status": _map_execution_status(ap.execution_status),
        "mode_active": ap.mode_active,
        "declared_transformation_modes": list(ap.declared_transformation_modes or []),
        "outputs": ap.outputs or {},
        "pass_started_at": _iso(ap.pass_started_at),
        "confidence": ap.confidence,
    }
    completed = _iso(ap.pass_completed_at)
    if completed is not None:
        payload["pass_completed_at"] = completed
    if ap.elapsed_ms is not None:
        payload["elapsed_ms"] = ap.elapsed_ms
    return {
        "element_type": "AnalysisPass",
        "element_id": ap.pass_id,
        "payload": payload,
    }


def _build_stakeholder_element(sh) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "stakeholder_id": sh.stakeholder_id,
        "name": sh.name,
    }
    if hasattr(sh, "stakeholder_type") and sh.stakeholder_type:
        payload["role"] = sh.stakeholder_type
    if sh.stakeholder_id == "SH001":
        payload["stakeholder_kind"] = "Automated"
    return {
        "element_type": "Stakeholder",
        "element_id": sh.stakeholder_id,
        "payload": payload,
    }


def _build_domain_element(dom) -> dict[str, Any]:
    cci_refs = _sort_list(list(dom.cell_content_item_refs or []))
    payload: dict[str, Any] = {
        "domain_id": dom.domain_id,
        "name": dom.name,
        "description": dom.description,
        "row_target": dom.row_target,
        "cell_content_item_refs": cci_refs,
    }
    if dom.classification_type is not None:
        payload["classification_type"] = dom.classification_type
    return {
        "element_type": "Domain",
        "element_id": dom.domain_id,
        "payload": payload,
    }


def _build_requirement_element(req) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "requirement_id": req.requirement_id,
        "statement": req.statement,
        "requirement_type": req.requirement_type,
        "row_target": req.row_target,
        "confidence": req.confidence,
        "cci_refs": req.cci_refs,
        "domain_refs": req.domain_refs,
        "answer_refs": req.answer_refs if req.answer_refs else [],
        "refines_refs": list(req.refines_refs) if req.refines_refs else [],
        "object_refs": list(req.object_refs) if req.object_refs else [],
    }
    if req.class_model is not None:
        payload["class_model"] = req.class_model
    if req.rationale:
        payload["rationale"] = req.rationale
    if req.fit_criteria:
        payload["fit_criteria"] = req.fit_criteria
    if req.verification_method:
        payload["verification_method"] = req.verification_method
    if req.priority:
        payload["priority"] = req.priority
    if req.retired_at:
        payload["retired_at"] = req.retired_at.isoformat()
    return {
        "element_type": "Requirement",
        "element_id": req.requirement_id,
        "payload": payload,
    }


def _build_data_dictionary_element(entry: dict[str, Any]) -> dict[str, Any]:
    """Build a DataDictionaryEntry element from a raw DB row dict."""
    kind = entry["entry_kind"]
    payload: dict[str, Any] = {
        "dd_id": entry["dd_id"],
        "entry_kind": kind,
        "provenance_ref": entry.get("provenance_ref"),
        "confidence": entry.get("confidence", 1.0),
    }
    if kind == "canonical":
        payload["name"] = entry.get("name")
        payload["description"] = entry.get("description") or ""
    elif kind == "synonym":
        payload["surface_term"] = entry.get("surface_term")
        payload["resolves_to"] = entry.get("resolves_to")
    elif kind == "relationship":
        payload["from_ref"] = entry.get("from_ref")
        payload["to_ref"] = entry.get("to_ref")
        payload["cardinality"] = entry.get("cardinality")
    return {
        "element_type": "DataDictionaryEntry",
        "element_id": entry["dd_id"],
        "payload": payload,
    }


def _build_zachman_cell_element(cell) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "cell_id": cell.cell_id,
        "row_target": cell.row_target,
        "column": cell.column,
        "confidence": 1.0,
    }
    return {
        "element_type": "ZachmanCell",
        "element_id": cell.cell_id,
        "payload": payload,
    }


def _build_cci_element(cci) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ci_id": cci.ci_id,
        "cell_id": cci.cell_id,
        "classification_type": cci.classification_type,
        "signal_refs": _sort_list(list(cci.signal_refs or [])),
        "description": cci.description,
        "confidence": cci.confidence,
    }
    if cci.trigger_condition is not None:
        payload["trigger_condition"] = cci.trigger_condition
    if cci.justification is not None:
        payload["justification"] = cci.justification
    return {
        "element_type": "CellContentItem",
        "element_id": cci.ci_id,
        "payload": payload,
    }


def _build_register(
    register_id: str,
    register_type: str,
    member_ids: list[str],
    completeness_rule: str,
    confidence: float = 1.0,
) -> dict[str, Any]:
    return {
        "element_type": register_type + "Register" if not register_type.endswith("Register") else register_type,
        "element_id": register_id,
        "payload": {
            "register_id": register_id,
            "register_type": register_type,
            "member_ids": _sort_list(member_ids),
            "completeness_rule": completeness_rule,
            "confidence": confidence,
        },
    }


def _derive_row_target(data: ProjectData) -> list[str] | str:
    rows: set[str] = set()
    for sig in data.signals:
        rows.add(sig.row_target)
    for cn in data.concerns:
        rows.add(cn.produced_in_row)
    for req in data.requirements:
        rows.add(req.row_target)
    for dom in data.domains:
        rows.add(dom.row_target)
    if not rows:
        return "1"
    sorted_rows = sorted(rows)
    return sorted_rows[0] if len(sorted_rows) == 1 else sorted_rows


def _sort_elements(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(e: dict[str, Any]) -> tuple[int, str]:
        etype = e["element_type"]
        rank = _TYPE_RANK.get(etype, 999)
        return (rank, e["element_id"])

    return sorted(elements, key=sort_key)


def _compute_content_hash(ledger_without_hash: dict[str, Any]) -> str:
    """Compute SHA-256 over the canonicalised ledger payload (Appendix B.5)."""
    serialised = json.dumps(
        ledger_without_hash,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    serialised = serialised.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in serialised.split("\n")]
    canonical_bytes = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def build_canonical_ledger(data: ProjectData) -> dict[str, Any]:
    """
    Build the canonical v2.15 ledger dict from *data*.

    Returns a dict that can be serialised to JSON with json.dumps().
    Non-canonical DB columns (project_id, created_at, phase_id, etc.) are
    stripped; execution_status is normalised to the canonical enum.
    """
    elements: list[dict[str, Any]] = []

    for src in data.sources:
        elements.append(_build_source_element(src))

    for seg in data.segments:
        elements.append(_build_segment_element(seg))

    for atom in data.source_atoms:
        elements.append(_build_source_atom_element(atom))

    for sig in data.signals:
        elements.append(_build_signal_element(sig))

    for cn in data.concerns:
        elements.append(_build_concern_element(cn))

    for ap in data.analysis_passes:
        elements.append(_build_analysis_pass_element(ap))

    for sh in data.stakeholders:
        elements.append(_build_stakeholder_element(sh))

    for dom in data.domains:
        elements.append(_build_domain_element(dom))

    for req in data.requirements:
        elements.append(_build_requirement_element(req))

    for dd_entry in data.data_dictionary_entries:
        elements.append(_build_data_dictionary_element(dd_entry))

    for cell in data.zachman_cells:
        elements.append(_build_zachman_cell_element(cell))

    for cci in data.ccis:
        elements.append(_build_cci_element(cci))

    source_ids = [src.source_id for src in data.sources]
    source_register = _build_register(
        "SOURCE_REG001",
        "Source",
        source_ids,
        "This register SHALL contain the identifiers of ALL Source elements present in the ledger.",
    )
    elements.append(source_register)

    signal_ids = [sig.signal_id for sig in data.signals]
    signal_register = _build_register(
        "SIGNAL_REG001",
        "Signal",
        signal_ids,
        "This register SHALL contain the identifiers of ALL Signal elements present in the ledger.",
    )
    elements.append(signal_register)

    stakeholder_ids = [sh.stakeholder_id for sh in data.stakeholders]
    stakeholder_register = _build_register(
        "STAKEHOLDER_REG001",
        "Stakeholder",
        stakeholder_ids,
        "This register SHALL contain the identifiers of ALL Stakeholder elements present in the ledger.",
    )
    elements.append(stakeholder_register)

    if data.segments:
        seg_ids = [seg.segment_id for seg in data.segments]
        seg_register = _build_register(
            "SEGMENT_REG001",
            "Segment",
            seg_ids,
            "This register SHALL contain the identifiers of ALL Segment elements present in the ledger.",
        )
        elements.append(seg_register)

    if data.source_atoms:
        atom_ids = [atom.atom_id for atom in data.source_atoms]
        atom_register = _build_register(
            "SOURCEATOM_REG001",
            "SourceAtom",
            atom_ids,
            "This register SHALL contain the identifiers of ALL SourceAtom elements present in the ledger.",
        )
        elements.append(atom_register)

    if data.concerns:
        concern_ids = [cn.concern_id for cn in data.concerns]
        concern_register = _build_register(
            "CONCERN_REG001",
            "Concern",
            concern_ids,
            "This register SHALL contain the identifiers of ALL Concern elements present in the ledger.",
        )
        elements.append(concern_register)

    if data.domains:
        domain_ids = [dom.domain_id for dom in data.domains]
        domain_register = _build_register(
            "DOMAIN_REG001",
            "Domain",
            domain_ids,
            "This register SHALL contain the identifiers of ALL Domain elements present in the ledger.",
        )
        elements.append(domain_register)

    if data.requirements:
        req_ids = [req.requirement_id for req in data.requirements]
        req_register = _build_register(
            "REQUIREMENT_REG001",
            "Requirement",
            req_ids,
            "This register SHALL contain the identifiers of ALL Requirement elements present in the ledger.",
        )
        elements.append(req_register)

    if data.data_dictionary_entries:
        dd_ids = [e["dd_id"] for e in data.data_dictionary_entries]
        dd_register = _build_register(
            "DD_REG001",
            "DataDictionary",
            dd_ids,
            "This register SHALL contain the identifiers of ALL DataDictionaryEntry elements present in the ledger.",
        )
        elements.append(dd_register)

    if data.zachman_cells:
        cell_ids = [cell.cell_id for cell in data.zachman_cells]
        cell_register = _build_register(
            "ZACHMANCELL_REG001",
            "ZachmanCell",
            cell_ids,
            "This register SHALL contain the identifiers of ALL ZachmanCell elements present in the ledger.",
        )
        elements.append(cell_register)

    if data.ccis:
        cci_ids = [cci.ci_id for cci in data.ccis]
        cci_register = _build_register(
            "CELLCONTENTITEM_REG001",
            "CellContentItem",
            cci_ids,
            "This register SHALL contain the identifiers of ALL CellContentItem elements present in the ledger.",
        )
        elements.append(cci_register)

    elements = _sort_elements(elements)

    register_index = sorted(
        [
            {
                "register_type": e["element_type"],
                "register_id": e["element_id"],
            }
            for e in elements
            if e["element_type"].endswith("Register")
        ],
        key=lambda r: (r["register_type"], r["register_id"]),
    )

    row_target = _derive_row_target(data)

    ledger: dict[str, Any] = {
        "sysengage_ledger_version": SPEC_VERSION,
        "schema_id": SCHEMA_ID,
        "row_target": row_target,
        "run_id": str(uuid.uuid4()),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "generator": {
            "name": GENERATOR_NAME,
            "version": GENERATOR_VERSION,
        },
        "elements": elements,
        "register_index": register_index,
    }

    content_hash = _compute_content_hash(ledger)
    ledger["content_hash"] = {
        "hash_alg": "sha256",
        "hash": content_hash,
    }

    return ledger


def ledger_to_json_str(ledger: dict[str, Any], indent: int = 2) -> str:
    """Serialise a canonical ledger dict to a UTF-8 JSON string (LF newlines)."""
    raw = json.dumps(ledger, ensure_ascii=False, indent=indent)
    return raw.replace("\r\n", "\n").replace("\r", "\n")
