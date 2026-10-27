import copy
import json
import importlib.util
from pathlib import Path
import pytest
from pydantic import ValidationError
from src.schemas import InvoiceExtraction
from src.fallback import reflection_prompt


def baseline_module():
    spec = importlib.util.spec_from_file_location("baseline", Path("audit/baseline_draft.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_naive_baseline_accepts_wrong_subtotal_final_rejects(valid):
    broken = copy.deepcopy(valid)
    broken["subtotal"] = "999.00"
    assert baseline_module().parse_invoice(json.dumps(broken))["subtotal"] == "999.00"
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(broken)


def test_naive_baseline_ignores_quantity_final_rejects(valid):
    broken = copy.deepcopy(valid)
    broken["line_items"][0]["quantity"] = -2
    baseline_module().parse_invoice(json.dumps(broken))
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(broken)


def test_retry_baseline_grows_final_bounded():
    baseline = baseline_module()
    doc, history = "x" * 60000, ""
    for _ in range(3):
        history = baseline.retry_prompt(doc, "old json", "error", history)
    assert len(history) > 180000
    assert len(reflection_prompt(doc, "old json", [{"msg": "error", "loc": []}])) < 7000
