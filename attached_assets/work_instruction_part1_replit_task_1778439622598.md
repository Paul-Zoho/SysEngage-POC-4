# Document 1 — Task for Replit Agent

Copy the section between the lines below into Replit Agent as a new task.

---

I need a small CLI utility for verification of the Source Capture mechanism build. The current state — mechanism API exercisable only via pytest, no web endpoints, no UI — leaves no Practitioner-accessible way for me to submit real input material and inspect the resulting ledger. This utility bridges that gap.

## What to build

A Python CLI utility, located at `sysengage/tools/run_capture.py` (create the `tools` subdirectory if it does not exist), invokable as:

```
python -m sysengage.tools.run_capture <input_file_path> <output_ledger_path>
```

Behaviour:

1. Read the input file from `<input_file_path>`. Supported formats: .txt, .md, .docx, .pdf (per the formats Source Capture supports).

2. Invoke the Source Capture mechanism API (the orchestrator entry point at `mechanisms/source_capture/__init__.py` or wherever you put it) with the input file. Use a fresh transaction; commit on success.

3. After the mechanism completes, query the database for all entities produced by this execution: every Source, Segment, SourceAtom, and AnalysisPass associated with the just-completed mechanism run. Use the AnalysisPass record from this run to scope the query (filter by produced_by_pass_id where applicable).

4. Assemble the entities into a single canonical ledger JSON document conforming to the structure defined in the canonical ledger spec § JSON CanonicalLedger constraints (NORMATIVE) (see `docs/sysengage_minimal_ledger_spec_v2_10.docx` if uploaded; otherwise reference the v2.9 version you already have). The structure is:

   ```json
   {
     "sysengage_ledger_version": "2.10",
     "schema_id": "sysengage.ledger.instance.v2_10",
     "row_target": null,
     "run_id": "<the AnalysisPass.pass_id from this execution>",
     "created_utc": "<ISO 8601 timestamp>",
     "generator": "sysengage_source_capture_v0.1",
     "elements": [
       {"element_id": "S001", "element_type": "Source", "payload": { ... }},
       {"element_id": "SEG001", "element_type": "Segment", "payload": { ... }},
       {"element_id": "SA001", "element_type": "SourceAtom", "payload": { ... }},
       {"element_id": "P001", "element_type": "AnalysisPass", "payload": { ... }}
     ]
   }
   ```

   Each element's `payload` contains all the canonical attributes for that element type per canonical ledger spec.

5. Write the JSON to `<output_ledger_path>` as a UTF-8 text file with 2-space indentation (pretty-printed for human readability).

6. Print a brief summary to stdout:
   ```
   Source Capture completed.
     AnalysisPass ID: P001
     Sources produced: 1
     Segments produced: 0
     SourceAtoms produced: 5
   Ledger written to: <output_ledger_path>
   ```

7. Exit code 0 on success; non-zero on failure with error message to stderr.

## Constraints

- This is a **verification harness, not a mechanism**. Do not register it under `mechanisms/`. The `tools/` subdirectory makes its purpose clear.
- The utility is **disposable transitional infrastructure**. Do not over-engineer. Single file is fine. No abstraction layers, no plugin architecture, no fancy CLI framework — `argparse` and the existing mechanism API are sufficient.
- Use only existing dependencies (no new packages added to `pyproject.toml`).
- The export logic (database query + JSON assembly) is a **separate function** in the same file — call it `export_ledger(pass_id) -> dict` or similar — so it can be reused by tests or by a future proper Ledger Export mechanism. Self-document this with a docstring noting it is a transitional utility.
- The CLI utility should fail gracefully if the database is unreachable or the input file does not exist; print a useful error message to stderr.

## Not in scope

- No web endpoint exposure of this utility
- No UI flow
- No multi-mechanism orchestration (Source Capture only)
- No re-execution semantics in the CLI (re-execution is exercisable separately via pytest per F19 resolution)
- No ledger import (round-trip not needed for verification)

## Verification of the utility itself

Add one pytest test at `tests/tools/test_run_capture.py` that:
- Creates a small input file in a tmp directory
- Invokes the utility via `subprocess.run(["python", "-m", "sysengage.tools.run_capture", input_path, output_path])`
- Asserts exit code is 0
- Loads the output JSON and asserts top-level keys conform to the canonical ledger schema (presence of `sysengage_ledger_version`, `schema_id`, `elements` array)
- Asserts the elements array contains at least one Source and at least one AnalysisPass

This test verifies the utility produces parseable, schema-conformant output. Detailed content verification continues to live in the existing `tests/source_capture/` test suite.

## Effort estimate

Roughly 30-45 minutes of your work. Mostly composition: reading existing models, querying database, building dict, writing JSON. The export function is the bulk of it.

## After you complete

Tell me when the utility is built and the test passes. I will then attempt verification with real input material and report back any findings.
