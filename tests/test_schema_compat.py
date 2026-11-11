"""Actual SDK wire assertions + deterministic tools. No real model requests."""
from copy import deepcopy
import json

import httpx
from openai import OpenAI
import pytest

from content_planner.agent import Limits, Planner
from content_planner.model import ModelConfigurationError, OpenAIResponsesModel
from content_planner.schema_compat import SchemaReferenceError, inline_local_refs
from content_planner.schemas import TOOL_MODELS, tool_definitions
from conftest import request as business_request


def response(output):
    return httpx.Response(200, json={"id": "resp_protocol", "object": "response", "created_at": 0,
        "status": "completed", "model": "protocol-fixture-not-real", "output": output})


def stop_output():
    return [{"type": "message", "id": "msg_stop", "role": "assistant", "status": "completed",
             "content": [{"type": "output_text", "annotations": [], "text": json.dumps({
                 "action": "stop", "reason_code": "TEST_STOP", "decision_summary": "离线协议测试结束",
                 "missing_fields": [], "pending_items": []})}]}]


def assert_no_refs(node):
    if isinstance(node, dict):
        assert "$ref" not in node
        for value in node.values():
            assert_no_refs(value)
    elif isinstance(node, list):
        for value in node:
            assert_no_refs(value)


def test_sdk_local_expansion_preserves_contract_and_cloud_schema(monkeypatch):
    from content_planner import model as module
    shared = tool_definitions()
    original = deepcopy(shared)
    pydantic_before = {name: m.model_json_schema() for name, m in TOOL_MODELS.items()}
    monkeypatch.setattr(module, "tool_definitions", lambda: shared)
    sent = []
    def respond(req):
        sent.append(json.loads(req.content))
        return response(stop_output())
    with OpenAI(api_key="not-real", base_url="http://127.0.0.1:11434/v1", max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(respond))) as client:
        local = OpenAIResponsesModel("fixture", "not-real", 1, client=client, service_type="ollama")
        cloud = OpenAIResponsesModel("fixture", "not-real", 1, client=client)
        local.choose({"state": {}}, 2)
        cloud.choose({"state": {}}, 2)
    assert sent[1]["tools"] == shared == original
    assert {name: m.model_json_schema() for name, m in TOOL_MODELS.items()} == pydantic_before
    outgoing = {tool["name"]: tool["parameters"] for tool in sent[0]["tools"]}
    assert_no_refs(outgoing)
    search = outgoing["search_materials"]
    filters = search["properties"]["filters"]
    assert filters["type"] == "object" and filters["additionalProperties"] is False
    assert filters["required"] == ["tags", "allowed_usage"]
    assert {v["type"] for v in filters["properties"]["allowed_usage"]["anyOf"]} == {"string", "null"}
    assert search["required"] == original[0]["parameters"]["required"]
    assert search["properties"]["limit"]["minimum"] == 1
    assert search["properties"]["limit"]["maximum"] == 5
    assert search["properties"]["decision_summary"]["maxLength"] == 500
    candidate = outgoing["estimate_plan"]["properties"]["new_spec"]["anyOf"]
    assert {b["type"] for b in candidate} == {"object", "null"}
    obj = next(b for b in candidate if b["type"] == "object")
    assert obj["additionalProperties"] is False
    assert obj["properties"]["mode"]["enum"] == ["basic", "premium"]
    assert obj["properties"]["material_ids"]["minItems"] == 1
    assert obj["properties"]["material_ids"]["maxItems"] == 5
    assert obj["properties"]["creative_brief"]["minLength"] == 1
    assert obj["properties"]["creative_brief"]["maxLength"] == 2000
    draft = outgoing["save_plan"]["properties"]["draft"]
    assert draft["type"] == "object" and draft["additionalProperties"] is False
    tasks = draft["properties"]["campaign_tasks"]
    assert tasks["minItems"] == 1 and tasks["maxItems"] == 12
    assert tasks["items"]["type"] == "object" and tasks["items"]["additionalProperties"] is False
    assert set(tasks["items"]["required"]) == {"task_id", "description", "depends_on", "owner_role", "relative_schedule"}
    assert tasks["items"]["properties"]["depends_on"]["items"]["type"] == "string"


