from decimal import Decimal
from pathlib import Path
import pytest
from pydantic import ValidationError
from src.schemas import InvoiceExtraction
from src.providers import DemoProvider
from src.extractor import extract_with_retry
from src.ingestion import ingest


def test_golden_pdf_extraction(source, tmp_path):
    result = extract_with_retry(source, DemoProvider(), dlq_dir=tmp_path, backoff=0)
    assert result.execution_status == "SUCCESS"
    assert result.attempts_used == 1 and result.error_log == []
    assert result.validated_data.total_amount == Decimal("1923.35")
    assert result.validated_data.invoice_date.isoformat() == "2024-10-12"
    assert len(result.validated_data.line_items) == 2
    assert list(tmp_path.iterdir()) == []

@pytest.mark.parametrize("qty", [0, -1, 1.5, True, "2"])
def test_quantity_rejected(valid, qty):
    valid["line_items"][0]["quantity"] = qty
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(valid)

@pytest.mark.parametrize("value", ["-1.00", "NaN", "Infinity", True, "1.234", "1.234,56"])
def test_invalid_money_rejected(valid, value):
    valid["total_amount"] = value
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(valid)

@pytest.mark.parametrize("target", ["total_amount", "subtotal"])
def test_cross_field_reconciliation(valid, target):
    valid[target] = "99.00"
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(valid)


def test_line_multiplication_checked(valid):
    valid["line_items"][0]["unit_price"] = "9.00"
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(valid)


def test_two_cent_tolerance(valid):
    valid["total_amount"] = "22.02"
    InvoiceExtraction.model_validate(valid)
    valid["total_amount"] = "22.03"
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(valid)


def test_ambiguous_date_and_extras_rejected(valid):
    valid["invoice_date"] = "10/12/2024"
    valid["invented"] = "forbidden"
    with pytest.raises(ValidationError) as err:
        InvoiceExtraction.model_validate(valid)
    assert len(err.value.errors()) == 2


def test_html_ingestion():
    text = ingest(Path("samples/vendor_contract.html").read_bytes(), "html")
    assert "ignoreThisUntrustedScript" not in text
    result = extract_with_retry(text, DemoProvider(), backoff=0)
    assert result.execution_status == "SUCCESS"
    assert result.validated_data.total_amount == Decimal("412.50")

@pytest.mark.parametrize("data,kind", [(b"not a pdf", "pdf"), ("   ", "text"), ("x" * 60001, "text")], ids=["invalid_pdf", "empty_text", "oversize_text"])
def test_ingestion_errors(data, kind):
    with pytest.raises(ValueError):
        ingest(data, kind)


def test_empty_lines_rejected(valid):
    valid["line_items"] = []
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(valid)
