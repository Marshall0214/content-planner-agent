"""Reports are built from confirmed state, not a model's completion claim."""
from copy import deepcopy
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform

from .accounting import canonical, iso
from .accounting import digest
from .store import new_id


def _pending_liability(snapshot, operation):
    """Use frozen persisted facts only, never a live/default price or a receipt."""
    key, tool = operation["operation_key"], operation["tool"]
    liability = {"operation_key": key, "tool": tool, "max_charge_units": None,
                 "max_sim_seconds": None, "source": "unavailable"}
    previous = snapshot.get("pending_liability") or {}
    attempt = next((a for a in reversed(snapshot["attempts"])
                    if a["operation_key"] == key), {})
    admitted = attempt.get("admitted_liability") or {}
    for source, value in (("previous_observation", previous), ("admitted_attempt", admitted)):
        if value.get("operation_key") == key:
            for field in ("max_charge_units", "max_sim_seconds"):
                if type(value.get(field)) is int and value[field] >= 0:
                    liability[field] = value[field]
            if any(liability[f] is not None for f in ("max_charge_units", "max_sim_seconds")):
                liability["source"] = source
                return liability
    # Compatibility with already-created STARTED records lacking admission data.
    args = attempt.get("arguments")
    quote_id = args.get("quote_id") if isinstance(args, dict) else None
    quote = snapshot["estimates"].get(quote_id, {})
    items = [item for item in quote.get("remaining_items", []) if item["tool"] == tool]
    if len(items) == 1:
        for field, quoted in (("max_charge_units", "fee_units"), ("max_sim_seconds", "duration_s")):
            if type(items[0].get(quoted)) is int and items[0][quoted] >= 0:
                liability[field] = items[0][quoted]
        liability["source"] = "persisted_quote"
    return liability


def project_read_snapshot(snapshot, unconfirmed_operations, interrupted=True):
    """Pure conservative view: no model, tool, writes, receipt reconciliation or resume."""
    s = deepcopy(snapshot)
    operations = deepcopy(unconfirmed_operations)
    if operations or s.get("unknown") or s["save_state"] == "UNKNOWN":
        save_pending = s["save_state"] == "UNKNOWN" or any(op["tool"] == "save_plan" for op in operations)
        terminal_already_stored = (
            s["status"] == "INCOMPLETE" and s["termination_reason"] == "RESULT_UNKNOWN"
            and s.get("unknown", False) and (not save_pending or s["save_state"] == "UNKNOWN"))
        liabilities = [_pending_liability(s, op) for op in operations]
        if not operations:
            liabilities = deepcopy(s.get("pending_liabilities") or (
                [s["pending_liability"]] if s.get("pending_liability") else []))
        s["read_projection"] = {"basis": "unconfirmed_operations", "persisted": False,
                                "persisted_task_status": snapshot["status"],
                                "persisted_save_state": snapshot["save_state"]}
        s.update(status="INCOMPLETE", termination_reason="RESULT_UNKNOWN", unknown=True,
                 unconfirmed_operations=operations, pending_liabilities=liabilities,
                 termination_persisted=bool(terminal_already_stored and s.get("termination_persisted", True)))
        s["pending_liability"] = liabilities[0] if liabilities else None
        if save_pending:
            s["save_state"] = "UNKNOWN"
        keys = {op["operation_key"] for op in operations}
        for attempt in s["attempts"]:
            if attempt["operation_key"] in keys and attempt["status"] in ("STARTED", "UNKNOWN"):
                attempt["status"] = "UNKNOWN"
                step = s["steps"].get(attempt["step_id"])
                if step and step["status"] != "SUCCEEDED":
                    step["status"] = "UNKNOWN"
    elif interrupted and s["status"] in ("CREATED", "RUNNING"):
        s.update(status="INCOMPLETE", termination_reason="IN_PROGRESS_OR_INTERRUPTED",
                 termination_persisted=False)
        s["read_projection"] = {"basis": "unfinished_request", "persisted": False,
                                "persisted_task_status": snapshot["status"],
                                "persisted_save_state": snapshot["save_state"]}
    return s


