# SysEngage Row 4 Applied to SysEngage

**Worked example — Row 4 framework applied to SysEngage as the project being analysed**

Filename: SysEngage_Row_4_Applied_to_SysEngage_v0_2.docx

Version: 0.2 (F11 + F18 resolution cycle)

Date: 6 May 2026

**Purpose. **Records the Row 4 architectural commitments for SysEngage as a software product. Applies the framework specified in SysEngage_Row_4_Understanding_v0_1.docx to SysEngage itself, locking technology stack, persistence, deployment, integration patterns, and conventions for the v1 prototype build. These commitments constrain every mechanism's Row 4 implementation per the common-foundations pattern (Row 4 Understanding §9).

**Status. **v0.3 — adds the connection-lifecycle pointer in §5 (Common Implementation Reference §1). v0.2 applied F11 and F18 resolutions per Practitioner direction 6 May 2026 during Replit Agent build cycle. Identifier conventions corrected to canonical ledger spec v2.9 patterns; CCI ci_id format locked to JSON Schema structured form. No other changes from v0.1 — provisional status of other commitments preserved.

**Changes from v0.1. **(1) F11 resolution: CCI ci_id format = ^CCI-ROW[1-6]-C-(What|How|Where|Who|When|Why)-\d{3}$ per canonical ledger spec v2.9 JSON Schema (Appendix C). Affects §5 (Tracker references) and §7 (Tracker references). (2) F18 resolution: identifier prefix patterns aligned with canonical ledger spec v2.9 — Source ^S\d{3}$, Segment ^SEG\d{3}$, SourceAtom ^SA\d{3}$, AnalysisPass ^P\d{3}$. v0.1 had restated SRC###/ATM###/AP### from memory; corrected here. Affects §5 (persistence commitment narrative).

**Companion artefacts. **Row 4 Understanding (framework) — SysEngage_Row_4_Understanding_v0_1.docx (unchanged). Mechanism Implementation Spec (first mechanism) — SysEngage_Row_4_Mechanism_Source_Capture_v0_2.docx (also revised in F11/F18 resolution cycle). Replit Agent handoff entry point — replit.md (in repository root, not a docx artefact; out of authoring scope as of 6 May 2026 since Replit Agent now maintains it).

## 1. Stop-Point Declaration

**Per Row 4 Understanding §2: **Practitioner selects stop-point determining how far Row 4 work proceeds.

| **Selected stop-point** | Standard — Row 4 Applied + per-mechanism Implementation Spec at depth tier (i)+ (architectural specification + verification criteria + test fixtures) |
| --- | --- |
| **Rationale** | v1 SysEngage build is a prototype — needs to validate that the production pattern (Row 4 specs → AI-coding-agent build) actually works. Standard stop-point lets us hand specs to Replit Agent and observe the build. Architectural-only would defer the test; spec-and-build would require automated invocation infrastructure not yet built. |
| **Target AI coding agent** | Replit Agent (Practitioner uses Replit for SysEngage build). Per Row 4 Understanding §3.2 — handoff entry-point file is replit.md. |
| **Handoff approach** | Manual — Practitioner ensures replit.md exists with project context; opens project in Replit; Replit Agent reads replit.md and the referenced specs; Practitioner iterates with Agent in Replit. |
| **Iteration model** | Practitioner reviews Agent-generated code in Replit; uses Plan Mode for architectural review before implementation execution; corrects mid-stream when Agent diverges from specs (per Replit / Claude Code best practice — tight feedback loops) |
| **Stop-point change history** | n/a — first declaration |

## 2. Platform Context

**Per Row 4 Understanding §4.1. **Foundational decisions about runtime/deployment environment.

