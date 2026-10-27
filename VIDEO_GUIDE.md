# Six-minute recording guide

Aim for **6:15 total**. Keep your webcam visible the entire time. Rehearse once;
this guide is a screen/action plan, not a guarantee of spoken duration.

Before recording: run the tests, run a real OpenAI extraction, and verify either
your deployment or Docker. Keep API keys, `.env` contents, account pages, and
private documents off screen. Have the editor, app, and terminal ready.

| Time | Show | Explain in plain language |
| --- | --- | --- |
| 0:00–1:00 | Folder layout, README diagram, `src/schemas.py` | Introduce yourself. The app turns messy invoice documents into checked records. A line item belongs inside an invoice. Show a quantity rule and the total-checking rules. Decimal keeps money calculations predictable. |
| 1:00–2:20 | `ai_prompt_log.md`, `audit/baseline_draft.py`, final validator and prompt builder | Explain honestly that AI generated this project and audit specimen. Show two concrete bad assumptions: checking only a grand total misses invalid subtotals/quantities; copying the entire document repeatedly makes prompts grow. Show the stricter checks and bounded retry prompt. Describe your own review only after doing it. |
| 2:20–3:30 | App, normal PDF, OpenAI mode, validated JSON | Use the sample PDF. Run a real extraction. Explain that the API constrains keys and types, then Python checks business rules. Show normalized dates, money and the reconciliation badge. |
| 3:30–4:25 | Failure simulations → reflection recovery → audit trail | Keep reflection on, attempts 3. Explain that this deliberately removes currency from the first response. Show the exact missing-field error and corrective prompt, then the valid second attempt. It is an injected fault, not a claim of a naturally observed provider failure. |
| 4:25–5:15 | Simulate Edge Case Failure, then downloaded DLQ JSON or `dlq/` | Show attempts stopping at the limit, no validated record, and the saved failure for human review. An invalid invoice must not quietly become a partial success. Optionally show the genuinely inconsistent sample. |
| 5:15–5:45 | Terminal: `uv run pytest -v` | Show the completed automated suite. Explain that it checks normal extraction, invalid values, reconciliation, retries, syntax repair, transport failures and UI actions. Tests use offline/mock responses; live API behavior is a separate check. |
| 5:45–6:15 | Deployment or running Docker and localhost app | Show actual deployment evidence or the working container. State limitations: text PDFs only, no OCR, unsupported discounts/shipping need review. |

## Docker alternative commands

```powershell
docker compose up --build
```

In a second terminal:

```powershell
docker compose ps
docker compose exec extractor python -m pytest -v
```

Only say the container works after running it. The supplied environment did not
have Docker, so you need to verify this part locally for the alternative demo.

## Presentation reminders

- Slides are optional; the assignment asks for a code/app/test walkthrough.
- Real OpenAI mode demonstrates constrained LLM extraction. Offline mode alone
  does not satisfy evidence of a live AI integration.
- Do not claim a validation pass proves every source fact is correct.
- YouTube must be unlisted or public. Check that the final video lasts 5:00–7:00.
