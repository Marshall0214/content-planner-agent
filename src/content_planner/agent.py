"""Bounded model -> local tool -> observed result loop; no post-save model turn."""
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime
import math
import sqlite3

from pydantic import ValidationError

from .accounting import Clock, Rejection, digest, iso
from .model import ModelConfigurationError
from .schemas import Request, StopDecision
from .reporting import project_read_snapshot, read_report_snapshot
from .store import event
from .tools import Catalog, Toolbox, initial_snapshot, requirement_rules


@dataclass
class Limits:
    max_model_turns: int = 12
    max_tool_requests: int = 10
    max_operation_attempts: int = 2
    model_timeout_s: float = 20
    tool_timeout_s: float = 3
    run_timeout_s: float = 180

    def __post_init__(self):
        if any(type(getattr(self, k)) is not int or getattr(self, k) < 1
               for k in ("max_model_turns", "max_tool_requests", "max_operation_attempts")):
            raise ValueError("count limits must be positive integers")
        if any(not math.isfinite(getattr(self, k)) or getattr(self, k) <= 0
               for k in ("model_timeout_s", "tool_timeout_s", "run_timeout_s")):
            raise ValueError("timeouts must be positive")


class Planner:
    def __init__(self, store, catalog=None, clock=None, limits=None):
        self.store, self.catalog = store, catalog or Catalog()
        self.clock, self.limits = clock or Clock(), limits or Limits()
        self.last_snapshot = None
        self.replayed = False

    def _finish(self, rid, status, reason, **extra):
        def change(s):
            # This method is only used for known outcomes. It never resolves UNKNOWN.
            if s["save_state"] == "CONFIRMED":
                raise RuntimeError("confirmed save must have returned immediately")
            s.update(status=status, termination_reason=reason, **extra)
            event(s, "termination", status=status, reason=reason)
        self.last_snapshot = self.store.update(rid, change)
        return self.last_snapshot

    def _limit_reason(self, s, started):
        if self.clock.monotonic() - started >= self.limits.run_timeout_s:
            return "RUN_LIMIT"
        if s["model_turns"] >= self.limits.max_model_turns:
            return "MODEL_LIMIT"
        if s["tool_requests"] >= self.limits.max_tool_requests:
            return "TOOL_LIMIT"
        return None

    def run(self, raw_input, mode, model_factory, fixture="no_fault"):
        self.replayed = False
        request = Request.model_validate(raw_input).model_dump(mode="json")
        self.submitted_input = deepcopy(request)
        if request["materials_catalog"] != self.catalog.material_data["catalog_id"] or request["cost_catalog"] != self.catalog.cost_data["catalog_id"]:
            raise ValueError("CATALOG_NOT_FOUND")
        if fixture not in self.catalog.fixtures:
            raise ValueError("unknown fixture")
        fingerprint = digest({"input": request, "catalogs": self.catalog.digests,
                              "mode": mode, "fixture": fixture, "contract_version": "1"})
        initial = initial_snapshot(request, mode, self.catalog, fixture)
        record, created = self.store.bind(request["request_key"], fingerprint, initial)
        rid = record["snapshot"]["request_id"]
        if not created:
            self.replayed = True
            s = read_report_snapshot(self.store, rid)
            if record["input_hash"] != fingerprint:
                # Ephemeral conflict report. Existing persistent request remains unchanged.
                existing_status = s["status"]
                s.update(status="FAILED", termination_reason="REQUEST_KEY_CONFLICT",
                         existing_task_status=existing_status, input_conflict=True,
                         termination_persisted=False)
                self.last_snapshot = s
                return s
            self.last_snapshot = s
            return self.last_snapshot
        missing = [name for name in ("budget_units", "deadline_at") if request[name] is None]
        if missing:
            return self._finish(rid, "NEEDS_INPUT", "MISSING_FIELDS", missing_fields=missing)
        try:
            requirement_rules(request)
        except Rejection as exc:
            return self._finish(rid, "NEEDS_INPUT", exc.code, pending_items=[exc.message, *exc.details.values()])
        if datetime.fromisoformat(request["deadline_at"]) <= self.clock.now():
            return self._finish(rid, "INCOMPLETE", "DEADLINE_EXPIRED")
        try:
            model = model_factory()
            if model.mode != mode:
                raise ModelConfigurationError("模型适配器模式与请求模式不一致")
        except ModelConfigurationError as exc:
            return self._finish(rid, "FAILED", "MODEL_CONFIGURATION", pending_items=[str(exc)])
        started = self.clock.monotonic()
        def start(s):
            s.update(status="RUNNING", started_at=iso(self.clock.now()), model_name=model.model_name,
                     model_configuration=deepcopy(getattr(model, "configuration", None)), limits=asdict(self.limits))
        self.store.update(rid, start)
        tb = Toolbox(self.store, rid, self.catalog, self.clock, fixture,
                     self.limits.max_operation_attempts, started + self.limits.run_timeout_s,
                     self.limits.tool_timeout_s)
        while True:
            record = self.store.read_record(rid)
            s = record["snapshot"]
            self.last_snapshot = s
            if s["unknown"] or record["unconfirmed_operations"]:
                # Read-only guard; no receipt lookups, no resumption.
                self.last_snapshot = project_read_snapshot(s, record["unconfirmed_operations"], interrupted=False)
                return self.last_snapshot
            reason = self._limit_reason(s, started)
            if reason:
                return self._finish(rid, "INCOMPLETE", reason)
            if mode == "real" and model.calls >= model.call_limit:
                return self._finish(rid, "INCOMPLETE", "REAL_CALL_LIMIT")
            visible = {k: deepcopy(s[k]) for k in (
                "input", "candidate_snapshots", "estimates", "steps", "attempts", "artifacts",
                "tool_results", "cumulative_sim_elapsed_s", "ledger_revision", "confirmed_incurred_units",
                "model_turns", "tool_requests")}
            observed = [e["event_id"] for e in s["events"] if e["kind"] == "tool_result"]
            context = {"state": visible, "cost_catalog": self.catalog.cost_data,
                       "clock_now_utc": iso(self.clock.now()), "observed_event_ids": observed,
                       "protocol_observations": [deepcopy(e["observation"]) for e in s["events"]
                                                 if e["kind"] == "protocol_error"],
                       "remaining_model_turns": self.limits.max_model_turns - s["model_turns"],
                       "remaining_tool_requests": self.limits.max_tool_requests - s["tool_requests"]}
            def before(s):
                s["model_turns"] += 1
                event(s, "model_request", mode=mode, observed_event_ids=observed,
                      context=context, context_digest=digest(context))
            self.store.update(rid, before)
            call_start = self.clock.monotonic()
            try:
                timeout = min(self.limits.model_timeout_s,
                              self.limits.run_timeout_s - (call_start - started))
                decision = model.choose(context, timeout=timeout)
            except Exception as exc:
                return self._finish(rid, "INCOMPLETE", "MODEL_UNAVAILABLE",
                                    pending_items=[f"模型调用失败：{type(exc).__name__}"])
            latency_ms = round((self.clock.monotonic() - call_start) * 1000, 3)
            self.store.update(rid, lambda s: event(s, "model_response", decision=decision.public(),
                                                   model_latency_ms=latency_ms))
            s = self.store.get(rid)
            # The last allowed model request may legally return its tool call.
            if self.clock.monotonic() - started >= self.limits.run_timeout_s:
                return self._finish(rid, "INCOMPLETE", "RUN_LIMIT")
            if (self.clock.monotonic() - call_start) > timeout:
                return self._finish(rid, "INCOMPLETE", "MODEL_TIMEOUT")
            if decision.stop is not None:
                try:
                    stop = StopDecision.model_validate(decision.stop)
                    return self._finish(rid, "NEEDS_INPUT" if stop.action == "need_input" else "INCOMPLETE",
                                        stop.reason_code, pending_items=stop.pending_items,
                                        missing_fields=stop.missing_fields)
                except ValidationError:
                    decision.protocol_error = "停止JSON非法，不能凭文字完成"
            if decision.protocol_error or not decision.tool:
                observation = {"outcome": "REJECTED", "error": {"code": "PROTOCOL_ERROR",
                               "message": decision.protocol_error or "缺少动作"}}
                self.store.update(rid, lambda s: event(s, "protocol_error", observation=observation))
                for call_id in decision.call_ids:
                    model.observe(observation, call_id)
                continue
            self.store.update(rid, lambda s: s.update(tool_requests=s["tool_requests"] + 1))
            try:
                result = tb.dispatch(decision.tool, decision.arguments, decision.call_id)
            except (sqlite3.Error, OSError):
                # No speculative writes or reconciliation on an uncertain storage path.
                s = deepcopy(tb.last_snapshot or self.last_snapshot)
                s.update(status="INCOMPLETE", unknown=True, termination_reason="RESULT_UNKNOWN",
                         termination_persisted=False)
                self.last_snapshot = s
                return s
            if result["outcome"] == "UNKNOWN":
                s = deepcopy(tb.last_snapshot)
                s.update(status="INCOMPLETE", unknown=True, termination_reason="RESULT_UNKNOWN")
                if not s["tool_results"] or s["tool_results"][-1]["outcome"] != "UNKNOWN":
                    s["tool_results"].append(result)
                    event(s, "tool_result", result=result, persistence="unconfirmed")
                self.last_snapshot = s
                return s
            s = tb.last_snapshot
            self.last_snapshot = s
            if decision.tool == "save_plan" and result["outcome"] == "SUCCESS":
                if s["status"] == "COMPLETED" and s["save_state"] == "CONFIRMED" and s["save_receipt"]:
                    return s  # No observe(), choose(), reconciliation or terminal rewrite after save.
                raise RuntimeError("save tool broke its success contract")
            if result.get("error") and result["error"]["code"] == "CLOCK_ERROR":
                return self._finish(rid, "INCOMPLETE", "CLOCK_ERROR")
            reason = self._limit_reason(s, started)
            if reason:
                return self._finish(rid, "INCOMPLETE", reason)
            model.observe(result, decision.call_id)

