"""SDK MockTransport only: state provenance and lossless native continuation."""
from copy import deepcopy
import json

import httpx
from openai import OpenAI
import pytest

from content_planner.accounting import canonical
from content_planner.model import ModelConfigurationError, OpenAIResponsesModel


def reply(output, number):
    return httpx.Response(200, json={"id": f"response_{number}", "object": "response", "created_at": 0,
                                   "status": "completed", "model": "offline-protocol-fixture", "output": output})


@pytest.mark.parametrize("provider", ["openai", "ollama"])
def test_sdk_keeps_one_latest_state_and_lossless_calls_observations_and_continuation(provider):
    observations = [
        {"outcome": "REJECTED", "error": {"code": "INVALID_ARGUMENT"}, "charged_units": 0},
        {"outcome": "SUCCESS", "data": {"matches": [{"material_id": "mat-001"}]}, "charged_units": 1},
        {"outcome": "SUCCESS", "data": {"quote_id": "quote1"}, "charged_units": 0},
        {"outcome": "SUCCESS", "data": {"artifact_id": "script1", "body": "成功正文保留"}, "charged_units": 6},
        {"outcome": "FAILED", "error": {"code": "SAVE_TEMPORARY", "retryable": True}, "charged_units": 0},
    ]
    originals = deepcopy(observations)
    sent, contexts = [], []
    tool_names = ["search_materials", "search_materials", "estimate_plan", "generate_script", "save_plan"]
    def respond(req):
        wire = json.loads(req.content)
        sent.append(wire)
        n = len(sent)
        if n == 6:
            return reply([], n)
        return reply([
            {"type": "reasoning", "id": f"rs{n}", "summary": [], "encrypted_content": f"opaque-continuation-{n}"},
            {"type": "message", "id": f"msg{n}", "role": "assistant", "status": "completed", "content": [
                {"type": "output_text", "text": '{"state":"provider message; must not be deleted"}', "annotations": []}]},
            {"type": "function_call", "id": f"fc{n}", "call_id": f"native{n}", "name": tool_names[n-1],
             "arguments": json.dumps({"marker": n}), "status": "completed"}], n)
    with OpenAI(api_key="offline-not-a-key", base_url="http://offline.invalid/v1", max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(respond))) as client:
        model = OpenAIResponsesModel("offline-protocol-fixture", "offline", 6, client=client, service_type=provider)
        for i in range(6):
            context = {"state": {"input": {"theme": "保留需求", "hard_requirements": ["必用素材:mat-001"],
                                                    "budget_units": 10, "deadline_at": "2026-11-10T12:00:00+08:00"},
                                  "confirmed_incurred_units": [0, 0, 1, 1, 7, 7][i], "ledger_revision": [0, 0, 1, 1, 2, 2][i],
                                  "ledger": ([{"amount_units": 1}] if i >= 2 else []) + ([{"amount_units": 6}] if i >= 4 else []),
                                  "estimates": {"quote_latest": {"quote_id": f"q{i}"}},
                                  "candidate_snapshots": {"hash": {"canonical_spec": {"material_ids": ["mat-001"]}}},
                                  "artifacts": {"script1": {"body": "成功正文保留"}} if i >= 4 else {},
                                  "tool_results": deepcopy(observations[:i])},
                       "remaining_model_turns": 12-i, "remaining_tool_requests": 10-i}
            contexts.append(deepcopy(context))
            decision = model.choose(context, 20)
            wire = sent[-1]
            assert wire["input"][0] == {"role": "user", "content": canonical(context)}
            assert sum(x.get("role") == "user" for x in wire["input"]) == 1
            assert json.loads(wire["input"][0]["content"]) == context
            native = wire["input"][1:]
            assert [x["type"] for x in native] == ["reasoning", "message", "function_call", "function_call_output"] * i
            for j in range(i):
                rs, msg, call, result = native[j*4:j*4+4]
                assert rs["id"] == f"rs{j+1}" and rs["encrypted_content"] == f"opaque-continuation-{j+1}"
                assert msg["content"][0]["text"] == '{"state":"provider message; must not be deleted"}'
                assert call["call_id"] == result["call_id"] == f"native{j+1}"
                assert call["arguments"] == json.dumps({"marker": j+1})
                assert result["output"] == canonical(observations[j])
            if i < 5:
                model.observe(observations[i], decision.call_id)
        frozen_history = deepcopy(model.history)
        with pytest.raises(ModelConfigurationError):
            model.choose({"state": "over limit must not replace latest state"}, 20)
        assert model.history == frozen_history and len(sent) == model.calls == 6
    assert observations == originals
    for i, wire in enumerate(sent):
        assert json.loads(wire["input"][0]["content"]) == contexts[i]  # Later rounds did not rewrite earlier captured evidence.


def test_snapshot_like_unowned_user_message_is_not_deleted_or_rewritten():
    sent = []
    def respond(req):
        sent.append(json.loads(req.content))
        return reply([], len(sent))
    first = {"state": {"confirmed_incurred_units": 0}, "remaining_model_turns": 3}
    current = {"state": {"confirmed_incurred_units": 7}, "remaining_model_turns": 2}
    with OpenAI(api_key="offline", base_url="http://offline.invalid/v1", max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(respond))) as client:
        model = OpenAIResponsesModel("fixture", "offline", 2, client=client)
        model.choose(first, 20)
        foreign = {"role": "user", "content": canonical(first)}
        model.history.append(foreign)  # Equal text, different identity and provenance.
        before = deepcopy(foreign)
        model.choose(current, 20)
        assert sent[1]["input"] == [{"role": "user", "content": canonical(current)}, before]
        assert foreign == before and first["state"]["confirmed_incurred_units"] == 0
