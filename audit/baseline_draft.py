"""AI-authored audit specimen, deliberately naive. Never used by the app.

Retained to demonstrate concrete extraction anti-patterns and regression checks.
This is not a historical record of changes made by the student.
"""
import json


def parse_invoice(payload):
    record = json.loads(payload)
    # BUG A: permits missing line items, negative quantities and wrong subtotals.
    total = sum(float(item["line_total"]) for item in record.get("line_items", []))
    if abs(total + float(record["tax_amount"]) - float(record["total_amount"])) > .02:
        raise ValueError("Totals do not match")
    return record


def retry_prompt(document, previous, error, history):
    # BUG B: keeps appending full document and old attempts; grows unbounded.
    return history + "\n" + document + "\n" + previous + "\n" + str(error)
