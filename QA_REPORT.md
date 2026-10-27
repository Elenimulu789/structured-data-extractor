# Verification report

## Completed by the assistant

- Environment: Linux, Python 3.11.17, Pydantic 2.14.1, Streamlit 1.66.1,
  OpenAI Python SDK 2.54.0; exact dependency resolutions in `uv.lock`.
- `uv sync`: completed successfully.
- `uv run pytest -v`: **39 passed**, including real PDF text extraction,
  HTML ingestion, strict field failures, Decimal reconciliation and tolerance,
  reflection recovery on attempt 2, bounded prompt size, hard failure after
  three attempts, heuristic syntax recovery, mandatory revalidation, transport
  retries, provider refusal, disk-write failure, actual source contradiction,
  a mocked strict OpenAI request, baseline audit regressions, and real Streamlit
  widget interactions. Full output: `audit/pytest_output.txt`.
- Streamlit subprocess startup and `/_stcore/health`: HTTP **200**, body `ok`.
- Sample PDF rendered with Poppler and visually inspected: one legible page,
  no clipping or overlap. The fixture includes mixed money/date formats.
- Windows batch launcher, environment example, Dockerfile, Compose definition,
  and setup instructions are included. They contain no API credentials.

## Limits of this evidence

- No live OpenAI request was made. Adapter tests mock the SDK; offline tests
  verify template parsing and orchestration, not provider schema acceptance,
  model availability, billing configuration or semantic accuracy.
- Docker was not installed, so no container build/run is claimed.
- Browser screenshot QA could not run because the browser download was
  unavailable. Streamlit's AppTest exercised the actual app script and buttons;
  this does not replace checking visual layout in your browser.
- No GitHub repository, hosted deployment, YouTube video or student-performed
  review is claimed.

## Checks to perform on your Windows computer

1. Follow `START_HERE.md`, open the app, and run `uv run pytest -v`.
2. Use your own API key to run the normal sample in OpenAI mode; verify the
   exact output against the source. Run reflection and DLQ simulations too.
3. Run `docker compose up --build`, verify localhost, and show the actual
   container during your recording; alternatively complete a cloud deployment.
4. Review the audit log and code, record your own observations, create your
   repository, and record the required 5–7 minute webcam walkthrough.
