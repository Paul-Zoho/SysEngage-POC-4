---
name: Project ID conventions
description: The project_id stored in Signal/CCI records uses an _E2E suffix that differs from the snapshot registry project_id label.
---

The snapshot registry `project_id` field is a short label (e.g. `"PMT"`, `"NQPS"`, `"ROW"`).
The actual `project_id` written into Signal, CCI, and AnalysisPass records uses the `_E2E` suffix form.

| Registry label | Actual DB project_id |
|---|---|
| PMT  | PMT_E2E  |
| NQPS | NQPS_E2E |
| ROW  | ROW1_E2E |

**Why:** The E2E runners were written first with the `_E2E` suffix; the registry labels were added later as human-readable identifiers and were not kept in sync.

**How to apply:** When writing a new project-specific runner, always use `PROJECT_ID = "<PROJECT>_E2E"`. Do not use the bare registry label — it will silently find zero Signals and produce 0 CCIs with status=Completed (no error raised).

Verified by querying `SELECT DISTINCT project_id FROM signal` on the main Neon DB (2026-05-26).
