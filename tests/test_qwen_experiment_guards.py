"""Fail-closed experiment gates: these tests never issue inference requests."""
import json
import sys

import httpx
import pytest

from scripts import validate_qwen


def test_failed_smoke_blocks_acceptance_before_client_or_database_creation(tmp_path, monkeypatch):
    previous = tmp_path / "failed-smoke.json"
    previous.write_text(json.dumps({"smoke_passed": False, "model": "actual-test-id",
                                    "endpoint": "http://127.0.0.1:11434/v1"}), encoding="utf-8")
    def forbidden(*args, **kwargs):
        raise AssertionError("failed smoke must not initialize an inference client or database")
    monkeypatch.setattr(validate_qwen, "OpenAI", forbidden)
    monkeypatch.setattr(validate_qwen, "Store", forbidden)
    monkeypatch.setattr(validate_qwen, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["validate_qwen.py", "acceptance", "--endpoint",
        "http://127.0.0.1:11434/v1", "--model", "actual-test-id", "--smoke-index", str(previous)])
    with pytest.raises(SystemExit) as exc:
        validate_qwen.main()
    assert exc.value.code == 2
    assert not (tmp_path / "var").exists() and not (tmp_path / "examples").exists()


@pytest.mark.parametrize("cap", [3, 6, 10, 20])
def test_batch_cap_rejects_extra_post_before_transport(tmp_path, cap):
    index = {"call_cap": cap, "inference_requests": [{} for _ in range(cap)], "active_case": "test"}
    transport = validate_qwen.RecordedTransport(index, tmp_path / "index.json", "http://127.0.0.1:11434/v1")
    transport.inner.close()
    def forbidden(request):
        raise AssertionError("quota must be checked before an HTTP request is sent")
    transport.inner = httpx.MockTransport(forbidden)
    try:
        with pytest.raises(RuntimeError, match="cap exhausted"):
            transport.handle_request(httpx.Request("POST", "http://127.0.0.1:11434/v1/responses", json={}))
        assert len(index["inference_requests"]) == cap and not (tmp_path / "index.json").exists()
    finally:
        transport.close()


def test_evidence_redacts_reasoning_without_changing_outbound_context():
    body = {"input": [{"type": "reasoning", "id": "r1", "summary": [{"text": "private reasoning"}]},
                       {"type": "function_call_output", "call_id": "real-id", "output": '{"outcome":"SUCCESS"}'}]}
    recorded = validate_qwen.public_request(body)
    assert "private reasoning" not in json.dumps(recorded)
    assert body["input"][0]["summary"][0]["text"] == "private reasoning"
    assert recorded["input"][0]["omitted_from_evidence"] is True
    assert recorded["input"][1] == body["input"][1]


def passed_normal_fixture(tmp_path):
    """Synthetic gate fixture only; never exported as real model evidence."""
    from content_planner.accounting import digest
    (tmp_path / "src/content_planner").mkdir(parents=True)
    (tmp_path / "data").mkdir()
    for name in ("pyproject.toml", "uv.lock"):
        (tmp_path / name).write_text("gate fixture", encoding="utf-8")
    source = digest({p: "gate fixture" for p in ("pyproject.toml", "uv.lock")})
    receipt, plan = {"plan_id": "test-plan"}, {"title": "synthetic test plan"}
    rows = []
    for case in ("normal", "normal_replay"):
        folder = tmp_path / case
        folder.mkdir()
        (folder / "output.json").write_text(json.dumps({"mode": "real", "task_status": "COMPLETED",
            "save_state": "CONFIRMED", "receipt": receipt, "saved_plan": plan}), encoding="utf-8")
        (folder / "metadata.json").write_text(json.dumps({"source_digest": source}), encoding="utf-8")
        rows.append({"case_id": case, "evidence_dir": case, "this_invocation_requests": 0,
                     "this_invocation_units": 0, "this_invocation_tool_requests": 0,
                     "this_invocation_execution_attempts": 0})
    data = {"normal_passed": True, "phase": "normal", "mode": "real", "model": "test-model",
            "endpoint": "http://127.0.0.1:11434/v1", "think": False, "temperature": 0.2,
            "max_output_tokens": 4000, "runs": rows, "normal_replay_checks": {k: True for k in (
                "no_new_inference", "no_new_tool_requests", "no_new_execution_attempts", "no_new_units",
                "same_receipt", "same_plan", "database_unchanged", "original_completed")}}
    p = tmp_path / "passed.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_specialties_selection_omits_normal_and_has_zero_call_inputs_first():
    jobs = validate_qwen.selected_jobs("specialties")
    assert [x[0] for x in jobs] == ["missing_budget_units", "missing_deadline_at", "budget", "save_failure"]
    assert jobs[0][1] == {"budget_units": None} and jobs[1][1] == {"deadline_at": None}
    assert jobs[2][1]["budget_units"] == 3 and jobs[3][2] == "save_fail_once"


