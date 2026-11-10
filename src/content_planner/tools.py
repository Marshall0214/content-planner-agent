"""Four local tools, immutable quote references, and transactional simulated charges."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3

from pydantic import ValidationError

from .accounting import Clock, Rejection, canonical, digest, effective_now, iso
from .schemas import TOOL_MODELS
from .store import Store, event, new_id

CONTRACT_VERSION = "1"


class Catalog:
    def __init__(self, data_dir=None):
        try:
            self._load(data_dir)
        except (KeyError, TypeError) as exc:
            raise ValueError(f"CATALOG_INVALID: missing or invalid catalog field ({type(exc).__name__})") from exc

    def _load(self, data_dir):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parents[2] / "data"
        self.material_data = json.loads((self.data_dir / "materials-v1.json").read_text(encoding="utf-8"))
        self.cost_data = json.loads((self.data_dir / "cost-v1.json").read_text(encoding="utf-8"))
        self.fixtures = json.loads((self.data_dir / "fixtures.json").read_text(encoding="utf-8"))
        self.materials = {}
        for item in self.material_data["materials"]:
            if item["material_id"] in self.materials or not item["facts"]:
                raise ValueError("CATALOG_INVALID: duplicate material or missing facts")
            self.materials[item["material_id"]] = {**item, "content_digest": digest(item)}
        required = ["search_materials", "estimate_plan", "generate_script.basic",
                    "generate_script.premium", "save_plan"]
        for name in required:
            price = self.cost_data["tools"][name]
            if any(type(price[k]) is not int or price[k] < 0 for k in ("fee", "seconds")):
                raise ValueError("CATALOG_INVALID: fee/seconds must be nonnegative integers")
        if self.price("estimate_plan") != (0, 0):
            raise ValueError("CATALOG_INVALID: estimates must be free with zero simulated duration")
        self.digests = {"materials": digest(self.material_data), "costs": digest(self.cost_data)}

    def price(self, tool, mode=None):
        name = f"{tool}.{mode}" if mode else tool
        value = self.cost_data["tools"][name]
        return value["fee"], value["seconds"]


def requirement_rules(request):
    """Deliberately finite P0 syntax, not a generic natural-language validator."""
    rules = []
    for text in request["hard_requirements"]:
        text = text.replace("：", ":")
        if text.startswith("必用素材:") and text.split(":", 1)[1].strip():
            rules.append(("material", text.split(":", 1)[1].strip()))
        elif text.startswith("必含原文:") and text.split(":", 1)[1].strip():
            rules.append(("text", text.split(":", 1)[1].strip()))
        else:
            raise Rejection("UNSUPPORTED_REQUIREMENT", "P0无法核验此硬需求，未将其删除或改为软偏好",
                            {"requirement": text, "supported": ["必用素材:ID", "必含原文:文字"]})
    return rules


def initial_snapshot(request, mode, catalog, fixture):
    return {
        "request_id": new_id("req"), "input": request, "mode": mode, "fixture": fixture,
        "catalog_digests": catalog.digests, "status": "CREATED", "termination_reason": None,
        "candidate_snapshots": {}, "estimates": {}, "steps": {}, "attempts": [],
        "artifacts": {}, "events": [], "saved_plan": None, "save_receipt": None,
        "save_state": "NOT_ATTEMPTED", "cumulative_sim_elapsed_s": 0, "ledger_revision": 0,
        "model_turns": 0, "tool_requests": 0, "unknown": False, "last_clock_at": None,
        "confirmed_incurred_units": 0, "ledger": [],
        "pending_items": [], "missing_fields": [], "tool_results": [],
    }


class Toolbox:
    def __init__(self, store: Store, request_id, catalog=None, clock=None, fixture="no_fault",
                 max_attempts=2, run_deadline=None, tool_timeout_s=3):
        self.store, self.request_id = store, request_id
        self.catalog, self.clock = catalog or Catalog(), clock or Clock()
        self.fixture, self.max_attempts = fixture, max_attempts
        self.run_deadline = run_deadline
        self.tool_timeout_s, self.tool_deadline = tool_timeout_s, None
        if fixture not in self.catalog.fixtures:
            raise ValueError("unknown fixture")
        self.last_snapshot = self.store.get(request_id)

    def _key(self, tool, args):
        return digest({"request_id": self.request_id, "tool": tool, "version": CONTRACT_VERSION,
                       "args": args, "data": self.catalog.digests})

    def _quote(self, snapshot, quote_id):
        if quote_id not in snapshot["estimates"]:
            raise Rejection("INVALID_QUOTE_REF", "报价不存在或不属于本请求")
        quote = snapshot["estimates"][quote_id]
        return quote, snapshot["candidate_snapshots"][quote["candidate_spec_hash"]]

    def _script(self, snapshot, artifact_id, spec_hash):
        artifact = snapshot["artifacts"].get(artifact_id)
        if not artifact or artifact["kind"] != "script" or artifact["effective_spec_hash"] != spec_hash:
            raise Rejection("INVALID_MATERIAL_REF", "脚本不存在、不属于本请求或与候选不匹配")
        if not isinstance(artifact.get("script", {}).get("body"), str) or not artifact["script"]["body"].strip():
            raise Rejection("SCRIPT_INVALID", "脚本正文为空，不能保存成功")
        return artifact

    def _candidate(self, snapshot, spec):
        ids = spec["material_ids"]
        found = set()
        for a in snapshot["artifacts"].values():
            if a["kind"] == "search":
                found.update(m["material_id"] for m in a["matches"])
        if any(mid not in found or mid not in self.catalog.materials for mid in ids):
            raise Rejection("INVALID_MATERIAL_REF", "候选只能引用本请求实际检索到的素材")
        for kind, value in requirement_rules(snapshot["input"]):
            if kind == "material" and value not in ids:
                raise Rejection("HARD_REQUIREMENT_VIOLATION", "不能删除必用素材", {"material_id": value})
        bound = {"spec": spec, "theme": snapshot["input"]["theme"],
                 "hard_requirements": snapshot["input"]["hard_requirements"],
                 "materials": [self.catalog.materials[mid]["content_digest"] for mid in ids],
                 "catalogs": self.catalog.digests}
        return {"spec_hash": digest(bound), "canonical_spec": deepcopy(spec),
                "bound_material_digests": bound["materials"],
                "hard_requirements_hash": digest(bound["hard_requirements"])}

    def _clock_guard(self, snapshot):
        now = self.clock.now()
        if snapshot["last_clock_at"] and now < datetime.fromisoformat(snapshot["last_clock_at"]):
            raise Rejection("CLOCK_ERROR", "UTC时钟倒退，停止执行")
        if self.run_deadline is not None and self.clock.monotonic() >= self.run_deadline:
            raise Rejection("RUN_LIMIT", "单次运行时限已到")
        if self.tool_deadline is not None and self.clock.monotonic() >= self.tool_deadline:
            raise Rejection("TOOL_TIMEOUT", "工具处理超时，未确认新的成功结果")
        return now

    def projection(self, snapshot, candidate):
        self._clock_guard(snapshot)
        h = candidate["spec_hash"]
        gen_key = self._key("generate_script", {"spec_hash": h})
        gen = self.store.operation(gen_key)
        fee, secs = self.catalog.price("generate_script", candidate["canonical_spec"]["mode"])
        saved = snapshot["save_state"] == "CONFIRMED"
        remaining = []
        if not saved and not (gen and gen["status"] == "SUCCEEDED"):
            remaining.append({"tool": "generate_script", "fee_units": fee, "duration_s": secs,
                              "operation_fingerprint": gen_key, "disposition": "REMAINING"})
        save_fee, save_secs = self.catalog.price("save_plan")
        if not saved:
            remaining.append({"tool": "save_plan", "fee_units": save_fee, "duration_s": save_secs,
                              "operation_fingerprint": None, "disposition": "REMAINING"})
        incurred = self.store.incurred(self.request_id)
        total = incurred + sum(x["fee_units"] for x in remaining)
        now = effective_now(snapshot, self.clock)
        finish = now + timedelta(seconds=sum(x["duration_s"] for x in remaining))
        deadline = datetime.fromisoformat(snapshot["input"]["deadline_at"])
        bgap = max(0, total - snapshot["input"]["budget_units"])
        tgap = max(0.0, (finish - deadline).total_seconds())
        feasibility = "BOTH" if bgap and tgap else "OVER_BUDGET" if bgap else "OVER_DEADLINE" if tgap else "FEASIBLE"
        return {"candidate_spec_hash": h, "ledger_revision": snapshot["ledger_revision"],
                "cost_catalog_hash": self.catalog.digests["costs"], "observed_at": iso(self.clock.now()),
                "effective_now": iso(now), "incurred_units": incurred, "remaining_items": remaining,
                "projected_total_units": total, "budget_gap_units": bgap,
                "remaining_sim_s": sum(x["duration_s"] for x in remaining),
                "projected_finish_at": iso(finish), "deadline_gap_s": tgap, "feasibility": feasibility,
                "reused_script_artifact_id": gen["result"]["data"]["artifact_id"] if gen and gen["status"] == "SUCCEEDED" else None}

    def _guard(self, snapshot, fee, seconds, candidate=None, quote=None):
        self._clock_guard(snapshot)
        if self.store.incurred(self.request_id) + fee > snapshot["input"]["budget_units"]:
            raise Rejection("BUDGET_GUARD", "本次新收费会超过预算")
        if quote and quote["ledger_revision"] != snapshot["ledger_revision"]:
            raise Rejection("STALE_ESTIMATE", "账本已变化，请引用原候选重新估价")
        deadline = datetime.fromisoformat(snapshot["input"]["deadline_at"])
        if candidate:
            projected = self.projection(snapshot, candidate)
            if projected["budget_gap_units"]:
                raise Rejection("BUDGET_GUARD", "完整剩余必需路径超预算", projected)
            if projected["deadline_gap_s"]:
                raise Rejection("DEADLINE_GUARD", "完整剩余路径不能按期准备", projected)
        elif effective_now(snapshot, self.clock) + timedelta(seconds=seconds) > deadline:
            raise Rejection("DEADLINE_GUARD", "本次操作不能按期完成")

    def _describe(self, tool, args, snapshot):
        """Validate semantic inputs before allocating an execution attempt."""
        candidate, quote, artifact, deps = None, None, None, []
        if tool == "search_materials":
            effective = {"query": args["query"], "filters": {
                "tags": sorted(set(args["filters"]["tags"])),
                "allowed_usage": args["filters"]["allowed_usage"]}, "limit": args["limit"]}
            key = self._key(tool, effective)
            fee, seconds = self.catalog.price(tool)
        elif tool == "estimate_plan":
            if args["new_spec"] is not None:
                candidate = self._candidate(snapshot, args["new_spec"])
            else:
                quote, candidate = self._quote(snapshot, args["quote_id"])
            if args["stage"] == "post_generation":
                artifact = self._script(snapshot, args["script_artifact_id"], candidate["spec_hash"])
                deps.append(artifact["step_id"])
            for a in snapshot["artifacts"].values():
                if a["kind"] == "search" and any(m["material_id"] in candidate["canonical_spec"]["material_ids"] for m in a["matches"]):
                    deps.append(a["step_id"])
            key = self._key(tool, {"invocation_id": new_id("estimate")})
            fee, seconds = 0, 0
        else:
            quote, candidate = self._quote(snapshot, args["quote_id"])
            deps.append(quote["step_id"])
            if tool == "generate_script":
                key = self._key(tool, {"spec_hash": candidate["spec_hash"]})
                fee, seconds = self.catalog.price(tool, candidate["canonical_spec"]["mode"])
            else:
                artifact = self._script(snapshot, args["script_artifact_id"], candidate["spec_hash"])
                self._validate_draft(args["draft"], artifact, candidate, snapshot)
                deps.append(artifact["step_id"])
                draft = {k: v for k, v in args["draft"].items() if k != "script_artifact_id"}
                key = self._key(tool, {"draft": draft, "spec_hash": candidate["spec_hash"],
                                       "script_content_hash": digest(artifact["script"])})
                fee, seconds = self.catalog.price(tool)
        return key, fee, seconds, candidate, quote, artifact, sorted(set(deps))

    def _validate_draft(self, draft, artifact, candidate, snapshot):
        if draft["script_artifact_id"] != artifact["artifact_id"]:
            raise Rejection("PLAN_INVALID", "Draft与参数中的脚本ID不一致")
        if sorted(set(draft["material_refs"])) != candidate["canonical_spec"]["material_ids"]:
            raise Rejection("PLAN_INVALID", "方案素材与候选不一致")
        if any(not str(x).strip() for name in ("channels", "risks", "assumptions") for x in draft[name]):
            raise Rejection("PLAN_INVALID", "方案列表含空内容")
        tasks = {t["task_id"]: t for t in draft["campaign_tasks"]}
        if len(tasks) != len(draft["campaign_tasks"]):
            raise Rejection("PLAN_INVALID", "活动任务ID重复")
        done, visiting = set(), set()
        def visit(tid):
            if tid not in tasks or tid in visiting:
                raise Rejection("PLAN_INVALID", "活动任务依赖不存在或成环")
            if tid in done:
                return
            visiting.add(tid)
            for dep in tasks[tid]["depends_on"]:
                visit(dep)
            visiting.remove(tid)
            done.add(tid)
        for tid in tasks:
            visit(tid)
        self._check_text_requirements(snapshot, artifact["script"]["body"])

    def _check_text_requirements(self, snapshot, text):
        for kind, value in requirement_rules(snapshot["input"]):
            if kind == "text" and value not in text:
                raise Rejection("HARD_REQUIREMENT_VIOLATION", "缺少必含原文", {"text": value})

    def _result(self, snapshot, tool, key, attempt_id, outcome, data=None, code=None,
                message=None, fee=0, seconds=0, reused=False, details=None):
        return {"request_id": self.request_id, "step_id": f"step_{key[:16]}",
                "attempt_id": attempt_id, "operation_key": key, "tool": tool, "outcome": outcome,
                "data": data, "error": None if code is None else {
                    "code": code, "message": message, "retryable": code in (
                        "SEARCH_TEMPORARY", "GENERATION_TEMPORARY", "SAVE_TEMPORARY", "ESTIMATE_READ_TEMPORARY"),
                    "details": details or {}},
                "charged_units": fee, "sim_elapsed_s": seconds, "reused": reused,
                "result_ref": (data or {}).get("artifact_id") or (data or {}).get("quote_id") or (data or {}).get("result_id") or (data or {}).get("document_ref"),
                "ledger_revision": snapshot["ledger_revision"], "observed_at": iso(self.clock.now())}

    def _record(self, snapshot, result, args, deps=(), started=False):
        sid = result["step_id"]
        if sid not in snapshot["steps"]:
            snapshot["steps"][sid] = {"step_id": sid, "kind": result["tool"], "depends_on": list(deps),
                                      "status": "PENDING", "result_ref": None}
        step = snapshot["steps"][sid]
        data = result.get("data") or {}
        ref_quote = snapshot["estimates"].get(args.get("quote_id")) if isinstance(args, dict) else None
        step["candidate_spec_hash"] = (data.get("candidate_spec_hash") or data.get("effective_spec_hash")
                                       or (ref_quote or {}).get("candidate_spec_hash"))
        status = "REUSED" if result["reused"] else "SUCCEEDED" if result["outcome"] == "SUCCESS" else result["outcome"]
        existing = next((a for a in snapshot["attempts"] if a["attempt_id"] == result["attempt_id"]), None)
        attempt = {"attempt_id": result["attempt_id"], "operation_key": result["operation_key"],
                   "step_id": sid, "tool": result["tool"], "status": "STARTED" if started else status,
                   "execution_started": started or (existing or {}).get("execution_started", False),
                   "provider_call_id": self.current_call_id, "arguments": args,
                   "started_at": (existing or {}).get("started_at", iso(self.clock.now())),
                   "ended_at": None if started else iso(self.clock.now()),
                   "sim_elapsed_s": result["sim_elapsed_s"], "observation": None if started else deepcopy(result)}
        if existing:
            existing.update(attempt)
        else:
            attempt["attempt_no"] = 1 + sum(a["step_id"] == sid for a in snapshot["attempts"])
            snapshot["attempts"].append(attempt)
        if step["status"] != "SUCCEEDED":
            step["status"] = "RUNNING" if started else "SUCCEEDED" if status in ("SUCCEEDED", "REUSED") else "UNKNOWN" if status == "UNKNOWN" else "FAILED"
        if result["outcome"] == "SUCCESS":
            step["result_ref"] = result["result_ref"]
        if not started:
            snapshot["tool_results"].append(deepcopy(result))
            event(snapshot, "tool_result", result=deepcopy(result))
        snapshot["last_clock_at"] = iso(self.clock.now())

    def _reject(self, tool, args, rejection, key=None):
        key = key or self._key(tool, {"invalid_invocation": new_id("bad")})
        with self.store.transaction():
            snapshot = self.store.get(self.request_id)
            result = self._result(snapshot, tool, key, new_id("attempt"), "REJECTED",
                                  code=rejection.code, message=rejection.message, details=rejection.details)
            self._record(snapshot, result, args)
            self.store.put(snapshot)
        self.last_snapshot = snapshot
        return result

    def dispatch(self, tool, raw_args, call_id="local"):
        self.tool_deadline = self.clock.monotonic() + self.tool_timeout_s
        self.current_call_id = call_id
        snapshot = self.store.get(self.request_id)
        self.last_snapshot = deepcopy(snapshot)
        if snapshot["unknown"] or self.store.unresolved(self.request_id):
            return self._unknown_report(snapshot, tool, None, "先前操作尚未确认")
        try:
            if tool not in TOOL_MODELS:
                raise Rejection("INVALID_ARGUMENT", "不支持的工具")
            args = TOOL_MODELS[tool].model_validate(raw_args).model_dump(mode="json")
            key, fee, seconds, candidate, quote, artifact, deps = self._describe(tool, args, snapshot)
            operation = self.store.operation(key)
            if operation and operation["status"] == "SUCCEEDED" and tool != "estimate_plan":
                result = deepcopy(operation["result"])
                result.update(attempt_id=new_id("attempt"), charged_units=0, sim_elapsed_s=0,
                              reused=True, reused_from=operation["result"]["attempt_id"],
                              ledger_revision=snapshot["ledger_revision"], observed_at=iso(self.clock.now()))
                with self.store.transaction():
                    snapshot = self.store.get(self.request_id)
                    self._record(snapshot, result, args, deps)
                    self.store.put(snapshot)
                self.last_snapshot = snapshot
                return result
            if operation and operation["execution_attempt_count"] >= self.max_attempts:
                raise Rejection("ATTEMPT_LIMIT", "同一语义操作实际尝试次数已耗尽")
            if operation and operation["status"] == "FAILED" and operation["result"] and not operation["result"]["error"]["retryable"]:
                raise Rejection("NOT_RETRYABLE", "原操作为永久失败，不能原样重试")
            if tool != "estimate_plan":
                if tool == "generate_script" and (quote["stage"] != "pre_generation" or quote["feasibility"] != "FEASIBLE"):
                    raise Rejection("DEPENDENCY_UNSATISFIED", "新生成需要可行的前置报价")
                if tool == "save_plan":
                    if snapshot["save_receipt"]:
                        raise Rejection("ALREADY_SAVED_CONFLICT", "已有不同的最终方案，不覆盖")
                    if quote["stage"] != "post_generation":
                        raise Rejection("DEPENDENCY_UNSATISFIED", "保存前必须生成后复估")
                self._guard(snapshot, fee, seconds, candidate, quote)
            else:
                self._clock_guard(snapshot)
        except ValidationError as exc:
            return self._reject(tool, raw_args, Rejection("INVALID_ARGUMENT", str(exc)))
        except Rejection as exc:
            return self._reject(tool, raw_args, exc, locals().get("key"))

        attempt_id = new_id("attempt")
        # Reservation records identity only. No simulated charge or external side effect.
        try:
            with self.store.transaction():
                snapshot = self.store.get(self.request_id)
                if operation:
                    self.store.conn.execute("UPDATE operations SET status='STARTED', execution_attempt_count=execution_attempt_count+1 WHERE operation_key=?", (key,))
                else:
                    self.store.conn.execute("INSERT INTO operations VALUES (?,?,?,?,?,1,NULL)",
                                            (key, self.request_id, tool, key, "STARTED"))
                started = self._result(snapshot, tool, key, attempt_id, "SUCCESS")
                self._record(snapshot, started, args, deps, started=True)
                self.store.put(snapshot)
            self.last_snapshot = deepcopy(snapshot)
            tool_attempt = sum(a["tool"] == tool and a["execution_started"] for a in snapshot["attempts"])
            fault = self.catalog.fixtures[self.fixture].get(tool, {}).get(str(tool_attempt))
            if fault == "UNKNOWN":
                # Test substitute for an unconfirmed business result, not recovery machinery.
                with self.store.transaction():
                    snapshot = self.store.get(self.request_id)
                    result = self._result(snapshot, tool, key, attempt_id, "UNKNOWN",
                                          code="RESULT_UNKNOWN", message="测试替身返回未确认结果", fee=None, seconds=None)
                    self._record(snapshot, result, args, deps)
                    snapshot.update(unknown=True, status="INCOMPLETE", termination_reason="RESULT_UNKNOWN")
                    snapshot["pending_liability"] = {"tool": tool, "operation_key": key,
                                                      "max_charge_units": fee, "max_sim_seconds": seconds}
                    if tool == "save_plan":
                        snapshot["save_state"] = "UNKNOWN"
                    self.store.conn.execute("UPDATE operations SET status='UNKNOWN' WHERE operation_key=?", (key,))
                    self.store.put(snapshot)
                self.last_snapshot = snapshot
                return result
            if fault:
                return self._failure(tool, args, key, attempt_id, fault, "注入的明确工具故障", seconds, deps)
            with self.store.transaction():
                snapshot = self.store.get(self.request_id)
                if tool != "estimate_plan":
                    self._guard(snapshot, fee, seconds, candidate, quote)
                data = self._perform(tool, args, snapshot, candidate, quote, artifact, key)
                if tool != "estimate_plan":
                    # Local work may have consumed real time after the initial guard.
                    self._guard(snapshot, fee, seconds, candidate, quote)
                else:
                    self._clock_guard(snapshot)
                if tool == "save_plan":
                    snapshot["save_receipt"]["saved_at_utc"] = iso(self.clock.now())
                    snapshot["save_receipt"]["effective_completed_at"] = iso(
                        effective_now(snapshot, self.clock) + timedelta(seconds=seconds))
                    data["receipt"] = deepcopy(snapshot["save_receipt"])
                snapshot["cumulative_sim_elapsed_s"] += seconds
                if fee:
                    entry = {"entry_id": new_id("fee"), "request_id": self.request_id, "operation_key": key,
                             "attempt_id": attempt_id, "tool": tool, "amount_units": fee,
                             "catalog_version": self.catalog.cost_data["catalog_id"], "committed_at": iso(self.clock.now())}
                    self.store.conn.execute("INSERT INTO ledger_entries VALUES (?,?,?,?,?,?,?,?)", tuple(entry.values()))
                    snapshot["ledger"].append(entry)
                    snapshot["confirmed_incurred_units"] += fee
                    snapshot["ledger_revision"] += 1
                result = self._result(snapshot, tool, key, attempt_id, "SUCCESS", data=data, fee=fee, seconds=seconds)
                self._record(snapshot, result, args, deps)
                self.store.conn.execute("UPDATE operations SET status='SUCCEEDED', confirmed_result_json=? WHERE operation_key=?", (canonical(result), key))
                if tool == "save_plan":
                    snapshot.update(status="COMPLETED", save_state="CONFIRMED", termination_reason="SAVED")
                    snapshot["save_receipt"]["ledger_revision_after"] = snapshot["ledger_revision"]
                    snapshot["save_receipt"]["total_actual_units"] = self.store.incurred(self.request_id)
                    data["receipt"] = deepcopy(snapshot["save_receipt"])
                    # The operation result must contain the same authoritative receipt.
                    self.store.conn.execute("UPDATE operations SET confirmed_result_json=? WHERE operation_key=?", (canonical(result), key))
                self.store.put(snapshot)
            self.last_snapshot = snapshot
            return result
        except Rejection as exc:
            return self._failure(tool, args, key, attempt_id, exc.code, exc.message, seconds, deps)
        except (sqlite3.Error, OSError) as exc:
            # No queries or old snapshot writes here: COMMIT acknowledgement may be lost.
            return self._unknown_report(self.last_snapshot, tool, key, f"持久化确认失败: {type(exc).__name__}", fee, seconds)

    def _failure(self, tool, args, key, attempt_id, code, message, seconds, deps):
        try:
            with self.store.transaction():
                snapshot = self.store.get(self.request_id)
                snapshot["cumulative_sim_elapsed_s"] += seconds
                if tool == "save_plan":
                    snapshot["save_state"] = "FAILED"
                result = self._result(snapshot, tool, key, attempt_id, "FAILED", code=code,
                                      message=message, seconds=seconds)
                self._record(snapshot, result, args, deps)
                self.store.conn.execute("UPDATE operations SET status='FAILED', confirmed_result_json=? WHERE operation_key=?", (canonical(result), key))
                self.store.put(snapshot)
            self.last_snapshot = snapshot
            return result
        except (sqlite3.Error, OSError):
            return self._unknown_report(self.last_snapshot, tool, key, "失败尝试的落盘结果也未确认")

    def _unknown_report(self, snapshot, tool, key, message, max_fee=None, max_seconds=None):
        snapshot = deepcopy(snapshot)
        snapshot.update(status="INCOMPLETE", unknown=True, termination_reason="RESULT_UNKNOWN",
                        termination_persisted=False)
        snapshot["pending_liability"] = {"tool": tool, "operation_key": key,
                                         "max_charge_units": max_fee, "max_sim_seconds": max_seconds}
        if tool == "save_plan":
            snapshot["save_state"] = "UNKNOWN"
            snapshot["save_receipt"] = None
            snapshot["saved_plan"] = None
        self.last_snapshot = snapshot
        return self._result(snapshot, tool, key or digest("unknown"), new_id("attempt"),
                            "UNKNOWN", code="RESULT_UNKNOWN", message=message, fee=None, seconds=None)

    def _perform(self, tool, args, snapshot, candidate, quote, artifact, key):
        step_id = f"step_{key[:16]}"
        if tool == "search_materials":
            matches = []
            query_tokens = args["query"].casefold().split()
            for material in self.catalog.materials.values():
                text = canonical(material).casefold()
                if not any(t in text for t in query_tokens):
                    continue
                if args["filters"]["tags"] and not set(args["filters"]["tags"]).issubset(material["tags"]):
                    continue
                if args["filters"]["allowed_usage"] and args["filters"]["allowed_usage"] != material["usage_scope"]:
                    continue
                matches.append(deepcopy(material))
            data = {"result_id": new_id("search"), "query": args["query"],
                    "catalog_version": "materials-v1", "matches": matches[:args["limit"]]}
            snapshot["artifacts"][data["result_id"]] = {**deepcopy(data), "kind": "search",
                                                       "artifact_id": data["result_id"], "step_id": step_id}
            return data
        if tool == "estimate_plan":
            h = candidate["spec_hash"]
            snapshot["candidate_snapshots"].setdefault(h, deepcopy(candidate))
            value = {**self.projection(snapshot, candidate), "quote_id": new_id("quote"),
                     "sequence": len(snapshot["estimates"]) + 1,
                     "stage": args["stage"], "step_id": step_id}
            snapshot["estimates"][value["quote_id"]] = deepcopy(value)
            return value
        if tool == "generate_script":
            spec = candidate["canonical_spec"]
            facts = "\n".join(f"- {self.catalog.materials[mid]['facts'][0]}（{mid}）" for mid in spec["material_ids"])
            required = "\n".join(v for kind, v in requirement_rules(snapshot["input"]) if kind == "text")
            body = (f"开场：围绕「{snapshot['input']['theme']}」，邀请观众找出一张旧照片。\n"
                    f"核心表达：{spec['creative_brief']}。{required}\n"
                    f"素材事实（合成演示）：\n{facts}\n"
                    "叙事：以照片中的细节串起校园记忆，使用今昔对照，避免未经证实的效果承诺。\n"
                    "结尾：邀请观众选择一张照片，写下一句想留给毕业时自己的话。")
            if spec["mode"] == "premium":
                body += "\n细化建议：用相同视角的今昔画面对照，以照片特写、场景过渡和人物旁白组织层次。"
            self._check_text_requirements(snapshot, body)
            artifact_id = new_id("script")
            data = {"artifact_id": artifact_id, "effective_spec_hash": candidate["spec_hash"],
                    "material_refs": spec["material_ids"], "mode": spec["mode"],
                    "script": {"title": snapshot["input"]["theme"], "body": body},
                    "warnings": ["素材为合成演示，需业务审阅；未执行真实拍摄或发布。"]}
            snapshot["artifacts"][artifact_id] = {**deepcopy(data), "kind": "script", "step_id": step_id,
                                                  "operation_key": key}
            return data
        # Full saved document contains actual script text and sources, not just IDs.
        tasks = [{**t, "status": "NOT_STARTED"} for t in args["draft"]["campaign_tasks"]]
        projected = self.projection(snapshot, candidate)
        plan_id = new_id("plan")
        receipt = {"plan_id": plan_id, "request_id": self.request_id,
                   "content_hash": digest({"draft": args["draft"], "spec_hash": candidate["spec_hash"],
                                           "script": artifact["script"]}),
                   "save_operation_key": key, "saved_at_utc": iso(self.clock.now()),
                   "effective_completed_at": projected["projected_finish_at"],
                   "ledger_revision_after": snapshot["ledger_revision"] + (1 if self.catalog.price(tool)[0] else 0),
                   "total_actual_units": projected["projected_total_units"]}
        document = {**args["draft"], "campaign_tasks": tasks, "script": artifact["script"],
                    "sources": [self.catalog.materials[mid] for mid in candidate["canonical_spec"]["material_ids"]],
                    "candidate_spec_hash": candidate["spec_hash"], "hard_requirements": snapshot["input"]["hard_requirements"],
                    "cost_summary": {"total_actual_units": projected["projected_total_units"],
                                     "budget_units": snapshot["input"]["budget_units"], "currency": "SIM_UNIT"},
                    "preparation_status": "READY_FOR_REVIEW", "campaign_execution_status": "NOT_STARTED"}
        snapshot["saved_plan"], snapshot["save_receipt"] = document, receipt
        return {"receipt": deepcopy(receipt), "document_ref": plan_id}