| **Decision category** | §4.1 Platform context |
| --- | --- |
| **Commitment** | Replit Deployments as deployment platform. Web service runtime context. Managed PaaS operating environment. Single-tenant for v1 (one Practitioner using SysEngage locally / personally). |
| **Rationale** | Practitioner uses Replit for build. Replit Deployments is the natural deployment target. Per §6.1 trade-offs — managed PaaS simplifies ops, fits prototype scope. Single-tenant for v1 avoids multi-tenancy complexity that isn't needed for prototype. |
| **Provisionality** | v1 Replit Deployments — locked for prototype. Multi-tenancy / production deployment platform (could remain Replit, could migrate elsewhere) — under-review for post-v1. |
| **Cascading commitments** | Persistence platform (§3) — Neon pairs naturally with Replit. Web framework (§6) — Replit supports any Python web framework but FastAPI is well-supported. |
| **Tracker references** | None directly. F4 architectural commitment applies (mechanism provenance in AnalysisPass) but is provider-agnostic. |

## 3. Language and Runtime Stack

**Per Row 4 Understanding §4.2.**

| **Decision category** | §4.2 Language and runtime stack |
| --- | --- |
| **Commitment** | Python 3.12+ as implementation language. uv as package manager (or pip if uv is not yet standard in Replit Python templates — Replit Agent decides at scaffold time). Standard Python packaging (pyproject.toml + dependencies declared). |
| **Rationale** | Per §6.2 trade-offs — Python's strong AI integration ecosystem (Anthropic SDK), document parsing libraries (python-docx, pypdf), and analytical/interpretive idioms fit SysEngage's nature. Practitioner is comfortable with Python and has not specified TypeScript preference. Python 3.12+ for modern type system features. |
| **Provisionality** | Python language — locked for v1 and beyond (changing language post-build would require complete rewrite). Specific Python version (3.12+) — locked for v1; may upgrade as Python evolves. Package manager — under-review (uv preferred but Replit defaults dictate). |
| **Cascading commitments** | Web framework choice narrows to Python frameworks. Validation library narrows to Python options (Pydantic recommended). Test framework narrows (pytest standard). |
| **Tracker references** | None directly. |

## 4. Code Repository and Version Control

**Per Row 4 Understanding §4.12.**

| **Decision category** | §4.12 Code repository and version control |
| --- | --- |
| **Commitment** | GitHub for code repository (Practitioner uses GitHub in previous projects). Standard branching: main as primary; feature branches for substantive changes. Replit ↔ GitHub integration for sync. Standard commit messages (no enforced convention for v1). |
| **Rationale** | Practitioner-established platform per Q2 confirmation 6 May 2026. Replit integrates well with GitHub. Per Issue F12 Q1 future expansion — Practitioner input files could potentially come from GitHub repos in future SysEngage versions; out of scope for v1 (file upload only). |
| **Provisionality** | GitHub platform — locked. Branching / commit conventions — v1-only (lightweight); production may require stricter conventions. |
| **Cascading commitments** | Migration files (§7) live in repo. Test fixtures live in repo. CLAUDE-equivalent (replit.md) lives in repo root. |
| **Tracker references** | F12 Q1 future expansion — GitHub as Practitioner input file source is candidate v0.2+ feature. |

## 5. Data Persistence

**Per Row 4 Understanding §4.4.**

