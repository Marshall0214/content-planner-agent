"""Actual subprocess smoke tests; never select real mode with usable credentials."""
import json
from pathlib import Path
import subprocess
import sys


def cli(*args):
    result = subprocess.run([sys.executable, "-m", "content_planner.cli", *map(str, args)],
                            capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.stdout.strip(), f"CLI produced no JSON: exit={result.returncode}; stderr={result.stderr!r}; args={args!r}"
    return result, json.loads(result.stdout)


def test_C01_C06_cli_make_run_inspect_export_and_replay(tmp_path):
    source, db, runs = tmp_path / "input.json", tmp_path / "cli.sqlite3", tmp_path / "runs"
    r, _ = cli("make-input", "--out", source, "--request-key", "cli-example")
    assert r.returncode == 0
    r, result = cli("run", "--mode", "offline_mock", "--input", source, "--db", db, "--out", runs)
    assert r.returncode == 0, r.stdout + r.stderr
    report = result["output"]
    assert report["task_status"] == "COMPLETED"
    r, viewed = cli("inspect", "--db", db, "--request-key", "cli-example")
    assert r.returncode == 0 and viewed["receipt"] == report["receipt"]
    r, exported = cli("export", "--db", db, "--plan-id", report["receipt"]["plan_id"], "--out", tmp_path / "export")
    assert r.returncode == 0
    assert json.loads((Path(exported["export_dir"]) / "plan.json").read_text(encoding="utf-8"))["script"]["body"]
    r, replay = cli("run", "--mode", "offline_mock", "--input", source, "--db", db, "--out", runs)
    assert r.returncode == 0 and replay["output"]["replayed"]
    assert replay["output"]["this_invocation_model_turns"] == 0
    assert replay["output"]["actual_costs"]["this_invocation_units"] == 0
    conflict_input = json.loads(source.read_text(encoding="utf-8"))
    conflict_input["budget_units"] = 20
    source.write_text(json.dumps(conflict_input), encoding="utf-8")
    r, conflict = cli("run", "--mode", "offline_mock", "--input", source, "--db", db, "--out", runs)
    assert r.returncode == 4
    evidence = Path(conflict["evidence_dir"])
    assert json.loads((evidence / "input.json").read_text(encoding="utf-8"))["budget_units"] == 20
    assert json.loads((evidence / "bound_input.json").read_text(encoding="utf-8"))["budget_units"] == 10
    assert conflict["output"]["existing_task_status"] == "COMPLETED"


def test_C02_cli_missing_budget_exit_and_actual_output(tmp_path):
    source = tmp_path / "missing.json"
    source.write_text(json.dumps({"request_key": "missing", "theme": "活动", "deadline_at": None}), encoding="utf-8")
    r, result = cli("run", "--mode", "offline_mock", "--input", source,
                    "--db", tmp_path / "missing.sqlite3", "--out", tmp_path / "runs")
    assert r.returncode == 2
    assert set(result["output"]["missing_fields"]) == {"budget_units", "deadline_at"}
    assert result["output"]["model_turns"] == 0