def test_generation_failure_selection_is_one_new_request_without_input_fault_hint():
    assert validate_qwen.selected_jobs("generate_failure") == [("generation_failure", {}, "generate_fail_once")]
    assert validate_qwen.stop_reason({"termination_reason": "MODEL_STOP"},
                                     {"this_invocation_requests": 6}, {}, case_cap=6) == "CASE_CALL_LIMIT_SPENT"


def test_generation_failure_input_key_does_not_reveal_case_or_fixture():
    base = {"theme": "unchanged theme", "budget_units": 10, "preferences": ["unchanged preference"]}
    raw = validate_qwen.experiment_input(base, "qwen_generate_failure_batch", "generation_failure", {}, "generate_failure")
    assert raw["request_key"].startswith("request_") and len(raw["request_key"]) == 40
    assert {k:v for k,v in raw.items() if k != "request_key"} == base
    assert not any(label in json.dumps(raw) for label in ("generation_failure", "generate_failure", "generate_fail_once", "GENERATION_TEMPORARY"))
    second = validate_qwen.experiment_input(base, "same-batch", "generation_failure", {}, "generate_failure")
    assert raw["request_key"] != second["request_key"]
    assert validate_qwen.experiment_input(base, "old-batch", "normal", {}, "normal")["request_key"] == "old-batch-normal"


def test_generation_failure_first_sdk_request_has_no_fault_hint(tmp_path, monkeypatch):
    """Actual SDK serialization, entirely MockTransport; not real model evidence."""
    captured = []
    def respond(request):
        body = json.loads(request.content)
        captured.append(body)
        text = body["input"][0]["content"]
        context = json.loads(text)
        assert context["state"]["input"]["request_key"].startswith("request_")
        assert not any(hint in text for hint in (
            "generation_failure", "generate_failure", "generate_fail_once", "GENERATION_TEMPORARY"))
        stop = {"action": "stop", "reason_code": "OFFLINE_PROTOCOL_STOP", "decision_summary": "offline SDK fixture only",
                "missing_fields": [], "pending_items": []}
        return httpx.Response(200, json={"id": "offline-sdk", "object": "response", "model": "test-model",
            "status": "completed", "usage": None, "output": [{"id": "offline-message", "type": "message",
            "role": "assistant", "content": [{"type": "output_text", "text": json.dumps(stop), "annotations": []}]}]})
    monkeypatch.setattr(validate_qwen, "ROOT", tmp_path)
    monkeypatch.setattr(validate_qwen, "normal_reference", lambda *args: {"fixture": "offline-test-only"})
    monkeypatch.setattr(httpx, "HTTPTransport", lambda **kwargs: httpx.MockTransport(respond))
    monkeypatch.setattr(sys, "argv", ["validate_qwen.py", "generate_failure", "--endpoint",
        "http://127.0.0.1:11434/v1", "--model", "test-model", "--normal-index", "unused-fixture", "--no-think"])
    validate_qwen.main()
    index = json.loads(next((tmp_path / "examples/test-results").glob("qwen_generate_failure_*.json")).read_text(encoding="utf-8"))
    assert len(captured) == 1 and index["call_cap"] == index["case_call_cap"] == 6
    assert len(index["runs"]) == 1 and index["runs"][0]["case_id"] == "generation_failure"


def test_normal_reference_checks_actual_nonempty_receipt_and_frozen_source(tmp_path, monkeypatch):
    p = passed_normal_fixture(tmp_path)
    monkeypatch.setattr(validate_qwen, "ROOT", tmp_path)
    reference = validate_qwen.normal_reference(p, "test-model", "http://127.0.0.1:11434/v1")
    assert reference["plan_id"] == "test-plan" and reference["new_inference_for_reference"] == 0
    (tmp_path / "uv.lock").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="source differs"):
        validate_qwen.normal_reference(p, "test-model", "http://127.0.0.1:11434/v1")


