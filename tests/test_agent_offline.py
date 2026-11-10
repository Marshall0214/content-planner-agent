from copy import deepcopy
from types import SimpleNamespace
import json
import pytest

from content_planner.agent import Limits, Planner
from content_planner.model import Decision, ModelConfigurationError, OfflineModel, OpenAIResponsesModel
from content_planner.reporting import build_report, write_evidence
from conftest import request, run_agent


def test_C04_budget_feedback_reaches_next_offline_request(env):
    _, model, s = run_agent(env, scenario="budget_adjust")
    assert s["status"] == "COMPLETED" and s["confirmed_incurred_units"] == 8
    quotes = sorted(s["estimates"].values(), key=lambda q: q["sequence"])
    assert quotes[0]["projected_total_units"] == 12 and quotes[1]["projected_total_units"] == 8
    results = [e for e in s["events"] if e["kind"] == "tool_result"]
    over = next(e for e in results if e["result"]["tool"] == "estimate_plan"
                and e["result"]["data"]["feasibility"] == "OVER_BUDGET")
    next_request = next(e for e in s["events"] if e["kind"] == "model_request"
                        and over["event_id"] in e["observed_event_ids"])
    assert next_request["context"]["state"]["tool_results"][-1]["data"]["projected_total_units"] == 12
    assert s["mode"] == "offline_mock"
    assert build_report(s)["real_model_decision_evidence"] is False


def test_C04_no_feasible_budget_stops_without_modifying_input(env):
    raw = request(env[2], budget=3)
    _, model, s = run_agent(env, raw=raw)
    assert s["status"] == "INCOMPLETE" and s["confirmed_incurred_units"] == 1
    assert s["input"]["budget_units"] == 3 and not s["save_receipt"]
    q = list(s["estimates"].values())[-1]
    assert q["projected_total_units"] == 8 and q["budget_gap_units"] == 5
    assert model.calls == 3
    milestones = {m["step"]: m["status"] for m in build_report(s)["task_plan"]}
    assert milestones["estimate_pre"] == "SUCCEEDED"  # successful estimate reports infeasibility
    assert milestones["generate"] == milestones["save"] == "PENDING"


@pytest.mark.parametrize("limit_name", ["max_model_turns", "max_tool_requests"])
@pytest.mark.parametrize("fixture,status,saved,fee", [
    ("no_fault", "COMPLETED", "CONFIRMED", 8),
    ("save_fail_once", "INCOMPLETE", "FAILED", 7),
    ("unknown_result", "INCOMPLETE", "UNKNOWN", 7),
])
def test_C10_last_legal_save_three_outcomes_no_extra_calls(env, limit_name, fixture, status, saved, fee):
    limits = Limits(**{limit_name: 5})
    _, model, s = run_agent(env, fixture=fixture, limits=limits)
    assert s["status"] == status and s["save_state"] == saved
    assert s["model_turns"] == s["tool_requests"] == model.calls == 5
    assert s["confirmed_incurred_units"] == fee
    assert any(a["kind"] == "script" for a in s["artifacts"].values())
    assert len(s["tool_results"]) == 5
    if saved == "UNKNOWN":
        assert build_report(s)["actual_costs"]["total_actual_units"] is None
    elif status == "COMPLETED":
        assert s["termination_reason"] == "SAVED"
    else:
        assert s["termination_reason"] in ("MODEL_LIMIT", "TOOL_LIMIT")


@pytest.mark.parametrize("scenario", ["invalid", "false_finish"])
def test_C10_C11_protocol_errors_cannot_claim_success_or_loop_forever(env, scenario):
    _, model, s = run_agent(env, scenario=scenario, limits=Limits(max_model_turns=3))
    assert s["status"] == "INCOMPLETE" and s["termination_reason"] == "MODEL_LIMIT"
    assert model.calls == 3 and not s["ledger"] and not s["save_receipt"]


def test_C11_protocol_error_is_actually_sent_to_next_model_request(env):
    _, _, s = run_agent(env, scenario="false_finish", limits=Limits(max_model_turns=2))
    sent = [e["context"] for e in s["events"] if e["kind"] == "model_request"]
    assert sent[0]["protocol_observations"] == []
    assert sent[1]["protocol_observations"][0]["error"]["code"] == "PROTOCOL_ERROR"


def test_C10_tool_limit_stops_before_new_model_turn(env):
    _, model, s = run_agent(env, limits=Limits(max_tool_requests=2))
    assert s["status"] == "INCOMPLETE" and s["termination_reason"] == "TOOL_LIMIT"
    assert model.calls == s["tool_requests"] == 2


