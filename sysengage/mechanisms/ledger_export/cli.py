"""
Ledger Export CLI.

Usage (named convention):
    python -m mechanisms.ledger_export.cli <project_id> \\
        --phase 03 --pass 3a --row 1 [--out-dir <dir>]

    Writes: <out-dir>/{ProjectID}_Ph{phase}_{pass}_{passLabel}_R{row}_Run{n}.json
    Run number is derived automatically from existing files in out-dir.

Usage (legacy):
    python -m mechanisms.ledger_export.cli <project_id> [--out-dir <dir>]

    Writes: <out-dir>/<project_id>.ledger.json
    --out-file overrides the filename entirely (legacy use only).
"""

from __future__ import annotations

import argparse
import os
import sys

_SYSENGAGE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_WORKSPACE_ROOT = os.path.dirname(_SYSENGAGE_ROOT)
_DEFAULT_OUT_DIR = os.path.join(_WORKSPACE_ROOT, "verification_outputs")

sys.path.insert(0, _SYSENGAGE_ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a SysEngage project ledger to JSON (spec v2.12)."
    )
    parser.add_argument("project_id", help="Project ID to export (e.g. PMT)")
    parser.add_argument(
        "--out-dir",
        default=_DEFAULT_OUT_DIR,
        help=f"Directory to write output file (default: {_DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--phase",
        default=None,
        help="Phase number (e.g. 03). Required for named-convention output.",
    )
    parser.add_argument(
        "--pass",
        dest="pass_",
        default=None,
        metavar="PASS",
        help="Pass identifier within the phase (e.g. 3a). Required for named-convention output.",
    )
    parser.add_argument(
        "--row",
        default=None,
        help="Zachman row number 1–6 (e.g. 1). Required for named-convention output.",
    )
    parser.add_argument(
        "--project-code",
        default=None,
        metavar="CODE",
        help="Short uppercase code used in the output filename (e.g. PMT). "
             "Defaults to project_id. Use this when project_id contains underscores "
             "or digits that are not valid in the naming convention (e.g. PMT_E2E → PMT).",
    )
    parser.add_argument(
        "--out-file",
        default=None,
        help="Override the output filename (basename only). Legacy use; ignored when "
             "--phase/--pass/--row are all supplied.",
    )
    args = parser.parse_args()

    project_id: str = args.project_id
    out_dir: str = args.out_dir

    os.makedirs(out_dir, exist_ok=True)

    from core.db import get_session
    from mechanisms.ledger_export import run_ledger_export

    print(f"[ledger-export] Loading project: {project_id!r}", flush=True)
    session = get_session()
    try:
        result = run_ledger_export(project_id=project_id, session=session)
    except ValueError as exc:
        print(f"[ledger-export] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        session.close()

    naming_args = (args.phase, args.pass_, args.row)
    if all(a is not None for a in naming_args):
        from core.output_naming import OutputNamingError, generate_filename
        naming_id = args.project_code if args.project_code else project_id
        try:
            basename = generate_filename(
                project_id=naming_id,
                phase=args.phase,
                pass_=args.pass_,
                row=args.row,
                out_dir=out_dir,
            )
        except OutputNamingError as exc:
            print(f"[ledger-export] Naming error: {exc}", file=sys.stderr)
            sys.exit(1)
    elif args.out_file:
        basename = args.out_file
    else:
        safe_id = project_id.replace("/", "_").replace("\\", "_")
        basename = f"{safe_id}.ledger.json"

    json_path = os.path.join(out_dir, basename)

    with open(json_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(result.json_str)
    print(f"[ledger-export] JSON → {json_path}", flush=True)

    ledger = result.ledger
    n_elements = len(ledger.get("elements", []))
    n_registers = len(ledger.get("register_index", []))
    project_name = result.project_name
    hash_prefix = ledger.get("content_hash", {}).get("hash", "")[:16]

    print(
        f"\n[ledger-export] Export complete\n"
        f"  Project:   {project_name} ({project_id})\n"
        f"  Elements:  {n_elements}\n"
        f"  Registers: {n_registers}\n"
        f"  Hash:      {hash_prefix}...\n"
        f"  File:      {basename}\n",
        flush=True,
    )


if __name__ == "__main__":
    main()
