"""
run_pmt_task37.py — Task #37 combined runner.

Runs both experiments in sequence:
  Step A: Matching determinism check   (run_pmt_det_check.py)
  Step B: Surgical attribution experiment (run_pmt_attr_r2.py)

Step B is skipped if Step A fails (determinism must hold before attribution is meaningful).

Invocation (from workspace root):
    python -u sysengage/run_pmt_task37.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SYSENGAGE_DIR = Path(__file__).parent
OUT_DIR       = SYSENGAGE_DIR.parent / "verification_outputs"
SEP           = "=" * 65
DET_OUT       = OUT_DIR / "PMT_Matching_Determinism_Check.json"


def _run(script: str, label: str) -> int:
    print(SEP, flush=True)
    print(f"[task37] Running {label} …", flush=True)
    print(SEP, flush=True)
    result = subprocess.run(
        [sys.executable, "-u", str(SYSENGAGE_DIR / script)],
        check=False,
    )
    return result.returncode


# ---------------------------------------------------------------------------
# Step A — Determinism check
# ---------------------------------------------------------------------------

rc_a = _run("run_pmt_det_check.py", "Step A: Determinism check")
if rc_a != 0:
    print(f"\n[task37] Step A FAILED (exit code {rc_a}) — aborting.", file=sys.stderr)
    sys.exit(rc_a)

# Verify the output says determinism passed
if DET_OUT.exists():
    with open(DET_OUT) as f:
        det = json.load(f)
    if not det.get("determinism_passed"):
        ndiff = det.get("diff_count", "?")
        print(
            f"\n[task37] Step A: determinism_passed=False ({ndiff} diffs) — aborting Step B.",
            file=sys.stderr,
        )
        sys.exit(2)
    print(f"\n[task37] Step A PASSED (determinism_passed=True)  →  proceeding to Step B.\n", flush=True)
else:
    print("[task37] WARNING: determinism output file not found; proceeding to Step B anyway.", flush=True)


# ---------------------------------------------------------------------------
# Step B — Attribution experiment
# ---------------------------------------------------------------------------

rc_b = _run("run_pmt_attr_r2.py", "Step B: Attribution experiment")
if rc_b != 0:
    print(f"\n[task37] Step B FAILED (exit code {rc_b}).", file=sys.stderr)
    sys.exit(rc_b)

# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[task37] Task #37 COMPLETE", flush=True)
print(SEP, flush=True)

attr_out = OUT_DIR / "PMT_Matching_Attribution_Analysis_R2.json"
if attr_out.exists():
    with open(attr_out) as f:
        attr = json.load(f)
    stab = attr.get("stability_summary", {})
    print(f"[task37]   Stability — match all 3 : {stab.get('match_all_3', {}).get('count', '?')}", flush=True)
    print(f"[task37]              match 2 of 3 : {stab.get('match_2_of_3', {}).get('count', '?')}", flush=True)
    print(f"[task37]              match 1 of 3 : {stab.get('match_1_of_3', {}).get('count', '?')}", flush=True)
    print(f"[task37]              match none   : {stab.get('match_none', {}).get('count', '?')}", flush=True)
    print(f"[task37]   Output: {attr_out.name}", flush=True)
if DET_OUT.exists():
    print(f"[task37]   Output: {DET_OUT.name}", flush=True)
