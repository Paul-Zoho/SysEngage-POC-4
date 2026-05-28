"""
run_dd_r4.py — Pass 3c Domain Derivation for PMT_E2E, Row 4.

Project-specific runner — does not modify the canonical E2E runner.
Per replit.md: create project-specific runners rather than modifying canonical ones.

Usage:
  python -u sysengage/run_dd_r4.py

Expects NEON_DATABASE_URL to point at the correct branch (main or test).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import mechanisms.domain_derivation as dd
from core.output_naming import generate_filename

PROJECT_ID = "PMT_E2E"
PRACTITIONER_ID = "SH001"
ROW = 4
OUT_DIR = Path(__file__).parent.parent / "verification_outputs"

print(
    f"[runner] Pass 3c Domain Derivation — {PROJECT_ID}  Row {ROW}",
    flush=True,
)
print(flush=True)

try:
    result = dd.run(
        project_id=PROJECT_ID,
        practitioner_id=PRACTITIONER_ID,
        row_ref=ROW,
    )
except Exception as exc:
    print(f"[runner] FAILED: {exc}", file=sys.stderr, flush=True)
    sys.exit(1)

md = result["mechanism_data"]
print(f"[runner] pass_id              = {result['pass_id']}", flush=True)
print(f"[runner] execution_status     = {result['execution_status']}", flush=True)
print(f"[runner] scenario             = {md.get('scenario')}", flush=True)
print(f"[runner] cci_count_input      = {md.get('cci_count_input')}", flush=True)
print(f"[runner] domain_count_produced= {md.get('domain_count_produced')}", flush=True)
print(f"[runner] domain_count_retired = {md.get('domain_count_retired')}", flush=True)
print(
    f"[runner] downstream_rerun_req = {md.get('downstream_rerun_required')}",
    flush=True,
)
print(flush=True)

for d in md.get("domains_produced", []):
    print(
        f"  {d['domain_id']}  {d['name']!r}  "
        f"{d['cci_ref_count']} CCIs  "
        f"cross-cutting={d.get('cross_cutting_cci_count', 0)}",
        flush=True,
    )

if md.get("orphaned_ccis_after_repair"):
    print(
        f"\n[runner] WARNING: orphaned CCIs after repair: {md['orphaned_ccis_after_repair']}",
        flush=True,
    )

import json

OUT_DIR.mkdir(parents=True, exist_ok=True)
out_path = OUT_DIR / generate_filename(
    project_code="PMT",
    phase="ph03",
    pass_name="3c_domain_derivation",
    row=ROW,
    ext="json",
)
with open(out_path, "w") as f:
    json.dump(result, f, indent=2, default=str)

print(f"\n[runner] Output written to: {out_path}", flush=True)
