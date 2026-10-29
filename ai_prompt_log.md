# AI Assistance and Verification Log

## Overview

This project uses AI-assisted development to create an invoice extraction pipeline with Pydantic v2 validation, structured AI responses, a reflection correction loop, and dead-letter queue handling.

AI assistance supported implementation drafting, test development, troubleshooting, and documentation.

## Summary of AI Requests

Development requests focused on:

- Defining nested invoice and line-item models with field constraints and financial reconciliation.
- Extracting information from PDF, HTML, and text documents using OpenAI Structured Outputs.
- Implementing a bounded reflection loop using validation errors.
- Adding JSON syntax repair and saving unrecoverable extractions for review.
- Building a Streamlit interface with validated results, reconciliation status, and an audit trail.
- Creating automated tests and documenting setup and deployment.

These are summaries of the development requests, not verbatim conversation transcripts.

## Code Review and Corrections

### 1. Sample-File Paths

The original test fixtures used relative paths to locate sample documents. Tests could fail when launched from outside the project folder.

**Correction:** The test setup now resolves the project directory from the test file’s location and sets the working directory before running each test.

### 2. Interface Test Paths

The initial interface test used:

```python
AppTest.from_file("src/app.py")
```

Streamlit resolved this relative to the test file and looked for the application inside `tests/src/app.py`.

**Correction:** The interface tests now calculate an absolute application path before creating the test instance.

### Additional Validation Checks

The review also covered:

- Consistent Pydantic v2 syntax.
- Decimal arithmetic for monetary values.
- Positive quantities and valid currency codes.
- Date normalization and rejection of ambiguous formats.
- Line-item calculations and invoice-total reconciliation.
- Bounded retry prompts and attempt limits.
- Full validation after heuristic repair.
- Explicit failure reporting instead of accepting incomplete records.

## Verification Results

The following checks were completed locally:

- **Automated tests:** 39 passed.
- **Live OpenAI extraction:** The sample invoice validated successfully on the first attempt.
- **Reconciliation:** The extracted total was $1,923.35, with a $0.00 difference.
- **Reflection recovery:** A deliberately removed currency field triggered validation and was restored successfully on attempt two.

Automated tests also cover hard failures, DLQ routing, syntax repair, provider errors, and interface behavior.

The fault-injection controls deliberately modify responses to demonstrate recovery and failure handling. They are separate from naturally occurring provider errors.

## Deployment

The interface has been deployed to Streamlit Community Cloud:

https://structured-data-extractor-acazx7jzlxtzrcggeewc27.streamlit.app/

## Remaining Review Notes

- Hosted application verification:
- Additional issues found during manual review:
- Changes made after review:
- Final video link and duration:

## Limitations

The application requires readable PDF text. Image-only scans need an additional OCR step.

Schema and reconciliation checks improve reliability but cannot guarantee that every extracted fact matches the source document.
