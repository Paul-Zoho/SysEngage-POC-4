"""
Public API for the Data Dictionary service.

Per Data Dictionary Spec v0.1 §4.

Stateless per call over persistent dictionary state (the ledger).
Not a numbered pass — operations are invoked individually on demand.

Operations:
  resolve_term(surface_term, provenance_ref, context) → ResolutionResult
  record_relationship(from_term, to_term, cardinality, provenance_ref)
  record_value(canonical_term, attr_name, value, provenance_ref)
  resolve_object(term) → dict | None
  aliases_of(canonical_id) → list[str]
  relationships_of(canonical_id) → list[dict]
  reject_synonym(synonym_dd_id) → dict  (false-merge correction)

All database writes commit their own session.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from core.db import get_session
from mechanisms.data_dictionary.audit import append_resolution_log
from mechanisms.data_dictionary.gating import (
    MULTI_CANDIDATE_MARGIN,
    RESOLUTION_CONFIDENCE_BAND,
)
from mechanisms.data_dictionary.rejection import reject_synonym as _reject_synonym
from mechanisms.data_dictionary.resolution import judge as _judge
from sqlalchemy import text

_log = logging.getLogger(__name__)

_DD_ID_RE = re.compile(r"^DD\d{3}$")


# ---------------------------------------------------------------------------
# DD-id allocation
# ---------------------------------------------------------------------------

def _next_dd_id(session) -> str:
    """Allocate the next DD### identifier from the database."""
    max_row = session.execute(
        text("SELECT dd_id FROM data_dictionary_entry ORDER BY dd_id DESC LIMIT 1")
    ).scalar_one_or_none()
    next_num = 1
    if max_row:
        try:
            next_num = int(max_row[2:]) + 1
        except (ValueError, IndexError):
            next_num = 1
    return f"DD{next_num:03d}"


# ---------------------------------------------------------------------------
# Pre-filter (DM) helpers
# ---------------------------------------------------------------------------

def _normalise(term: str) -> str:
    return term.strip().lower()


def _lookup_existing(session, surface_term: str) -> dict | None:
    """
    Pre-filter: check if surface_term already exists as a canonical name or synonym.
    Returns the canonical entry dict or None.
    """
    norm = _normalise(surface_term)

    # Exact canonical name match (case-insensitive)
    canonical = session.execute(
        text("SELECT dd_id, name, description FROM data_dictionary_entry "
             "WHERE entry_kind='canonical' AND lower(name) = :norm AND retired_at IS NULL"),
        {"norm": norm},
    ).mappings().one_or_none()
    if canonical:
        return {"dd_id": canonical["dd_id"], "name": canonical["name"], "status": "existing"}

    # Synonym match
    synonym = session.execute(
        text("SELECT d.dd_id, d.resolves_to, c.name "
             "FROM data_dictionary_entry d "
             "JOIN data_dictionary_entry c ON c.dd_id = d.resolves_to "
             "WHERE d.entry_kind='synonym' AND lower(d.surface_term) = :norm "
             "AND d.retired_at IS NULL AND c.retired_at IS NULL"),
        {"norm": norm},
    ).mappings().one_or_none()
    if synonym:
        return {"dd_id": synonym["resolves_to"], "name": synonym["name"], "status": "existing"}

    return None


def _load_canonical_entries(session) -> list[dict]:
    """Load all active canonical entries with their synonyms."""
    canonicals = session.execute(
        text("SELECT dd_id, name, description FROM data_dictionary_entry "
             "WHERE entry_kind='canonical' AND retired_at IS NULL")
    ).mappings().all()

    results: list[dict] = []
    for c in canonicals:
        synonyms = session.execute(
            text("SELECT surface_term FROM data_dictionary_entry "
                 "WHERE entry_kind='synonym' AND resolves_to = :did AND retired_at IS NULL"),
            {"did": c["dd_id"]},
        ).scalars().all()
        results.append({
            "dd_id": c["dd_id"],
            "name": c["name"],
            "description": c["description"] or "",
            "synonyms": list(synonyms),
        })
    return results


# ---------------------------------------------------------------------------
# Public operations
# ---------------------------------------------------------------------------

