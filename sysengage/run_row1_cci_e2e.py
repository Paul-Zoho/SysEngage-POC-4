"""
One-shot CCI Construction E2E runner for ROW1_E2E project, row_ref=1.
Writes result to /tmp/row1_cci_result.json and logs to /tmp/row1_cci_e2e.log.
"""
import json
import sys
import time

sys.path.insert(0, "/home/runner/workspace/sysengage")

from mechanisms.cci_construction import run

print("Starting CCI Construction for ROW1_E2E row_ref=1 ...", flush=True)
t0 = time.time()

result = run(
    project_id="ROW1_E2E",
    practitioner_id="SH_ROW1",
    row_ref=1,
)

elapsed = round(time.time() - t0, 1)
print(f"Finished in {elapsed}s", flush=True)
print(json.dumps(result, default=str, indent=2)[:2000], flush=True)

with open("/tmp/row1_cci_result.json", "w") as f:
    json.dump(result, f, default=str, indent=2)

print("Result written to /tmp/row1_cci_result.json", flush=True)
