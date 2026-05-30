"""
branch_manager.py — Neon database branch management for SysEngage test isolation.

Implements the workflow defined in:
  specifications/SysEngage_Test_Branch_Management_v0_1.md

Operations
----------
  create_snapshot      Create a snapshot branch from the current main branch state.
  create_test_branch   Create a disposable test branch from a named snapshot.
  delete_test_branch   Delete a test branch after analysis.
  delete_snapshot      Delete a snapshot branch from Neon and remove it from the registry.
  promote_to_snapshot  Create a snapshot from a verified test branch and delete the branch.
  list_snapshots       List all snapshot branches from the local registry.

Authentication
--------------
  NEON_API_KEY   — Neon API key (required, set in Replit Secrets)
  NEON_PROJECT_ID — Neon project ID (optional; auto-detected if you have exactly one project)

Registry
--------
  Stored at: sysengage/test_infrastructure/snapshot_registry.json
  Version-controlled alongside the codebase.

Usage examples
--------------
  python sysengage/scripts/branch_manager.py create_snapshot --project PMT --phase ph03 --pass 3a --row R1
  python sysengage/scripts/branch_manager.py create_test_branch --snapshot snap_PMT_ph03_3a_R1 --scenario Ph3b_Dedup_On
  python sysengage/scripts/branch_manager.py rename_branch --branch test_PMT_ph03_3a_R1_Ph3b_Dedup_On --new-name test_PMT_ph03_3a_R1_Ph3b_Rerun
  python sysengage/scripts/branch_manager.py delete_test_branch --branch test_PMT_ph03_3a_R1_Ph3b_Dedup_On
  python sysengage/scripts/branch_manager.py delete_snapshot --snapshot snap_PMT_ph03_3a_R1
  python sysengage/scripts/branch_manager.py promote_to_snapshot --branch test_PMT_ph03_3a_R1_Ph3b_Dedup_On --phase ph03 --pass 3b --row R1
  python sysengage/scripts/branch_manager.py list_snapshots
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import urllib.request
import urllib.error

NEON_API_BASE = "https://console.neon.tech/api/v2"
REGISTRY_PATH = Path(__file__).parent.parent / "test_infrastructure" / "snapshot_registry.json"

SNAP_NAME_RE = re.compile(
    r"^snap_([A-Z]+)_(ph\d{2})_([0-9][a-z])_R(\d+)$"
)


# ---------------------------------------------------------------------------
# Neon API client
# ---------------------------------------------------------------------------

def _api_key() -> str:
    key = os.environ.get("NEON_API_KEY", "")
    if not key:
        print(
            "ERROR: NEON_API_KEY is not set. Add it to Replit Secrets and try again.",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def _neon_request(
    method: str,
    path: str,
    body: dict | None = None,
) -> dict:
    url = f"{NEON_API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        print(f"ERROR: Neon API {method} {path} → HTTP {exc.code}: {body_text}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: Neon API request failed: {exc}", file=sys.stderr)
        sys.exit(1)


def _get_project_id() -> str:
    explicit = os.environ.get("NEON_PROJECT_ID", "")
    if explicit:
        return explicit

    # Try listing projects (works with account-level keys)
    url = f"{NEON_API_BASE}/projects"
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            projects = data.get("projects", [])
            if len(projects) == 1:
                return projects[0]["id"]
            if not projects:
                print("ERROR: No Neon projects found for this API key.", file=sys.stderr)
                sys.exit(1)
            names = [f"  {p['id']}  ({p['name']})" for p in projects]
            print(
                "ERROR: Multiple Neon projects found. Set NEON_PROJECT_ID to one of:\n"
                + "\n".join(names),
                file=sys.stderr,
            )
            sys.exit(1)
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        # Project-scoped API keys return 403/404 for /projects but embed the
        # project ID in the error body. The body is JSON; parse it first so we
        # search the unescaped message string, not the raw JSON bytes.
        try:
            body_json = json.loads(body_text)
            search_text = body_json.get("message", body_text)
        except Exception:
            search_text = body_text
        m = re.search(r'subject_project_id:"([^"]+)"', search_text)
        if m:
            project_id = m.group(1)
            print(
                f"[branch-manager] Project-scoped API key detected — "
                f"using project: {project_id}\n"
                f"  Tip: set NEON_PROJECT_ID={project_id} to skip auto-detection.",
                file=sys.stderr,
            )
            return project_id
        print(
            f"ERROR: Cannot list Neon projects (HTTP {exc.code}): {body_text}\n"
            "Set NEON_PROJECT_ID explicitly and try again.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: Neon project detection failed: {exc}", file=sys.stderr)
        sys.exit(1)


def _list_branches(project_id: str) -> list[dict]:
    data = _neon_request("GET", f"/projects/{project_id}/branches")
    return data.get("branches", [])


def _find_branch_by_name(project_id: str, name: str) -> dict | None:
    for branch in _list_branches(project_id):
        if branch["name"] == name:
            return branch
    return None


def _get_primary_branch(project_id: str) -> dict:
    for branch in _list_branches(project_id):
        if branch.get("primary") or branch.get("default"):
            return branch
    # Fall back to branch named "main" or "master"
    for branch in _list_branches(project_id):
        if branch["name"] in ("main", "master"):
            return branch
    print("ERROR: Cannot identify the primary branch.", file=sys.stderr)
    sys.exit(1)


def _create_branch(
    project_id: str,
    branch_name: str,
    parent_id: str,
) -> tuple[str, str]:
    """
    Create a branch with a read-write endpoint.

    Returns (branch_id, connection_uri).
    """
    payload = {
        "branch": {"name": branch_name, "parent_id": parent_id},
        "endpoints": [{"type": "read_write"}],
    }
    data = _neon_request("POST", f"/projects/{project_id}/branches", body=payload)

    branch_id = data["branch"]["id"]

    # Extract connection URI (Neon returns one per role)
    uris = data.get("connection_uris", [])
    if not uris:
        # Fallback: construct from endpoint host using the stable main-branch URL
        # as the credential template. Prefer DATABASE_URL_MAIN (the permanent
        # main URL per spec Rule 4) over NEON_DATABASE_URL (which may be
        # pointing at a test branch during a test run).
        endpoints = data.get("endpoints", [])
        host = endpoints[0]["host"] if endpoints else ""
        main_url = (
            os.environ.get("DATABASE_URL_MAIN")
            or os.environ.get("NEON_DATABASE_URL", "")
        )
        if main_url and host:
            conn_uri = re.sub(r"@[^/]+/", f"@{host}/", main_url)
        else:
            conn_uri = f"(endpoint host: {host} — build connection string manually)"
    else:
        conn_uri = uris[0]["connection_uri"]

    return branch_id, conn_uri


def _delete_branch(project_id: str, branch_id: str) -> None:
    _neon_request("DELETE", f"/projects/{project_id}/branches/{branch_id}")


def _wait_for_branch_ready(project_id: str, branch_id: str, timeout: int = 60) -> None:
    """Poll until the branch leaves 'creating' state."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        data = _neon_request("GET", f"/projects/{project_id}/branches/{branch_id}")
        state = data.get("branch", {}).get("creation_source") or data.get("branch", {}).get("state", "")
        if data.get("branch", {}).get("ready", True):
            return
        time.sleep(2)


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"snapshots": []}