@pytest.mark.parametrize("bad", [
    {"$ref": "#/$defs/missing"},
    {"$ref": "https://external.invalid/tool.json"},
    {"$ref": "other.json#/$defs/X"},
    {"$ref": "#anchor"},
    {"$ref": 1},
    {"$defs": {"A": {"$ref": "#/$defs/A"}}, "$ref": "#/$defs/A"},
    {"$defs": {"A": {"$ref": "#/$defs/B"}, "B": {"$ref": "#/$defs/A"}}, "$ref": "#/$defs/A"},
    {"title": "not a schema", "$ref": "#/title"},
    {"$ref": "#/$defs/bad~2escape"},
])
def test_bad_references_fail_closed(bad):
    before = deepcopy(bad)
    with pytest.raises(SchemaReferenceError):
        inline_local_refs(bad)
    assert bad == before


def test_pointer_escaping_repeated_refs_and_sibling_constraints():
    root = {"$defs": {"A/B~C": {"type": "string", "minLength": 1, "maxLength": 20}},
            "type": "object", "additionalProperties": False, "required": ["values", "short"],
            "properties": {"values": {"type": "array", "items": {"$ref": "#/$defs/A~1B~0C"}},
                           "short": {"$ref": "#/$defs/A~1B~0C", "maxLength": 5}}}
    out = inline_local_refs(root)
    assert out["properties"]["values"]["items"] == root["$defs"]["A/B~C"]
    assert out["properties"]["short"]["allOf"] == [root["$defs"]["A/B~C"], {"maxLength": 5}]
    assert out["required"] == root["required"] and out["additionalProperties"] is False
    assert_no_refs(out)


def test_instance_values_inside_enum_are_preserved_as_data():
    schema = {"type": "object", "enum": [{"$ref": "a literal field, not a schema reference"}],
              "additionalProperties": False, "required": []}
    assert inline_local_refs(schema) == schema


def test_bad_schema_preflight_spends_no_request_or_business_fee(env, monkeypatch):
    from content_planner import model as module
    monkeypatch.setattr(module, "tool_definitions", lambda: [{"name": "bad", "parameters": {"$ref": "#/missing"}}])
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid schema must fail before client creation or request")
    import openai
    monkeypatch.setattr(openai, "OpenAI", forbidden)
    planner = Planner(env[0], env[1], env[2])
    snapshot = planner.run(business_request(env[2]), "real", lambda:
        OpenAIResponsesModel("fixture", "local-placeholder", 3, service_type="ollama"))
    assert snapshot["termination_reason"] == "MODEL_CONFIGURATION"
    assert snapshot["model_turns"] == snapshot["tool_requests"] == 0
    assert snapshot["ledger"] == [] and snapshot["confirmed_incurred_units"] == 0


def test_sdk_string_filters_rejected_object_executes_and_observation_uses_original_ids(env):
    store, catalog, clock = env
    raw = business_request(clock)
    sent = []
    filters = {"tags": [], "allowed_usage": None}
    def respond(req):
        body = json.loads(req.content)
        sent.append(body)
        number = len(sent)
        if number == 2:
            assert store.incurred(store.by_key(raw["request_key"])["snapshot"]["request_id"]) == 0
        if number == 3:
            return response(stop_output())
        args = {"query": "照片", "filters": json.dumps(filters) if number == 1 else filters,
                "limit": 3, "decision_summary": "仅离线SDK与参数校验测试"}
        return response([{"type": "function_call", "id": f"fc_{number}", "call_id": f"original_{number}",
                          "name": "search_materials", "arguments": json.dumps(args), "status": "completed"}])
    with OpenAI(api_key="local-placeholder", base_url="http://127.0.0.1:11434/v1", max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(respond))) as client:
        model = OpenAIResponsesModel("fixture", "local-placeholder", 3, client=client, service_type="ollama")
        snapshot = Planner(store, catalog, clock, Limits(max_model_turns=3)).run(raw, "real", lambda: model)
    assert [r["outcome"] for r in snapshot["tool_results"]] == ["REJECTED", "SUCCESS"]
    assert snapshot["tool_results"][0]["error"]["code"] == "INVALID_ARGUMENT"
    assert snapshot["confirmed_incurred_units"] == 1 and len(snapshot["ledger"]) == 1
    assert sum(a["execution_started"] for a in snapshot["attempts"]) == 1
    assert snapshot["termination_reason"] == "TEST_STOP"
    for wire, call_id, outcome in [(sent[1], "original_1", "REJECTED"), (sent[2], "original_2", "SUCCESS")]:
        observed = next(x for x in wire["input"] if x.get("type") == "function_call_output" and x["call_id"] == call_id)
        assert json.loads(observed["output"])["outcome"] == outcome
