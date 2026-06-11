# SysEngage Row 4 — Common Implementation Reference

**Version:** 0.1
**Date:** 06 June 2026
**Status:** Active
**Filename:** SysEngage_Row_4_Common_Implementation_Reference_v0_1.md

---

## Purpose

This is a **controlled reference document** for the SysEngage Row 4 (physical / implementation) tier. It owns the *how* of **common implementation functions** — physical-tier disciplines that recur across multiple mechanisms and must behave identically everywhere. Mechanism specifications **conform to** this document by citation rather than restating its content: a mechanism's implementation spec references the relevant section here instead of carrying its own copy of the discipline.

The pattern is deliberate. A cross-cutting physical function (connection lifecycle, transaction boundary, retry behaviour) implemented separately in each mechanism spec drifts: when the function is improved, or the infrastructure changes, every copy must be found and updated, and one is always missed. Defining each common function **once** here, with the mechanism specs citing it, gives a single source of truth, makes conformance checkable ("does this mechanism cite and follow §N?"), and lets the function be improved in one place with every conformer inheriting the change.

**Tier position.** This document is a **freestanding peer** to Row 4 Applied. Applied owns architectural *commitments* (platform, stack, persistence choices); this document owns common *implementation patterns* that realise those commitments. The mechanism specs cite both. This document does not restate Applied's commitments; it assumes them.

**Relationship to the four-stage DM/IM pattern.** Each mechanism spec defines its own four-stage pattern — Stage 1 DM reads, Stage 2 IM (AI) calls, Stage 3 DM+IM, Stage 4 DM writes. The common functions here are invoked *within* that pattern (e.g. §1 governs connection lifecycle across the Stage 2/3 IM phase). This document does not define the four-stage pattern; it governs common behaviour inside it.

---

## How to conform

A mechanism implementation spec conforms to a section of this document by:
1. **Citing** the section at the relevant stage (e.g. "Stage 4 connection acquisition per Common Implementation Reference §1").
2. **Not restating** the realisation — the citation is authoritative; local copies are prohibited (they are the drift this document exists to prevent).
3. Appearing in the **Conformance Register** (below) so the set of conformers is known and a change here has a known propagation list.

---

## §1 — Connection and Session Lifecycle Across the IM Phase

**Applies to:** every mechanism whose IM phase (AI calls) may run long enough for the persistence endpoint to suspend — i.e. every AI-bearing mechanism. The current set: Requirement Derivation, Domain Derivation, CCI Construction, Requirement Matching (any mechanism with a Stage 2/3 IM phase).

### §1.1 The invariant — the IM phase is a connection-lifetime boundary

The platform commitment (Applied §5) is **Neon serverless PostgreSQL**, whose endpoints **auto-suspend after ~5 minutes idle**. A single mechanism run reads in Stage 1 (seconds), runs AI calls in Stages 2–3 (routinely 3–5+ minutes), then writes in Stage 4. The IM phase alone regularly exceeds the idle threshold, during which the endpoint suspends and the SSL session on every pooled connection is torn down.

Therefore the **invariant**: *no database connection may be held open across, or assumed live after, the IM phase.* Concretely, two-sided:
- **Stage 1 releases.** Stage 1 reads all required data into memory and releases its connection; it does not hold a connection open through the IM phase.
- **Stage 4 acquires fresh.** Stage 4 establishes new connectivity rather than relying on anything opened before Stage 2.

A connection that was never held across the IM phase cannot go stale across it; a connection acquired fresh after the IM phase is verified live. The invariant makes the IM phase a hard boundary for DB resources.

### §1.2 The failure mode (why the obvious mitigations are insufficient)

The naive expectation is that connection-pool health checks catch a dead connection. They do not, reliably, in this case:

- **`pool_pre_ping=True` has a documented SSL gap.** The pre-ping issues a lightweight check at checkout, but an OS-buffered SSL `close_notify` can let the ping appear to succeed while the TLS session is actually torn down; the failure then surfaces only on the first *real* query. A per-connection liveness heuristic cannot be relied on against serverless SSL termination.
- **`pool_recycle` races the suspend.** Age-based recycling (e.g. `pool_recycle=240`) recycles a connection by age at checkout, but the endpoint suspend is driven by *Neon's* idle timeout, not the connection's age — a connection younger than the recycle window can already be dead. And a fresh checkout after suspension still requires an endpoint **wake-up**, which the pool's pre-ping does not retry through.
- **`session.close()` itself crashes on a dead connection.** Closing a session issues a ROLLBACK to clean up its transaction; on a dead SSL connection that ROLLBACK is the operation that raises. So a dead connection cannot simply be closed — closing is itself a wire operation that fails.

