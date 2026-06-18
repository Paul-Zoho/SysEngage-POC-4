"""
class_model_projection — deterministic prose statement projector (F105 / v0.33).

Per Requirement Derivation Mechanism Spec v0.33 §4.4.3c:

  Renders a normative prose statement from a class_model dict.
  Used in Stage 4 §4.4.3c when a Structural proposal has class_model set
  but statement is None or blank.

  The projection is deterministic — the same class_model always produces the
  same statement string.  It is stored in requirement.statement so that all
  downstream consumers see a non-null, non-empty value.

  Projection format:
    "The <Entity> <tier-label> entity <verb>: attributes: <attr-list>
     [; relationships to: <rel-list>]."

  Tier labels:
    2 → conceptual
    3 → logical
    4 → physical
    5 → deployment
"""

from __future__ import annotations

from typing import Any

_TIER_LABELS: dict[int, str] = {
    2: "conceptual",
    3: "logical",
    4: "physical",
    5: "deployment",
}

_VERB_BY_KIND: dict[str, str] = {
    "identity": "shall define",
    "decompose": "shall decompose into",
    "realise_relationship": "shall realise the relationship",
    "introduce": "shall introduce",
    "merge": "shall merge",
}

_ORIGIN_ABBREV: dict[str, str] = {
    "refines": "ref",
    "realises": "real",
    "introduced": "new",
}


def _attr_descriptor(attr: dict[str, Any]) -> str:
    name = str(attr.get("name", "?")).strip()
    parts: list[str] = [name]

    key = attr.get("key")
    if key:
        parts.append(f"[{key}]")

    if attr.get("physical_type"):
        parts.append(str(attr["physical_type"]))
    elif attr.get("logical_type"):
        parts.append(str(attr["logical_type"]))
    elif attr.get("semantic_type"):
        parts.append(str(attr["semantic_type"]))

    if attr.get("key") == "FK" and attr.get("target_ref"):
        parts.append(f"→{attr['target_ref']}")

    null_ok = attr.get("null_allowed")
    if null_ok is not None:
        parts.append("NULL" if null_ok else "NOT NULL")

    origin = attr.get("origin", "")
    if origin in _ORIGIN_ABBREV:
        parts.append(f"({_ORIGIN_ABBREV[origin]})")

    return " ".join(parts)


def _rel_descriptor(rel: dict[str, Any]) -> str:
    target = str(rel.get("target", "?")).strip()
    card = rel.get("cardinality", "")
    label = rel.get("label", "")
    parts: list[str] = [target]
    if card:
        parts.append(f"({card})")
    if label:
        parts.append(f'"{label}"')
    return " ".join(parts)


def project_class_model(cm: dict[str, Any]) -> str:
    """
    Return a normative prose statement projected from a class_model dict.

    Raises ValueError if entity or tier is missing/invalid.
    """
    entity = str(cm.get("entity", "")).strip()
    if not entity:
        raise ValueError("class_model.entity is required for projection")

    tier = cm.get("tier")
    tier_label = _TIER_LABELS.get(tier, f"tier-{tier}")  # type: ignore[arg-type]

    rk = str(cm.get("refinement_kind", "identity"))
    verb = _VERB_BY_KIND.get(rk, "shall define")

    attrs: list[dict[str, Any]] = [
        a for a in cm.get("attributes", []) if isinstance(a, dict)
    ]
    rels: list[dict[str, Any]] = [
        r for r in cm.get("relationships", []) if isinstance(r, dict)
    ]

    attr_str = ""
    if attrs:
        attr_str = "attributes: " + ", ".join(_attr_descriptor(a) for a in attrs)

    rel_str = ""
    if rels:
        rel_str = "relationships to: " + ", ".join(_rel_descriptor(r) for r in rels)

    body_parts = [p for p in [attr_str, rel_str] if p]
    body = "; ".join(body_parts) if body_parts else "(no attributes defined)"

    return f"The {entity} {tier_label} entity {verb}: {body}."
