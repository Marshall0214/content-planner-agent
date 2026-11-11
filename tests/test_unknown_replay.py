"""Storage failures must stay unknown across ordinary reads, without recovery."""
import json
from pathlib import Path

import pytest

from content_planner.agent import Planner
from content_planner.cli import main
from content_planner.model import OfflineModel
from content_planner.reporting import build_report
from content_planner.tools import Toolbox
from conftest import request


def fail_save_write(store):
    # A real failed SQLite write, not the persisted unknown_result fixture.
    store.conn.execute("""CREATE TRIGGER fail_unknown_save BEFORE INSERT ON ledger_entries
        WHEN NEW.tool='save_plan'
        BEGIN SELECT RAISE(ABORT, 'regression: save write failed'); END""")


def first_memory_unknown(env):
    store, catalog, clock = env
    fail_save_write(store)
    raw = request(clock, key="storage-unknown")
    model = OfflineModel()
    planner = Planner(store, catalog, clock)
    first = planner.run(raw, "offline_mock", lambda: model)
    report = build_report(first)
    assert report["task_status"] == "INCOMPLETE"
    assert report["save_state"] == "UNKNOWN"
    assert report["actual_costs"]["total_actual_units"] is None
    assert report["actual_costs"]["last_known_confirmed_units"] == 7
    stored = store.get(first["request_id"])
    assert stored["status"] == "RUNNING" and stored["save_state"] == "NOT_ATTEMPTED"
    assert not stored.get("unknown")
    assert store.unresolved(first["request_id"])
    return raw, first


def assert_unknown_read(report):
    assert report["task_status"] == "INCOMPLETE"
    assert report["termination_reason"] == "RESULT_UNKNOWN"
    assert report["save_state"] == "UNKNOWN"
    assert report["actual_costs"]["total_actual_units"] is None
    assert report["actual_costs"]["current_amount_confirmed"] is False
    assert report["actual_costs"]["last_known_confirmed_units"] == 7
    assert report["pending_liability"]["tool"] == "save_plan"
    assert report["pending_liability"]["max_charge_units"] == 1
    assert report["pending_liability"]["max_sim_seconds"] == 60
    assert report["termination_persisted"] is False
    assert report["receipt"] is None and report["saved_plan"] is None
    assert report["latest_projection"] is None
    assert report["partial_scripts"]
    assert report["task_plan"][-1]["status"] == "UNKNOWN"


@pytest.mark.parametrize("operation_status", ["STARTED", "UNKNOWN"])
@pytest.mark.parametrize("legacy_attempt", [False, True])
def test_C11_memory_unknown_then_replay_reads_unconfirmed_operation(
        env, monkeypatch, operation_status, legacy_attempt):
    store, catalog, clock = env
    raw, first = first_memory_unknown(env)
    rid = first["request_id"]
    key = next(r[0] for r in store.conn.execute(
        "SELECT operation_key FROM operations WHERE request_id=? AND tool='save_plan'", (rid,)))
    store.conn.execute("UPDATE operations SET status=? WHERE operation_key=?", (operation_status, key))
    if legacy_attempt:
        # Old records have only quote references, no admitted-liability metadata.
        def legacy(s):
            for attempt in s["attempts"]:
                attempt.pop("admitted_liability", None)
        store.update(rid, legacy)
    before = list(store.conn.iterdump())
    changes = store.conn.total_changes
    statements = []
    store.conn.set_trace_callback(statements.append)
    def forbidden(*args, **kwargs):
        raise AssertionError("replay must not create a model or dispatch a tool")
    monkeypatch.setattr(Toolbox, "dispatch", forbidden)
    planner = Planner(store, catalog, clock)
    replay = planner.run(raw, "offline_mock", forbidden)
    store.conn.set_trace_callback(None)
    report = build_report(replay, planner.replayed)
    assert_unknown_read(report)
    assert planner.replayed
    assert report["this_invocation_model_turns"] == 0
    assert report["actual_costs"]["this_invocation_units"] == 0
    assert store.conn.total_changes == changes
    assert list(store.conn.iterdump()) == before
    assert all(sql.lstrip().upper().startswith("SELECT") for sql in statements), statements
    save_attempt = next(a for a in report["attempts"] if a["operation_key"] == key)
    assert save_attempt["status"] == "UNKNOWN"
    assert any(s["kind"] == "save_plan" and s["status"] == "UNKNOWN"
               for s in report["execution_steps"])