def _save_registry(registry: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(registry, f, indent=2)
        f.write("\n")


def _registry_add_snapshot(entry: dict) -> None:
    registry = _load_registry()
    registry["snapshots"] = [
        s for s in registry["snapshots"] if s["name"] != entry["name"]
    ]
    registry["snapshots"].append(entry)
    _save_registry(registry)


def _registry_remove(name: str) -> None:
    registry = _load_registry()
    registry["snapshots"] = [s for s in registry["snapshots"] if s["name"] != name]
    _save_registry(registry)


def _registry_get(name: str) -> dict | None:
    registry = _load_registry()
    for s in registry["snapshots"]:
        if s["name"] == name:
            return s
    return None


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def cmd_create_snapshot(args: argparse.Namespace) -> None:
    """Create a snapshot branch from the current main branch state."""
    project_code = args.project.upper()
    phase = args.phase.lower()
    pass_ = getattr(args, "pass").lower()
    row = args.row.upper()

    snap_name = f"snap_{project_code}_{phase}_{pass_}_{row}"
    print(f"[branch-manager] Creating snapshot: {snap_name}")

    neon_project = _get_project_id()
    print(f"[branch-manager] Neon project: {neon_project}")

    existing = _find_branch_by_name(neon_project, snap_name)
    if existing:
        print(f"[branch-manager] Branch '{snap_name}' already exists (id={existing['id']})")
        conn_uri = _build_conn_uri_for_branch(neon_project, existing["id"])
        _print_snapshot_created(snap_name, existing["id"], conn_uri)
        return

    primary = _get_primary_branch(neon_project)
    print(f"[branch-manager] Cloning from primary branch: {primary['name']} ({primary['id']})")

    branch_id, conn_uri = _create_branch(neon_project, snap_name, primary["id"])

    entry = {
        "name": snap_name,
        "project_id": project_code,
        "phase": phase,
        "pass": pass_,
        "row": row,
        "state_description": args.description or f"Post-{pass_}: {project_code} {row} state",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "VERIFIED",
        "ver_criteria_passed": [],
        "neon_branch_id": branch_id,
        "neon_project_id": neon_project,
    }
    _registry_add_snapshot(entry)
    _print_snapshot_created(snap_name, branch_id, conn_uri)


def cmd_create_test_branch(args: argparse.Namespace) -> None:
    """Create a disposable test branch from a named snapshot."""
    snapshot_name = args.snapshot
    scenario = args.scenario

    match = SNAP_NAME_RE.match(snapshot_name)
    if match:
        project_code, phase, pass_, row_num = match.groups()
    else:
        # Non-standard name (e.g. snap_ph03_3a_AllProjects) — fall back to registry
        entry = _registry_get(snapshot_name)
        if not entry:
            print(
                f"ERROR: snapshot name '{snapshot_name}' does not match "
                "snap_{{PROJECT}}_{{phase}}_{{pass}}_R{{row}} and is not in the registry.",
                file=sys.stderr,
            )
            sys.exit(1)
        project_code = entry.get("project_id", "ALL")
        phase = entry.get("phase", "")
        pass_ = entry.get("pass", "")
        row_num = entry.get("row", "R0").lstrip("R")

    test_branch_name = f"test_{project_code}_{phase}_{pass_}_R{row_num}_{scenario}"
    print(f"[branch-manager] Creating test branch: {test_branch_name}")
    print(f"[branch-manager] Cloning from snapshot: {snapshot_name}")

    neon_project = _get_project_id()

    snap_branch = _find_branch_by_name(neon_project, snapshot_name)
    if not snap_branch:
        print(f"ERROR: Snapshot branch '{snapshot_name}' not found in Neon.", file=sys.stderr)
        print("Run 'list_snapshots' to see available snapshots.", file=sys.stderr)
        sys.exit(1)

    existing = _find_branch_by_name(neon_project, test_branch_name)
    if existing:
        print(f"WARNING: Test branch '{test_branch_name}' already exists. Delete it first.")
        conn_uri = _build_conn_uri_for_branch(neon_project, existing["id"])
        _print_test_branch_created(test_branch_name, existing["id"], snapshot_name, conn_uri)
        return

    branch_id, conn_uri = _create_branch(neon_project, test_branch_name, snap_branch["id"])
    _print_test_branch_created(test_branch_name, branch_id, snapshot_name, conn_uri)


def cmd_delete_test_branch(args: argparse.Namespace) -> None:
    """Delete a test branch after analysis."""
    branch_name = args.branch
    if not branch_name.startswith("test_"):
        print(
            f"ERROR: '{branch_name}' does not look like a test branch (must start with 'test_').\n"
            "Snapshot branches cannot be deleted via this command.",
            file=sys.stderr,
        )
        sys.exit(1)

    neon_project = _get_project_id()
    branch = _find_branch_by_name(neon_project, branch_name)
    if not branch:
        print(f"[branch-manager] Branch '{branch_name}' not found in Neon — nothing to delete.")
        return

    _delete_branch(neon_project, branch["id"])
    _registry_remove(branch_name)
    print(f"[branch-manager] Deleted test branch: {branch_name}")


def cmd_delete_snapshot(args: argparse.Namespace) -> None:
    """Delete a snapshot branch from Neon and remove it from the registry."""
    snap_name = args.snapshot

    entry = _registry_get(snap_name)
    if not entry:
        print(
            f"ERROR: Snapshot '{snap_name}' not found in registry.\n"
            "Run 'list_snapshots' to see available snapshots.",
            file=sys.stderr,
        )
        sys.exit(1)

    neon_project = _get_project_id()
    branch = _find_branch_by_name(neon_project, snap_name)

    if branch:
        # Safety: refuse if this branch has children in Neon.
        # Neon's parent-child tree means deleting a parent also prevents
        # deleting it when children exist — see branch management spec.
        all_branches = _list_branches(neon_project)
        children = [b["name"] for b in all_branches if b.get("parent_id") == branch["id"]]
        if children:
            print(
                f"ERROR: '{snap_name}' has {len(children)} child branch(es) — cannot delete:\n"
                + "\n".join(f"  {c}" for c in children),
                file=sys.stderr,
            )
            print(
                "Delete child branches first (use delete_test_branch for test_ branches, "
                "or delete_snapshot for snapshot children), then retry.",
                file=sys.stderr,
            )
            sys.exit(1)

        _delete_branch(neon_project, branch["id"])
        print(f"[branch-manager] Deleted Neon branch: {snap_name} ({branch['id']})")
    else:
        print(
            f"[branch-manager] '{snap_name}' not found in Neon — "
            "removing stale registry entry."
        )

    _registry_remove(snap_name)
    print(f"[branch-manager] Removed from registry: {snap_name}")


def cmd_promote_to_snapshot(args: argparse.Namespace) -> None:
    """Create a snapshot from a verified test branch, then delete the test branch."""
    test_branch_name = args.branch
    project_code = test_branch_name.split("_")[1].upper()
    phase = args.phase.lower()
    pass_ = getattr(args, "pass").lower()
    row = args.row.upper()

    snap_name = f"snap_{project_code}_{phase}_{pass_}_{row}"
    print(f"[branch-manager] Promoting '{test_branch_name}' → snapshot '{snap_name}'")

    neon_project = _get_project_id()

    test_branch = _find_branch_by_name(neon_project, test_branch_name)
    if not test_branch:
        print(f"ERROR: Test branch '{test_branch_name}' not found in Neon.", file=sys.stderr)
        sys.exit(1)

    existing_snap = _find_branch_by_name(neon_project, snap_name)
    if existing_snap:
        print(
            f"ERROR: Snapshot '{snap_name}' already exists. "
            "Delete it first if you need to rebuild.",
            file=sys.stderr,
        )
        sys.exit(1)

    branch_id, conn_uri = _create_branch(neon_project, snap_name, test_branch["id"])

    entry = {
        "name": snap_name,
        "project_id": project_code,
        "phase": phase,
        "pass": pass_,
        "row": row,
        "state_description": args.description or f"Post-{pass_}: {project_code} {row} — promoted from {test_branch_name}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "VERIFIED",
        "ver_criteria_passed": [],
        "neon_branch_id": branch_id,
        "neon_project_id": neon_project,
    }
    _registry_add_snapshot(entry)

    _delete_branch(neon_project, test_branch["id"])
    print(f"[branch-manager] Deleted test branch: {test_branch_name}")
    _print_snapshot_created(snap_name, branch_id, conn_uri)


def cmd_rename_branch(args: argparse.Namespace) -> None:
    """Rename a test branch in Neon (does not affect snapshots)."""
    old_name = args.branch
    new_name = args.new_name

    if not old_name.startswith("test_"):
        print(
            f"ERROR: '{old_name}' does not look like a test branch (must start with 'test_').\n"
            "Snapshot branches cannot be renamed via this command.",
            file=sys.stderr,
        )
        sys.exit(1)

    neon_project = _get_project_id()
    branch = _find_branch_by_name(neon_project, old_name)
    if not branch:
        print(f"ERROR: Branch '{old_name}' not found in Neon.", file=sys.stderr)
        sys.exit(1)

    _neon_request(
        "PATCH",
        f"/projects/{neon_project}/branches/{branch['id']}",
        body={"branch": {"name": new_name}},
    )
    print(f"[branch-manager] Renamed '{old_name}' → '{new_name}'")


def cmd_list_snapshots(args: argparse.Namespace) -> None:
    """List all snapshot branches from the local registry."""
    registry = _load_registry()
    snapshots = registry.get("snapshots", [])
    if not snapshots:
        print("[branch-manager] No snapshots registered yet.")
        return

    col_name = max(len(s["name"]) for s in snapshots)
    col_status = 10
    col_created = 20
    header = (
        f"{'Name':<{col_name}}  {'Status':<{col_status}}  {'Created':<{col_created}}  VER criteria"
    )
    print(header)
    print("-" * len(header))
    for s in sorted(snapshots, key=lambda x: x["name"]):
        created = s.get("created_at", "")[:19].replace("T", " ")
        ver = ", ".join(s.get("ver_criteria_passed", [])) or "—"
        print(f"{s['name']:<{col_name}}  {s['status']:<{col_status}}  {created:<{col_created}}  {ver}")


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _build_conn_uri_for_branch(project_id: str, branch_id: str) -> str:
    data = _neon_request("GET", f"/projects/{project_id}/branches/{branch_id}/endpoints")
    endpoints = data.get("endpoints", [])
    if not endpoints:
        return "(no endpoint found)"
    host = endpoints[0]["host"]
    # Use DATABASE_URL_MAIN (permanent main URL) as the credential template per
    # spec Rule 4. Fall back to NEON_DATABASE_URL if DATABASE_URL_MAIN is not set.
    main_url = (
        os.environ.get("DATABASE_URL_MAIN")
        or os.environ.get("NEON_DATABASE_URL", "")
    )
    if main_url and host:
        return re.sub(r"@[^/]+/", f"@{host}/", main_url)
    return f"(endpoint: {host})"


def _print_snapshot_created(name: str, branch_id: str, conn_uri: str) -> None:
    print(f"\n[branch-manager] Snapshot created successfully")
    print(f"  Name:      {name}")
    print(f"  Branch ID: {branch_id}")
    print(f"\n  Connection string (set as NEON_DATABASE_URL for this branch):")
    print(f"  {conn_uri}")
    print(f"\n  Registry updated: {REGISTRY_PATH}")


def _print_test_branch_created(
    name: str, branch_id: str, cloned_from: str, conn_uri: str
) -> None:
    print(f"\n[branch-manager] Test branch created successfully")
    print(f"  Name:        {name}")
    print(f"  Branch ID:   {branch_id}")
    print(f"  Cloned from: {cloned_from}")
    print(f"\n  Set NEON_DATABASE_URL to this connection string before running your test:")
    print(f"  {conn_uri}")
    print(f"\n  When done: python sysengage/scripts/branch_manager.py delete_test_branch --branch {name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="branch_manager.py",
        description="Neon branch management for SysEngage test isolation.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # create_snapshot
    p = sub.add_parser("create_snapshot", help="Create a snapshot from the current main branch.")
    p.add_argument("--project", required=True, help="Project code, e.g. PMT")
    p.add_argument("--phase", required=True, help="Phase identifier, e.g. ph03")
    p.add_argument("--pass", required=True, dest="pass", help="Pass identifier, e.g. 3a")
    p.add_argument("--row", required=True, help="Row identifier, e.g. R1")
    p.add_argument("--description", default="", help="Human-readable state description")

    # create_test_branch
    p = sub.add_parser("create_test_branch", help="Create a test branch from a snapshot.")
    p.add_argument("--snapshot", required=True, help="Snapshot name, e.g. snap_PMT_ph03_3a_R1")
    p.add_argument("--scenario", required=True, help="Scenario descriptor — must be prefixed with the pass being tested, e.g. Ph3b_Dedup_On")

    # rename_branch
    p = sub.add_parser("rename_branch", help="Rename a test branch in Neon.")
    p.add_argument("--branch", required=True, help="Current test branch name")
    p.add_argument("--new-name", required=True, dest="new_name", help="New test branch name")

    # delete_test_branch
    p = sub.add_parser("delete_test_branch", help="Delete a test branch after analysis.")
    p.add_argument("--branch", required=True, help="Test branch name, e.g. test_PMT_ph03_3a_R1_dedup_on")

    # delete_snapshot
    p = sub.add_parser(
        "delete_snapshot",
        help="Delete a snapshot branch from Neon and remove it from the registry.",
    )
    p.add_argument("--snapshot", required=True, help="Snapshot name as it appears in the registry")

    # promote_to_snapshot
    p = sub.add_parser("promote_to_snapshot", help="Promote a verified test branch to a snapshot.")
    p.add_argument("--branch", required=True, help="Test branch name to promote")
    p.add_argument("--phase", required=True, help="Phase for the new snapshot, e.g. ph03")
    p.add_argument("--pass", required=True, dest="pass", help="Pass for the new snapshot, e.g. 3b")
    p.add_argument("--row", required=True, help="Row for the new snapshot, e.g. R1")
    p.add_argument("--description", default="", help="Human-readable state description")

    # list_snapshots
    sub.add_parser("list_snapshots", help="List all registered snapshot branches.")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Warn if DATABASE_URL_MAIN is not set — spec Rule 4 requires it as the
    # permanent safe copy of the main branch connection string.
    if args.command != "list_snapshots" and not os.environ.get("DATABASE_URL_MAIN"):
        print(
            "WARNING: DATABASE_URL_MAIN is not set. "
            "Set it in Replit Secrets to the main branch connection string "
            "so it is never accidentally overwritten during test branch operations "
            "(spec §5 Rule 4).",
            file=sys.stderr,
        )

    dispatch = {
        "create_snapshot": cmd_create_snapshot,
        "create_test_branch": cmd_create_test_branch,
        "rename_branch": cmd_rename_branch,
        "delete_test_branch": cmd_delete_test_branch,
        "delete_snapshot": cmd_delete_snapshot,
        "promote_to_snapshot": cmd_promote_to_snapshot,
        "list_snapshots": cmd_list_snapshots,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
