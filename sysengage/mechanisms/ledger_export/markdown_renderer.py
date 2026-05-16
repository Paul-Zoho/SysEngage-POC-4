"""
Ledger Export — Markdown Projection Renderer.

Renders a human-readable Markdown projection of a canonical v2.12 ledger.
Per spec Appendix A: Markdown outputs are projections/views; the JSON ledger
is the authoritative canonical artefact. This projection is for human review.

Section structure follows the canonical element_type ordering from the spec
enum, emitting only sections where elements actually exist.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mechanisms.ledger_export.db_reader import ProjectData


def _fmt_list(items: list[str]) -> str:
    if not items:
        return "_none_"
    return ", ".join(f"`{i}`" for i in sorted(items))


def _opt(value: Any, label: str) -> str:
    if value is None or value == "" or value == []:
        return ""
    return f"- **{label}:** {value}\n"


def _confidence_bar(confidence: float) -> str:
    filled = round(confidence * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"`{bar}` {confidence:.2f}"


def _iso_or_none(dt: datetime | None) -> str:
    if dt is None:
        return "_in progress_"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def render_markdown(data: ProjectData, ledger_meta: dict[str, Any]) -> str:
    """
    Render a Markdown projection from *data* and ledger-level metadata.

    *ledger_meta* should contain the top-level canonical ledger dict keys:
    sysengage_ledger_version, run_id, created_utc, row_target, content_hash.
    """
    lines: list[str] = []

    _header(lines, data, ledger_meta)
    _section_analysis_passes(lines, data)
    _section_sources(lines, data)
    _section_segments(lines, data)
    _section_source_atoms(lines, data)
    _section_signals(lines, data)
    _section_concerns(lines, data)
    _section_stakeholders(lines, data)
    _section_domains(lines, data)
    _section_requirements(lines, data)
    _section_registers(lines, data)
    _footer(lines, ledger_meta)

    return "\n".join(lines)


def _header(lines: list[str], data: ProjectData, meta: dict[str, Any]) -> None:
    project = data.project
    version = meta.get("sysengage_ledger_version", "2.12")
    run_id = meta.get("run_id", "")
    created = meta.get("created_utc", "")
    row_target = meta.get("row_target", "")
    if isinstance(row_target, list):
        row_target_str = ", ".join(row_target)
    else:
        row_target_str = str(row_target)

    content_hash = meta.get("content_hash", {})
    hash_str = content_hash.get("hash", "")[:16] + "..." if content_hash.get("hash") else ""

    lines += [
        f"---",
        f"sysengage_ledger_version: \"{version}\"",
        f"schema_id: \"{meta.get('schema_id', '')}\"",
        f"project_id: \"{project.project_id}\"",
        f"project_name: \"{project.name}\"",
        f"run_id: \"{run_id}\"",
        f"created_utc: \"{created}\"",
        f"row_target: \"{row_target_str}\"",
        f"generator: \"{meta.get('generator', {}).get('name', '')} v{meta.get('generator', {}).get('version', '')}\"",
        f"content_hash: \"{hash_str}\"",
        f"---",
        "",
        f"# SysEngage Canonical Ledger — {project.name}",
        "",
        f"> **Spec version:** v{version} | "
        f"**Project:** `{project.project_id}` | "
        f"**Rows:** {row_target_str}",
        f">",
        f"> This document is a **Markdown projection** (human review view). "
        f"The authoritative canonical artefact is the companion `.ledger.json` file.",
        "",
        "## Summary",
        "",
        "| Element Type | Count |",
        "| --- | --- |",
        f"| Source | {len(data.sources)} |",
        f"| Segment | {len(data.segments)} |",
        f"| SourceAtom | {len(data.source_atoms)} |",
        f"| Signal | {len(data.signals)} |",
        f"| Concern | {len(data.concerns)} |",
        f"| AnalysisPass | {len(data.analysis_passes)} |",
        f"| Stakeholder | {len(data.stakeholders)} |",
        f"| Domain | {len(data.domains)} |",
        f"| Requirement | {len(data.requirements)} |",
        "",
    ]


def _section_analysis_passes(lines: list[str], data: ProjectData) -> None:
    passes = data.analysis_passes
    if not passes:
        return
    lines += [
        "---",
        "",
        f"## Analysis Passes ({len(passes)})",
        "",
    ]
    for ap in sorted(passes, key=lambda p: p.pass_id):
        completed = _iso_or_none(ap.pass_completed_at)
        elapsed = f"{ap.elapsed_ms:,} ms" if ap.elapsed_ms is not None else "_unknown_"
        status = ap.execution_status
        status_icon = "✓" if status in ("Success", "Completed") else ("⚠" if "Warning" in status or status == "PartialSuccess" else "✗")

        lines += [
            f"### {ap.pass_id} — {ap.mechanism}",
            "",
            f"- **Pass Type:** {ap.pass_type}",
            f"- **Mechanism:** `{ap.mechanism}`",
            f"- **Execution Status:** {status_icon} `{status}`",
            f"- **Mode Active:** `{ap.mode_active}`",
            f"- **Declared Modes:** {_fmt_list(list(ap.declared_transformation_modes or []))}",
            f"- **Evaluated Scope:** {ap.evaluated_scope}",
            f"- **Started:** `{_iso_or_none(ap.pass_started_at)}`",
            f"- **Completed:** `{completed}`",
            f"- **Elapsed:** {elapsed}",
            f"- **Confidence:** {_confidence_bar(ap.confidence)}",
        ]

        outputs = ap.outputs or {}
        if outputs:
            rw = outputs.get("read_witness")
            md = outputs.get("mechanism_data")
            mv = outputs.get("mode_violations")
            rld = outputs.get("row_lens_data")

            if rw:
                lines += [
                    "",
                    "**Read Witness:**",
                    "",
                    f"| Key | Value |",
                    f"| --- | --- |",
                    f"| `input_hash` | `{rw.get('input_hash', '')}` |",
                    f"| `byte_count` | {rw.get('byte_count', '_n/a_')} |",
                    f"| `character_count` | {rw.get('character_count', '_n/a_')} |",
                    f"| `read_mode` | `{rw.get('read_mode', '')}` |",
                    f"| `read_completion_status` | `{rw.get('read_completion_status', '')}` |",
                ]

            if md:
                lines += ["", "**Mechanism Data:**", ""]
                for k, v in sorted(md.items()):
                    lines.append(f"- `{k}`: {v}")

            if rld:
                lines += [
                    "",
                    "**Row Lens Data (v2.12):**",
                    "",
                    f"| Key | Value |",
                    f"| --- | --- |",
                    f"| `row_ref` | {rld.get('row_ref', '_n/a_')} |",
                    f"| `stream1_source_count` | {rld.get('stream1_source_count', '_n/a_')} |",
                    f"| `stream2_requirement_count` | {rld.get('stream2_requirement_count', '_n/a_')} |",
                    f"| `signal_count_produced` | {rld.get('signal_count_produced', '_n/a_')} |",
                    f"| `concern_count_produced` | {rld.get('concern_count_produced', '_n/a_')} |",
                ]

            if mv:
                lines += ["", f"**Mode Violations:** {len(mv)} recorded"]
                for v in mv:
                    lines.append(f"- {v}")
            elif mv is not None:
                lines += ["", "**Mode Violations:** _none_"]

        lines.append("")


def _section_sources(lines: list[str], data: ProjectData) -> None:
    sources = data.sources
    if not sources:
        return
    lines += [
        "---",
        "",
        f"## Sources ({len(sources)})",
        "",
    ]
    for src in sorted(sources, key=lambda s: s.source_id):
        lines += [
            f"### {src.source_id}",
            "",
            f"- **Input Material:** {src.input_material_ref}",
            f"- **Segmentation Context:** {src.segmentation_context}",
            f"- **Confidence:** {_confidence_bar(src.confidence)}",
        ]
        if src.parent_source_ref:
            lines.append(f"- **Parent Source:** `{src.parent_source_ref}`")
        lines += [
            "",
            f"> {src.source_text}",
            "",
        ]


def _section_segments(lines: list[str], data: ProjectData) -> None:
    segments = data.segments
    if not segments:
        return
    lines += [
        "---",
        "",
        f"## Segments ({len(segments)})",
        "",
    ]
    for seg in sorted(segments, key=lambda s: s.segment_id):
        lines += [
            f"### {seg.segment_id} — {seg.title}",
            "",
            f"- **Source Refs:** {_fmt_list(list(seg.source_refs or []))}",
            f"- **Confidence:** {_confidence_bar(seg.confidence)}",
        ]
        if seg.description:
            lines += ["", f"{seg.description}"]
        if seg.parent_segment_ref:
            lines.append(f"- **Parent Segment:** `{seg.parent_segment_ref}`")
        lines.append("")


def _section_source_atoms(lines: list[str], data: ProjectData) -> None:
    atoms = data.source_atoms
    if not atoms:
        return
    lines += [
        "---",
        "",
        f"## Source Atoms ({len(atoms)})",
        "",
    ]
    for atom in sorted(atoms, key=lambda a: a.atom_id):
        lines += [
            f"### {atom.atom_id}",
            "",
            f"- **Parent Source:** `{atom.source_ref}`",
            f"- **Confidence:** {_confidence_bar(atom.confidence)}",
        ]
        if atom.segment_ref:
            lines.append(f"- **Segment Ref:** `{atom.segment_ref}`")
        if atom.parent_atom_ref:
            lines.append(f"- **Parent Atom:** `{atom.parent_atom_ref}`")
        lines += [
            "",
            f"> {atom.atom_text}",
            "",
        ]


def _section_signals(lines: list[str], data: ProjectData) -> None:
    signals = data.signals
    if not signals:
        return
    lines += [
        "---",
        "",
        f"## Signals ({len(signals)})",
        "",
    ]
    by_row: dict[str, list] = {}
    for sig in signals:
        by_row.setdefault(sig.row_target, []).append(sig)

    for row in sorted(by_row.keys()):
        row_signals = sorted(by_row[row], key=lambda s: s.signal_id)
        lines += [
            f"### Row {row} Signals ({len(row_signals)})",
            "",
        ]
        for sig in row_signals:
            lines += [
                f"#### {sig.signal_id} — `{sig.signal_type}`",
                "",
                f"- **Row Target:** {sig.row_target}",
                f"- **Signal Type:** `{sig.signal_type}`",
                f"- **Source Refs:** {_fmt_list(list(sig.source_refs or []))}",
                f"- **Confidence:** {_confidence_bar(sig.confidence)}",
            ]
            if sig.sourceatom_refs:
                lines.append(f"- **SourceAtom Refs:** {_fmt_list(list(sig.sourceatom_refs))}")
            if sig.derived_from_concern_id:
                lines.append(f"- **Derived from Concern:** `{sig.derived_from_concern_id}`")
            lines += [
                "",
                f"> {sig.description}",
                "",
            ]


def _section_concerns(lines: list[str], data: ProjectData) -> None:
    concerns = data.concerns
    if not concerns:
        return
    lines += [
        "---",
        "",
        f"## Concerns ({len(concerns)})",
        "",
    ]
    by_row: dict[str, list] = {}
    for cn in concerns:
        by_row.setdefault(cn.produced_in_row, []).append(cn)

    for row in sorted(by_row.keys()):
        row_concerns = sorted(by_row[row], key=lambda c: c.concern_id)
        lines += [
            f"### Row {row} Concerns ({len(row_concerns)})",
            "",
        ]
        for cn in row_concerns:
            state_icon = {
                "Open": "🔴",
                "Resolved": "🟢",
                "Dispositioned": "🟡",
            }.get(cn.state, "⚪")
            lines += [
                f"#### {cn.concern_id} [{state_icon} {cn.state}]",
                "",
                f"- **State:** {cn.state}",
                f"- **Produced in Row:** {cn.produced_in_row}",
                f"- **Practitioner:** `{cn.practitioner_id}`",
                f"- **Source Refs:** {_fmt_list(list(cn.source_refs or []))}",
                f"- **Confidence:** {_confidence_bar(cn.confidence)}",
            ]
            if cn.dispositioned_with_outcome:
                lines.append(f"- **Disposition Outcome:** `{cn.dispositioned_with_outcome}`")
            if cn.disposition_rationale:
                lines.append(f"- **Disposition Rationale:** {cn.disposition_rationale}")
            lines += [
                "",
                f"> {cn.description}",
                "",
            ]


def _section_stakeholders(lines: list[str], data: ProjectData) -> None:
    stakeholders = data.stakeholders
    if not stakeholders:
        return
    lines += [
        "---",
        "",
        f"## Stakeholders ({len(stakeholders)})",
        "",
        "| ID | Name | Role / Kind |",
        "| --- | --- | --- |",
    ]
    for sh in sorted(stakeholders, key=lambda s: s.stakeholder_id):
        role = getattr(sh, "stakeholder_type", "") or ""
        kind = "Automated" if sh.stakeholder_id == "SH001" else "Human"
        lines.append(f"| `{sh.stakeholder_id}` | {sh.name} | {role} ({kind}) |")
    lines.append("")


def _section_domains(lines: list[str], data: ProjectData) -> None:
    domains = data.domains
    if not domains:
        return
    lines += [
        "---",
        "",
        f"## Domains ({len(domains)})",
        "",
    ]
    for dom in sorted(domains, key=lambda d: d.domain_id):
        lines += [
            f"### {dom.domain_id} — {dom.name}",
            "",
            f"- **Row Target:** {dom.row_target}",
            "",
        ]


def _section_requirements(lines: list[str], data: ProjectData) -> None:
    requirements = data.requirements
    if not requirements:
        return
    lines += [
        "---",
        "",
        f"## Requirements ({len(requirements)})",
        "",
    ]
    by_row: dict[str, list] = {}
    for req in requirements:
        by_row.setdefault(req.row_target, []).append(req)

    for row in sorted(by_row.keys()):
        row_reqs = sorted(by_row[row], key=lambda r: r.requirement_id)
        lines += [
            f"### Row {row} Requirements ({len(row_reqs)})",
            "",
        ]
        for req in row_reqs:
            domain_ref = getattr(req, "domain_id", None) or ""
            lines += [
                f"#### {req.requirement_id}",
                "",
                f"- **Row Target:** {req.row_target}",
            ]
            if domain_ref:
                lines.append(f"- **Domain:** `{domain_ref}`")
            lines += [
                "",
                f"> {req.statement}",
                "",
            ]


def _section_registers(lines: list[str], data: ProjectData) -> None:
    lines += [
        "---",
        "",
        "## Registers",
        "",
        "| Register | Type | Member Count |",
        "| --- | --- | --- |",
        f"| `SOURCE_REG001` | Source | {len(data.sources)} |",
        f"| `SIGNAL_REG001` | Signal | {len(data.signals)} |",
        f"| `STAKEHOLDER_REG001` | Stakeholder | {len(data.stakeholders)} |",
    ]
    if data.segments:
        lines.append(f"| `SEGMENT_REG001` | Segment | {len(data.segments)} |")
    if data.source_atoms:
        lines.append(f"| `SOURCEATOM_REG001` | SourceAtom | {len(data.source_atoms)} |")
    if data.concerns:
        lines.append(f"| `CONCERN_REG001` | Concern | {len(data.concerns)} |")
    if data.domains:
        lines.append(f"| `DOMAIN_REG001` | Domain | {len(data.domains)} |")
    if data.requirements:
        lines.append(f"| `REQUIREMENT_REG001` | Requirement | {len(data.requirements)} |")
    lines.append("")


def _footer(lines: list[str], meta: dict[str, Any]) -> None:
    created = meta.get("created_utc", "")
    version = meta.get("sysengage_ledger_version", "2.12")
    run_id = meta.get("run_id", "")
    content_hash = meta.get("content_hash", {})
    hash_full = content_hash.get("hash", "")
    hash_alg = content_hash.get("hash_alg", "sha256")

    lines += [
        "---",
        "",
        "## Ledger Provenance",
        "",
        f"| Field | Value |",
        f"| --- | --- |",
        f"| Spec Version | v{version} |",
        f"| Run ID | `{run_id}` |",
        f"| Created UTC | `{created}` |",
        f"| Content Hash ({hash_alg}) | `{hash_full}` |",
        "",
        f"_Generated by SysEngage Ledger Export — spec conformant Markdown projection_",
        "",
    ]
