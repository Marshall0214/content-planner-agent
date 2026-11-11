"""Local Responses configuration + actual SDK wire format; no real inference."""
import json

import httpx
from openai import OpenAI
import pytest

from content_planner.model import ModelConfigurationError, OpenAIResponsesModel


def configure(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "ollama")
    monkeypatch.setenv("MODEL_NAME", "verified-model-id")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv("MODEL_TEMPERATURE", "0.2")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_THINK", raising=False)


def test_local_responses_native_call_id_and_actual_observation_roundtrip(monkeypatch):
    configure(monkeypatch)
    sent = []
    result = {"outcome": "FAILED", "error": {"code": "SAVE_TEMPORARY", "retryable": True}}
    stop = {"action": "stop", "decision_summary": "根据实际错误保留成果停止", "reason_code": "TOOL_FAILED",
            "missing_fields": [], "pending_items": ["保存未完成"]}
    def respond(request):
        body = json.loads(request.content)
        sent.append(body)
        assert request.url.path == "/v1/responses"
        assert body["temperature"] == 0.2 and body["store"] is False
        output = ([{"type": "function_call", "id": "fc_1", "call_id": "native-id-1",
                    "name": "search_materials", "arguments": '{"query":"照片"}', "status": "completed"}]
                  if len(sent) == 1 else [{"type": "message", "id": "msg_2", "role": "assistant", "status": "completed",
                    "content": [{"type": "output_text", "text": json.dumps(stop), "annotations": []}]}])
        return httpx.Response(200, json={"id": f"resp_{len(sent)}", "object": "response", "created_at": 0,
                                        "status": "completed", "model": "verified-model-id", "output": output,
                                        "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}})
    with OpenAI(api_key="local-placeholder", base_url="http://127.0.0.1:11434/v1", max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(respond))) as client:
        model = OpenAIResponsesModel.from_env(2, client=client)
        first = model.choose({"state": {}}, 2)
        model.observe(result, first.call_id)
        second = model.choose({"state": {"tool_results": [result]}}, 2)
        assert first.call_id == "native-id-1" and first.usage["total_tokens"] == 15
        assert second.stop == stop and model.mode == "real"
        assert any(x.get("type") == "function_call_output" and x["call_id"] == first.call_id
                   and json.loads(x["output"]) == result for x in sent[1]["input"])
        assert not any(k in sent[1] for k in ("previous_response_id", "conversation"))
        assert model.configuration["service_type"] == "ollama"
        with pytest.raises(ModelConfigurationError):
            model.choose({}, 2)
        assert len(sent) == 2


@pytest.mark.parametrize("endpoint", ["", "http://remote.invalid/v1", "https://ollama.com/v1",
                                       "http://127.0.0.1:11434", "http://key:secret@localhost:11434/v1"])
def test_local_requires_explicit_loopback_v1_endpoint(monkeypatch, endpoint):
    configure(monkeypatch)
    monkeypatch.setenv("OPENAI_BASE_URL", endpoint)
    with pytest.raises(ModelConfigurationError):
        OpenAIResponsesModel.from_env(3)


@pytest.mark.parametrize("value", ["nan", "inf", "-1", "3", "invalid"])
def test_local_temperature_must_be_finite_and_bounded(monkeypatch, value):
    configure(monkeypatch)
    monkeypatch.setenv("MODEL_TEMPERATURE", value)
    with pytest.raises(ModelConfigurationError):
        OpenAIResponsesModel.from_env(3)


def test_local_missing_model_fails_without_cloud_key_or_fallback(monkeypatch):
    configure(monkeypatch)
    monkeypatch.delenv("MODEL_NAME")
    with pytest.raises(ModelConfigurationError):
        OpenAIResponsesModel.from_env(3)


@pytest.mark.parametrize("enabled", [False, True])
def test_ollama_thinking_switch_serializes_as_protocol_extension(monkeypatch, enabled):
    configure(monkeypatch)
    monkeypatch.setenv("MODEL_THINK", str(enabled).lower())
    sent = []
    def respond(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "resp_think", "object": "response", "created_at": 0,
            "status": "completed", "model": "verified-model-id", "output": [], "usage": None})
    with OpenAI(api_key="local", base_url="http://127.0.0.1:11434/v1", max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(respond))) as client:
        model = OpenAIResponsesModel.from_env(1, client=client)
        model.choose({"state": {}}, timeout=2)
        assert sent[0]["think"] is enabled
        assert model.configuration["inference_parameters"]["think"] is enabled


def test_invalid_thinking_switch_is_configuration_error(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv("MODEL_THINK", "automatic")
    with pytest.raises(ModelConfigurationError):
        OpenAIResponsesModel.from_env(1)
