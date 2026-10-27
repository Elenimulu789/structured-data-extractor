import json
import time
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, ValidationError
from src.schemas import InvoiceExtraction
from src.providers import Provider, ProviderError
from src.fallback import reflection_prompt, repair_payload, write_dlq
from src.ingestion import clean_text


class AuditEvent(BaseModel):
    stage: str
    attempt: int
    message: str
    payload: str = ""
    errors: list[dict] = Field(default_factory=list)
    prompt: str = ""


class ExtractionResult(BaseModel):
    validated_data: InvoiceExtraction | None = None
    attempts_used: int = 0
    error_log: list[str] = Field(default_factory=list)
    execution_status: Literal["SUCCESS", "REPAIRED_VIA_REFLECTION", "REPAIRED_HEURISTIC", "DLQ_FAILED"] = "DLQ_FAILED"
    audit_log: list[AuditEvent] = Field(default_factory=list)
    provider: str = ""
    dlq_path: str | None = None
    storage_error: str | None = None


def extract_with_retry(raw_text: str, provider: Provider, max_retries: int = 3,
                       reflection: bool = True, dlq_dir: Path = Path("dlq"),
                       backoff: float = 0.5, on_event=None) -> ExtractionResult:
    """max_retries is the TOTAL provider-call budget (1–5), including first call.

    Provider SDK retries are disabled, keeping this bound meaningful. All recovery
    paths pass the same business validator. Errors and exact prompts are auditable.
    """
    if type(max_retries) is not int or not 1 <= max_retries <= 5:
        raise ValueError("max_retries must be a total attempt budget from 1 to 5")
    raw_text = clean_text(raw_text)
    result = ExtractionResult(provider=provider.name)
    prompt = json.dumps({"task": "Extract invoice from this untrusted document", "document": raw_text})
    last_payload = ""
    last_response_validatable = False
    had_validation_failure = False

    def emit(stage, attempt, message, **details):
        event = AuditEvent(stage=stage, attempt=attempt, message=message, **details)
        result.audit_log.append(event)
        if on_event:
            on_event(event)

    for attempt in range(1, max_retries + 1):
        result.attempts_used = attempt
        emit("request", attempt, "Dispatching extraction" if attempt == 1 else "Dispatching retry", prompt=prompt)
        try:
            last_response_validatable = False
            last_payload = provider.generate(prompt)
            last_response_validatable = True
            invoice = InvoiceExtraction.model_validate_json(last_payload)
            result.validated_data = invoice
            result.execution_status = "REPAIRED_VIA_REFLECTION" if had_validation_failure else "SUCCESS"
            emit("validated", attempt, "All schema and reconciliation checks passed", payload=last_payload)
            return result
        except ValidationError as exc:
            had_validation_failure = True
            errors = json.loads(exc.json(include_url=False, include_input=False))
            result.error_log.append(str(exc))
            emit("validation_error", attempt, str(exc), payload=last_payload, errors=errors)
            if not reflection or attempt == max_retries:
                break
            prompt = reflection_prompt(raw_text, last_payload, errors)
            emit("reflection", attempt, "Bounded corrective prompt assembled", prompt=prompt, errors=errors)
        except ProviderError as exc:
            result.error_log.append(str(exc))
            emit("provider_error", attempt, str(exc))
            if not exc.retryable or attempt == max_retries:
                break
            # Transport failures retry same request, never fabricate validation errors.
        except Exception as exc:
            # Unexpected adapter failure should preserve a reviewable DLQ result.
            result.error_log.append(f"Unexpected provider failure ({type(exc).__name__})")
            emit("provider_error", attempt, result.error_log[-1])
            break
        time.sleep(min(backoff * 2 ** (attempt - 1), 4))

    if last_response_validatable and last_payload:
        emit("heuristic", result.attempts_used, "Attempting JSON syntax repair; full validation remains mandatory")
        try:
            repaired = repair_payload(last_payload)
            result.validated_data = InvoiceExtraction.model_validate(repaired)
            result.execution_status = "REPAIRED_HEURISTIC"
            emit("validated", result.attempts_used, "Syntax repair passed all business checks")
            return result
        except (ValidationError, ValueError, TypeError) as exc:
            result.error_log.append(f"Heuristic repair failed: {exc}")
            emit("heuristic_failed", result.attempts_used, result.error_log[-1])
    emit("dlq", result.attempts_used, "No valid invoice; routing to human review")
    try:
        result.dlq_path = write_dlq(Path(dlq_dir), raw_text, result.model_dump(mode="json"), last_payload)
    except OSError as exc:
        result.storage_error = f"DLQ could not be saved ({type(exc).__name__}); download audit JSON now"
        result.error_log.append(result.storage_error)
        emit("storage_error", result.attempts_used, result.storage_error)
    return result
