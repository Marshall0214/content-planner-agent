from copy import deepcopy
import sqlite3
import pytest

from content_planner.accounting import canonical
from content_planner.agent import Planner
from content_planner.model import OfflineModel, draft_for
from content_planner.reporting import build_report
from conftest import make_toolbox, call, search, prepare, run_agent, request
from test_accounting_and_time import save


def test_C01_exactly_three_tables_and_full_saved_content(env):
    _, model, s = run_agent(env)
    tables = {r[0] for r in env[0].conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {"requests", "operations", "ledger_entries"}
    assert s["status"] == "COMPLETED" and s["save_state"] == "CONFIRMED"
    assert s["confirmed_incurred_units"] == 8 and model.calls == s["tool_requests"] == 5
    assert s["saved_plan"]["script"]["body"].strip() and s["saved_plan"]["sources"]
    assert all(t["status"] == "NOT_STARTED" for t in s["saved_plan"]["campaign_tasks"])
    assert "duration_s" not in s["saved_plan"]["script"]  # video specs are not a gate
    assert s["save_receipt"]["plan_id"]
    assert s["save_receipt"]["total_actual_units"] == s["saved_plan"]["cost_summary"]["total_actual_units"] == 8
    assert s["tool_results"][-1]["data"]["receipt"] == s["save_receipt"]
    assert all(step["status"] == "SUCCEEDED" for step in s["steps"].values())


def test_C05_save_fail_once_reuses_success_and_preserves_failed_attempt(env):
    _, model, s = run_agent(env, fixture="save_fail_once")
    assert s["status"] == "COMPLETED" and s["confirmed_incurred_units"] == 8
    assert model.calls == 6
    assert [a["status"] for a in s["attempts"] if a["tool"] == "save_plan"] == ["FAILED", "SUCCEEDED"]
    assert sum(a["tool"] == "generate_script" and a["execution_started"] for a in s["attempts"]) == 1
    assert s["cumulative_sim_elapsed_s"] == 420
    assert len(s["artifacts"]) == 2


def test_C05_permanent_save_failure_is_not_success(env):
    _, _, s = run_agent(env, fixture="save_denied")
    assert s["status"] == "INCOMPLETE" and s["save_state"] == "FAILED"
    assert not s["save_receipt"] and s["confirmed_incurred_units"] == 7
    assert any(a["kind"] == "script" for a in s["artifacts"].values())
    assert s["attempts"][-1]["status"] == "FAILED"


def test_C06_replay_and_conflict_have_no_new_calls_or_charges(env):
    raw = request(env[2])
    _, _, first = run_agent(env, raw=raw)
    original = canonical(env[0].get(first["request_id"]))
    replay_model = OfflineModel()
    p = Planner(*env[:2], clock=env[2])
    replay = p.run(raw, "offline_mock", lambda: replay_model)
    assert p.replayed and replay_model.calls == 0
    assert replay["save_receipt"] == first["save_receipt"]
    assert build_report(replay, True)["actual_costs"]["this_invocation_units"] == 0
    bad = {**raw, "budget_units": 20}
    conflict = p.run(bad, "offline_mock", lambda: replay_model)
    assert conflict["termination_reason"] == "REQUEST_KEY_CONFLICT"
    assert canonical(env[0].get(first["request_id"])) == original
    assert len(env[0].ledger(first["request_id"])) == 3


def test_search_success_reuse_and_failed_retry_limit(env):
    tb = make_toolbox(env)
    first, repeated = search(tb), search(tb)
    assert repeated["reused"] and repeated["data"] == first["data"]
    assert repeated["charged_units"] == repeated["sim_elapsed_s"] == 0
    assert env[0].incurred(tb.request_id) == 1


def test_C11_unknown_freezes_and_replay_does_not_execute(env):
    raw = request(env[2])
    p, model, s = run_agent(env, fixture="unknown_result", raw=raw)
    assert s["status"] == "INCOMPLETE" and s["save_state"] == "UNKNOWN"
    report = build_report(s)
    assert report["actual_costs"]["total_actual_units"] is None
    assert report["actual_costs"]["last_known_confirmed_units"] == 7
    assert model.calls == 5
    p.run(raw, "offline_mock", lambda: (_ for _ in ()).throw(AssertionError("must not create a model")),
          fixture="unknown_result")
    assert p.replayed and env[0].incurred(s["request_id"]) == 7
    assert env[0].operation(s["tool_results"][-1]["operation_key"])["status"] == "UNKNOWN"


def test_atomic_save_rollback_keeps_script_and_ledger(env):
    tb = make_toolbox(env)
    _, script, q = prepare(tb)
    env[0].conn.execute("""CREATE TEMP TRIGGER fail_save_fee BEFORE INSERT ON ledger_entries
        WHEN NEW.tool='save_plan' BEGIN SELECT RAISE(ABORT, 'test rollback'); END""")
    r = save(tb, script, q)
    assert r["outcome"] == "UNKNOWN"  # conservative storage-error boundary
    stored = env[0].get(tb.request_id)  # test inspection, not application recovery
    assert not stored["saved_plan"] and not stored["save_receipt"]
    assert script["artifact_id"] in stored["artifacts"]
    assert env[0].incurred(tb.request_id) == 7


def test_unknown_commit_ack_does_not_overwrite_committed_snapshot(env):
    store = env[0]
    real = store.conn
    class LostAck:
        def __init__(self):
            self.armed = False
            self.failed = False
            self.queries_after_loss = 0
        def __getattr__(self, key):
            return getattr(real, key)
        def execute(self, sql, params=()):
            if self.failed:
                self.queries_after_loss += 1
            if sql.startswith("UPDATE requests") and '"status":"COMPLETED"' in str(params):
                self.armed = True
            result = real.execute(sql, params)
            if sql == "COMMIT" and self.armed and not self.failed:
                self.failed = True
                raise sqlite3.OperationalError("test lost acknowledgement after actual commit")
            return result
    proxy = LostAck()
    store.conn = proxy
    _, _, s = run_agent(env)
    assert s["status"] == "INCOMPLETE" and s["save_state"] == "UNKNOWN"
    assert proxy.queries_after_loss == 0  # no automatic reconciliation or stale writes
    store.conn = real
    persisted = store.get(s["request_id"])  # explicit test inspection
    assert persisted["status"] == "COMPLETED" and persisted["save_receipt"]
    assert store.incurred(s["request_id"]) == 8


def test_C12_draft_mismatch_cycle_and_empty_script_rejected(env):
    tb = make_toolbox(env)
    _, script, q = prepare(tb)
    state = env[0].get(tb.request_id)
    draft = draft_for(state, script)
    draft["campaign_tasks"][0]["depends_on"] = ["publish"]
    r = call(tb, "save_plan", quote_id=q["quote_id"], script_artifact_id=script["artifact_id"], draft=draft)
    assert r["outcome"] == "REJECTED" and r["error"]["code"] == "PLAN_INVALID"
    draft = draft_for(state, script)
    draft["material_refs"] = ["mat-003"]
    r = call(tb, "save_plan", quote_id=q["quote_id"], script_artifact_id=script["artifact_id"], draft=draft)
    assert r["outcome"] == "REJECTED"
    assert env[0].incurred(tb.request_id) == 7 and not env[0].get(tb.request_id)["save_receipt"]
    env[0].update(tb.request_id, lambda s: s["artifacts"][script["artifact_id"]]["script"].update(body=" "))
    r = save(tb, script, q)
    assert r["outcome"] == "REJECTED" and r["error"]["code"] == "SCRIPT_INVALID"
    assert not env[0].get(tb.request_id)["save_receipt"]


def test_operation_attempt_limit_does_not_reset_when_quote_changes(env):
    tb = make_toolbox(env, fixture="save_fail_once", max_attempts=1)
    _, script, q = prepare(tb)
    assert save(tb, script, q)["outcome"] == "FAILED"
    new_q = call(tb, "estimate_plan", new_spec=None, quote_id=q["quote_id"],
                 stage="post_generation", script_artifact_id=script["artifact_id"])["data"]
    second = save(tb, script, new_q)
    assert second["outcome"] == "REJECTED" and second["error"]["code"] == "ATTEMPT_LIMIT"
    assert env[0].incurred(tb.request_id) == 7
