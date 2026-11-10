"""Actual installed SDK + HTTPX in-memory transport. No outbound HTTP or real inference."""
import json
import httpx
import openai

from content_planner.model import OpenAIResponsesModel


def test_installed_sdk_serializes_tool_continuation_and_disables_retries(monkeypatch):
    requests = []
    stop = {"action": "stop", "decision_summary": "本地协议测试停止", "reason_code": "TEST",
            "missing_fields": [], "pending_items": []}
    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            output = [{"type": "function_call", "id": "fc_local", "call_id": "call_local",
                       "name": "search_materials", "arguments": json.dumps(
                           {"query": "照片", "filters": {"tags": [], "allowed_usage": None},
                            "limit": 3, "decision_summary": "协议测试"}), "status": "completed"}]
        else:
            output = [{"type": "message", "id": "msg_local", "role": "assistant", "status": "completed",
                       "content": [{"type": "output_text", "text": json.dumps(stop), "annotations": []}]}]
        return httpx.Response(200, json={"id": "resp_local", "object": "response", "created_at": 0,
                                        "status": "completed", "model": "local-sdk-test", "output": output})
    real_constructor = openai.OpenAI
    captured = {}
    def constructor(**kwargs):
        captured.update(kwargs)
        return real_constructor(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    monkeypatch.setattr(openai, "OpenAI", constructor)
    model = OpenAIResponsesModel("explicit-local-sdk-test", "not-a-real-key", 2)
    decision = model.choose({"state": {}}, timeout=2)
    assert decision.tool == "search_materials" and captured["max_retries"] == 0
    model.observe({"outcome": "FAILED", "error": {"code": "SEARCH_TEMPORARY"}}, decision.call_id)
    after = model.choose({"state": {"observed_failure": True}}, timeout=2)
    assert after.stop == stop
    assert len(requests) == 2 and requests[0]["parallel_tool_calls"] is False
    assert requests[0]["model"] == "explicit-local-sdk-test" and requests[0]["store"] is False
    assert any(x.get("type") == "function_call_output" and x["call_id"] == "call_local" for x in requests[1]["input"])
    model.client.close()
