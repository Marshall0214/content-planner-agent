from copy import deepcopy
from datetime import datetime

from content_planner.model import draft_for
from conftest import make_toolbox, call, search, quote, prepare


def save(tb, script, q):
    state = tb.store.get(tb.request_id)
    return call(tb, "save_plan", quote_id=q["quote_id"], script_artifact_id=script["artifact_id"],
                draft=draft_for(state, script))


def test_C07_new_quote_same_spec_reuses_product_and_free_estimates(env):
    tb = make_toolbox(env)
    q1, script, q2 = prepare(tb)
    assert q1["quote_id"] != q2["quote_id"]
    assert q1["candidate_spec_hash"] == q2["candidate_spec_hash"]
    assert (q2["incurred_units"], q2["projected_total_units"]) == (7, 8)
    before = env[0].get(tb.request_id)
    reused = call(tb, "generate_script", quote_id=q2["quote_id"])
    assert reused["reused"] and reused["data"]["artifact_id"] == script["artifact_id"]
    assert reused["charged_units"] == reused["sim_elapsed_s"] == 0
    env[2].advance(60)
    q3 = call(tb, "estimate_plan", new_spec=None, quote_id=q1["quote_id"],
              stage="post_generation", script_artifact_id=script["artifact_id"])["data"]
    assert q3["quote_id"] not in (q1["quote_id"], q2["quote_id"])
    assert q3["observed_at"] != q2["observed_at"]
    assert q3["ledger_revision"] == before["ledger_revision"]
    assert q3["projected_total_units"] == 8
    assert len(env[0].ledger(tb.request_id)) == 2  # estimate never charges
    assert env[0].get(tb.request_id)["cumulative_sim_elapsed_s"] == before["cumulative_sim_elapsed_s"]


def test_C08_sunk_cost_11_then_basic_and_save_is_18(env):
    tb = make_toolbox(env, budget=20)
    _, premium, _ = prepare(tb, "premium")
    assert env[0].incurred(tb.request_id) == 11
    q = quote(tb, "basic")["data"]
    assert q["incurred_units"] == 11 and q["projected_total_units"] == 18
    basic = call(tb, "generate_script", quote_id=q["quote_id"])["data"]
    q2 = call(tb, "estimate_plan", new_spec=None, quote_id=q["quote_id"], stage="post_generation",
              script_artifact_id=basic["artifact_id"])["data"]
    r = save(tb, basic, q2)
    assert r["outcome"] == "SUCCESS"
    assert env[0].incurred(tb.request_id) == 18
    s = env[0].get(tb.request_id)
    assert premium["artifact_id"] in s["artifacts"]
    assert s["saved_plan"]["script_artifact_id"] == basic["artifact_id"]
    assert s["save_receipt"]["total_actual_units"] == 18


def test_C09_360_sim_plus_60_real_is_420_and_reuse_adds_zero(env):
    tb = make_toolbox(env)
    q1, script, _ = prepare(tb)
    assert env[0].get(tb.request_id)["cumulative_sim_elapsed_s"] == 300
    start = env[2].now()
    env[2].advance(60)
    reused = call(tb, "generate_script", quote_id=q1["quote_id"])
    assert reused["sim_elapsed_s"] == 0
    q = call(tb, "estimate_plan", new_spec=None, quote_id=q1["quote_id"], stage="post_generation",
             script_artifact_id=script["artifact_id"])["data"]
    assert (datetime.fromisoformat(q["projected_finish_at"]) - start).total_seconds() == 420
    r = save(tb, script, q)
    assert (datetime.fromisoformat(r["data"]["receipt"]["effective_completed_at"]) - start).total_seconds() == 420
    assert env[0].get(tb.request_id)["cumulative_sim_elapsed_s"] == 360


def test_C09_latest_clock_guard_rejects_previously_feasible_quote(env):
    tb = make_toolbox(env, minutes=7)
    search(tb)
    q = quote(tb)["data"]
    assert q["feasibility"] == "FEASIBLE"
    env[2].advance(120)
    r = call(tb, "generate_script", quote_id=q["quote_id"])
    assert r["outcome"] == "REJECTED" and r["error"]["code"] == "DEADLINE_GUARD"
    assert env[0].incurred(tb.request_id) == 1


def test_C09_over_deadline_report_and_clock_backwards(env):
    tb = make_toolbox(env, minutes=5)
    search(tb)
    q = quote(tb)["data"]
    assert q["feasibility"] == "OVER_DEADLINE" and q["deadline_gap_s"] == 60
    env[2].advance(-1)
    r = quote(tb)
    assert r["outcome"] == "REJECTED" and r["error"]["code"] == "CLOCK_ERROR"


def test_ledger_changes_invalidate_new_execution_but_not_reference(env):
    tb = make_toolbox(env, budget=20)
    search(tb)
    q = quote(tb)["data"]
    call(tb, "search_materials", query="校园", filters={"tags": [], "allowed_usage": None}, limit=2)
    rejected = call(tb, "generate_script", quote_id=q["quote_id"])
    assert rejected["error"]["code"] == "STALE_ESTIMATE"
    fresh = call(tb, "estimate_plan", new_spec=None, quote_id=q["quote_id"],
                 stage="pre_generation", script_artifact_id=None)["data"]
    assert fresh["incurred_units"] == 2 and fresh["projected_total_units"] == 9
    assert call(tb, "generate_script", quote_id=fresh["quote_id"])["outcome"] == "SUCCESS"


def test_local_tool_timeout_rolls_back_new_product_and_charge(env, monkeypatch):
    tb = make_toolbox(env)
    search(tb)
    q = quote(tb)["data"]
    original = tb._perform
    def slow(*args):
        result = original(*args)
        env[2].advance(4)
        return result
    monkeypatch.setattr(tb, "_perform", slow)
    r = call(tb, "generate_script", quote_id=q["quote_id"])
    assert r["outcome"] == "FAILED" and r["error"]["code"] == "TOOL_TIMEOUT"
    assert env[0].incurred(tb.request_id) == 1
    assert not any(a["kind"] == "script" for a in env[0].get(tb.request_id)["artifacts"].values())

