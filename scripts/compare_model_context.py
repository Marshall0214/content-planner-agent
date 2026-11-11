"""Offline SDK replay of the recorded normal timeout, never a task resumption.

Uses only HTTPX MockTransport. Replays recorded provider output/observations,
captures new SDK requests, compares common JSON serialization sizes. No Planner,
business tool, database write, model network request or new model output.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid

import httpx
from openai import APITimeoutError, OpenAI

from content_planner.accounting import canonical, digest
from content_planner.model import OpenAIResponsesModel

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def measure(body):
    text = canonical(body)
    return {"characters": len(text), "utf8_bytes": len(text.encode("utf-8")), "messages": len(body["input"])}


def compare(recording, destination):
    recording = recording.resolve()
    source = json.loads(recording.read_text(encoding="utf-8"))
    if source["phase"] != "normal" or source["inference_requests"][-1].get("error", {}).get("type") != "ReadTimeout":
        raise ValueError("This diagnostic supports the recorded single normal-chain read timeout only.")
    baseline = source["inference_requests"]
    folder = ROOT / source["runs"][0]["evidence_dir"]
    trace_file = folder / "trace.jsonl"
    events = [json.loads(s) for s in trace_file.read_text(encoding="utf-8").splitlines()]
    contexts = [e["context"] for e in events if e["kind"] == "model_request"]
    results = [e["result"] for e in events if e["kind"] == "tool_result"]
    if not (len(contexts) == len(baseline) == len(results) + 1):
        raise ValueError("Unexpected recording layout; no observations may be inferred or invented.")
    evidence_files = [recording, *sorted(p for p in folder.rglob("*") if p.is_file())]
    before_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence_files}
    outputs, observations, owned_positions, expected_native = [], [], [], []
    positions = []
    for i, entry in enumerate(baseline):
        history = entry["request"]["input"]
        position = len(history) - 1
        if history[position] != {"role": "user", "content": canonical(contexts[i])}:
            raise ValueError("Recorded snapshot does not match the explicit model_request Trace event.")
        positions.append(position)
        owned_positions.append(positions.copy())
        expected_native.append([deepcopy(item) for n, item in enumerate(history) if n not in positions])
        if i == len(baseline)-1:
            continue
        next_history = baseline[i+1]["request"]["input"]
        if next_history[:len(history)] != history:
            raise ValueError("Unexpected non-append legacy layout; refusing heuristic history deletion.")
        suffix = next_history[len(history):]
        if len(suffix) < 3 or suffix[-2].get("type") != "function_call_output":
            raise ValueError("Missing exact recorded native observation boundary.")
        provider_output, observation = suffix[:-2], suffix[-2]
        if any(item.get("omitted_from_evidence") for item in provider_output):
            raise ValueError("Cannot reconstruct redacted provider continuation objects.")
        calls = [x for x in provider_output if x.get("type") == "function_call"]
        if len(calls) != 1 or calls[0]["call_id"] != observation["call_id"]:
            raise ValueError("Recorded call/observation identity mismatch.")
        if json.loads(observation["output"]) != results[i]:
            raise ValueError("Recorded observation differs from the actual Trace result.")
        outputs.append(deepcopy(provider_output))
        observations.append(deepcopy(observation))

    destination.mkdir(parents=True, exist_ok=False)
    captured, metrics = [], []
    def respond(request):
        i = len(captured)
        body = json.loads(request.content)
        captured.append(body)
        old = baseline[i]["request"]
        assert {k: v for k, v in body.items() if k != "input"} == {k: v for k, v in old.items() if k != "input"}
        assert request.extensions["timeout"] == baseline[i]["timeout"]
        assert body["input"][0] == {"role": "user", "content": canonical(contexts[i])}
        assert body["input"][1:] == expected_native[i]
        assert sum(x.get("role") == "user" for x in body["input"]) == 1
        (destination / f"request_{i+1:02d}_after.json").write_bytes(request.content)
        metrics.append({"request_number": i+1, "before": measure(old), "after": measure(body),
                        "adapter_snapshots_before": len(owned_positions[i]), "adapter_snapshots_after": 1,
                        "non_state_items_equal": True, "latest_context_equal": True,
                        "inference_parameters_schema_and_timeout_equal": True,
                        "actual_after_sdk_payload_bytes": len(request.content)})
        if i == len(baseline)-1:
            raise httpx.ReadTimeout("recorded timeout fixture; offline MockTransport replay", request=request)
        recorded = baseline[i]["response"]
        return httpx.Response(200, json={"id": recorded["id"], "object": "response", "created_at": 0,
            "status": recorded["status"], "model": recorded["model"], "usage": recorded["usage"], "output": outputs[i]})

    replayed_error = None
    with OpenAI(api_key="offline-protocol-placeholder", base_url="http://offline.invalid/v1", max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(respond), trust_env=False)) as client:
        adapter = OpenAIResponsesModel(source["model"], "offline-protocol-placeholder", len(baseline),
            base_url="http://offline.invalid/v1", client=client, service_type="ollama",
            temperature=source["temperature"], think=source["think"])
        context_copy = deepcopy(contexts)
        for i, context in enumerate(contexts):
            try:
                decision = adapter.choose(context, timeout=baseline[i]["timeout"]["read"])
            except APITimeoutError:
                if i != len(baseline)-1:
                    raise
                replayed_error = "APITimeoutError from recorded offline timeout fixture"
                break
            call = next(x for x in outputs[i] if x["type"] == "function_call")
            assert decision.call_id == call["call_id"] and decision.tool == call["name"]
            assert decision.arguments == json.loads(call["arguments"])
            adapter.observe(json.loads(observations[i]["output"]), observations[i]["call_id"])
        assert contexts == context_copy and adapter.calls == len(baseline) == len(captured)
    after_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence_files}
    assert before_hashes == after_hashes
    latest = contexts[-1]
    prices = latest["state"]["confirmed_incurred_units"]
    last_quote = max(latest["state"]["estimates"].values(), key=lambda q: q["sequence"])
    paths = [*sorted((ROOT / "src/content_planner").glob("*.py")), *sorted((ROOT / "data").glob("*.json")),
             ROOT / "pyproject.toml", ROOT / "uv.lock"]
    summary = {
        "kind": "actual_offline_recorded_sdk_replay_not_live_inference", "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "recording": str(recording.relative_to(ROOT)), "source_digest": digest({str(p.relative_to(ROOT)): p.read_text(encoding="utf-8") for p in paths}),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "new_real_model_requests": 0, "new_business_tool_executions": 0, "new_simulated_units": 0,
        "sdk_mock_requests": len(captured), "replayed_error": replayed_error,
        "measurement": "Both bodies reserialized using canonical(): sorted keys, compact JSON, ensure_ascii=False, UTF-8. Baseline raw network bytes unavailable. Character/byte counts are not tokens or performance.",
        "latest_state": {"original_requirements": latest["state"]["input"], "confirmed_incurred_units": prices,
                         "ledger_revision": latest["state"]["ledger_revision"], "latest_quote_id": last_quote["quote_id"],
                         "latest_quote_stage": last_quote["stage"], "latest_quote_total_units": last_quote["projected_total_units"],
                         "candidate_count": len(latest["state"]["candidate_snapshots"]),
                         "artifact_ids": list(latest["state"]["artifacts"]),
                         "remaining_model_turns": latest["remaining_model_turns"], "remaining_tool_requests": latest["remaining_tool_requests"]},
        "recorded_observations": [{"call_id": item["call_id"], "outcome": json.loads(item["output"])["outcome"],
                                   "output_digest": digest(json.loads(item["output"]))} for item in observations],
        "original_recording_and_trace_unchanged": before_hashes == after_hashes,
        "metrics": metrics, "online_context_compatibility": "not_run", "normal_chain_completion": "not_run"}
    write(destination / "comparison.json", summary)
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--recording", type=Path, required=True)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    destination = args.out or ROOT / "examples/test-results" / ("context_replay_" + uuid.uuid4().hex[:12])
    result = compare(args.recording, destination)
    print(json.dumps({"summary": str(destination / "comparison.json"), "new_real_model_requests": 0,
                      "sdk_mock_requests": result["sdk_mock_requests"], "last_request": result["metrics"][-1]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
