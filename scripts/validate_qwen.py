"""Explicit bounded real-local experiment, not a predefined model action path.

Smoke allows 3 POSTs, normal allows one chain with 10 POSTs and zero-call replay.
Acceptance (30 maximum) requires a passed smoke and separate user authorization.
Specialties reuses confirmed normal/replay evidence: 20 POSTs total, 10 per case.
Generate_failure runs one independent request, with at most 6 POSTs.
Every POST, including failed/timeout requests, spends the local quota.
No cloud endpoints, pulls, fallback, recovery, or automatic experiment retries.
"""
import argparse
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
import uuid

import httpx
from openai import OpenAI

from content_planner.agent import Limits, Planner
from content_planner.accounting import digest
from content_planner.model import OpenAIResponsesModel
from content_planner.reporting import build_report, write_evidence
from content_planner.store import Store

ROOT = Path(__file__).resolve().parents[1]


def normal_reference(path, model, endpoint):
    """Read existing evidence only, before any new database/client is created."""
    path = Path(path).resolve()
    previous = json.loads(path.read_text(encoding="utf-8"))
    required_checks = {"no_new_inference", "no_new_tool_requests", "no_new_execution_attempts",
                       "no_new_units", "same_receipt", "same_plan", "database_unchanged", "original_completed"}
    if not (previous.get("normal_passed") and previous.get("phase") == "normal"
            and previous.get("mode") == "real" and previous.get("model") == model
            and previous.get("endpoint") == endpoint and previous.get("think") is False
            and previous.get("temperature") == 0.2 and previous.get("max_output_tokens") == 4000
            and required_checks <= previous.get("normal_replay_checks", {}).keys()
            and all(previous["normal_replay_checks"][k] is True for k in required_checks)):
        raise ValueError("requires passed real normal/replay evidence for the unchanged configuration")
    rows = {r["case_id"]: r for r in previous["runs"]}
    records = [json.loads((ROOT / rows[c]["evidence_dir"] / "output.json").read_text(encoding="utf-8"))
               for c in ("normal", "normal_replay")]
    first, replay = records
    if not (all(r["mode"] == "real" and r["task_status"] == "COMPLETED"
                and r["save_state"] == "CONFIRMED" and r["receipt"] and r["saved_plan"] for r in records)
            and first["receipt"] == replay["receipt"] and first["saved_plan"] == replay["saved_plan"]
            and all(rows["normal_replay"][k] == 0 for k in (
                "this_invocation_requests", "this_invocation_units", "this_invocation_tool_requests",
                "this_invocation_execution_attempts"))):
        raise ValueError("normal/replay must have the same nonempty saved plan/receipt and zero replay side effects")
    paths = [*sorted((ROOT / "src/content_planner").glob("*.py")),
             *sorted((ROOT / "data").glob("*.json")), ROOT / "pyproject.toml", ROOT / "uv.lock"]
    source = digest({str(p.relative_to(ROOT)): p.read_text(encoding="utf-8") for p in paths})
    meta = json.loads((ROOT / rows["normal"]["evidence_dir"] / "metadata.json").read_text(encoding="utf-8"))
    if source != meta["source_digest"]:
        raise ValueError("business source differs from the referenced normal evidence")
    return {"index": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "normal_evidence": rows["normal"]["evidence_dir"],
            "replay_evidence": rows["normal_replay"]["evidence_dir"], "source_digest": source,
            "plan_id": first["receipt"]["plan_id"], "new_inference_for_reference": 0}


def selected_jobs(phase):
    if phase == "generate_failure":
        return [("generation_failure", {}, "generate_fail_once")]
    if phase in ("smoke", "normal"):
        return [(phase, {}, "no_fault")]
    specials = [
        ("budget", {"budget_units": 3, "preferences": ["运营有一个尚未核价的基础方案想法，请给出实际估价后再决定是否继续。"]}, "no_fault"),
        ("save_failure", {}, "save_fail_once"),
    ]
    if phase == "specialties":
        return [("missing_budget_units", {"budget_units": None}, "no_fault"),
                ("missing_deadline_at", {"deadline_at": None}, "no_fault"), *specials]
    return [("normal", {}, "no_fault"), *specials]


