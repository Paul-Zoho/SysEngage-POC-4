"""
CHK-3d-11 — Structural class_model validity check.

Per Requirement Derivation Mechanism Spec v0.36 §4.3.

Validates a class_model dict on a Structural proposal after Stage 2.
Returns a list of violation dicts.  Callers must inspect severity:

  "hard"  — the proposal must be excluded from production (similar to
             statement-level hard failures in existing checks).
  "soft"  — advisory; the proposal survives but a warning is recorded.

Hard violations:
  - entity absent or empty
  - tier == 1 (detail: tier1_class_model) — [D] Row 1 authors no class_model
  - tier not in {2,3,4,5} (other invalid tiers)
  - tier does not match row_target
  - refinement_kind not in valid enum
  - no attributes (list is empty)
  - Row 2: no attribute carries semantic_type
  - >1 attribute with key == 'PK'
  - any attribute with blank name
  - any attribute with invalid origin enum
  - any relationship with blank target
  - [C] Row 2 profile violations: key/domain/target_ref forbidden at Row 2
  - [C] Row 2–3 type violation: type value not in logical closed enum

Soft violations:
  - FK attribute missing target_ref (referential check deferred to sub-pass 2)
  - attribute domain list contains blank values
"""

from __future__ import annotations

from typing import Any

_VALID_KINDS = frozenset(
    {"identity", "decompose", "realise_relationship", "introduce", "merge"}
)
_VALID_ORIGINS = frozenset({"refines", "realises", "introduced"})

# [C] Closed logical type enum — valid at Rows 2 and 3.
# A value outside this set at Row 2 or 3 is a profile violation (type_not_logical).
# Rows 4+ allow free-form physical types (VARCHAR(255), etc.).
_LOGICAL_TYPE_ENUM = frozenset(
    {"String", "Integer", "DateTime", "Boolean", "Decimal", "Enum", "Reference", "JSON"}
)


def validate_class_model(
    cm: dict[str, Any], row_ref: int
) -> list[dict[str, Any]]:
    """
    Run CHK-3d-11 structural validity checks (v0.36: adds [C] profile + [D] tier-1).

    Returns list of violation dicts:
        {"check_id": "CHK-3d-11", "detail": str, "severity": "hard"|"soft"}

    Empty list ⟹ no violations.
    """
    violations: list[dict[str, Any]] = []

    def hard(detail: str) -> None:
        violations.append(
            {"check_id": "CHK-3d-11", "detail": detail, "severity": "hard"}
        )

    def soft(detail: str) -> None:
        violations.append(
            {"check_id": "CHK-3d-11", "detail": detail, "severity": "soft"}
        )

    if not isinstance(cm, dict):
        hard("class_model is not a dict")
        return violations

    # --- entity ---
    entity = cm.get("entity", "")
    if not entity or not str(entity).strip():
        hard("entity absent or empty")

    # --- tier ---
    tier = cm.get("tier")
    if tier == 1:
        # [D] Row 1 authors no class_model — specific detail for diagnostics
        hard("tier1_class_model")
    elif tier not in {2, 3, 4, 5}:
        hard(f"tier must be in {{2,3,4,5}}, got {tier!r}")
    elif int(tier) != int(row_ref):
        hard(f"tier {tier} does not match row_target {row_ref}")

    # --- refinement_kind ---
    rk = cm.get("refinement_kind", "")
    if rk not in _VALID_KINDS:
        hard(f"refinement_kind {rk!r} not in {sorted(_VALID_KINDS)}")

    # --- attributes ---
    attrs = cm.get("attributes", [])
    if not isinstance(attrs, list) or len(attrs) == 0:
        hard("class_model must have ≥1 attribute")
        return violations

    if row_ref == 2:
        sem_typed = [
            a for a in attrs
            if isinstance(a, dict) and a.get("semantic_type")
        ]
        if not sem_typed:
            hard(
                "Row 2 class_model requires ≥1 attribute with semantic_type set"
            )

    pk_count = sum(
        1 for a in attrs if isinstance(a, dict) and a.get("key") == "PK"
    )
    if pk_count > 1:
        hard(f"class_model has {pk_count} PK attributes — at most 1 permitted")

    for i, attr in enumerate(attrs):
        if not isinstance(attr, dict):
            hard(f"attributes[{i}] is not a dict")
            continue

        if not attr.get("name", "").strip():
            hard(f"attributes[{i}].name is empty")

        origin = attr.get("origin", "")
        if origin not in _VALID_ORIGINS:
            hard(
                f"attributes[{i}].origin {origin!r} not in "
                f"{sorted(_VALID_ORIGINS)}"
            )

        # [C] Per-row attribute profile enforcement (v0.36)
        if row_ref == 2:
            # Row 2 profile forbids: key, domain, target_ref.
            # type is allowed ONLY if it is from the closed logical enum.
            if attr.get("key") is not None:
                hard(
                    f"profile_violation_row2:key — "
                    f"attributes[{i}] key={attr['key']!r} forbidden at Row 2"
                )
            if attr.get("domain") is not None:
                hard(
                    f"profile_violation_row2:domain — "
                    f"attributes[{i}] domain field forbidden at Row 2"
                )
            if attr.get("target_ref") is not None and str(attr.get("target_ref", "")).strip():
                hard(
                    f"profile_violation_row2:target_ref — "
                    f"attributes[{i}] target_ref forbidden at Row 2"
                )
            type_val = attr.get("type")
            if type_val is not None and str(type_val).strip():
                if str(type_val).strip() not in _LOGICAL_TYPE_ENUM:
                    hard(
                        f"profile_violation_row2:type_not_logical — "
                        f"attributes[{i}] type={type_val!r} is not in the "
                        f"logical closed enum {sorted(_LOGICAL_TYPE_ENUM)}"
                    )

        elif row_ref == 3:
            # Row 3: key/domain/target_ref are allowed; type must still be logical.
            type_val = attr.get("type")
            if type_val is not None and str(type_val).strip():
                if str(type_val).strip() not in _LOGICAL_TYPE_ENUM:
                    hard(
                        f"profile_violation_row3:type_not_logical — "
                        f"attributes[{i}] type={type_val!r} is not in the "
                        f"logical closed enum {sorted(_LOGICAL_TYPE_ENUM)}"
                    )

        # Row 2 profile check already hard-rejects key; run FK soft check for rows 3+
        if row_ref != 2 and attr.get("key") == "FK":
            tr = attr.get("target_ref", "")
            if not tr or not str(tr).strip():
                soft(
                    f"attributes[{i}] is FK but target_ref is blank "
                    f"(referential check deferred to Stage 4 sub-pass 2)"
                )

        domain_vals = attr.get("domain")
        if domain_vals is not None and row_ref != 2:
            if not isinstance(domain_vals, list):
                soft(f"attributes[{i}].domain is not a list")
            else:
                blanks = [v for v in domain_vals if not str(v).strip()]
                if blanks:
                    soft(
                        f"attributes[{i}].domain contains "
                        f"{len(blanks)} blank value(s)"
                    )

    # --- relationships ---
    rels = cm.get("relationships", [])
    if isinstance(rels, list):
        for i, rel in enumerate(rels):
            if not isinstance(rel, dict):
                hard(f"relationships[{i}] is not a dict")
                continue
            tgt = rel.get("target", "")
            if not tgt or not str(tgt).strip():
                hard(f"relationships[{i}].target is empty")

    return violations