def read_report_snapshot(store, request_id):
    record = store.read_record(request_id)
    if record is None:
        raise ValueError("request not found")
    return project_read_snapshot(record["snapshot"], record["unconfirmed_operations"])


def preparation_plan(snapshot):
    """Required work, including unexecuted milestones, separate from actual attempts."""
    quotes = sorted(snapshot["estimates"].values(), key=lambda q: q["sequence"])
    active = quotes[-1]["candidate_spec_hash"] if quotes else None
    def step_state(tool, spec=None):
        relevant = [s for s in snapshot["steps"].values() if s["kind"] == tool
                    and (spec is None or s.get("candidate_spec_hash") == spec)]
        if any(s["status"] == "SUCCEEDED" for s in relevant):
            return "SUCCEEDED"
        ids = {s["step_id"] for s in relevant}
        last = next((a for a in reversed(snapshot["attempts"]) if a["step_id"] in ids), None)
        return snapshot["steps"][last["step_id"]]["status"] if last else "PENDING"
    states = {"retrieve": step_state("search_materials"),
              "generate": step_state("generate_script", active) if active else "PENDING",
              "save": "SUCCEEDED" if snapshot["save_state"] == "CONFIRMED" else
                      snapshot["save_state"] if snapshot["save_state"] in ("FAILED", "UNKNOWN") else "PENDING"}
    for stage, key in (("pre_generation", "estimate_pre"), ("post_generation", "estimate_post")):
        states[key] = "SUCCEEDED" if any(q["candidate_spec_hash"] == active and q["stage"] == stage
                                       for q in quotes) else "PENDING"
    order = ["retrieve", "estimate_pre", "generate", "estimate_post", "save"]
    return [{"step": name, "depends_on": [] if i == 0 else [order[i-1]], "status": states[name]}
            for i, name in enumerate(order)]


def build_report(snapshot, replayed=False):
    s = deepcopy(snapshot)
    unknown = bool(s.get("unknown", False) or s["save_state"] == "UNKNOWN"
                   or s.get("unconfirmed_operations"))
    latest = max(s["estimates"].values(), key=lambda q: q["sequence"]) if s["estimates"] else None
    current_projection = None
    if s["status"] == "COMPLETED" and not unknown:
        current_projection = {"basis": "confirmed_saved_result", "ledger_revision": s["ledger_revision"],
                              "incurred_units": s["confirmed_incurred_units"], "remaining_items": [],
                              "remaining_sim_s": 0, "projected_total_units": s["confirmed_incurred_units"]}
    elif unknown:
        latest = None
    report = {
        "request_id": s["request_id"], "request_key": s["input"]["request_key"], "mode": s["mode"],
        "real_model_decision_evidence": False,  # Online trajectories require separate human assessment.
        "task_status": s["status"], "termination_reason": s["termination_reason"],
        "preparation_status": "READY_FOR_REVIEW" if s["status"] == "COMPLETED" and not unknown else "INCOMPLETE",
        "campaign_execution_status": "NOT_STARTED", "save_state": s["save_state"],
        "receipt": s["save_receipt"] if not unknown else None,
        "saved_plan": s["saved_plan"] if not unknown else None,
        "partial_scripts": [a for a in s["artifacts"].values() if a["kind"] == "script"],
        "material_results": [a for a in s["artifacts"].values() if a["kind"] == "search"],
        "execution_steps": list(s["steps"].values()), "attempts": s["attempts"],
        "task_plan": preparation_plan(s),
        "tool_results": s["tool_results"], "latest_projection": latest,
        "current_cost_projection": current_projection,
        "actual_costs": {"currency": "SIM_UNIT", "entries": s["ledger"],
                         "total_actual_units": None if unknown else s["confirmed_incurred_units"],
                         "last_known_confirmed_units": s["confirmed_incurred_units"],
                         "current_amount_confirmed": not unknown,
                         "this_invocation_units": 0 if replayed else None if unknown else s["confirmed_incurred_units"]},
        "cumulative_sim_elapsed_s": s["cumulative_sim_elapsed_s"],
        "time_basis": "wall_plus_simulated_tools",
        "model_turns": s["model_turns"], "tool_requests": s["tool_requests"],
        "this_invocation_model_turns": 0 if replayed else s["model_turns"],
        "this_invocation_tool_requests": 0 if replayed else s["tool_requests"],
        "replayed": replayed, "pending_items": s["pending_items"], "missing_fields": s["missing_fields"],
        "input_conflict": s.get("input_conflict", False), "existing_task_status": s.get("existing_task_status"),
        "termination_persisted": s.get("termination_persisted", True),
        "pending_liability": s.get("pending_liability"),
        "pending_liabilities": s.get("pending_liabilities", [s["pending_liability"]] if s.get("pending_liability") else []),
        "unconfirmed_operations": s.get("unconfirmed_operations", []),
        "read_projection": s.get("read_projection"),
        "notice": "offline_mock为脚本化流程验证，不是真实模型决策证据。" if s["mode"] == "offline_mock"
                  else "真实模式记录需人工检查反馈与动作关联；当前不自动判定合格动态路径。",
    }
    return report