def test_C11_inspect_and_run_replay_have_same_unknown_projection(env, tmp_path, capsys):
    store, _, _ = env
    raw, first = first_memory_unknown(env)
    source = tmp_path / "input.json"
    source.write_text(json.dumps(raw), encoding="utf-8")
    before = list(store.conn.iterdump())
    exit_code = main(["run", "--mode", "offline_mock", "--input", str(source),
                      "--db", store.path, "--out", str(tmp_path / "runs")])
    replay = json.loads(capsys.readouterr().out)
    assert exit_code == 3
    assert_unknown_read(replay["output"])
    assert main(["inspect", "--request-key", raw["request_key"], "--db", store.path]) == 0
    inspected = json.loads(capsys.readouterr().out)
    assert_unknown_read(inspected)
    for field in ("task_status", "save_state", "termination_reason", "actual_costs",
                  "pending_liability", "termination_persisted"):
        assert inspected[field] == replay["output"][field]
    assert list(store.conn.iterdump()) == before
    recorded = json.loads((Path(replay["evidence_dir"]) / "output.json").read_text(encoding="utf-8"))
    assert_unknown_read(recorded)


def test_C11_missing_liability_metadata_remains_unknown_instead_of_guessing(env):
    store, catalog, clock = env
    raw, first = first_memory_unknown(env)
    def remove_price(s):
        for attempt in s["attempts"]:
            if attempt["tool"] == "save_plan":
                attempt.pop("admitted_liability", None)
                attempt["arguments"]["quote_id"] = "unavailable-old-quote"
    store.update(first["request_id"], remove_price)
    replay = Planner(store, catalog, clock).run(raw, "offline_mock",
                                                lambda: (_ for _ in ()).throw(AssertionError()))
    report = build_report(replay, True)
    assert report["save_state"] == "UNKNOWN"
    assert report["actual_costs"]["total_actual_units"] is None
    assert report["pending_liability"]["operation_key"]
    assert report["pending_liability"]["max_charge_units"] is None
    assert report["pending_liability"]["max_sim_seconds"] is None
    assert not report["termination_persisted"]


@pytest.mark.parametrize("tool,known_fee", [("search_materials", 0), ("generate_script", 1)])
def test_C11_non_save_pending_operation_does_not_invent_pending_save(env, tool, known_fee):
    store, catalog, clock = env
    # Tool names are fixed test parameters, not untrusted SQL.
    store.conn.execute(f"""CREATE TRIGGER fail_non_save BEFORE INSERT ON ledger_entries
        WHEN NEW.tool='{tool}' BEGIN SELECT RAISE(ABORT, 'storage write failed'); END""")
    raw = request(clock)
    planner = Planner(store, catalog, clock)
    first = planner.run(raw, "offline_mock", lambda: OfflineModel())
    assert first["unknown"]
    replay = planner.run(raw, "offline_mock", lambda: (_ for _ in ()).throw(AssertionError()))
    report = build_report(replay, True)
    assert report["task_status"] == "INCOMPLETE"
    assert report["save_state"] == "NOT_ATTEMPTED"
    assert report["actual_costs"]["total_actual_units"] is None
    assert report["actual_costs"]["last_known_confirmed_units"] == known_fee
    assert report["pending_liability"]["tool"] == tool
    assert report["pending_liability"]["max_charge_units"] == (1 if tool == "search_materials" else 6)
    assert not report["termination_persisted"]
