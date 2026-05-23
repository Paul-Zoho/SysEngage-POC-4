"""
run_pmt_cci_r1_branch_test.py — Branch-isolated CCI Construction comparison for PMT Row 1.

Creates a Neon snapshot of the current main branch state, then clones two disposable
test branches to compare CCI Construction output with and without deduplication.

Produces two JSON ledger files (dedup_on and dedup_off) in verification_outputs/.

Invocation (from workspace root):
    python -u sysengage/run_pmt_cci_r1_branch_test.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
SYSENGAGE = Path(__file__).parent
ROOT = SYSENGAGE.parent
sys.path.insert(0, str(SYSENGAGE))

from scripts.branch_manager import (
    _create_branch,
    _delete_branch,
    _find_branch_by_name,
    _get_primary_branch,
    _get_project_id,
    _registry_add_snapshot,
    _registry_remove,
    REGISTRY_PATH,
)
from core.output_naming import generate_filename

OUT_DIR = ROOT / "verification_outputs"
SNAP_NAME = "snap_PMT_ph03_3a_R1"

SCENARIOS = [
    {
        "label": "dedup_on",
        "branch": "test_PMT_ph03_3a_R1_dedup_on",
        "skip_dedup": False,
        "pass_": "3b",
    },
    {
        "label": "dedup_off",
        "branch": "test_PMT_ph03_3a_R1_dedup_off",
        "skip_dedup": True,
        "pass_": "3b",
    },
]


def banner(msg: str) -> None:
    print(f"\n{'─' * 60}", flush=True)
    print(f"  {msg}", flush=True)
    print(f"{'─' * 60}", flush=True)


def ensure_snapshot(neon_project: str) -> str:
    """
    Return the Neon branch ID for SNAP_NAME, creating it if necessary.
    Returns the branch ID.
    """
    banner(f"SNAPSHOT: {SNAP_NAME}")
    existing = _find_branch_by_name(neon_project, SNAP_NAME)
    if existing:
        bid = existing["id"]
        print(f"[orchestrator] Snapshot already exists — reusing (id={bid})", flush=True)
        return bid

    primary = _get_primary_branch(neon_project)
    print(f"[orchestrator] Cloning from primary: {primary['name']} ({primary['id']})", flush=True)
    branch_id, conn_uri = _create_branch(neon_project, SNAP_NAME, primary["id"])
    print(f"[orchestrator] Snapshot created: id={branch_id}", flush=True)

    from datetime import datetime, timezone
    _registry_add_snapshot({
        "name": SNAP_NAME,
        "project_id": "PMT",
        "phase": "ph03",
        "pass": "3a",
        "row": "R1",
        "state_description": "Post-3a: PMT R1 state (source capture + prior CCI runs)",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "VERIFIED",
        "ver_criteria_passed": [],
        "neon_branch_id": branch_id,
        "neon_project_id": neon_project,
    })
    print(f"[orchestrator] Registry updated: {REGISTRY_PATH}", flush=True)
    return branch_id


def run_scenario(neon_project: str, snap_branch_id: str, scenario: dict) -> str:
    """
    Clone a test branch from the snapshot, run CCI, export JSON, delete branch.
    Returns the path to the generated JSON file.
    """
    label = scenario["label"]
    branch_name = scenario["branch"]
    skip_dedup = scenario["skip_dedup"]

    banner(f"SCENARIO: {label}  (skip_deduplication={skip_dedup})")

    # ── create test branch ────────────────────────────────────────────────────
    existing = _find_branch_by_name(neon_project, branch_name)
    if existing:
        print(f"[orchestrator] WARNING: branch '{branch_name}' already exists — deleting first", flush=True)
        _delete_branch(neon_project, existing["id"])

    print(f"[orchestrator] Creating test branch: {branch_name}", flush=True)
    branch_id, conn_uri = _create_branch(neon_project, branch_name, snap_branch_id)
    print(f"[orchestrator] Test branch ready: id={branch_id}", flush=True)

    # ── run CCI construction against test branch ───────────────────────────────
    print(f"[orchestrator] Running CCI construction (skip_dedup={skip_dedup})...", flush=True)

    runner_script = str(SYSENGAGE / "_cci_runner_subprocess.py")
    env = {**os.environ, "NEON_DATABASE_URL": conn_uri}

    result = subprocess.run(
        [sys.executable, "-u", runner_script,
         "--skip-dedup", str(skip_dedup),
         "--label", label],
        env=env,
        capture_output=False,  # stream directly to console
    )
    if result.returncode != 0:
        print(f"[orchestrator] ERROR: CCI runner exited with code {result.returncode}", file=sys.stderr, flush=True)
        print(f"[orchestrator] Cleaning up test branch: {branch_name}", flush=True)
        _delete_branch(neon_project, branch_id)
        sys.exit(result.returncode)

    # ── export JSON ledger from test branch ────────────────────────────────────
    print(f"[orchestrator] Exporting ledger from test branch...", flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    basename = generate_filename(
        project_id="PMT",
        phase="03",
        pass_=scenario["pass_"],
        row="1",
        out_dir=str(OUT_DIR),
    )
    json_path = OUT_DIR / basename

    export_result_path = str(SYSENGAGE / "_cci_export_subprocess.py")
    result2 = subprocess.run(
        [sys.executable, "-u", export_result_path,
         "--out", str(json_path)],
        env=env,
        capture_output=False,
    )
    if result2.returncode != 0:
        print(f"[orchestrator] ERROR: ledger export failed (code {result2.returncode})", file=sys.stderr, flush=True)

    # ── clean up test branch ───────────────────────────────────────────────────
    print(f"[orchestrator] Deleting test branch: {branch_name}", flush=True)
    _delete_branch(neon_project, branch_id)
    _registry_remove(branch_name)
    print(f"[orchestrator] Test branch deleted.", flush=True)

    return str(json_path)


def main() -> None:
    print("[orchestrator] PMT Row 1 branch-isolated CCI comparison", flush=True)
    print(f"[orchestrator] Scenarios: {[s['label'] for s in SCENARIOS]}", flush=True)

    neon_project = _get_project_id()
    print(f"[orchestrator] Neon project: {neon_project}", flush=True)

    snap_branch_id = ensure_snapshot(neon_project)

    outputs: list[str] = []
    for scenario in SCENARIOS:
        json_path = run_scenario(neon_project, snap_branch_id, scenario)
        outputs.append(json_path)

    banner("DONE")
    print("[orchestrator] Generated files:", flush=True)
    for p in outputs:
        print(f"  {p}", flush=True)
    print(flush=True)


if __name__ == "__main__":
    main()
