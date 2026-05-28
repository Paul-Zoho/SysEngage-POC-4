---
name: VER test isolation — orchestrator session commits
description: VER (verification criteria) tests must explicitly clean up prior DD state because the orchestrator commits its own session.
---

## Rule
When writing `TestVerificationCriteria` tests for any mechanism that uses its own `get_session()` and commits inside `dd.run()` (or equivalent), the `setup` fixture must DELETE prior mechanism state for the test project using a committed operation BEFORE seeding.

**Why:** The conftest `session` fixture uses rollback semantics (yields and then rollbacks). But the orchestrator calls `get_session()` and commits independently. That means passes/domains/memberships written during a test run PERSIST in the Neon DB after the test's session rolls back. On the next test run, Stage 1 finds the prior pass with a matching CCI hash and returns `idempotent_exit`, which may not have the full `mechanism_data` keys expected by the test assertions.

**Pattern:**
```python
@pytest.fixture(autouse=True)
def setup(self, session):
    session.execute(text("DELETE FROM domain_cci_membership WHERE project_id = :pid"), {"pid": PROJECT_ID})
    session.execute(text("DELETE FROM domain WHERE project_id = :pid"), {"pid": PROJECT_ID})
    session.execute(text("DELETE FROM analysis_pass WHERE project_id = :pid AND mechanism = 'DomainDerivation'"), {"pid": PROJECT_ID})
    session.commit()
    seed_standard_test_dataset(session)
    session.commit()
```

**How to apply:** Any future VER test class that calls the full mechanism orchestrator must add the same DELETE+commit pattern for its mechanism's tables. ZachmanCell cell_id format is `ZC-R{row}-C-{column}` (e.g. `ZC-R4-C-What`), not `CELL-R4-What`.