def experiment_input(base, batch, case, changes, phase):
    # Case labels are experiment metadata, never a pre-fault hint to the model.
    key = "request_" + uuid.uuid4().hex if phase == "generate_failure" else batch + "-" + case
    return {**base, "request_key": key, **changes}


def stop_reason(report, row, invariant_checks, case_cap=10):
    if any(v["status"] != "passed" for v in invariant_checks.values()):
        return "INVARIANT_FAILED"
    if report["termination_reason"] in {
        "MODEL_UNAVAILABLE", "MODEL_TIMEOUT", "MODEL_CONFIGURATION", "RESULT_UNKNOWN",
        "REAL_CALL_LIMIT", "RUN_LIMIT", "MODEL_LIMIT", "TOOL_LIMIT", "CLOCK_ERROR"}:
        return report["termination_reason"]
    if row["this_invocation_requests"] >= case_cap:
        return "CASE_CALL_LIMIT_SPENT"
    return None


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def public_request(body):
    """Keep actual tool/context fields, omit provider reasoning from evidence only."""
    copied = deepcopy(body)
    if isinstance(copied.get("input"), list):
        copied["input"] = [
            {"type": "reasoning", "id": item.get("id"), "omitted_from_evidence": True}
            if item.get("type") == "reasoning" else item for item in copied["input"]]
    return copied


