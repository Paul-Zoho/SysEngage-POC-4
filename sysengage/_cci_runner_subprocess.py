"""
_cci_runner_subprocess.py — CCI Construction subprocess worker.

Called by run_pmt_cci_r1_branch_test.py with NEON_DATABASE_URL set to a test branch.
Not intended to be run directly.

Usage:
    python -u sysengage/_cci_runner_subprocess.py --skip-dedup True --label dedup_off
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import mechanisms.cci_construction as cci

PROJECT_ID = "PMT_E2E"
PRACTITIONER_ID = "SH001"
ROW = 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-dedup", required=True,
                        help="True or False — whether to skip deduplication")
    parser.add_argument("--label", default="",
                        help="Scenario label for log output")
    args = parser.parse_args()

    skip_dedup = args.skip_dedup.strip().lower() in ("true", "1", "yes")
    label = args.label or ("dedup_off" if skip_dedup else "dedup_on")

    print(f"[cci-worker:{label}] Running CCI Construction — skip_deduplication={skip_dedup}", flush=True)
    print(f"[cci-worker:{label}] project={PROJECT_ID}  row={ROW}", flush=True)
    print(flush=True)

    try:
        result = cci.run(
            project_id=PROJECT_ID,
            practitioner_id=PRACTITIONER_ID,
            row_ref=ROW,
            skip_deduplication=skip_dedup,
        )
    except Exception as exc:
        print(f"[cci-worker:{label}] FAILED: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    cd = result["cci_data"]
    print(f"[cci-worker:{label}] pass_id           = {result['pass_id']}", flush=True)
    print(f"[cci-worker:{label}] execution_status  = {result['execution_status']}", flush=True)
    print(f"[cci-worker:{label}] ccis_created      = {cd['ccis_created']}", flush=True)
    print(f"[cci-worker:{label}] ccis_merged       = {cd['ccis_merged']}", flush=True)
    print(f"[cci-worker:{label}] batches_processed = {cd['batches_processed']}", flush=True)
    print(f"[cci-worker:{label}] batches_failed    = {cd['batches_failed']}", flush=True)
    print(flush=True)
    print(f"[cci-worker:{label}] Done.", flush=True)


if __name__ == "__main__":
    main()
