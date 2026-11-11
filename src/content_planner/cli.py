"""Local CLI; real mode requires explicit configuration and a call allowance."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import argparse
import json
import os
import sqlite3
from pathlib import Path
import sys

from pydantic import ValidationError

from .agent import Limits, Planner
from .model import OfflineModel, OpenAIResponsesModel
from .reporting import build_report, read_report_snapshot, render_markdown, write_evidence
from .store import Store
from .tools import Catalog


def parser():
    root = argparse.ArgumentParser(description="内容任务规划：offline_mock从不代表真实模型证据")
    sub = root.add_subparsers(dest="command", required=True)
    make = sub.add_parser("make-input", help="生成含当前绝对截止时间的实际输入文件")
    make.add_argument("--out", required=True)
    make.add_argument("--request-key", required=True)
    make.add_argument("--budget", type=int, default=10)
    make.add_argument("--minutes", type=int, default=30)
    run = sub.add_parser("run")
    run.add_argument("--mode", choices=("offline_mock", "real"), required=True)
    run.add_argument("--input", required=True)
    run.add_argument("--db", default=os.getenv("PLANNER_DB", "var/planner.sqlite3"))
    run.add_argument("--out", default="examples/runs")
    run.add_argument("--fixture", default="no_fault")
    run.add_argument("--case-id")
    run.add_argument("--offline-scenario", choices=("basic", "budget_adjust", "stop_on_failure", "invalid", "false_finish"), default="basic")
    run.add_argument("--real-call-limit", type=int)
    run.add_argument("--data-dir")
    for name, env, default, typ in (
        ("max-model-turns", "MAX_MODEL_TURNS", 12, int),
        ("max-tool-requests", "MAX_TOOL_REQUESTS", 10, int),
        ("max-operation-attempts", "MAX_OPERATION_ATTEMPTS", 2, int),
        ("model-timeout-s", "MODEL_TIMEOUT_S", 20, float),
        ("tool-timeout-s", "TOOL_TIMEOUT_S", 3, float),
        ("run-timeout-s", "RUN_TIMEOUT_S", 180, float),
    ):
        run.add_argument("--" + name, type=typ, default=os.getenv(env, default))
    inspect = sub.add_parser("inspect")
    inspect.add_argument("--request-key", required=True)
    inspect.add_argument("--db", default=os.getenv("PLANNER_DB", "var/planner.sqlite3"))
    export = sub.add_parser("export")
    export.add_argument("--plan-id", required=True)
    export.add_argument("--out", required=True)
    export.add_argument("--db", default=os.getenv("PLANNER_DB", "var/planner.sqlite3"))
    return root


def exit_code(report):
    if report["termination_reason"] == "REQUEST_KEY_CONFLICT":
        return 4
    if report["termination_reason"] == "MODEL_CONFIGURATION":
        return 5
    return {"COMPLETED": 0, "NEEDS_INPUT": 2, "INCOMPLETE": 3, "FAILED": 5}.get(report["task_status"], 5)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    store = None
    try:
        if args.command == "make-input":
            if args.minutes < 1 or args.budget < 0:
                raise ValueError("budget>=0 and minutes>=1 required")
            value = {"request_key": args.request_key, "theme": "毕业季：用旧照片做一支回忆短片",
                     "budget_units": args.budget,
                     "deadline_at": (datetime.now(timezone.utc) + timedelta(minutes=args.minutes)).isoformat(),
                     "materials_catalog": "materials-v1", "cost_catalog": "cost-v1",
                     "hard_requirements": [], "preferences": ["预算允许时优先丰富叙事"],
                     "parent_request_key": None}
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"input_file": str(path.resolve())}, ensure_ascii=False))
            return 0
        store = Store(args.db, timeout=getattr(args, "tool_timeout_s", 3))
        if args.command == "run":
            limits = Limits(**{name: getattr(args, name) for name in Limits.__dataclass_fields__})
            raw = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
            if args.mode == "real" and args.offline_scenario != "basic":
                raise ValueError("real mode cannot select an offline scenario")
            factory = (lambda: OfflineModel(args.offline_scenario)) if args.mode == "offline_mock" else (
                lambda: OpenAIResponsesModel.from_env(args.real_call_limit))
            planner = Planner(store, Catalog(args.data_dir), limits=limits)
            snapshot = planner.run(raw, args.mode, factory, args.fixture)
            report = build_report(snapshot, planner.replayed)
            path = write_evidence(snapshot, report, args.out, args.case_id, asdict(limits),
                                  submitted_input=planner.submitted_input)
            print(json.dumps({"evidence_dir": str(path.resolve()), "output": report}, ensure_ascii=False))
            return exit_code(report)
        if args.command == "inspect":
            record = store.by_key(args.request_key)
            if record is None:
                raise ValueError("request not found")
            snapshot = read_report_snapshot(store, record["snapshot"]["request_id"])
            print(json.dumps(build_report(snapshot, True), ensure_ascii=False))
            return 0
        snapshot = store.find_plan(args.plan_id)
        if snapshot:
            snapshot = read_report_snapshot(store, snapshot["request_id"])
        if not snapshot or snapshot["save_state"] != "CONFIRMED" or snapshot.get("unknown"):
            raise ValueError("confirmed plan not found; no UNKNOWN reconciliation attempted")
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "plan.json").write_text(json.dumps(snapshot["saved_plan"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / "report.md").write_text(render_markdown(build_report(snapshot, True)), encoding="utf-8")
        print(json.dumps({"plan_id": args.plan_id, "export_dir": str(out.resolve())}, ensure_ascii=False))
        return 0
    except (ValidationError, ValueError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc), "status": "FAILED"}, ensure_ascii=False))
        return 4
    finally:
        if store:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