The consequence: neither per-connection health checks nor ordinary session cleanup is sufficient. The **entire pool** must be discarded and the endpoint re-verified.

### §1.3 The realisation

Two components.

**(a) `db.py` — a reusable refresh helper.**
Export the engine and provide:

```
refresh_engine_pool():
    engine.dispose()      # closes and discards ALL pooled connections; does not raise regardless of their state
    _wait_for_db(...)      # retries until the Neon endpoint is genuinely awake and accepting connections
```

`engine.dispose()` purges the whole pool (not a per-connection check), so no stale connection can survive into the next checkout. `_wait_for_db()` (already present, run at import) handles the endpoint wake. The helper makes this callable after the IM phase, not only at import time.

**(b) Stage 4 — refresh before the write, without a crashing close.**
Before Stage 4 acquires its connection:

```
session.invalidate()      # mark the held connection dead WITHOUT attempting ROLLBACK (avoids the §1.2 close() crash)
refresh_engine_pool()     # = engine.dispose() + _wait_for_db()
session = get_session()   # genuinely fresh connection against a just-verified endpoint
```

`session.invalidate()` is required rather than `session.close()`: it discards the dead connection without issuing the ROLLBACK that would crash on it. Then the pool is purged and the endpoint verified before a fresh session is taken.

**(c) Between heavy passes (launcher / dispatch).**
A sequential runner executing multiple rows/passes in one process ages the shared pool across the whole run (by a late row, pooled connections may be tens of minutes old, and the endpoint may have suspended between passes). The dispatch loop calls `refresh_engine_pool()` **between passes** (e.g. between rows in the 3d loop). This is defence-in-depth — it also covers the suspend that can occur between one pass's Stage 4 and the next pass's Stage 1 reads — and is retained even though per-Stage-4 refresh already handles the within-pass case.

### §1.4 Conformance requirements

A conforming mechanism spec must, at minimum:
- Read all Stage 1 data into memory and release the Stage 1 connection before the IM phase (§1.1).
- Apply the §1.3(b) sequence (`invalidate` → `refresh_engine_pool` → fresh `get_session`) before Stage 4 writes.
- Cite this section at Stage 4 rather than restating the sequence.
- Where the mechanism is run by a sequential dispatcher, ensure §1.3(c) between-pass refresh applies.

A mechanism spec **must not** carry its own copy of the realisation sequence; the citation is authoritative.

---

## Reserved for future common functions

This document is structured to accumulate further common physical-tier disciplines as they are identified and validated. Candidate sections (not yet authored — to be added only when validated in implementation):
- **§2 — Stage 4 ledger-write transaction boundary** (commit/rollback discipline, atomic multi-entity writes).
- **§3 — AI-call retry and failure handling** (timeout, retry policy, `execution_status=Failed` semantics).

Sections are added here (single source of truth) and cited by the mechanism specs, never duplicated into them.

---

## Conformance Register

The mechanism specs that cite this document, and the sections they conform to. A change to a cited section has this register as its propagation list.

| Mechanism spec | §1 Connection lifecycle | Notes |
|---|---|---|
| Requirement Derivation (Row 4) | Conforming (v0.18+) | First conformer; §1 realisation validated on PMT rows 1–5 |
| Domain Derivation (Row 4) | **To bring into conformance** | Same IM exposure; cite §1 at next revision |
| CCI Construction (Row 4) | **To bring into conformance** | Same IM exposure; cite §1 at next revision |
| Requirement Matching (Row 4) | **To bring into conformance** | IM judgement phase; cite §1 at next revision |

---

## Document End

End of SysEngage Row 4 Common Implementation Reference v0.1. A controlled, freestanding reference document for common physical-tier implementation functions; mechanism specs conform by citation, not restatement. §1 (Connection and Session Lifecycle Across the IM Phase) is the first common function: the IM phase is a connection-lifetime boundary (Stage 1 releases, Stage 4 acquires fresh); the realisation is `session.invalidate()` → `engine.dispose()` + `_wait_for_db()` → fresh `get_session()`, with a `refresh_engine_pool()` helper and between-pass refresh in the dispatcher. Validated on PMT rows 1–5. Requirement Derivation Row 4 v0.18 is the first conformer; Domain Derivation, CCI Construction, and Requirement Matching are to be brought into conformance at their next revisions (see Conformance Register).