def resolve_term(
    surface_term: str,
    provenance_ref: str | None,
    context: str,
) -> dict[str, Any]:
    """
    Resolve surface_term against the Data Dictionary.

    Per §4.1: Pre-filter (DM) → Comparison (IM) → Gate (DM) → Audit (DM).

    Returns
    -------
    dict with keys:
      outcome  : existing | synonym | canonical | flagged
      dd_id    : canonical dd_id (set when outcome ∈ existing|synonym|canonical)
      confidence: float
    """
    session = get_session()
    try:
        # Step 1: Pre-filter (DM)
        existing = _lookup_existing(session, surface_term)
        if existing:
            append_resolution_log(
                session,
                surface_term=surface_term,
                provenance_ref=provenance_ref,
                outcome="existing",
                confidence=1.0,
                competing_refs=None,
                auto_recorded=True,
            )
            session.commit()
            return {"outcome": "existing", "dd_id": existing["dd_id"], "confidence": 1.0}

        # Step 2: IM comparison
        canonical_entries = _load_canonical_entries(session)
        judge_result = _judge(
            surface_term=surface_term,
            context=context,
            canonical_entries=canonical_entries,
        )

        if judge_result.get("_judge_failed"):
            # AI failure → fail-safe to flagged
            append_resolution_log(
                session,
                surface_term=surface_term,
                provenance_ref=provenance_ref,
                outcome="flagged",
                confidence=0.0,
                competing_refs=None,
                auto_recorded=False,
            )
            session.commit()
            return {"outcome": "flagged", "dd_id": None, "confidence": 0.0}

        confidence = float(judge_result.get("confidence", 0.0))
        best_ids: list[str] = judge_result.get("best_canonical_ids", [])
        is_multi = bool(judge_result.get("is_multi_candidate", False))

        # Step 3: Gate (DM)
        if confidence < RESOLUTION_CONFIDENCE_BAND or is_multi:
            # Flag for Practitioner review
            append_resolution_log(
                session,
                surface_term=surface_term,
                provenance_ref=provenance_ref,
                outcome="flagged",
                confidence=confidence,
                competing_refs=best_ids if is_multi else None,
                auto_recorded=False,
            )
            session.commit()
            return {"outcome": "flagged", "dd_id": None, "confidence": confidence}

        if best_ids:
            # Synonym: resolves to existing canonical
            best_id = best_ids[0]
            new_dd_id = _next_dd_id(session)
            session.execute(
                text(
                    "INSERT INTO data_dictionary_entry "
                    "(dd_id, entry_kind, surface_term, resolves_to, provenance_ref, confidence, created_at) "
                    "VALUES (:did, 'synonym', :st, :rt, :pr, :conf, :now)"
                ),
                {
                    "did": new_dd_id,
                    "st": surface_term,
                    "rt": best_id,
                    "pr": provenance_ref,
                    "conf": confidence,
                    "now": datetime.now(timezone.utc),
                },
            )
            append_resolution_log(
                session,
                surface_term=surface_term,
                provenance_ref=provenance_ref,
                outcome="synonym",
                confidence=confidence,
                competing_refs=None,
                auto_recorded=True,
            )
            session.commit()
            return {"outcome": "synonym", "dd_id": best_id, "confidence": confidence}

        else:
            # New canonical
            new_dd_id = _next_dd_id(session)
            session.execute(
                text(
                    "INSERT INTO data_dictionary_entry "
                    "(dd_id, entry_kind, name, description, attributes, provenance_ref, confidence, created_at) "
                    "VALUES (:did, 'canonical', :name, :desc, '[]'::jsonb, :pr, :conf, :now)"
                ),
                {
                    "did": new_dd_id,
                    "name": surface_term,
                    "desc": context[:500] if context else "",
                    "pr": provenance_ref,
                    "conf": confidence,
                    "now": datetime.now(timezone.utc),
                },
            )
            append_resolution_log(
                session,
                surface_term=surface_term,
                provenance_ref=provenance_ref,
                outcome="canonical",
                confidence=confidence,
                competing_refs=None,
                auto_recorded=True,
            )
            session.commit()
            return {"outcome": "canonical", "dd_id": new_dd_id, "confidence": confidence}

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def record_relationship(
    from_term: str,
    to_term: str,
    cardinality: str,
    provenance_ref: str | None,
) -> dict[str, Any]:
    """
    Record a directed relationship between two canonical terms.

    Per §4.4: both endpoints must resolve to canonical entries.
    A flagged endpoint blocks the relationship.
    Reflexive (from == to) permitted with advisory.
    """
    from_res = resolve_term(from_term, provenance_ref, context=f"relationship source: {from_term}")
    to_res = resolve_term(to_term, provenance_ref, context=f"relationship target: {to_term}")

    if from_res["outcome"] == "flagged" or to_res["outcome"] == "flagged":
        return {
            "status": "blocked",
            "reason": "One or both endpoint terms are flagged for Practitioner review",
        }

    from_id = from_res["dd_id"]
    to_id = to_res["dd_id"]

    session = get_session()
    try:
        if from_id == to_id:
            _log.info("record_relationship: reflexive relationship %s → %s (advisory)", from_id, to_id)

        new_dd_id = _next_dd_id(session)
        session.execute(
            text(
                "INSERT INTO data_dictionary_entry "
                "(dd_id, entry_kind, from_ref, to_ref, cardinality, provenance_ref, confidence, created_at) "
                "VALUES (:did, 'relationship', :fr, :tr, :card, :pr, 1.0, :now)"
            ),
            {
                "did": new_dd_id,
                "fr": from_id,
                "tr": to_id,
                "card": cardinality,
                "pr": provenance_ref,
                "now": datetime.now(timezone.utc),
            },
        )
        session.commit()
        return {"status": "recorded", "relationship_id": new_dd_id}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def record_value(
    canonical_term: str,
    attr_name: str,
    value: str,
    provenance_ref: str | None,
) -> dict[str, Any]:
    """
    Record a named-addressable value in an attribute's value_set.

    Per §4.5: resolve canonical_term; ensure attr exists (create if not);
    ensure value is in that attribute's value_set (add if not).
    """
    res = resolve_term(canonical_term, provenance_ref, context=f"attribute record: {canonical_term}")
    if res["outcome"] == "flagged":
        return {"status": "blocked", "reason": "Term flagged for Practitioner review"}

    canonical_id = res["dd_id"]
    session = get_session()
    try:
        entry = session.execute(
            text("SELECT attributes FROM data_dictionary_entry "
                 "WHERE dd_id = :did AND entry_kind = 'canonical'"),
            {"did": canonical_id},
        ).mappings().one_or_none()

        if entry is None:
            raise ValueError(f"Canonical entry {canonical_id!r} not found")

        attrs: list[dict] = list(entry["attributes"] or [])
        attr_entry = next((a for a in attrs if a.get("attr_name") == attr_name), None)
        if attr_entry is None:
            attrs.append({"attr_name": attr_name, "value_set": [value]})
        else:
            vs = attr_entry.get("value_set") or []
            if value not in vs:
                vs.append(value)
            attr_entry["value_set"] = vs

        session.execute(
            text("UPDATE data_dictionary_entry SET attributes = CAST(:attrs AS jsonb) "
                 "WHERE dd_id = :did"),
            {"attrs": json.dumps(attrs), "did": canonical_id},
        )
        session.commit()
        return {"status": "recorded", "dd_id": canonical_id, "attr_name": attr_name, "value": value}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def resolve_object(term: str) -> dict[str, Any] | None:
    """
    Resolve an Object/entity term to its canonical DD entry (read-only).

    Returns dict with {dd_id, name, status} or None if not resolvable.
    status = existing|synonym|canonical|flagged (mirrors resolve_term outcomes).
    """
    session = get_session()
    try:
        existing = _lookup_existing(session, term)
        if existing:
            return {"dd_id": existing["dd_id"], "name": existing["name"], "status": "existing"}
        return None
    finally:
        session.close()


