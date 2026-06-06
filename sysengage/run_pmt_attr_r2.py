"""
run_pmt_attr_r2.py — PMT Row 2 matching attribution experiment (Task #37 Step B).

Surgical experiment: hold Row 2 derivation fixed (R11's requirements), vary the
Row 1 baseline (R11 / R12 / R13), observe how attribution changes.

Workflow
--------
1.  Read R11's active Row 2 requirements from the verified 3e ledger JSON.
2.  For each baseline (R11, R12, R13):
    a. Clone snap_PMT_ph03_3e_R2_3x_YYYYMMDD → tmp_PMT_attr_{X}.
    b. Spawn _rm_attr_worker.py as subprocess with NEON_DATABASE_URL set to the branch.
    c. Collect per-req refines_refs + match summary from worker output JSON.
    d. Delete the temp branch.
3.  Aggregate results into:
    - Per-requirement attribution table (which baselines each req finds a parent under).
    - Stability buckets: match all 3 / 2 of 3 / 1 of 3 / none.
4.  Write verification_outputs/PMT_Matching_Attribution_Analysis_R2.json.

Invocation (from workspace root):
    python -u sysengage/run_pmt_attr_r2.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SYSENGAGE_DIR = Path(__file__).parent
sys.path.insert(0, str(SYSENGAGE_DIR))
sys.path.insert(0, str(SYSENGAGE_DIR / "scripts"))

import branch_manager as bm

SOURCE_SNAP_PREFIX = "snap_PMT_ph03_3e_R2_3x_"
OUT_DIR            = SYSENGAGE_DIR.parent / "verification_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_OUT       = OUT_DIR / "PMT_Matching_Attribution_Analysis_R2.json"

BASELINES: list[dict[str, str]] = [
    {"project_id": "PMT_E2E_R11", "branch_suffix": "R11", "mode": "rerun"},
    {"project_id": "PMT_E2E_R12", "branch_suffix": "R12", "mode": "substitute"},
    {"project_id": "PMT_E2E_R13", "branch_suffix": "R13", "mode": "substitute"},
]

R11_LEDGER = OUT_DIR / "PMT_Ph03_3e_RequirementMatching_R2_Run4.json"

SEP = "=" * 65


# ---------------------------------------------------------------------------
# Step 1 — Read R11 active Row 2 requirements from verified 3e ledger
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[attr] Step 1 — Read R11 Row 2 requirements from 3e ledger", flush=True)
print(SEP, flush=True)

if not R11_LEDGER.exists():
    print(f"[attr] ERROR: R11 3e ledger not found: {R11_LEDGER}", file=sys.stderr)
    sys.exit(1)

with open(R11_LEDGER) as f:
    r11_data = json.load(f)

r11_row2_active: list[dict] = [
    e["payload"]
    for e in r11_data.get("elements", [])
    if e.get("element_type") == "Requirement"
    and str(e["payload"].get("row_target", "")) == "2"
    and not e["payload"].get("retired_at")
]
SOURCE_REQ_IDS = sorted(r["requirement_id"] for r in r11_row2_active)
print(f"[attr]   Found {len(r11_row2_active)} active R11 Row 2 requirements:", flush=True)
for rid in SOURCE_REQ_IDS:
    print(f"[attr]     {rid}", flush=True)

# Write to a temp file for subprocess workers
_tmp_dir       = Path(tempfile.mkdtemp(prefix="sysengage_attr_"))
source_reqs_json = _tmp_dir / "r11_row2_reqs.json"
with open(source_reqs_json, "w", encoding="utf-8") as f:
    json.dump(r11_row2_active, f)
print(f"[attr]   Source reqs written to: {source_reqs_json}", flush=True)


# ---------------------------------------------------------------------------
# Step 2 — Locate source snapshot
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[attr] Step 2 — Locate source snapshot", flush=True)
print(SEP, flush=True)

neon_project = bm._get_project_id()

source_branch = None
for candidate in bm._neon_request("GET", f"/projects/{neon_project}/branches").get("branches", []):
    if candidate.get("name", "").startswith(SOURCE_SNAP_PREFIX):
        source_branch = candidate
        break

if not source_branch:
    print(f"[attr] ERROR: No branch matching '{SOURCE_SNAP_PREFIX}*' found.", file=sys.stderr)
    sys.exit(1)

SOURCE_SNAP     = source_branch["name"]
source_branch_id = source_branch["id"]
print(f"[attr]   Source: {SOURCE_SNAP} ({source_branch_id})", flush=True)


# ---------------------------------------------------------------------------
# Step 3 — Run each baseline (sequential: clone → subprocess → delete)
# ---------------------------------------------------------------------------

def _get_branch_url(neon_project: str, branch_id: str) -> str:
    """Return a connection URL for a branch, sanitised for Neon PgBouncer."""
    ep_data  = bm._neon_request("GET", f"/projects/{neon_project}/branches/{branch_id}/endpoints")
    endpoints = ep_data.get("endpoints", [])
    if not endpoints:
        raise RuntimeError(f"Branch {branch_id} has no endpoint.")
    test_host = endpoints[0]["host"]
    base_url  = os.environ.get("NEON_DATABASE_URL", "")
    import re
    url = re.sub(r"@[^/?]+", f"@{test_host}", base_url)
    url = url.replace("channel_binding=require", "channel_binding=prefer")
    return url


def _run_baseline(baseline: dict[str, str], tmp_dir: Path) -> dict[str, Any]:
    project_id   = baseline["project_id"]
    suffix       = baseline["branch_suffix"]
    mode         = baseline["mode"]
    branch_name  = f"tmp_PMT_attr_{suffix}"
    out_file     = tmp_dir / f"attr_{suffix}.json"

    print(SEP, flush=True)
    print(f"[attr] Baseline {suffix}: mode={mode}  project={project_id}", flush=True)
    print(SEP, flush=True)

    # Remove stale branch if present
    existing = bm._find_branch_by_name(neon_project, branch_name)
    if existing:
        bm._delete_branch(neon_project, existing["id"])
        print(f"[attr]   Removed stale {branch_name}", flush=True)

    # Clone from 3e snapshot
    branch_id, branch_url = bm._create_branch(neon_project, branch_name, source_branch_id)
    print(f"[attr]   Created {branch_name} ({branch_id})", flush=True)

    try:
        # Spawn worker subprocess
        env = {**os.environ, "NEON_DATABASE_URL": branch_url}
        worker = str(SYSENGAGE_DIR / "_rm_attr_worker.py")
        cmd = [
            sys.executable, "-u", worker,
            "--mode", mode,
            "--target-project", project_id,
            "--source-reqs-json", str(source_reqs_json),
            "--out-file", str(out_file),
        ]
        print(f"[attr]   Spawning worker: {' '.join(cmd[-8:])}", flush=True)
        result = subprocess.run(cmd, env=env, check=False)
        if result.returncode != 0:
            print(
                f"[attr] ERROR: worker for {suffix} exited with code {result.returncode}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Read worker output
        with open(out_file) as f:
            data: dict[str, Any] = json.load(f)
        print(f"[attr]   {suffix}: refine={data['match_summary']['refine']}"
              f"  no_match={data['match_summary']['no_match']}"
              f"  flagged={data['match_summary']['flagged']}", flush=True)
        return data

    finally:
        # Delete the temp branch whether the worker succeeded or failed
        bm._delete_branch(neon_project, branch_id)
        print(f"[attr]   Deleted {branch_name} ({branch_id})", flush=True)


baseline_results: list[dict[str, Any]] = []
for bl in BASELINES:
    baseline_results.append(_run_baseline(bl, _tmp_dir))

print(flush=True)


# ---------------------------------------------------------------------------
# Step 4 — Aggregate attribution analysis
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[attr] Step 4 — Aggregate attribution", flush=True)
print(SEP, flush=True)

# Index results by project_id
results_by_project = {r["target_project"]: r for r in baseline_results}
baseline_order = [bl["project_id"] for bl in BASELINES]

# Build per-requirement cross-baseline view
per_req: dict[str, dict[str, Any]] = {}
for rid in SOURCE_REQ_IDS:
    per_req[rid] = {}
    for pid in baseline_order:
        res = results_by_project.get(pid, {})
        # Use refines_refs_by_source_id (keyed by original R11 IDs) when present;
        # fall back to refines_refs for backward compatibility.
        refines_lookup = res.get("refines_refs_by_source_id") or res.get("refines_refs", {})
        refines = refines_lookup.get(rid, [])
        # Also look up the detailed outcome (per_requirement uses original R11 IDs via id_map)
        outcome = next(
            (r["outcome"] for r in res.get("per_requirement", [])
             if r["requirement_id"] == rid),
            "no_match",
        )
        per_req[rid][pid] = {
            "outcome": outcome,
            "matched_parent_ids": refines,
        }

# Stability buckets
def _refine_count(rid: str) -> int:
    return sum(
        1 for pid in baseline_order
        if per_req[rid][pid]["outcome"] == "refine"
    )

match_all_3  = [rid for rid in SOURCE_REQ_IDS if _refine_count(rid) == 3]
match_2_of_3 = [rid for rid in SOURCE_REQ_IDS if _refine_count(rid) == 2]
match_1_of_3 = [rid for rid in SOURCE_REQ_IDS if _refine_count(rid) == 1]
match_none   = [rid for rid in SOURCE_REQ_IDS if _refine_count(rid) == 0]

print(f"[attr]   match all 3 baselines  : {match_all_3}", flush=True)
print(f"[attr]   match 2 of 3 baselines : {match_2_of_3}", flush=True)
print(f"[attr]   match 1 of 3 baselines : {match_1_of_3}", flush=True)
print(f"[attr]   match none             : {match_none}", flush=True)

print(flush=True)
print("[attr]   Per-requirement breakdown:", flush=True)
header = f"  {'ReqID':8}  " + "  ".join(f"{pid[-3:]}" for pid in baseline_order)
print(f"[attr]{header}", flush=True)
for rid in SOURCE_REQ_IDS:
    cells = []
    for pid in baseline_order:
        out = per_req[rid][pid]["outcome"]
        parents = per_req[rid][pid]["matched_parent_ids"]
        cell = f"{out[:6]:6}({','.join(parents) or '-':6})"
        cells.append(cell)
    row_str = "  ".join(cells)
    print(f"[attr]   {rid:8}  {row_str}", flush=True)


# ---------------------------------------------------------------------------
# Step 5 — Write analysis JSON
# ---------------------------------------------------------------------------

analysis: dict[str, Any] = {
    "experiment": "PMT_Matching_Attribution_Analysis_R2",
    "description": (
        "Row 2 derivation held fixed at PMT_E2E_R11; Row 1 baseline varied "
        "across PMT_E2E_R11 / PMT_E2E_R12 / PMT_E2E_R13. "
        "Measures which Row 2 requirements find a parent under each baseline."
    ),
    "source_row2_derivation": "PMT_E2E_R11",
    "source_snapshot": SOURCE_SNAP,
    "baselines": baseline_order,
    "ran_at": datetime.now(timezone.utc).isoformat(),
    "source_requirement_ids": SOURCE_REQ_IDS,
    "per_requirement": per_req,
    "stability_summary": {
        "match_all_3":  {"count": len(match_all_3),  "requirements": match_all_3},
        "match_2_of_3": {"count": len(match_2_of_3), "requirements": match_2_of_3},
        "match_1_of_3": {"count": len(match_1_of_3), "requirements": match_1_of_3},
        "match_none":   {"count": len(match_none),   "requirements": match_none},
    },
    "baseline_summaries": {
        r["target_project"]: r["match_summary"] for r in baseline_results
    },
    "ledger_basenames": {
        r["target_project"]: r["ledger_basename"] for r in baseline_results
    },
}

with open(ANALYSIS_OUT, "w", encoding="utf-8", newline="\n") as f:
    json.dump(analysis, f, indent=2)
print(f"\n[attr]   Analysis written: {ANALYSIS_OUT.name}", flush=True)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[attr] ATTRIBUTION EXPERIMENT COMPLETE", flush=True)
print(SEP, flush=True)
print(f"[attr]   Source: {len(SOURCE_REQ_IDS)} R11 Row 2 reqs × 3 Row 1 baselines", flush=True)
print(f"[attr]   Match all 3  : {len(match_all_3)}  {match_all_3}", flush=True)
print(f"[attr]   Match 2 of 3 : {len(match_2_of_3)}  {match_2_of_3}", flush=True)
print(f"[attr]   Match 1 of 3 : {len(match_1_of_3)}  {match_1_of_3}", flush=True)
print(f"[attr]   Match none   : {len(match_none)}  {match_none}", flush=True)
print(f"[attr]   Output: {ANALYSIS_OUT.name}", flush=True)