def test_C10_wall_time_stops_before_tool_execution(env):
    clock = env[2]
    class Slow(OfflineModel):
        def choose(self, context, timeout):
            value = super().choose(context, timeout)
            clock.advance(181)
            return value
    _, model, s = run_agent(env, model=Slow())
    assert s["termination_reason"] == "RUN_LIMIT"
    assert model.calls == 1 and s["tool_requests"] == 0 and not s["ledger"]


def test_model_timeout_does_not_execute_late_action(env):
    clock = env[2]
    class Slow(OfflineModel):
        def choose(self, context, timeout):
            value = super().choose(context, timeout)
            clock.advance(timeout + 1)
            return value
    _, model, s = run_agent(env, model=Slow())
    assert s["termination_reason"] == "MODEL_TIMEOUT"
    assert model.calls == 1 and not s["ledger"] and s["tool_requests"] == 0


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 0, -1])
def test_limits_reject_nonfinite_or_nonpositive_timeouts(value):
    with pytest.raises(ValueError):
        Limits(run_timeout_s=value)


def test_C05_generation_failure_retry_is_model_action_and_retained(env):
    _, model, s = run_agent(env, fixture="generate_fail_once")
    assert s["status"] == "COMPLETED" and s["confirmed_incurred_units"] == 8
    attempts = [a for a in s["attempts"] if a["tool"] == "generate_script"]
    assert [a["status"] for a in attempts] == ["FAILED", "SUCCEEDED"]
    assert s["cumulative_sim_elapsed_s"] == 600
    assert any(r["tool"] == "generate_script" and r["outcome"] == "FAILED" for r in model.observed)


def test_real_mode_missing_config_never_falls_back(env, monkeypatch):
    for name in ("MODEL_NAME", "OPENAI_API_KEY", "MODEL_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    p = Planner(env[0], env[1], env[2])
    s = p.run(request(env[2]), "real", lambda: OpenAIResponsesModel.from_env(None))
    assert s["status"] == "FAILED" and s["termination_reason"] == "MODEL_CONFIGURATION"
    assert s["model_turns"] == 0 and s["mode"] == "real" and not s["artifacts"]


def test_mode_mismatch_cannot_disguise_mock_as_real(env):
    p = Planner(env[0], env[1], env[2])
    s = p.run(request(env[2]), "real", lambda: OfflineModel())
    assert s["termination_reason"] == "MODEL_CONFIGURATION" and not s["ledger"]


def test_responses_adapter_roundtrip_protocol_with_fake_sdk_no_network():
    class FakeResponses:
        def __init__(self):
            self.requests = []
        def create(self, **kwargs):
            self.requests.append(deepcopy(kwargs))
            if len(self.requests) == 1:
                return SimpleNamespace(id="fake-response-1", usage=None, output_text="",
                    output=[SimpleNamespace(type="function_call", name="search_materials", call_id="fake-call-1",
                        arguments=json.dumps({"query": "照片", "filters": {"tags": [], "allowed_usage": None},
                                              "limit": 3, "decision_summary": "查素材"}))])
            return SimpleNamespace(id="fake-response-2", usage=None, output=[],
                output_text=json.dumps({"action": "stop", "decision_summary": "测试停止",
                    "reason_code": "TEST", "missing_fields": [], "pending_items": []}))
    responses = FakeResponses()
    adapter = OpenAIResponsesModel("explicit-test-model", "not-a-real-key", 2,
                                   client=SimpleNamespace(responses=responses))
    decision = adapter.choose({"state": {}}, timeout=2)
    assert decision.tool == "search_materials"
    observation = {"outcome": "FAILED", "error": {"code": "SEARCH_TEMPORARY"}}
    adapter.observe(observation, decision.call_id)
    final = adapter.choose({"state": {"actual_feedback": observation}}, timeout=2)
    assert final.stop["action"] == "stop"
    sent = responses.requests[-1]
    outputs = [x for x in sent["input"] if isinstance(x, dict) and x.get("type") == "function_call_output"]
    assert outputs[0]["call_id"] == "fake-call-1"
    assert json.loads(outputs[0]["output"]) == observation
    assert sent["parallel_tool_calls"] is False and sent["store"] is False
    with pytest.raises(ModelConfigurationError):
        adapter.choose({}, timeout=2)
    assert len(responses.requests) == 2


def test_evidence_files_are_real_offline_output_not_real_claim(env, tmp_path):
    _, _, s = run_agent(env)
    report = build_report(s)
    dest = write_evidence(s, report, tmp_path, "C01")
    recorded = json.loads((dest / "output.json").read_text(encoding="utf-8"))
    assert recorded["mode"] == "offline_mock" and not recorded["real_model_decision_evidence"]
    assert (dest / "trace.jsonl").read_text(encoding="utf-8").strip()
    assert "脚本正文" in (dest / "report.md").read_text(encoding="utf-8")
    assert not list((tmp_path / "real").glob("*")) if (tmp_path / "real").exists() else True