def aliases_of(canonical_id: str) -> list[str]:
    """
    Return all surface_terms (synonyms) that resolve to canonical_id.
    Per §4.7: aliases are a query, not a field read (D-dd-4 decision).
    """
    session = get_session()
    try:
        rows = session.execute(
            text("SELECT surface_term FROM data_dictionary_entry "
                 "WHERE entry_kind='synonym' AND resolves_to = :did AND retired_at IS NULL"),
            {"did": canonical_id},
        ).scalars().all()
        return list(rows)
    finally:
        session.close()


def relationships_of(canonical_id: str) -> list[dict]:
    """
    Return all directed relationships involving canonical_id (from or to).
    Per §4.7.
    """
    session = get_session()
    try:
        rows = session.execute(
            text(
                "SELECT dd_id, from_ref, to_ref, cardinality "
                "FROM data_dictionary_entry "
                "WHERE entry_kind='relationship' AND retired_at IS NULL "
                "AND (from_ref = :did OR to_ref = :did)"
            ),
            {"did": canonical_id},
        ).mappings().all()
        result: list[dict] = []
        for r in rows:
            other_id = r["to_ref"] if r["from_ref"] == canonical_id else r["from_ref"]
            direction = "outgoing" if r["from_ref"] == canonical_id else "incoming"
            result.append({
                "relationship_id": r["dd_id"],
                "other_id": other_id,
                "cardinality": r["cardinality"],
                "direction": direction,
            })
        return result
    finally:
        session.close()


def reject_synonym(
    synonym_dd_id: str,
    project_id: str = "",
) -> dict[str, Any]:
    """
    False-merge correction: reject a synonym entry.
    Per §4.6: promotes surface_term to canonical, retires synonym, queues re-resolution.
    """
    session = get_session()
    try:
        result = _reject_synonym(session, synonym_dd_id=synonym_dd_id, project_id=project_id)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
