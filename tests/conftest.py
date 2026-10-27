import json
from pathlib import Path
import pytest
from src.ingestion import ingest

@pytest.fixture
def valid():
    return {"invoice_number": "TEST-1042", "vendor_name": "Test Vendor", "invoice_date": "2024-10-12",
            "line_items": [{"description": "Equipment", "quantity": 2, "unit_price": "10.00", "line_total": "20.00"}],
            "subtotal": "20.00", "tax_amount": "2.00", "total_amount": "22.00", "currency": "USD"}

@pytest.fixture
def source():
    return ingest(Path("samples/invoice_messy.pdf").read_bytes(), "pdf")

class ScriptedProvider:
    name = "Mock provider (test only)"
    def __init__(self, outputs):
        self.outputs = outputs
        self.prompts = []
    def generate(self, prompt):
        self.prompts.append(prompt)
        output = self.outputs[min(len(self.prompts)-1, len(self.outputs)-1)]
        if isinstance(output, Exception):
            raise output
        return json.dumps(output) if isinstance(output, dict) else output

@pytest.fixture(autouse=True)
def project_directory(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
