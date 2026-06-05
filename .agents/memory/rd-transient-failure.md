---
name: RD transient failure after long DD run
description: RD can fail with execution_status=Failed, pass_id=None on first attempt after a long DD run; restarting the runner resumes from RD and succeeds.
---

# RD Transient Failure After DD

## The rule
After a long DD run, the first RD attempt may silently fail returning `{"execution_status": "Failed", "failure_reason": ...}` with no pass_id. Restarting the runner (which reuses the existing test branch) skips all prior steps via idempotency guards and retries RD — which then succeeds.

**Why:** Likely a stale Neon session/connection or cold-start recovery immediately after the heavy DD AI calls exhaust the connection window. Phase 0 (`ensure_*` helpers) or Stage 1 preflight open a new session; if the compute is briefly cold the session handshake times out.

**How to apply:**
- When RD reports `execution_status = Failed, pass_id = None` and the test branch is still alive: just restart the CCI E2E Runner workflow.
- The runner detects the existing branch by `TEST_BRANCH_NAME`, reconstructs the URL, and resumes from RD.
- Do NOT delete the test branch before restarting — the idempotency skip requires the prior Completed pass records to exist.
- The runner now prints `failure_reason` for Failed results (added in the Run 10 debug session), so future failures will self-explain.
