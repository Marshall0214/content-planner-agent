"""Execute offline CLI cases and index their actual outputs; never call real mode."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sqlite3
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def command(*args):
    result = subprocess.run([sys.executable, "-m", "content_planner.cli", *map(str, args)],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise RuntimeError(result.stdout + result.stderr)
    return result, payload


def database_dump(path):
    with sqlite3.connect(path) as conn:
        return list(conn.iterdump())


def assert_unknown_storage_report(report):
    assert report["task_status"] == "INCOMPLETE" and report["termination_reason"] == "RESULT_UNKNOWN"
    assert report["save_state"] == "UNKNOWN"
    assert report["actual_costs"]["total_actual_units"] is None
    assert report["actual_costs"]["current_amount_confirmed"] is False
    assert report["actual_costs"]["last_known_confirmed_units"] == 7
    assert report["pending_liability"]["max_charge_units"] == 1
    assert report["pending_liability"]["max_sim_seconds"] == 60
    assert report["termination_persisted"] is False


def main():
    batch = "batch_" + uuid.uuid4().hex[:12]
    work = ROOT / "var" / batch
    work.mkdir(parents=True)
    result, payload = command("make-input", "--out", work / "normal.json", "--request-key", batch + "-normal")
    if result.returncode:
        raise RuntimeError(payload)
    base = json.loads((work / "normal.json").read_text(encoding="utf-8"))
    index = {"batch_id": batch, "mode": "offline_mock", "real_model_validation": "not_run",
             "recorded_at_utc": datetime.now(timezone.utc).isoformat(), "runs": []}
    jobs = [
        ("C01", "normal", {}, "no_fault", "basic", [], 0),
        ("C06", "normal", {}, "no_fault", "basic", [], 0),
        ("C06-conflict", "conflict", {"request_key": base["request_key"], "budget_units": 20}, "no_fault", "basic", [], 4),
        ("C02", "missing_budget", {"budget_units": None}, "no_fault", "basic", [], 2),
        ("C03", "missing_deadline", {"deadline_at": None}, "no_fault", "basic", [], 2),
        ("C04", "budget_stop", {"budget_units": 3}, "no_fault", "basic", [], 3),
        ("C04-adjust", "budget_adjust", {}, "no_fault", "budget_adjust", [], 0),
        ("C05", "save_retry", {}, "save_fail_once", "basic", [], 0),
        ("C05-permanent", "save_denied", {}, "save_denied", "basic", [], 3),
        ("C10-success", "last_success", {}, "no_fault", "basic", ["--max-tool-requests", "5"], 0),
        ("C10-failed", "last_failed", {}, "save_fail_once", "basic", ["--max-tool-requests", "5"], 3),
        ("C10-unknown", "last_unknown", {}, "unknown_result", "basic", ["--max-tool-requests", "5"], 3),
        ("C11-storage-first", "storage_unknown", {}, "no_fault", "basic", [], 3),
        ("C11-storage-replay", "storage_unknown", {}, "no_fault", "basic", [], 3),
    ]
    storage_dump = None
    for case, name, changes, fixture, scenario, options, expected_exit in jobs:
        source = work / f"{name}.json"
        if name != "normal":
            raw = {**base, "request_key": f"{batch}-{name}", **changes}
            source.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if case == "C11-storage-first":
            # Evidence injection only: force a real SQLite save write to roll back.
            # The production application gains no recovery or failure-control feature.
            key = f"{batch}-{name}".replace("'", "''")
            with sqlite3.connect(work / "planner.sqlite3") as conn:
                conn.executescript(f"""CREATE TRIGGER evidence_save_write_error
                    BEFORE INSERT ON ledger_entries
                    WHEN NEW.tool='save_plan' AND NEW.request_id IN
                        (SELECT request_id FROM requests WHERE request_key='{key}')
                    BEGIN SELECT RAISE(ABORT, 'evidence: save write failed'); END;""")
        args = ["run", "--mode", "offline_mock", "--input", str(source), "--db", str(work / "planner.sqlite3"),
                "--fixture", fixture, "--offline-scenario", scenario, "--case-id", case,
                "--out", str(ROOT / "examples" / "runs"), *options]
        result, payload = command(*args)
        if result.returncode != expected_exit:
            raise RuntimeError(f"{case}: expected {expected_exit}, got {result.returncode}: {payload}")
        report = payload["output"]
        if case in ("C11-storage-first", "C11-storage-replay"):
            assert_unknown_storage_report(report)
            if case == "C11-storage-first":
                storage_dump = database_dump(work / "planner.sqlite3")
            else:
                assert report["this_invocation_model_turns"] == report["this_invocation_tool_requests"] == 0
                assert report["actual_costs"]["this_invocation_units"] == 0
                assert database_dump(work / "planner.sqlite3") == storage_dump
        folder = Path(payload["evidence_dir"])
        # All files below are actual subprocess output.
        (folder / "stdout.json").write_text(result.stdout, encoding="utf-8")
        (folder / "stderr.txt").write_text(result.stderr, encoding="utf-8")
        index["runs"].append({"case_id": case, "evidence_dir": str(folder.relative_to(ROOT)).replace("\\", "/"),
            "exit_code": result.returncode, "task_status": report["task_status"], "save_state": report["save_state"],
            "actual_units": report["actual_costs"]["total_actual_units"],
            "last_known_units": report["actual_costs"]["last_known_confirmed_units"],
            "model_turns_this_invocation": report["this_invocation_model_turns"], "replayed": report["replayed"],
            "termination_persisted": report["termination_persisted"], "pending_liability": report["pending_liability"]})
    inspected_unknown, unknown_data = command("inspect", "--db", work / "planner.sqlite3",
                                              "--request-key", f"{batch}-storage_unknown")
    assert inspected_unknown.returncode == 0
    assert_unknown_storage_report(unknown_data)
    assert database_dump(work / "planner.sqlite3") == storage_dump
    inspect_file = ROOT / "examples" / "test-results" / f"{batch}_unknown_inspect.json"
    inspect_file.write_text(inspected_unknown.stdout, encoding="utf-8")
    index["unknown_replay_checks"] = {"memory_unknown_preserved_on_replay": True,
                                     "inspect_agrees": True, "database_unchanged": True,
                                     "inspect_output": str(inspect_file.relative_to(ROOT)).replace("\\", "/")}
    # Verify read and export against the actual normal run's receipt.
    normal_output = json.loads((ROOT / index["runs"][0]["evidence_dir"] / "output.json").read_text(encoding="utf-8"))
    inspected, inspect_data = command("inspect", "--db", work / "planner.sqlite3", "--request-key", base["request_key"])
    exported, export_data = command("export", "--db", work / "planner.sqlite3",
                                    "--plan-id", normal_output["receipt"]["plan_id"], "--out", work / "export")
    assert inspected.returncode == exported.returncode == 0
    index["read_export_checks"] = {"inspect_matches_receipt": inspect_data["receipt"] == normal_output["receipt"],
                                   "export_contains_script": bool(json.loads(
                                       (Path(export_data["export_dir"]) / "plan.json").read_text(encoding="utf-8"))["script"]["body"])}
    out = ROOT / "examples" / "test-results" / f"{batch}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"batch_index": str(out.relative_to(ROOT)), "actual_cli_runs": len(index["runs"]),
                      "real_model_calls": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
