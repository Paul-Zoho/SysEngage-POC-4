"""
object_refs_resolver — materialise object_refs candidate paths (F107 / v0.33).

Per Requirement Derivation Mechanism Spec v0.33 §4.4.3a Step 4:

  Behavioural (Functional/Constraint) proposals may carry candidate object_refs
  paths proposed by the AI in Stage 2.  Each path has the form:

      "<Entity>.<attr_name>[.<value>]"

  Resolution algorithm:
    1. Parse the path into (entity_name, attr_name, value_name?).
    2. Look up entity_name in the working class_model set (keyed by entity name;
       case-insensitive fallback).
    3. Find attr_name in the entity's class_model.attributes list.
    4. If value_name is supplied and the attribute has a domain list, confirm the
       value appears in it.  If the attribute has no domain list, the value is
       accepted with a debug advisory.
    5. Resolved paths are returned unchanged (same string as input).
    6. Paths that fail at any step go to dangling with a reason tag.

  The class_model working set is built from Structural proposals processed in
  Stage 4 sub-pass 1 for the current row.  Cross-row resolution is not attempted.
"""

from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)


def resolve_object_refs(
    candidate_paths: list[str],
    class_models_by_entity: dict[str, dict[str, Any]],
    provenance_ref: str,
) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Resolve AI-proposed object_refs paths against the working class_model set.

    Args:
        candidate_paths:        AI-proposed paths, e.g. ["Task.status.open"].
        class_models_by_entity: entity_name → class_model dict for this row.
                                Keys are used case-insensitively.
        provenance_ref:         requirement_id owning these paths (for logging).

    Returns:
        (resolved_paths, dangling_entries)
        resolved_paths:   paths that fully resolve — stored in object_refs column.
        dangling_entries: dicts with keys: path, reason, provenance_ref.
    """
    resolved: list[str] = []
    dangling: list[dict[str, Any]] = []

    lower_index: dict[str, dict[str, Any]] = {
        k.lower(): v for k, v in class_models_by_entity.items()
    }

    for path in candidate_paths:
        if not path or not path.strip():
            dangling.append(
                {"path": path, "reason": "blank_path", "provenance_ref": provenance_ref}
            )
            continue

        parts = path.split(".", 2)
        if len(parts) < 2:
            dangling.append(
                {
                    "path": path,
                    "reason": "malformed_path_min_2_segments",
                    "provenance_ref": provenance_ref,
                }
            )
            continue

        entity_name = parts[0].strip()
        attr_name = parts[1].strip()
        value_name = parts[2].strip() if len(parts) == 3 else None

        # Step 1 — resolve entity
        cm = class_models_by_entity.get(entity_name) or lower_index.get(
            entity_name.lower()
        )
        if cm is None:
            dangling.append(
                {
                    "path": path,
                    "reason": f"entity_not_in_working_set:{entity_name!r}",
                    "provenance_ref": provenance_ref,
                }
            )
            continue

        # Step 2 — resolve attribute
        attrs: list[dict[str, Any]] = cm.get("attributes", [])
        matched_attr: dict[str, Any] | None = None
        for a in attrs:
            if (
                isinstance(a, dict)
                and a.get("name", "").strip().lower() == attr_name.lower()
            ):
                matched_attr = a
                break

        if matched_attr is None:
            dangling.append(
                {
                    "path": path,
                    "reason": f"attribute_not_in_class_model:{attr_name!r}",
                    "provenance_ref": provenance_ref,
                }
            )
            continue

        # Step 3 — resolve value (optional)
        if value_name is not None:
            domain_vals: list[str] | None = matched_attr.get("domain")
            if domain_vals is None:
                _log.debug(
                    "object_refs %r: attr %r has no domain list; value %r accepted advisory",
                    path,
                    attr_name,
                    value_name,
                )
            else:
                domain_lower = [str(v).strip().lower() for v in domain_vals]
                if value_name.lower() not in domain_lower:
                    dangling.append(
                        {
                            "path": path,
                            "reason": f"value_not_in_domain:{value_name!r}",
                            "provenance_ref": provenance_ref,
                        }
                    )
                    continue

        resolved.append(path)

    return resolved, dangling