class RecordedTransport(httpx.BaseTransport):
    def __init__(self, index, path, endpoint):
        self.index, self.path, self.endpoint = index, path, urlsplit(endpoint)
        self.inner = httpx.HTTPTransport(retries=0)

    def handle_request(self, request):
        if (request.url.host != self.endpoint.hostname or request.url.port != self.endpoint.port
                or request.url.path != "/v1/responses" or request.method != "POST"):
            raise RuntimeError("experiment permits only the configured local Responses endpoint")
        if len(self.index["inference_requests"]) >= self.index["call_cap"]:
            raise RuntimeError("batch real request cap exhausted")
        if self.index.get("case_call_cap") and sum(
                r["case_id"] == self.index["active_case"] for r in self.index["inference_requests"]) >= self.index["case_call_cap"]:
            raise RuntimeError("case real request cap exhausted")
        entry = {"number": len(self.index["inference_requests"]) + 1,
                 "case_id": self.index["active_case"], "url": str(request.url),
                 "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                 "request": public_request(json.loads(request.content)), "timeout": request.extensions.get("timeout")}
        # No headers/credentials or provider reasoning are recorded.
        self.index["inference_requests"].append(entry)
        write(self.path, self.index)
        start = time.monotonic()
        try:
            response = self.inner.handle_request(request)
            response.read()
            entry["status_code"] = response.status_code
            data = response.json()
            entry["response"] = {k: data.get(k) for k in ("id", "model", "status", "usage", "error")}
            entry["response"]["tool_calls"] = [x for x in data.get("output", []) if x.get("type") == "function_call"]
            return response
        except Exception as exc:
            entry["error"] = {"type": type(exc).__name__, "detail": str(exc)}
            raise
        finally:
            entry["latency_ms"] = round((time.monotonic() - start) * 1000, 3)
            write(self.path, self.index)

    def close(self):
        self.inner.close()


def feedback_links(index, folder):
    events = [json.loads(line) for line in (folder / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
    requests = [x for x in index["inference_requests"] if x["case_id"] == index["active_case"]]
    links = []
    for event in events:
        if event["kind"] != "tool_result":
            continue
        result = event["result"]
        for req in requests:
            for item in req["request"]["input"]:
                if item.get("type") == "function_call_output" and json.loads(item["output"]) == result:
                    links.append({"tool_event_id": event["event_id"], "tool": result["tool"],
                                  "outcome": result["outcome"], "call_id": item["call_id"],
                                  "next_request_number": req["number"]})
                    break
    return links


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=["smoke", "normal", "acceptance", "specialties", "generate_failure"])
    p.add_argument("--endpoint", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--smoke-index")
    p.add_argument("--normal-index", help="Passed real normal/replay evidence; required for specialties")
    p.add_argument("--no-think", action="store_true", help="Explicit Ollama think=false; recorded, not a model default claim")
    args = p.parse_args()
    endpoint = urlsplit(args.endpoint)
    if endpoint.hostname not in ("127.0.0.1", "localhost", "::1") or endpoint.scheme != "http" or endpoint.path.rstrip("/") != "/v1":
        p.error("explicit local http /v1 endpoint required")
    if args.phase == "acceptance":
        if not args.smoke_index:
            p.error("acceptance requires --smoke-index")
        smoke = json.loads(Path(args.smoke_index).read_text(encoding="utf-8"))
        if not smoke.get("smoke_passed") or smoke["model"] != args.model or smoke["endpoint"] != args.endpoint:
            p.error("smoke not passed for this model/endpoint; no larger experiment allowed")
    reference = None
    if args.phase in ("specialties", "generate_failure"):
        if not args.normal_index or not args.no_think:
            p.error(args.phase + " requires --normal-index and --no-think")
        try:
            reference = normal_reference(args.normal_index, args.model, args.endpoint)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            p.error(str(exc))
    batch = "qwen_" + args.phase + "_" + uuid.uuid4().hex[:12]
    work = ROOT / "var" / batch
    work.mkdir(parents=True)
    out = ROOT / "examples/test-results" / (batch + ".json")
    index = {"batch_id": batch, "phase": args.phase, "mode": "real", "service_type": "ollama",
             "protocol": "responses_stateless_native_tools", "model": args.model, "endpoint": args.endpoint,
             "call_cap": {"smoke": 3, "normal": 10, "acceptance": 30, "specialties": 20, "generate_failure": 6}[args.phase],
             "case_call_cap": 6 if args.phase == "generate_failure" else 10, "inference_requests": [], "runs": [],
             "normal_reference": reference, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             "starting_project_requests": sum(len(json.loads(p.read_text(encoding="utf-8")).get("inference_requests", []))
                                               for p in (ROOT / "examples/test-results").glob("qwen_*.json")),
             "smoke_index": args.smoke_index, "temperature": 0.2, "max_output_tokens": 4000,
             "think": False if args.no_think else None,
             "limits": {"max_model_turns": 12, "max_tool_requests": 10, "model_timeout_s": 20, "run_timeout_s": 180},
             "recorded_at_utc": datetime.now(timezone.utc).isoformat()}
    write(out, index)
    os.environ.update(MODEL_PROVIDER="ollama", MODEL_NAME=args.model, OPENAI_BASE_URL=args.endpoint, MODEL_TEMPERATURE="0.2")
    if args.no_think:
        os.environ["MODEL_THINK"] = "false"
    else:
        os.environ.pop("MODEL_THINK", None)
    base = {"theme": "毕业季：用旧照片做一支回忆短片", "budget_units": 10,
            "deadline_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
            "materials_catalog": "materials-v1", "cost_catalog": "cost-v1", "hard_requirements": [],
            "preferences": ["预算允许时优先丰富叙事"], "parent_request_key": None}
    jobs = selected_jobs(args.phase)
    normal = None
    def run_case(store, case, raw, fixture):
        index["active_case"] = case
        write(out, index)
        before = len(index["inference_requests"])
        record_before = store.by_key(raw["request_key"])
        executions_before = sum(a["execution_started"] for a in record_before["snapshot"]["attempts"]) if record_before else 0
        client = None
        def factory():
            nonlocal client
            left = min(index["call_cap"] - len(index["inference_requests"]), index["case_call_cap"] -
                       sum(r["case_id"] == case for r in index["inference_requests"]))
            if left <= 0:
                raise RuntimeError("no remaining batch allowance")
            client = OpenAI(api_key="ollama-local-unused", base_url=args.endpoint, max_retries=0,
                            http_client=httpx.Client(transport=RecordedTransport(index, out, args.endpoint), trust_env=False))
            return OpenAIResponsesModel.from_env(min(3 if args.phase == "smoke" else 10, left), client=client)
        planner = Planner(store, limits=Limits())
        try:
            snapshot = planner.run(raw, "real", factory, fixture)
        finally:
            if client:
                client.close()
        report = build_report(snapshot, planner.replayed)
        folder = write_evidence(snapshot, report, ROOT / "examples/runs", case,
                                submitted_input=planner.submitted_input)
        row = {"case_id": case, "evidence_dir": str(folder.relative_to(ROOT)).replace("\\", "/"),
               "task_status": report["task_status"], "reason": report["termination_reason"], "save_state": report["save_state"],
               "this_invocation_requests": len(index["inference_requests"]) - before,
               "this_invocation_units": report["actual_costs"]["this_invocation_units"],
               "total_units": report["actual_costs"]["total_actual_units"],
               "executed_tool_attempts": sum(a["execution_started"] for a in snapshot["attempts"]),
               "this_invocation_execution_attempts": sum(a["execution_started"] for a in snapshot["attempts"]) - executions_before,
               "this_invocation_tool_requests": report["this_invocation_tool_requests"],
               "protocol_errors": sum(e["kind"] == "protocol_error" for e in snapshot["events"]),
               "receipt": report["receipt"], "feedback_links": feedback_links(index, folder)}
        index["runs"].append(row)
        write(out, index)
        print(json.dumps({"case_id": case, "status": report["task_status"], "reason": report["termination_reason"],
                          "requests": row["this_invocation_requests"], "evidence": row["evidence_dir"]}, ensure_ascii=False), flush=True)
        return report
    with closing(Store(work / "planner.sqlite3")) as store:
        for case, changes, fixture in jobs:
            if len(index["inference_requests"]) >= index["call_cap"]:
                index["stopped"] = "BATCH_CALL_LIMIT"
                break
            raw = experiment_input(base, batch, case, changes, args.phase)
            write(work / (case + ".json"), raw)
            report = run_case(store, case, raw, fixture)
            if case == "normal":
                normal = (raw, report)
            checks = json.loads((ROOT / index["runs"][-1]["evidence_dir"] / "assertions.json").read_text(encoding="utf-8"))["checks"]
            reason = stop_reason(report, index["runs"][-1], checks, index["case_call_cap"])
            if reason:
                index["stopped"] = reason
                break
        if normal and (args.phase == "acceptance" or (args.phase == "normal" and normal[1]["task_status"] == "COMPLETED")):
            raw, first = normal
            before_replay = list(store.conn.iterdump())
            replay = run_case(store, "normal_replay", raw, "no_fault")
            index["normal_replay_checks"] = {
                "no_new_inference": index["runs"][-1]["this_invocation_requests"] == 0,
                "no_new_tool_requests": index["runs"][-1]["this_invocation_tool_requests"] == 0,
                "no_new_execution_attempts": index["runs"][-1]["this_invocation_execution_attempts"] == 0,
                "no_new_units": replay["actual_costs"]["this_invocation_units"] == 0,
                "same_receipt": replay["receipt"] == first["receipt"],
                "same_plan": replay["saved_plan"] == first["saved_plan"],
                "database_unchanged": list(store.conn.iterdump()) == before_replay,
                "original_completed": first["task_status"] == "COMPLETED"}
        if args.phase == "acceptance" and normal:
            for field in ("budget_units", "deadline_at"):
                run_case(store, "missing_" + field, {**base, "request_key": batch + "-missing-" + field, field: None}, "no_fault")
    if args.phase == "normal":
        index["normal_passed"] = bool(normal and normal[1]["task_status"] == "COMPLETED"
                                      and normal[1]["save_state"] == "CONFIRMED" and normal[1]["receipt"]
                                      and index.get("normal_replay_checks")
                                      and all(index.get("normal_replay_checks", {}).values()))
    if args.phase == "smoke":
        responses = [x for x in index["inference_requests"] if x.get("status_code") == 200]
        index["smoke_passed"] = (len(responses) >= 2 and bool(index["runs"][0]["feedback_links"])
            and not index.get("stopped") and not index["runs"][0]["protocol_errors"]
            and index["runs"][0]["executed_tool_attempts"] > 0
            and len(responses) == len(index["inference_requests"])
            and any(x.get("response", {}).get("tool_calls") for x in responses))
    index.pop("active_case", None)
    index["actual_requests"] = len(index["inference_requests"])
    write(out, index)
    print(json.dumps({"index": str(out.relative_to(ROOT)), "actual_requests": index["actual_requests"],
                      "smoke_passed": index.get("smoke_passed"), "stopped": index.get("stopped")}, ensure_ascii=False))
    if args.phase == "smoke" and not index["smoke_passed"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