| **Decision category** | §4.4 Data persistence |
| --- | --- |
| **Commitment** | Neon PostgreSQL as persistence platform. Hybrid storage approach: relational tables per canonical entity type (Source, Segment, SourceAtom, Signal, ZachmanCell, CellContentItem, Domain, Requirement, Stakeholder, Concern, Question, Answer, Suggestion, Risk, Gap, AnalysisPass) with foreign-key referential integrity; JSONB columns for flexible-structure attributes (AnalysisPass.outputs, mechanism-specific data). SQLAlchemy 2.x as ORM. Alembic for schema migrations. Postgres sequences for identifier sequencing per prefix per canonical ledger spec v2.9 patterns: Source ^S\d{3}$, Segment ^SEG\d{3}$, SourceAtom ^SA\d{3}$, AnalysisPass ^P\d{3}$, Domain ^D\d{3}$, Requirement ^R\d{3}$, Gap ^G\d{3}$. CellContentItem uses structured form ^CCI-ROW[1-6]-C-(What│How│Where│Who│When│Why)-\d{3}$ per canonical JSON Schema (sequence allocation per ZachmanCell — one sequence per (row, column) pair, not one global CCI sequence). ZachmanCell uses structured form ^ZC-R[1-6]-C-(What│How│Where│Who│When│Why)$. Identifiers MUST conform to canonical regex; SysEngage NEVER restates identifier prefixes — always reference canonical ledger spec for the authoritative regex per F18 / F9 (B) discipline. |
| **Rationale** | Per §6.3 trade-offs — relational with JSONB hybrid suits canonical entity catalogue with relationships. Neon serverless model fits occasional Practitioner use (cost-friendly). Practitioner has used Neon in previous projects. SQLAlchemy is the standard Python ORM. Alembic is standard with SQLAlchemy and version-controlled in GitHub. Identifier patterns per canonical ledger spec — no SysEngage-side invention or restating. |
| **Provisionality** | Neon platform — locked for v1. PostgreSQL choice — locked (foundational architectural choice). SQLAlchemy 2.x — locked (mature standard). Alembic — locked. Identifier patterns — locked per canonical ledger spec v2.9. Specific schema design — under-review (will evolve as canonical schema evolves and as mechanisms surface needs). |
| **Cascading commitments** | Schema migrations live in alembic/ directory in repo. Pydantic models mirror SQLAlchemy models for validation (per §7). Identifier sequencing convention requires Postgres sequence per prefix for simple-form identifiers; per (row, column) pair for CellContentItem structured form. Pydantic regex validators populated from canonical ledger spec patterns directly. |
| **Connection lifecycle** | Neon serverless endpoints auto-suspend (~5 min idle), so a database connection must NOT be held open across, or assumed live after, a mechanism's IM (AI-call) phase. Connection and session lifecycle across the IM phase is governed by the **Common Implementation Reference §1** (the controlled how-document for common physical-tier functions) — Stage 1 releases its connection after reading; Stage 4 acquires fresh. Mechanism specs conform by citation; the realisation is not restated here or in Applied. This is a property of the Neon-serverless commitment above and applies to every AI-bearing mechanism. |
| **Tracker references** | F11 RESOLVED v0.2 (CCI ci_id format = ^CCI-ROW[1-6]-C-(What│How│Where│Who│When│Why)-\d{3}$ per canonical JSON Schema — applied here). F18 RESOLVED v0.2 (identifier prefix patterns aligned with canonical regexes — applied here). F4 (mechanism provenance in AnalysisPass) — applied via JSONB column on AnalysisPass table. |

## 6. Web Framework / API Layer

**Per Row 4 Understanding §4.3.**

| **Decision category** | §4.3 Web framework / API layer |
| --- | --- |
| **Commitment** | FastAPI as web framework. REST API style for inter-component communication. Server-rendered Jinja templates for v1 Practitioner UI. No JS framework / SPA for v1. No authentication for v1 (single-tenant prototype). |
| **Rationale** | Per §6.4 trade-offs — FastAPI's async capability, automatic OpenAPI generation, and Pydantic-native integration fit SysEngage's API-heavy nature. Per §6.5 — server-rendered Jinja templates simplest for v1 Source Capture UI (file upload form + summary view); JS framework deferred until Practitioner UI complexity warrants. No authentication is appropriate for single-tenant prototype; multi-tenancy is post-v1 concern. |
| **Provisionality** | FastAPI — locked for v1. REST API — locked for v1; GraphQL or other styles deferred. Jinja templates — v1-only; later mechanisms (Question / Answer workflow, Concern review) may justify JS framework. No authentication — v1-only; multi-tenancy adds authentication need. |
| **Cascading commitments** | Pydantic v2 (FastAPI-native validation) cascades from FastAPI choice. Async patterns supported throughout. OpenAPI documentation auto-generated. |
| **Tracker references** | None directly. |

## 7. Schema and Validation

**Per Row 4 Understanding §4.6.**

