# AI assistance and technical audit

## Assistance record

The user supplied the complete structured-extraction assignment as
`Pasted markdown(2).md` and then asked ChatGPT: **"can  you just build it"**.
ChatGPT generated this project, its tests, documentation, and the audit analysis.
The student should review and run the result, and add their own findings here.
This file does not claim the student authored code, performed an audit, or ran
checks that they have not personally performed.

### Attachment-derived implementation brief

The following is a **summary of the requirements used by the assistant**, not a
verbatim extra prompt typed by the user:

> Build a Python 3.11 invoice extractor with nested Pydantic v2 models, native
> strict structured decoding, bounded validation reflection, JSON syntax repair
> and DLQ. Add PDF/HTML ingestion, a Streamlit interface, sample documents, QA,
> container files, and auditable setup documentation. Money, date normalization,
> exact error locations, reconciliation and visible failure simulation matter.

## Retained baseline output and audit specimen

`audit/baseline_draft.py` is a deliberately naive AI-authored specimen retained
for demonstration. It is not the running implementation or a historical record
of student edits. Its complete executable source is in that file. It parses
JSON, checks one aggregate equality using floats, and concatenates documents
and previous messages into a growing retry history. This makes the two failure
modes concrete and reproducible without inventing a student revision history.

## Finding 1: incomplete deterministic validation

**Baseline:** `parse_invoice` accepts a false `subtotal` whenever the sum of line
totals plus tax equals the grand total. It also accepts negative quantities
because it never compares quantity × price with the supplied line total.

**Example:** a two-item-quantity line with unit price 10, line total 20, tax 2 and
total 22 still passes the baseline with subtotal 999 or quantity -2.

**Final correction:** `src/schemas.py` uses nested v2 models, strict positive
integer quantities, Decimal money, per-line multiplication checks, and three
separate aggregate invariants. Unknown fields and empty line lists are rejected.
No heuristic or reflection path skips these rules.

**Evidence:** `tests/test_audit_regressions.py` proves the specimen accepts these
inputs and the final model rejects them. `tests/test_extraction.py` additionally
covers tolerance boundaries, non-finite money, negatives and ambiguous formats.

## Finding 2: unbounded retry context

**Baseline:** `retry_prompt` appends the entire document, previous response and
previous history every time. Three retries of a 60,000-character document grow
past 180,000 characters before counting outputs or errors.

**Final correction:** `src/fallback.py::reflection_prompt` constructs a new JSON
message for each retry, keeping 4,200 source characters from the beginning and
1,800 from the end, with an omission marker when necessary. It includes at most
8,000 previous-response characters and the first 20 exact validation errors.
No prior prompt history accumulates. The entire attempt budget is explicit.

**Trade-off:** middle-of-document evidence can be omitted; this bounded window
is suitable for the short sample invoices. Multi-invoice and long-document
production processing would need section selection/chunking, rather than guessing.

**Evidence:** the baseline-growth regression and bounded-prompt fallback test.

## Additional checks

| Audit area | Final implementation and limitation |
| --- | --- |
| Pydantic v1/v2 collision | Uses `field_validator`, `model_validator`, `model_validate_json`, `model_dump`; no v1 validators or `.dict()` |
| JSON mode vs constrained decoding | OpenAI adapter sets native `json_schema`, `strict: true`; a separate wire schema avoids leaking business-validator assumptions into provider compatibility |
| Monetary precision | Decimal values with finite checks and two decimal places; no float equality in final reconciliation |
| Nonstandard dates | Explicit pre-parser supports ordinal month-name dates; ambiguous slash dates are rejected |
| Half-empty fallback objects | All success paths require a complete validated invoice; otherwise DLQ |
| Silent transport retries | SDK retries disabled; one visible total attempt budget; permanent failures stop early |
| Unsafe untrusted text | System instruction treats documents as data; HTML scripts/styles removed; source text is displayed as text, not rendered HTML |
| Offline claims | Template parser and injected faults visibly labeled; no claim that offline tests validate live LLM reasoning |
| Sensitive logs | API key is not included in prompts or DLQ; source documents are retained locally for review and must be protected |

## Verification performed by the assistant

The full automated suite, including Streamlit widget flows, was run in the build
environment. See `QA_REPORT.md` for the final count and scope. No user API key was
available, so live API extraction was not executed. Docker was unavailable, so
container execution was not claimed. There is no published deployment or video.

## Student verification record (fill in after you perform it)

- Date and operating system:
- Tests I ran and actual result:
- Live API example and observation:
- Container or deployment URL/evidence:
- Code I reviewed and changes I made:
- Any additional issues I found:

Do not describe the specimen audit as a historical student bug-fix process. If the
instructor requires an actual first-draft-to-revision record, make and document
your own review/revision and preserve that evidence rather than misrepresenting
this generated example.

## Actual issues found while running this generated project

These are distinct from the intentionally naive specimen above and were observed
in the first test execution during this build:

1. **Sample paths depended on the caller's working directory.** The original
   fixtures read `Path("samples/invoice_messy.pdf")` with no project-directory
   setup. Running pytest with a project path from its parent caused missing-file
   failures. The final `tests/conftest.py::project_directory` autouse fixture
   resolves the repository root from `__file__` and sets the working directory
   explicitly for each test, so samples resolve consistently.
2. **Streamlit AppTest resolved the UI filename against the test file.** The
   generated `AppTest.from_file("src/app.py")` looked for `tests/src/app.py` in
   the installed Streamlit version. The observed failure was
   `FileNotFoundError: AppTest script not found at .../tests/src/app.py`.
   `tests/test_ui.py` now computes an absolute application path from the test
   file's location before constructing AppTest. Both real widget tests then passed.

These fixes were made and verified by the assistant, not attributed to the
student. The final full test output is retained in `audit/pytest_output.txt`.