def render_markdown(report):
    costs = report["actual_costs"]
    lines = [f"# {report.get('saved_plan', {}).get('title', '') if report.get('saved_plan') else report['request_key']}",
             "", f"模式：{report['mode']}。{report['notice']}", "",
             f"任务：{report['task_status']}；保存：{report['save_state']}；原因：{report['termination_reason']}",
             "营销活动执行：NOT_STARTED。", ""]
    plan = report.get("saved_plan")
    if plan:
        for key, label in (("objective", "目标"), ("audience", "受众"), ("key_message", "核心信息")):
            lines.extend([f"## {label}", "", plan[key], ""])
        lines.extend(["## 建议渠道", "", "、".join(plan["channels"]), "", "## 脚本正文", "", plan["script"]["body"], ""])
        lines.extend(["## 素材引用（合成演示）", ""])
        for item in plan["sources"]:
            lines.append(f"- {item['material_id']}：{item['title']}；{item['source_ref']}；{item['usage_scope']}")
        lines.extend(["", "## 活动任务建议（均未执行）", ""])
        for t in plan["campaign_tasks"]:
            lines.append(f"- {t['task_id']}：{t['description']}；依赖{t['depends_on']}；{t['owner_role']}；{t['relative_schedule']}")
        lines.extend(["", "## 风险和假设", ""])
        lines.extend(f"- {x}" for x in plan["risks"] + plan["assumptions"])
    else:
        lines.extend(["## 未完成原因与已有产物", "", str(report["termination_reason"])])
        lines.extend(f"- {x}" for x in report["pending_items"] + report["missing_fields"])
        for a in report["partial_scripts"]:
            lines.extend(["", f"### 保留脚本 {a['artifact_id']}", "", a["script"]["body"]])
    lines.extend(["", "## 本次准备工作的实际步骤", ""])
    for item in report["task_plan"]:
        lines.append(f"- 必需里程碑 {item['step']}：{item['status']}；依赖{item['depends_on']}")
    for step in report["execution_steps"]:
        lines.append(f"- {step['step_id']}：{step['kind']} / {step['status']}；依赖{step['depends_on']}")
    lines.extend(["", "## 费用（模拟unit，非API账单）", ""])
    lines.extend(f"- {e['tool']}：{e['amount_units']}；操作{e['operation_key'][:12]}" for e in costs["entries"])
    lines.extend(["", f"已确认总额：{costs['total_actual_units'] if costs['current_amount_confirmed'] else '未知'}；"
                  f"最后可信累计：{costs['last_known_confirmed_units']}；本次增量：{costs['this_invocation_units']}。"])
    if report["current_cost_projection"] or report["latest_projection"]:
        q = report["current_cost_projection"] or report["latest_projection"]
        lines.append(f"剩余预计：{sum(i['fee_units'] for i in q['remaining_items'])}；预计总额：{q['projected_total_units']}。")
    if report["receipt"]:
        lines.append(f"保存回执：{report['receipt']['plan_id']}；有效完成时间：{report['receipt']['effective_completed_at']}。")
    elif report["save_state"] == "UNKNOWN":
        lines.append("保存结果未确认：P0不自动查证，不假定免费、失败或未提交，不盲目重跑。")
    for liability in report["pending_liabilities"]:
        fee = liability["max_charge_units"] if liability["max_charge_units"] is not None else "未知"
        seconds = liability["max_sim_seconds"] if liability["max_sim_seconds"] is not None else "未知"
        lines.append(f"待确认责任：{liability['tool']}；最高可能费用{fee}；模拟耗时上界{seconds}秒；不是已收费结论。")
    if not report["termination_persisted"]:
        if report["read_projection"]:
            lines.append("本次终态是只读内存投影，未回写数据库；未用旧快照覆盖可能已提交的事实。")
        else:
            lines.append("本次终止观察未能安全持久化；未用旧快照覆盖可能已提交的事实。")
    return "\n".join(lines) + "\n"


