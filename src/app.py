"""Run from project root: uv run streamlit run src/app.py"""
import os
import sys
from decimal import Decimal
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
from dotenv import load_dotenv
from src.ingestion import ingest
from src.extractor import extract_with_retry
from src.providers import DemoProvider, OpenAIProvider, FaultProvider

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="SchemaExtractor", page_icon="🧾", layout="wide")
st.markdown("""<style>.block-container{max-width:1400px;padding-top:2rem}
[data-testid="stMetric"]{background:white;border:1px solid #e0e7ee;border-radius:12px;padding:14px}
h1{letter-spacing:-1.3px} .eyebrow{color:#0f766e;font-size:12px;font-weight:700;letter-spacing:2px}</style>""", unsafe_allow_html=True)
st.markdown('<div class="eyebrow">DOCUMENT INTELLIGENCE / INVOICE WORKSPACE</div>', unsafe_allow_html=True)
st.title("Messy documents. Verified records.")
st.caption("SchemaExtractor • Extract, reconcile, and review every step.")
with st.sidebar:
    st.header("Extraction settings")
    mode = st.radio("Engine", ["Offline demo", "OpenAI Structured Outputs"])
    st.caption("Offline mode is a deterministic sample-template parser. It does not use an LLM.")
    reflection = st.toggle("Reflection self-correction", value=True)
    attempts = st.slider("Maximum total attempts", 1, 5, 3)
    key = ""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if mode.startswith("OpenAI"):
        key = st.text_input("API key (optional if .env configured)", type="password") or os.getenv("OPENAI_API_KEY", "")
        model = st.text_input("Model supporting Structured Outputs", value=model)
        st.caption("Running sends document text to OpenAI and may incur API charges.")
    st.divider()
    st.caption("PDF limits: 10 MB / 30 pages. Text limit: 60,000 characters. Image-only PDFs require external OCR.")
    st.caption("DLQ records contain document text and audit details. Keep them private; delete them after review.")

source_kind = st.radio("Document source", ["Sample library", "Upload file", "Paste text / HTML"], horizontal=True)
raw = ""
try:
    if source_kind == "Sample library":
        sample = st.selectbox("Choose a document", ["invoice_messy.pdf", "vendor_contract.html", "invoice_inconsistent.txt", "nonsense.txt"])
        kind = "pdf" if sample.endswith("pdf") else "html" if sample.endswith("html") else "text"
        raw = ingest((ROOT / "samples" / sample).read_bytes(), kind)
    elif source_kind == "Upload file":
        upload = st.file_uploader("Invoice PDF, HTML, or UTF-8 text", type=["pdf", "html", "txt"])
        if upload:
            kind = "pdf" if upload.name.lower().endswith("pdf") else "html" if upload.name.lower().endswith("html") else "text"
            raw = ingest(upload.getvalue(), kind)
    else:
        is_html = st.checkbox("Input is HTML")
        pasted = st.text_area("Document content", height=180)
        if pasted.strip():
            raw = ingest(pasted, "html" if is_html else "text")
except ValueError as exc:
    st.error(str(exc))

left, right = st.columns([1, 1], gap="large")
with left:
    st.subheader("01 / Source document")
    st.text_area("Extracted source text", value=raw, height=310, disabled=True)
    run = st.button("Extract & validate", type="primary", disabled=not raw)
    with st.expander("Failure simulations"):
        st.caption("These buttons deliberately inject invalid provider output for the demonstration. Reflection removes a currency field on attempt 1; hard failure always returns nonsense.")
        refl = st.button("Simulate reflection recovery", disabled=not raw)
        hard = st.button("Simulate Edge Case Failure", disabled=not raw)
        syntax = st.button("Simulate JSON syntax repair", disabled=not raw)

signature = (raw, mode, reflection, attempts, model)
if run or refl or hard or syntax:
    if mode.startswith("OpenAI") and not key:
        st.error("Add an OpenAI API key or choose Offline demo.")
    else:
        provider = OpenAIProvider(key, model) if mode.startswith("OpenAI") else DemoProvider()
        if refl or hard or syntax:
            provider = FaultProvider(provider, "reflection" if refl else "hard_failure" if hard else "syntax")
        st.session_state.pop("extraction", None)
        with right:
            try:
                with st.status("Processing document…", expanded=True) as status:
                    result = extract_with_retry(raw, provider, max_retries=attempts,
                        reflection=False if syntax else reflection,
                        dlq_dir=Path(os.getenv("DLQ_DIR", str(ROOT / "dlq"))),
                        on_event=lambda event: st.write(f"Attempt {event.attempt} · {event.stage}: {event.message[:140]}"))
                    status.update(label="Validated" if result.validated_data else "Human review required", state="complete" if result.validated_data else "error", expanded=False)
                st.session_state.extraction = (signature, result)
            except Exception as exc:
                st.error(f"Extraction could not start ({type(exc).__name__}). Check configuration and try again.")
with right:
    st.subheader("02 / Validated record")
    cached = st.session_state.get("extraction")
    if cached and cached[0] == signature:
        result = cached[1]
        a, b = st.columns(2)
        a.metric("Provider calls", result.attempts_used)
        b.metric("Outcome", "Verified" if result.validated_data else "Review needed")
        st.caption(f"{result.provider} · {result.execution_status}")
        if result.validated_data:
            invoice = result.validated_data
            lines = sum((line.line_total for line in invoice.line_items), Decimal("0"))
            delta = abs(lines + invoice.tax_amount - invoice.total_amount)
            st.success(f"RECONCILED · line items + tax = {lines + invoice.tax_amount:,.2f} {invoice.currency} · difference {delta:.2f}")
            st.json(invoice.model_dump(mode="json"), expanded=True)
            st.download_button("Download validated invoice", invoice.model_dump_json(indent=2), "validated_invoice.json", "application/json")
        else:
            st.error("No valid record returned. Review the document and audit trail.")
            if result.dlq_path:
                st.caption(f"DLQ record saved: {Path(result.dlq_path).name}")
            if result.storage_error:
                st.error(result.storage_error)
        st.download_button("Download complete audit", result.model_dump_json(indent=2), "extraction_audit.json", "application/json")
        with st.expander("03 / Audit trail & exact corrective prompts", expanded=not bool(result.validated_data)):
            for index, event in enumerate(result.audit_log, 1):
                st.markdown(f"**{index}. Attempt {event.attempt} / {event.stage}**")
                st.text(event.message)
                if event.errors:
                    st.json(event.errors)
                if event.payload:
                    st.code(event.payload, language="json")
                if event.prompt:
                    st.code(event.prompt, language="json")
    else:
        st.info("Run an extraction to see validated JSON, reconciliation, and a full audit trail.")
