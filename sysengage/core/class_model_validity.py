"""
CHK-3d-11 — Structural class_model validity check.

Per Requirement Derivation Mechanism Spec v0.33 §4.3.

Validates a class_model dict on a Structural proposal after Stage 2.
Returns a list of violation dicts.  Callers must inspect severity:

  "hard"  — the proposal must be excluded from production (similar to
             statement-level hard failures in existing checks).
  "soft"  — advisory; the proposal survives but a warning is recorded.

Hard violations:
  - entity absent or empty
  - tier not in {2,3,4,5}
  - tier does not match row_target
  - refinement_kind not in valid enum
  - no attributes (list is empty)
  - Row 2: no attribute carries semantic_type
  - >1 attribute with key == 'PK'
  - any attribute with blank name
  - any attribute with invalid origin enum
  - any relationship with blank target

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


def validate_class_model(
    cm: dict[str, Any], row_ref: int
) -> list[dict[str, Any]]:
    """
    Run CHK-3d-11 structural validity checks.

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
    if tier not in {2, 3, 4, 5}:
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

        if attr.get("key") == "FK":
            tr = attr.get("target_ref", "")
            if not tr or not str(tr).strip():
                soft(
                    f"attributes[{i}] is FK but target_ref is blank "
                    f"(referential check deferred to Stage 4 sub-pass 2)"
                )

        domain_vals = attr.get("domain")
        if domain_vals is not None:
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