def assertions_for(report):
    entries = report["actual_costs"]["entries"]
    checks = {
        "ledger_operation_unique": len({e["operation_key"] for e in entries}) == len(entries),
        "known_fee_sum": (sum(e["amount_units"] for e in entries) == report["actual_costs"]["last_known_confirmed_units"]),
        "no_false_saved_success": report["task_status"] != "COMPLETED" or bool(
            report["receipt"] and report["saved_plan"] and report["save_state"] == "CONFIRMED"),
        "offline_mode_visible": report["mode"] != "offline_mock" or "offline_mock" in report["notice"],
        "activity_not_executed": report["campaign_execution_status"] == "NOT_STARTED",
        "unknown_amount_stays_unknown": not (
            report["save_state"] == "UNKNOWN" or report["unconfirmed_operations"]) or (
                report["actual_costs"]["total_actual_units"] is None
                and not report["actual_costs"]["current_amount_confirmed"]),
    }
    return {"scope": "automatic invariants only; not a dynamic-decision or marketing-quality verdict",
            "checks": {k: {"status": "passed" if v else "failed"} for k, v in checks.items()},
            "real_dynamic_path": {"status": "not_run" if report["mode"] == "offline_mock" else "requires_human_review"}}


def write_evidence(snapshot, report, out_root, case_id=None, settings=None, submitted_input=None):
    run_id = new_id("run")
    destination = Path(out_root) / report["mode"] / run_id
    destination.mkdir(parents=True, exist_ok=False)
    deps = {}
    for name in ("content-planner-agent", "pydantic", "openai", "pytest"):
        try:
            deps[name] = version(name)
        except PackageNotFoundError:
            deps[name] = None
    metadata = {
        "run_id": run_id, "case_id": case_id, "request_id": report["request_id"],
        "request_key": report["request_key"], "mode": report["mode"], "replayed": report["replayed"],
        "model_name": snapshot.get("model_name"), "fixture": snapshot["fixture"],
        "model_configuration": snapshot.get("model_configuration"),
        "catalog_digests": snapshot["catalog_digests"], "python": platform.python_version(),
        "dependencies": deps, "recorded_at_utc": iso(datetime.now(timezone.utc)),
        "limits": settings or snapshot.get("limits"),
        "online_validation": "not_run" if report["mode"] == "offline_mock" or not report["model_turns"] else "requires_review",
        "read_projection": report["read_projection"],
    }
    project = Path(__file__).resolve().parents[2]
    paths = [*sorted((project / "src" / "content_planner").glob("*.py")),
             *sorted((project / "data").glob("*.json")), project / "pyproject.toml", project / "uv.lock"]
    metadata["source_digest"] = digest({str(p.relative_to(project)): p.read_text(encoding="utf-8")
                                        for p in paths if p.is_file()})
    files = {"input.json": submitted_input if submitted_input is not None else snapshot["input"],
             "metadata.json": metadata, "output.json": report,
             "ledger.json": report["actual_costs"], "artifacts.json": snapshot["artifacts"],
             "receipt.json": {"save_state": report["save_state"], "receipt": report["receipt"]},
             "assertions.json": assertions_for(report)}
    if report["input_conflict"]:
        files["bound_input.json"] = snapshot["input"]
    for name, data in files.items():
        (destination / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (destination / "trace.jsonl").write_text(
        "".join(canonical(e) + "\n" for e in snapshot["events"]), encoding="utf-8")
    (destination / "report.md").write_text(render_markdown(report), encoding="utf-8")
    return destination