| **Decision category** | §4.6 Schema and validation |
| --- | --- |
| **Commitment** | Pydantic v2 as validation library. Schema definition strategy: Pydantic models for in-memory entity representation; SQLAlchemy models for persistence; mapping layer between them. Cross-entity referential integrity: Postgres foreign keys for database-enforced; Pydantic validators for application-level invariants. Validation timing: on entity creation (Pydantic constructor), on persistence (SQLAlchemy ORM events), on read (deserialisation through Pydantic). Schema versioning: Alembic migrations for database schema; Pydantic model evolution managed in code review. |
| **Rationale** | Per §6.7 trade-offs — strict validation on every operation suits canonical entity discipline. Pydantic v2 is FastAPI-native and integrates with SQLAlchemy. Two-model pattern (Pydantic + SQLAlchemy) is standard but adds maintenance overhead — accepted for v1 given clear validation benefits. |
| **Provisionality** | Pydantic v2 — locked for v1 and v2.x evolution. Two-model pattern — locked for v1; may consider unified ORM/validation library (e.g., SQLModel) post-v1 if maintenance overhead becomes substantial. |
| **Cascading commitments** | Pydantic models live in schemas/ directory in repo. SQLAlchemy models live in models/ directory. Mapping/conversion utilities live in mappers/ directory (or similar — Replit Agent decides exact module organisation). |
| **Tracker references** | F11 RESOLVED v0.2 (CCI ci_id format locked to canonical structured form per JSON Schema; Pydantic regex validator uses canonical pattern directly — no SysEngage-side restate per F9 (B) / F18 discipline). |

## 8. AI Model Integration

**Per Row 4 Understanding §4.5.**

| **Decision category** | §4.5 AI Model integration |
| --- | --- |
| **Commitment** | Anthropic Claude API as AI Model provider. Anthropic Python SDK as client library. Specific model selection deferred to runtime configuration (config file specifies model name, e.g., "claude-sonnet-4-6" or "claude-opus-4-7"). Prompt management: prompts stored as Python string templates in prompts/ directory (one file per mechanism; mechanism-specific prompts referenced by mechanism implementation). Caching: deferred for v1 (no caching). Cost-control: rate-limit / max-token configuration in code; no separate budget enforcement layer for v1. Fallback: on AI Model unavailability, mechanism execution fails with execution_status=Failed; Practitioner notified; no automatic retry for v1. |
| **Rationale** | Per §6.6 trade-offs — vendor SDK is straightforward, well-documented, fits v1 simplicity. Anthropic specifically because Practitioner uses Anthropic products and conversation context is grounded in Claude. Vendor-neutral abstraction (LiteLLM) deferred until multi-vendor need arises. Source Capture is fully deterministic (zero AI involvement) so AI Model integration not exercised by first mechanism — but commitment locked here for downstream mechanisms. |
| **Provisionality** | Anthropic Claude — v1 locked; vendor-neutral abstraction is candidate v2+ enhancement. Anthropic Python SDK — locked. Prompt storage approach — v1-only; prompt-management library (Promptbook, etc.) is candidate v2+ enhancement when mechanisms accumulate. Caching / cost-control — v1-only deferred; production deployment will require both. |
| **Cascading commitments** | Anthropic SDK as dependency. Configuration approach for model selection. Mechanism implementations that involve AI use Anthropic SDK invocation pattern (locked here, applied per mechanism). |
| **Tracker references** | None directly. Source Capture mechanism does not exercise AI integration; downstream mechanisms (Actor Signal Identification, Row-Lens Source Re-Analysis) will. |

## 9. Mode Discipline Implementation

**Per Row 4 Understanding §4.7.**

| **Decision category** | §4.7 Mode discipline implementation |
| --- | --- |
| **Commitment** | Decorator pattern for Pass mode declaration. Decorator @pass_mode("LPM") or @pass_mode("IM", with_lpm=True) wraps Pass functions. Decorator records mode_active on AnalysisPass at Pass start; instruments Pass execution to detect mode violations; sets execution_status=Failed if violation detected. LPM-specific enforcement: byte-preservation discipline implemented via an immutable Source content wrapper (Source.content property is read-only after creation; attempts to modify raise RuntimeError). Mode metadata recorded on AnalysisPass in standard fields per §10. |
| **Rationale** | Per §6.8 trade-offs — decorator pattern is Python-idiomatic, declarative, runtime-checkable; fits FastAPI/Python conventions. Wrapper class pattern would be more verbose; type-system-encoded would require advanced type tricks not warranting the complexity for v1. |
| **Provisionality** | Decorator pattern — locked. Specific decorator API surface — under-review (will refine as more mechanisms exercise the pattern). |
| **Cascading commitments** | Decorators live in core/modes/ directory (or similar). Every mechanism Pass function uses @pass_mode decorator. AnalysisPass schema includes mode_active and mode_violations fields per §10. |
| **Tracker references** | None directly. |

