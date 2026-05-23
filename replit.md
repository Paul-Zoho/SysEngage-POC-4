# SysEngage

AI-powered Systems Engineering tool that runs stateful mechanism passes (Source Capture, CCI Construction, Row-Lens Re-Analysis) against a Neon PostgreSQL ledger.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 8080)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `python -u sysengage/run_row1_cci_e2e.py` — run CCI Construction E2E (ROW project, Row 1, skip_dedup=True)
- `python -u sysengage/run_pmt_cci_r1.py` — run CCI Construction for PMT Row 1

## Required Secrets

| Secret | Purpose |
|---|---|
| `NEON_DATABASE_URL` | Neon Postgres connection string (main development branch) |
| `NEON_API_KEY` | Neon API key — required for branch manager (test isolation) |
| `ANTHROPIC_API_KEY` | Claude API key for AI mechanism steps |
| `SESSION_SECRET` | Express session secret |

**`DATABASE_URL_MAIN` convention:** The main development connection string lives in `NEON_DATABASE_URL`. When running test branches, set `NEON_DATABASE_URL` to the test branch connection string for the duration of the test. Never overwrite `NEON_DATABASE_URL` with a test branch value permanently — restore it after the test.

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5 (port 8080)
- DB: PostgreSQL (Neon) + SQLAlchemy ORM + Alembic migrations
- Python 3.12 — all mechanism code in `sysengage/`
- AI: Anthropic Claude (via `core/ai_client.py`)
- Validation: Zod (`zod/v4`), Pydantic (Python)
- Build: esbuild (CJS bundle)

## Where things live

```
sysengage/
  core/              — DB session, AI client, ledger helpers, output naming
  mechanisms/        — Pass implementations (source_capture, cci_construction, row_lens_source_reanalysis)
  models/            — SQLAlchemy ORM models
  tests/             — pytest test suites per mechanism
  scripts/           — Utility scripts (branch_manager.py)
  test_infrastructure/ — snapshot_registry.json (Neon branch registry)
  run_row1_cci_e2e.py  — ROW project E2E runner
  run_pmt_cci_r1.py    — PMT Row 1 test runner
artifacts/
  api-server/        — Express API server (TypeScript)
specifications/      — Authoritative spec documents
verification_outputs/ — Ledger JSON exports from test runs
```

- DB schema source of truth: `sysengage/models/` + Alembic migrations in `sysengage/alembic/`
- API contract: OpenAPI spec in `artifacts/api-spec/`

## Neon Branch Management (Test Isolation)

See `specifications/SysEngage_Test_Branch_Management_v0_1.md` for the full spec.

**Core workflow:** snapshot → test branch → run mechanism → analyse → delete branch

```
# 1. Create a clean starting-point snapshot (once, after a verified pass)
python sysengage/scripts/branch_manager.py create_snapshot \
  --project PMT --phase ph03 --pass 3a --row R1

# 2. Clone a disposable test branch for one scenario
python sysengage/scripts/branch_manager.py create_test_branch \
  --snapshot snap_PMT_ph03_3a_R1 --scenario dedup_on
# → outputs the connection string; set NEON_DATABASE_URL to it

# 3. Run your mechanism test against the test branch
python -u sysengage/run_pmt_cci_r1.py

# 4. Analyse output, then delete the test branch
python sysengage/scripts/branch_manager.py delete_test_branch \
  --branch test_PMT_ph03_3a_R1_dedup_on

# List all registered snapshots
python sysengage/scripts/branch_manager.py list_snapshots
```

NEON_PROJECT_ID is auto-detected from NEON_API_KEY if you have a single Neon project. Set it explicitly if you have multiple projects.

## Architecture decisions

- Each mechanism pass is stateful — it reads from and writes to the Neon ledger. Neon branch cloning provides isolated, reproducible test environments without re-running upstream passes.
- `skip_deduplication=True` in the E2E runner is intentional — it surfaces the raw duplicate level before the cluster-based dedup sweep (Step 4) runs. Tests that validate dedup behaviour use separate runners with `skip_deduplication=False`.
- DB-backed tests must be run one test at a time (not as a full suite) due to Neon connection-pool interference across tests in the same process. Use the individual test commands documented in each test file.
- `build_cci_data()` in `step6_analysis_pass.py` accepts `execution_warnings=None` (defaults to empty list) for backward compatibility with call sites that predate v0.7.

## Gotchas

- **DB tests crash with exit code -1** when run as a full suite — this is OOM/Neon pool interference. Always run class batches or individual tests.
- **CCI verification criteria tests** (`test_verification_criteria.py`) must be run one at a time: `pytest "tests/cci_construction/test_verification_criteria.py::ClassName::test_name"`.
- **`NEON_DATABASE_URL` and `DATABASE_URL`** — the app reads `NEON_DATABASE_URL` first. `DATABASE_URL` is the Replit Helium fallback. Always update `NEON_DATABASE_URL` when rotating the Neon connection string.
- **Never `pnpm run dev` at workspace root** — individual artifacts run via Replit workflows with `PORT` and `BASE_PATH` wired up.
- **Port**: API server binds to `PORT` env var (workflow sets it); default 8080 in production.

## User preferences

- DB-heavy tests: always run individually or in small batches, never as a full module.
- Output ledger files: always use `generate_filename()` from `core/output_naming.py` — never name files manually.
- Test runners: create project-specific runners (e.g. `run_pmt_cci_r1.py`) rather than modifying the canonical E2E runner.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
- Spec files: `specifications/` — authoritative for all mechanism behaviour
- Snapshot registry: `sysengage/test_infrastructure/snapshot_registry.json`
