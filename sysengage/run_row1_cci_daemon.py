"""
Double-fork daemon launcher for ROW1_E2E CCI Construction E2E.
Detaches completely from the parent process group so the bash tool
cannot kill it when its shell exits.
"""
import os
import sys

LOG_FILE = "/tmp/row1_cci_e2e.log"
RESULT_FILE = "/tmp/row1_cci_result.json"


def daemonize() -> None:
    # First fork
    pid = os.fork()
    if pid > 0:
        print(f"Daemon PID: {pid}", flush=True)
        sys.exit(0)

    # Detach from parent session
    os.setsid()

    # Second fork (prevents re-acquiring a controlling terminal)
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    # Redirect stdio to log file
    sys.stdout.flush()
    sys.stderr.flush()
    log_fd = os.open(LOG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.dup2(log_fd, sys.stdout.fileno())
    os.dup2(log_fd, sys.stderr.fileno())
    os.close(log_fd)


def worker() -> None:
    import json
    import sys
    import time

    sys.path.insert(0, "/home/runner/workspace/sysengage")

    print("ROW1_E2E CCI E2E daemon started", flush=True)

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

    with open(RESULT_FILE, "w") as f:
        json.dump(result, f, default=str, indent=2)

    print(f"Result written to {RESULT_FILE}", flush=True)


if __name__ == "__main__":
    # If called with --worker, we are inside the daemon
    if "--worker" in sys.argv:
        worker()
    else:
        daemonize()
        # After second fork, exec the worker
        os.execv(sys.executable, [sys.executable, __file__, "--worker"])
