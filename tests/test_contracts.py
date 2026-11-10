from copy import deepcopy
import json
import pytest
from pydantic import ValidationError

from content_planner.schemas import Request, EstimateArgs, tool_definitions
from content_planner.tools import Catalog
from conftest import request, run_agent, make_toolbox, call, search, quote, prepare


@pytest.mark.parametrize("field", ["budget_units", "deadline_at"])
def test_C02_C03_missing_inputs_never_call_model(env, field):
    raw = request(env[2])
    raw[field] = None
    _, model, s = run_agent(env, raw=raw)
    assert s["status"] == "NEEDS_INPUT"
    assert s["missing_fields"] == [field]
    assert model.calls == 0 and env[0].incurred(s["request_id"]) == 0
    assert not s["save_receipt"] and not s["attempts"]


@pytest.mark.parametrize("bad", [True, False, -1, 1.0, "10", float("nan"), float("inf")])
def test_C12_budget_strict(env, bad):
    raw = request(env[2])
    raw["budget_units"] = bad
    with pytest.raises(ValidationError):
        Request.model_validate(raw)


@pytest.mark.parametrize("bad", ["2026-11-10", "2026-11-10T10:00:00", 123, True])
def test_C12_deadline_explicit_time_and_offset(env, bad):
    raw = request(env[2])
    raw["deadline_at"] = bad
    with pytest.raises(ValidationError):
        Request.model_validate(raw)


def test_C12_zero_budget_does_not_pay_for_search(env):
    tb = make_toolbox(env, budget=0)
    r = search(tb)
    assert r["outcome"] == "REJECTED" and r["error"]["code"] == "BUDGET_GUARD"
    assert r["charged_units"] == 0 and env[0].incurred(tb.request_id) == 0


def test_C12_expired_deadline_prevents_calls(env):
    raw = request(env[2], minutes=-1)
    _, model, s = run_agent(env, raw=raw)
    assert s["termination_reason"] == "DEADLINE_EXPIRED"
    assert model.calls == 0 and not s["ledger"]


def test_C12_invalid_refs_and_empty_body_not_success(env):
    tb = make_toolbox(env)
    r = call(tb, "generate_script", quote_id="another-request-quote")
    assert r["error"]["code"] == "INVALID_QUOTE_REF"
    search(tb)
    r = call(tb, "estimate_plan", new_spec={"material_ids": ["not-found"], "mode": "basic", "creative_brief": "内容"},
             quote_id=None, stage="pre_generation", script_artifact_id=None)
    assert r["error"]["code"] == "INVALID_MATERIAL_REF"
    assert env[0].incurred(tb.request_id) == 1


def test_C12_finite_hard_requirements_preserved(env):
    raw = request(env[2])
    raw["hard_requirements"] = ["必含原文:珍藏每一次告别", "必用素材:mat-001"]
    _, _, s = run_agent(env, raw=raw)
    assert s["status"] == "COMPLETED"
    assert "珍藏每一次告别" in s["saved_plan"]["script"]["body"]
    assert s["saved_plan"]["hard_requirements"] == sorted(raw["hard_requirements"])
    assert "mat-001" in s["saved_plan"]["material_refs"]


def test_C12_unsupported_explicit_video_requirement_not_silently_softened(env):
    raw = request(env[2])
    raw["hard_requirements"] = ["成片必须精确30秒"]
    _, model, s = run_agent(env, raw=raw)
    assert s["status"] == "NEEDS_INPUT"
    assert s["termination_reason"] == "UNSUPPORTED_REQUIREMENT"
    assert s["input"]["hard_requirements"] == raw["hard_requirements"]
    assert not s["ledger"] and model.calls == 0


def test_C12_required_material_not_dropped_in_candidate(env):
    raw = request(env[2])
    raw["hard_requirements"] = ["必用素材:mat-003"]
    # Construct a bound tool fixture with that original requirement.
    tb = make_toolbox(env)
    env[0].update(tb.request_id, lambda s: s["input"].update(hard_requirements=raw["hard_requirements"]))
    search(tb)
    r = quote(tb)  # proposes only mat-001
    assert r["outcome"] == "REJECTED" and r["error"]["code"] == "HARD_REQUIREMENT_VIOLATION"


def test_schema_strict_tool_contracts():
    def check(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                check(value)
        elif isinstance(node, list):
            for value in node:
                check(value)
    for tool in tool_definitions():
        assert tool["strict"] is True
        check(tool["parameters"])


def test_quote_inputs_exclusive():
    raw = {"new_spec": None, "quote_id": None, "stage": "pre_generation",
           "script_artifact_id": None, "decision_summary": "测试"}
    with pytest.raises(ValidationError):
        EstimateArgs.model_validate(raw)
    raw.update(new_spec={"material_ids": ["mat-001"], "mode": "basic", "creative_brief": "内容"}, quote_id="q")
    with pytest.raises(ValidationError):
        EstimateArgs.model_validate(raw)


def test_invalid_cost_table_rejected_before_running(tmp_path):
    original = Catalog()
    (tmp_path / "materials-v1.json").write_text(json.dumps(original.material_data), encoding="utf-8")
    bad = deepcopy(original.cost_data)
    bad["tools"]["save_plan"]["fee"] = -1
    (tmp_path / "cost-v1.json").write_text(json.dumps(bad), encoding="utf-8")
    (tmp_path / "fixtures.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="CATALOG_INVALID"):
        Catalog(tmp_path)