## 10. Audit Trail Implementation

**Per Row 4 Understanding §4.8 / Issue F4 architectural commitment.**

| **Decision category** | §4.8 Audit trail implementation |
| --- | --- |
| **Commitment** | AnalysisPass entity persisted in PostgreSQL as analysis_pass table with JSONB outputs column for mechanism-internal data. Standard fields populated by every mechanism: pass_id (sequence), phase_id, pass_started_at, pass_completed_at, execution_status, mode_active (text), mode_violations (JSONB array), ai_model_fingerprints (JSONB array, empty for non-AI mechanisms), elapsed_ms, practitioner_id (FK to stakeholder). Mechanism-specific extensions: stored under outputs.mechanism_data JSON sub-structure with mechanism-specific schema per Implementation Spec. Read Witness data convention (per F10): stored under outputs.read_witness sub-structure for Phase 1 Source Capture AnalysisPass records (input_hash, byte_count, character_count, read_mode, read_completion_status). Audit trail readability: human-inspectable JSON; not optimised for storage compactness. |
| **Rationale** | Per Row 4 Understanding §9 common-foundations: AnalysisPass conventions must be common across mechanisms. Per Issue F4 architectural commitment (Option 2): mechanism provenance lives on AnalysisPass.outputs. Per Issue F10 architectural commitment: Read Witness data lives on AnalysisPass.outputs.read_witness. JSONB column gives schema flexibility for mechanism-specific data without requiring schema migration per mechanism. |
| **Provisionality** | AnalysisPass table structure — locked. Standard fields list — locked. JSONB outputs structure conventions — under-review (will refine as more mechanisms surface specific needs). outputs.mechanism_data sub-schema per mechanism — defined per Implementation Spec. |
| **Cascading commitments** | AnalysisPass schema in Alembic migrations. Helper functions for AnalysisPass record creation and outputs sub-structure population. |
| **Tracker references** | F4 (mechanism provenance architecture — applied here). F10 (Read Witness storage — applied here as outputs.read_witness convention). |

## 11. Practitioner UI Patterns

**Per Row 4 Understanding §4.9.**

| **Decision category** | §4.9 Practitioner UI patterns |
| --- | --- |
| **Commitment** | Web UI delivered via FastAPI + Jinja templates. v1 scope: minimal — file upload form (for Source Capture input), post-execution summary view (showing produced entities and AnalysisPass status). Practitioner workflow features (Concern review, Question answering, Suggestion disposition, Signal review) deferred for v1 — these emerge as later mechanisms need them. No authentication for v1 (single-tenant). Notification: post-execution summary view shows current state; no push notifications / email / etc. for v1. |
| **Rationale** | Source Capture is the first mechanism — only needs minimal UI for v1 prototype. Per Row 4 Understanding §9.3 hybrid pattern — UI shell pattern in Applied; mechanism-specific Practitioner-facing operations in Implementation Spec. Source Capture has no Practitioner-facing operations beyond input + summary. |
| **Provisionality** | Web UI delivery — locked for v1. Jinja templates — v1-only; JS framework may be needed when Practitioner workflow features are added (Concern review etc. benefit from richer interaction). v1 scope (minimal) — explicit; expect substantial expansion when downstream mechanisms produce Concerns / Questions. |
| **Cascading commitments** | Templates live in templates/ directory. UI shell (base template, common layout) defined here; per-mechanism Practitioner-facing pages defined in respective Implementation Specs. |
| **Tracker references** | None directly. |

## 12. Testing and Verification

**Per Row 4 Understanding §4.10.**