@pytest.mark.parametrize("change", ["empty_receipts", "missing_check", "model", "think", "replay_cost"])
@pytest.mark.parametrize("phase", ["specialties", "generate_failure"])
def test_specialties_gate_fails_before_database_or_model(tmp_path, monkeypatch, change, phase):
    p = passed_normal_fixture(tmp_path)
    d = json.loads(p.read_text(encoding="utf-8"))
    if change == "empty_receipts":
        for case in ("normal", "normal_replay"):
            out = tmp_path / case / "output.json"
            v = json.loads(out.read_text(encoding="utf-8")); v["receipt"] = None
            out.write_text(json.dumps(v), encoding="utf-8")
    elif change == "missing_check":
        del d["normal_replay_checks"]["database_unchanged"]
    elif change in ("model", "think"):
        d[change] = "wrong-model" if change == "model" else True
    else:
        d["runs"][1]["this_invocation_units"] = 1
    p.write_text(json.dumps(d), encoding="utf-8")
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid reference must not start a new task or inference")
    monkeypatch.setattr(validate_qwen, "ROOT", tmp_path)
    monkeypatch.setattr(validate_qwen, "OpenAI", forbidden)
    monkeypatch.setattr(validate_qwen, "Store", forbidden)
    monkeypatch.setattr(sys, "argv", ["validate_qwen.py", phase, "--endpoint",
        "http://127.0.0.1:11434/v1", "--model", "test-model", "--normal-index", str(p), "--no-think"])
    with pytest.raises(SystemExit) as exc:
        validate_qwen.main()
    assert exc.value.code == 2 and not (tmp_path / "var").exists()


def test_specialties_missing_fields_use_real_entry_but_never_initialize_model(tmp_path, monkeypatch):
    p = passed_normal_fixture(tmp_path)
    # Use the real immutable data files for Planner input validation, not inference.
    def forbidden(*args, **kwargs):
        raise AssertionError("missing budget/deadline must not initialize inference")
    monkeypatch.setattr(validate_qwen, "ROOT", tmp_path)
    monkeypatch.setattr(validate_qwen, "normal_reference", lambda *args: {"fixture": "test-only"})
    monkeypatch.setattr(validate_qwen, "OpenAI", forbidden)
    original = validate_qwen.selected_jobs
    monkeypatch.setattr(validate_qwen, "selected_jobs", lambda phase: original(phase)[:2])
    monkeypatch.setattr(sys, "argv", ["validate_qwen.py", "specialties", "--endpoint",
        "http://127.0.0.1:11434/v1", "--model", "test-model", "--normal-index", str(p), "--no-think"])
    validate_qwen.main()
    index = json.loads(next((tmp_path / "examples/test-results").glob("qwen_specialties_*.json")).read_text(encoding="utf-8"))
    assert index["call_cap"] == 20 and index["case_call_cap"] == 10 and index["actual_requests"] == 0
    assert len(index["runs"]) == 2
    assert all(r["task_status"] == "NEEDS_INPUT" and r["this_invocation_requests"] == 0
               and r["this_invocation_units"] == 0 and r["executed_tool_attempts"] == 0 for r in index["runs"])


@pytest.mark.parametrize("case_cap", [6, 10])
def test_case_cap_independent_from_batch_and_failed_requests_count(tmp_path, case_cap):
    index = {"call_cap": 20, "case_call_cap": case_cap, "inference_requests": [{"case_id": "budget"}] * (case_cap-1),
             "active_case": "budget"}
    transport = validate_qwen.RecordedTransport(index, tmp_path / "index.json", "http://127.0.0.1:11434/v1")
    transport.inner.close()
    def timeout(request):
        raise httpx.ReadTimeout("offline timeout fixture", request=request)
    transport.inner = httpx.MockTransport(timeout)
    req = lambda: httpx.Request("POST", "http://127.0.0.1:11434/v1/responses", json={})
    try:
        with pytest.raises(httpx.ReadTimeout):
            transport.handle_request(req())
        assert len(index["inference_requests"]) == case_cap and index["inference_requests"][-1]["error"]["type"] == "ReadTimeout"
        with pytest.raises(RuntimeError, match="case real request cap exhausted"):
            transport.handle_request(req())
        assert len(index["inference_requests"]) == case_cap
        index["active_case"] = "save_failure"
        with pytest.raises(httpx.ReadTimeout):
            transport.handle_request(req())
        assert len(index["inference_requests"]) == case_cap+1
    finally:
        transport.close()


@pytest.mark.parametrize("reason", ["MODEL_UNAVAILABLE", "MODEL_TIMEOUT", "RESULT_UNKNOWN", "REAL_CALL_LIMIT", "RUN_LIMIT", "MODEL_LIMIT", "TOOL_LIMIT"])
def test_specialties_stop_before_next_case_on_failure_or_limit(reason):
    assert validate_qwen.stop_reason({"termination_reason": reason}, {"this_invocation_requests": 3},
                                     {"known_fee_sum": {"status": "passed"}}) == reason


def test_specialties_stop_on_invariant_failure_and_spent_case_quota():
    report = {"termination_reason": "SAVED"}
    assert validate_qwen.stop_reason(report, {"this_invocation_requests": 7}, {"fee": {"status": "failed"}}) == "INVARIANT_FAILED"
    assert validate_qwen.stop_reason(report, {"this_invocation_requests": 10}, {}) == "CASE_CALL_LIMIT_SPENT"
    assert validate_qwen.stop_reason({"termination_reason": "NO_FEASIBLE_QUOTE"}, {"this_invocation_requests": 4}, {}) is None
