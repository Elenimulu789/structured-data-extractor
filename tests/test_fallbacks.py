import copy
import json
from pathlib import Path
import pytest
from src.extractor import extract_with_retry
from src.providers import ProviderError, DemoProvider
from src.fallback import reflection_prompt
from tests.conftest import ScriptedProvider


def test_reflection_success_attempt_two(valid, source, tmp_path):
    broken = copy.deepcopy(valid)
    broken.pop("currency")
    provider = ScriptedProvider([broken, valid])
    result = extract_with_retry(source, provider, dlq_dir=tmp_path, backoff=0)
    assert result.execution_status == "REPAIRED_VIA_REFLECTION"
    assert result.attempts_used == 2
    correction = json.loads(provider.prompts[1])
    assert correction["validation_errors"][0]["loc"] == ["currency"]
    assert "previous_response" in correction and "source_excerpt" in correction
    assert result.error_log and not list(tmp_path.iterdir())


def test_dlq_after_three_calls(source, tmp_path):
    provider = ScriptedProvider(["gibberish"])
    result = extract_with_retry(source, provider, max_retries=3, dlq_dir=tmp_path, backoff=0)
    assert result.execution_status == "DLQ_FAILED"
    assert result.attempts_used == len(provider.prompts) == 3
    assert result.validated_data is None
    record = json.loads(Path(result.dlq_path).read_text())
    assert record["source_text"] == source and record["last_payload"] == "gibberish"
    assert record["result"]["audit_log"]


def test_no_reflection_one_call(valid, source, tmp_path):
    valid.pop("currency")
    provider = ScriptedProvider([valid])
    result = extract_with_retry(source, provider, reflection=False, dlq_dir=tmp_path, backoff=0)
    assert result.attempts_used == 1 and result.execution_status == "DLQ_FAILED"


def test_heuristic_success_still_validates(valid, source, tmp_path):
    payload = json.dumps(valid)[:-1] + ",}"
    result = extract_with_retry(source, ScriptedProvider([payload]), reflection=False, dlq_dir=tmp_path, backoff=0)
    assert result.execution_status == "REPAIRED_HEURISTIC"
    assert result.validated_data.currency == "USD"


def test_heuristic_cannot_bypass_business_rules(valid, source, tmp_path):
    valid["total_amount"] = "999.00"
    payload = json.dumps(valid)[:-1] + ",}"
    result = extract_with_retry(source, ScriptedProvider([payload]), reflection=False, dlq_dir=tmp_path, backoff=0)
    assert result.execution_status == "DLQ_FAILED" and result.validated_data is None


def test_prompt_size_bounded():
    text = reflection_prompt("a" * 60000, "b" * 100000, [{"loc": ["currency"], "msg": "required"}])
    assert len(text) < 15000
    data = json.loads(text)
    assert len(data["source_excerpt"]) < 6100
    assert len(data["previous_response"]) == 8000


def test_transient_failure_retries(valid, source, tmp_path):
    provider = ScriptedProvider([ProviderError("rate limited", retryable=True), valid])
    result = extract_with_retry(source, provider, dlq_dir=tmp_path, backoff=0)
    assert result.execution_status == "SUCCESS" and result.attempts_used == 2
    assert provider.prompts[0] == provider.prompts[1]


def test_permanent_provider_failure_stops(source, tmp_path):
    provider = ScriptedProvider([ProviderError("invalid key")])
    result = extract_with_retry(source, provider, dlq_dir=tmp_path, backoff=0)
    assert result.execution_status == "DLQ_FAILED" and result.attempts_used == 1


def test_dlq_disk_failure_is_visible(source, tmp_path):
    blocked = tmp_path / "not_directory"
    blocked.write_text("occupied")
    result = extract_with_retry(source, ScriptedProvider(["nonsense"]), max_retries=1, dlq_dir=blocked, backoff=0)
    assert result.storage_error and result.dlq_path is None
    assert result.execution_status == "DLQ_FAILED"


def test_actual_contradiction_is_not_invented_away(tmp_path):
    text = Path("samples/invoice_inconsistent.txt").read_text()
    result = extract_with_retry(text, DemoProvider(), dlq_dir=tmp_path, backoff=0)
    assert result.execution_status == "DLQ_FAILED" and result.attempts_used == 3


def test_openai_adapter_sends_strict_schema_and_returns_raw(valid):
    from types import SimpleNamespace as NS
    from src.providers import OpenAIProvider
    provider = object.__new__(OpenAIProvider)
    provider.model = "mock-model"
    captured = {}
    def create(**kwargs):
        captured.update(kwargs)
        return NS(choices=[NS(finish_reason="stop", message=NS(refusal=None, content=json.dumps(valid)))])
    provider.client = NS(chat=NS(completions=NS(create=create)))
    assert json.loads(provider.generate("document")) == valid
    schema = captured["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"]["additionalProperties"] is False
    assert schema["schema"]["$defs"]["WireLine"]["additionalProperties"] is False
    assert set(schema["schema"]["required"]) == set(schema["schema"]["properties"])


def test_refusal_is_not_parsed():
    from types import SimpleNamespace as NS
    from src.providers import OpenAIProvider
    provider = object.__new__(OpenAIProvider)
    provider.model = "mock-model"
    provider.client = NS(chat=NS(completions=NS(create=lambda **kw: NS(choices=[NS(finish_reason="stop", message=NS(refusal="Missing evidence", content=None))]))))
    with pytest.raises(ProviderError, match="refused"):
        provider.generate("not an invoice")