| **Decision category** | §4.10 Testing and verification |
| --- | --- |
| **Commitment** | pytest as test framework. Test data / fixtures: real-world samples committed to fixtures/ directory in repo (with synthetic edge-case fixtures alongside). Determinism testing: bit-identity for fully deterministic mechanisms (Source Capture, Domain Identification when written, etc.); semantic-equivalence with AI Model fingerprint capture for AI-involving mechanisms (Actor Signal Identification, Row-Lens Source Re-Analysis). Coverage targets: aim for >80% line coverage on core mechanism logic; not enforced as gate for v1. Integration testing across mechanisms: deferred for v1 (one mechanism implemented at a time). |
| **Rationale** | Per §6 — pytest is Python standard with rich fixture support. Real-world samples test against actual document shapes; synthetic edge-case fixtures test specific scenarios. Bit-identity is the strongest determinism test where applicable; semantic-equivalence is the appropriate weaker standard for AI. |
| **Provisionality** | pytest — locked. Real-world samples approach — v1; coverage targets — v1-only (no enforcement); integration testing deferred — v1-only. |
| **Cascading commitments** | tests/ directory structure: one subdirectory per mechanism. fixtures/ directory: shared test inputs. conftest.py for shared pytest fixtures (database setup, ledger reset, etc.). |
| **Tracker references** | None directly. |

## 13. Cross-Mechanism Coordination

**Per Row 4 Understanding §4.11.**

| **Decision category** | §4.11 Cross-mechanism coordination |
| --- | --- |
| **Commitment** | Sequential runner for v1. Orchestrator function invokes mechanisms in canonical Phase / Pass order. Phase 1 Source Capture invocation pattern: input file path + project context → mechanism invoked synchronously → ledger entities written. Cross-mechanism input/output coordination via ledger reads (Mechanism B reads what Mechanism A produced from the ledger). Phase 10 trigger handling: deferred for v1 — single-pass execution only; mid-project iteration not supported in v1 prototype. No event-driven / pub-sub for v1. No workflow engine (Airflow / Prefect / Temporal) for v1. |
| **Rationale** | Per §6.9 trade-offs — sequential runner is simplest, easy to debug, sufficient for v1. Event-driven and workflow engines add infrastructure overhead not justified at prototype scale. Per Row 4 Understanding §4.11 — v1 scope typically simple sequential runner. |
| **Provisionality** | Sequential runner — v1-only; production version will likely need event-driven or workflow engine. Phase 10 deferral — v1-only; later v0.x will need re-execution support. |
| **Cascading commitments** | Orchestrator function in core/orchestrator.py (or similar). Mechanism invocation API standardised so orchestrator can call each mechanism uniformly. |
| **Tracker references** | None directly. |

## 14. Implementation Handoff

**Per Row 4 Understanding §4.13.**

| **Decision category** | §4.13 Implementation handoff |
| --- | --- |
| **Commitment** | Target AI coding agent: Replit Agent. Handoff file format: replit.md (auto-generated by Replit on project creation; manually edited or replaced with our content). Handoff content scope: replit.md is concise — references the deep specs (Row 4 Applied, Source Capture Implementation Spec) by file path; does not duplicate detail (per progressive-disclosure pattern). Iteration model: Practitioner uses Replit Agent's Plan Mode for architectural review before implementation execution; Practitioner reviews Agent-generated code as it's produced; corrections happen mid-stream when Agent diverges from specs. |
| **Rationale** | Per stop-point Standard. Replit-specific because Practitioner uses Replit. replit.md is concise per CLAUDE-equivalent best practices ("don't tell agent everything; tell agent how to find detail"). Plan Mode pattern aligns with Claude Code's "plan first, then execute in fresh session" workflow. |
| **Provisionality** | Replit Agent target — locked for v1 build. replit.md content — v1; will refine based on actual Replit Agent reading effectiveness. |
| **Cascading commitments** | replit.md lives in repo root. Reference structure: replit.md → Row 4 Applied → Implementation Specs → canonical schema. |
| **Tracker references** | None directly. |

## 15. Recap — v1 Locked Stack Summary

Quick-reference summary of v1 locked architectural stack:

| **Layer** | **Commitment** |
| --- | --- |
| **Deployment platform** | Replit Deployments (managed PaaS, single-tenant) |
| **Code repository** | GitHub |
| **Language** | Python 3.12+ |
| **Web framework** | FastAPI |
| **Persistence** | Neon PostgreSQL via SQLAlchemy 2.x |
| **Schema migrations** | Alembic |
| **Validation** | Pydantic v2 |
| **AI Model integration** | Anthropic Python SDK (Claude API) |
| **Frontend** | Server-rendered Jinja templates (no JS framework for v1) |
| **Testing** | pytest (with real + synthetic fixtures) |
| **Mode discipline** | Decorator pattern (@pass_mode) |
| **Audit trail** | AnalysisPass entity with JSONB outputs column |
| **Cross-mechanism orchestration** | Sequential runner (v1 only) |
| **Implementation handoff** | Replit Agent via replit.md |
| **Stop-point** | Standard (Applied + Mechanism Implementation Spec) |

## 16. Recommended Project Structure

**[INFERRED] **Recommended file/directory structure for SysEngage repo. Replit Agent may adjust during scaffold; this is the intended shape for the v1 prototype.

sysengage/

├── replit.md                    # Replit Agent handoff entry point

├── README.md                    # Project README

├── pyproject.toml               # Python project + dependencies

├── alembic.ini                  # Alembic config

├── alembic/                     # Schema migrations

│   ├── env.py

│   └── versions/

├── core/                        # Core architectural patterns

│   ├── modes/                   # @pass_mode decorator + LPM enforcement

│   ├── orchestrator.py          # Cross-mechanism orchestration

│   └── audit_trail.py           # AnalysisPass helpers

├── schemas/                     # Pydantic models (canonical entities)

│   ├── source.py

│   ├── segment.py

│   ├── source_atom.py

│   ├── analysis_pass.py

│   └── ...                      # one file per canonical entity

├── models/                      # SQLAlchemy models (DB layer)

│   ├── source.py

│   ├── segment.py

│   └── ...

├── mappers/                     # Pydantic ↔ SQLAlchemy mapping

├── mechanisms/                  # Mechanism implementations

│   ├── source_capture/          # Phase 1 Source Capture mechanism

│   │   ├── __init__.py

│   │   ├── pass_0_read_witness.py

│   │   ├── pass_0a_segment_construction.py

│   │   ├── pass_0b_source_capture.py

│   │   └── pass_0c_source_atom_splitting.py

│   └── ...                      # other mechanisms as added

├── prompts/                     # AI Model prompt templates

│   └── (none for Source Capture; downstream mechanisms add per-mechanism prompts)

├── api/                         # FastAPI routes

│   ├── main.py                  # FastAPI app

│   ├── source_capture.py        # Source Capture endpoints

│   └── ...

├── templates/                   # Jinja templates

│   ├── base.html

│   ├── source_capture/

│   │   ├── upload.html

│   │   └── summary.html

│   └── ...

├── static/                      # CSS / static assets

├── tests/                       # pytest tests

│   ├── conftest.py              # Shared fixtures

│   ├── source_capture/

│   │   ├── test_pass_0.py

│   │   ├── test_pass_0a.py

│   │   ├── test_pass_0b.py

│   │   └── test_pass_0c.py

│   └── ...

├── fixtures/                    # Test input data

│   ├── source_capture/

│   │   ├── happy_path/          # Real-world sample documents

│   │   └── edge_cases/          # Synthetic edge-case documents

│   └── ...

└── docs/                        # Project documentation

    ├── row4_understanding/      # Row 4 framework artefact

    ├── row4_applied/            # Row 4 Applied artefact

    └── mechanisms/              # Mechanism Implementation Specs

***Note: **** Replit Agent will scaffold the actual project. This structure is the intent; minor variations (e.g., flatter or deeper module organisation) are acceptable as long as the architectural commitments above are honoured.*

## Document End

End of SysEngage Row 4 Applied to SysEngage v0.2.

All v1 architectural commitments locked. Provisionality marked explicitly per category. Cascading commitments documented. Tracker references where applicable.

Companion artefacts:

- SysEngage_Row_4_Understanding_v0_1.docx — framework artefact (this Applied artefact applies that framework)

- SysEngage_Row_4_Mechanism_Source_Capture_v0_2.docx — first Mechanism Implementation Spec, applies these commitments to Source Capture (also revised v0.2 in F11/F18 resolution cycle)

- replit.md — Replit Agent handoff entry point in repo root, references all of the above