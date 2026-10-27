"""Business rules remain mandatory after every provider or heuristic repair."""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

TOLERANCE = Decimal("0.02")
Money = Annotated[Decimal, Field(ge=0, le=Decimal("1000000000"), max_digits=12, decimal_places=2)]


def money(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("Expected a finite monetary number")
    cleaned = str(value).strip()
    # Only unambiguous US/UK grouped amounts; do not guess decimal-comma formats.
    if isinstance(value, str):
        cleaned = re.sub(r"^(?:USD|EUR|GBP)\s*", "", cleaned)
        cleaned = re.sub(r"^[$€£]\s*", "", cleaned)
        if not re.fullmatch(r"-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?", cleaned):
            raise ValueError("Use 1234.56 or 1,234.56; ambiguous money is rejected")
        cleaned = cleaned.replace(",", "")
    try:
        result = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("Invalid monetary value") from exc
    if not result.is_finite():
        raise ValueError("Money must be finite")
    return result


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class LineItem(StrictModel):
    description: str = Field(min_length=1, max_length=300)
    quantity: Annotated[StrictInt, Field(gt=0, le=1000000)]
    unit_price: Annotated[Decimal, Field(gt=0, le=Decimal("1000000000"), max_digits=12, decimal_places=2)]
    line_total: Money

    @field_validator("unit_price", "line_total", mode="before")
    @classmethod
    def normalize_money(cls, value):
        return money(value)

    @model_validator(mode="after")
    def reconcile_line(self):
        if abs(self.quantity * self.unit_price - self.line_total) > TOLERANCE:
            raise ValueError("quantity × unit_price must equal line_total within 0.02")
        return self


class InvoiceExtraction(StrictModel):
    invoice_number: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,63}$")
    vendor_name: str = Field(min_length=1, max_length=200)
    invoice_date: date
    line_items: list[LineItem] = Field(min_length=1, max_length=200)
    subtotal: Money
    tax_amount: Money
    total_amount: Money
    currency: Literal["USD", "EUR", "GBP"]

    @field_validator("subtotal", "tax_amount", "total_amount", mode="before")
    @classmethod
    def normalize_money(cls, value):
        return money(value)

    @field_validator("invoice_date", mode="before")
    @classmethod
    def normalize_date(cls, value):
        if type(value) is date:
            return value
        if not isinstance(value, str):
            raise ValueError("Date must be an ISO date or a supported month-name date")
        value = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", value.strip(), flags=re.I)
        value = re.sub(r"\s+of\s+", " ", value, flags=re.I)
        for fmt in ("%Y-%m-%d", "%d %b, %Y", "%d %B, %Y", "%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        raise ValueError("Unsupported or ambiguous date; use YYYY-MM-DD or 12th of Oct, 2024")

    @model_validator(mode="after")
    def reconcile_invoice(self):
        lines = sum((item.line_total for item in self.line_items), Decimal("0"))
        if abs(lines - self.subtotal) > TOLERANCE:
            raise ValueError("sum(line_total) must match subtotal within 0.02")
        if abs(self.subtotal + self.tax_amount - self.total_amount) > TOLERANCE:
            raise ValueError("subtotal + tax_amount must match total_amount within 0.02")
        if abs(lines + self.tax_amount - self.total_amount) > TOLERANCE:
            raise ValueError("sum(line_total) + tax_amount must match total_amount within 0.02")
        return self
