# Run your project on Windows

1. Download the ZIP and extract it. Open the `structured-data-extractor` folder.
2. In that folder, right-click empty space and choose **Open in Terminal**.
3. If you do not already have uv, run:

```powershell
winget install --id astral-sh.uv -e
```

Close and reopen the terminal after installing. Then run these commands from the
folder containing `pyproject.toml`:

```powershell
uv sync --frozen
uv run streamlit run src/app.py
```

uv downloads Python 3.11 if needed. If Streamlit does not open automatically,
visit **http://localhost:8501**. Keep the terminal open while using the app.
After setup, you can also double-click `start-windows.bat`.

## Try it immediately

- Keep **Offline demo** selected.
- Leave **Reflection self-correction** on and attempts at **3**.
- Choose `invoice_messy.pdf`, then **Extract & validate**.
- Open **Failure simulations** and choose **Simulate reflection recovery**.
- Open the audit trail to see the missing-currency error and corrective prompt.
- Choose **Simulate Edge Case Failure** to demonstrate the DLQ.

Offline mode is a simple parser for the included template. It is not a live AI
extraction demonstration. It helps you test the interface without API charges.

## Turn on real AI extraction

In a second terminal, from this folder:

```powershell
Copy-Item .env.example .env
notepad .env
```

Put your OpenAI API key after `OPENAI_API_KEY=`. Save, then restart the app and
select **OpenAI Structured Outputs**. You can also paste your key into the app's
password field. ChatGPT Plus and API billing are separate.

Use your own key locally; never put it into GitHub or your recording. The app
sends document text to the API only when you run extraction in OpenAI mode.

## Run the tests

Open another terminal in the project folder:

```powershell
uv run pytest -v
```

## What remains for submission

Review the code and AI audit log so you understand them. Run a real API extraction
and either deploy to a host or execute the included Docker setup. Then create your
GitHub repository and record your 5–7 minute video with your webcam visible.
`VIDEO_GUIDE.md` explains what to show. `SUBMISSION_TEMPLATE.md` has the submission
fields. The package does not create a repository, deployment, or video for you.
