"""Deterministic retrieval contracts, grounded feedback and unchanged charges."""
from copy import deepcopy

import pytest

from content_planner.agent import Planner
from conftest import call, make_toolbox, request


def retrieve(tb, query="回忆", tags=None, usage=None, limit=5):
    return call(tb, "search_materials", query=query, filters={"tags": [] if tags is None else tags,
                "allowed_usage": usage}, limit=limit)


@pytest.mark.parametrize("query,tags,unrecognized", [
    ("毕业季 旧照片 回忆短片", ["毕业", "回忆", "照片", "短片"], ["毕业", "短片"]),
    ("青春 校园 毕业 照片 回忆", ["青春", "校园", "毕业"], ["青春", "毕业"]),
])
def test_actual_queries_optional_filters_explain_empty_and_clear_only_on_new_action(env, query, tags, unrecognized):
    tb = make_toolbox(env)
    before = deepcopy(tags)
    empty = retrieve(tb, query, tags)
    assert empty["outcome"] == "SUCCESS" and empty["data"]["matches"] == []
    f = empty["data"]["feedback"]
    assert (f["keyword_match_count"], f["filtered_match_count"], f["returned_count"]) == (3, 0, 0)
    assert f["applied_filters"] == {"tags": sorted(tags), "allowed_usage": None}
    assert set(f["unrecognized_tags"]) == set(unrecognized)
    assert f["catalog_available_tags"] == sorted({t for m in env[1].materials.values() for t in m["tags"]})
    assert f["empty_reason"] == "FILTERS_EXCLUDED_ALL"
    assert tags == before and env[0].incurred(tb.request_id) == 1
    assert empty["charged_units"] == 1 and empty["sim_elapsed_s"] == 60
    # This is a distinct explicit caller/model action, not a backend fallback.
    found = retrieve(tb, query, [])
    assert len(found["data"]["matches"]) == 3 and found["data"]["feedback"]["filtered_match_count"] == 3
    assert env[0].incurred(tb.request_id) == 2
    reused = retrieve(tb, query, [])
    assert reused["reused"] and reused["charged_units"] == reused["sim_elapsed_s"] == 0
    assert env[0].incurred(tb.request_id) == 2
    assert env[0].get(tb.request_id)["cumulative_sim_elapsed_s"] == 120


@pytest.mark.parametrize("tags,ids", [
    (["照片"], {"mat-001", "mat-003"}),
    (["毕业季", "照片"], {"mat-001"}),
    (["校园", "创意"], set()),
])
def test_valid_tags_use_all_exact_not_or(env, tags, ids):
    result = retrieve(make_toolbox(env), tags=tags)
    assert {m["material_id"] for m in result["data"]["matches"]} == ids
    assert result["data"]["feedback"]["unrecognized_tags"] == []
    assert result["data"]["feedback"]["filter_semantics"]["tags"] == "ALL_EXACT"


@pytest.mark.parametrize("usage,count", [(None, 3), ("demo_only", 3), ("DEMO_ONLY", 0), ("", 0)])
def test_usage_is_exact_and_only_null_disables_filter(env, usage, count):
    tb = make_toolbox(env)
    result = retrieve(tb, usage=usage)
    assert len(result["data"]["matches"]) == count
    assert result["data"]["feedback"]["applied_filters"]["allowed_usage"] == usage
    assert result["data"]["feedback"]["catalog_available_usage_scopes"] == ["demo_only"]
    assert result["charged_units"] == env[0].incurred(tb.request_id) == 1


def test_truly_outside_catalog_stays_empty_and_is_charged(env):
    tb = make_toolbox(env)
    result = retrieve(tb, query="海底火山玄武岩无人深潜")
    f = result["data"]["feedback"]
    assert result["data"]["matches"] == []
    assert (f["keyword_match_count"], f["filtered_match_count"], f["returned_count"]) == (0, 0, 0)
    assert f["empty_reason"] == "NO_KEYWORD_MATCH"
    assert f["catalog_available_tags"] == sorted({t for m in env[1].materials.values() for t in m["tags"]})
    assert env[0].incurred(tb.request_id) == result["charged_units"] == 1


def test_counts_before_limit_are_distinct_from_returned_count(env):
    result = retrieve(make_toolbox(env), limit=1)
    f = result["data"]["feedback"]
    assert len(result["data"]["matches"]) == 1
    assert (f["keyword_match_count"], f["filtered_match_count"], f["returned_count"]) == (3, 3, 1)


def test_no_materials_estimate_still_rejects_without_new_charge(env):
    tb = make_toolbox(env)
    empty = retrieve(tb, tags=["未识别标签"])
    assert empty["data"]["matches"] == [] and env[0].incurred(tb.request_id) == 1
    estimate = call(tb, "estimate_plan", new_spec={"material_ids": [], "mode": "basic", "creative_brief": "测试"},
                    quote_id=None, stage="pre_generation", script_artifact_id=None)
    assert estimate["outcome"] == "REJECTED" and estimate["error"]["code"] == "INVALID_ARGUMENT"
    assert estimate["charged_units"] == estimate["sim_elapsed_s"] == 0
    assert env[0].incurred(tb.request_id) == 1
    assert env[0].get(tb.request_id)["estimates"] == {}


def test_unsupported_explicit_hard_filter_is_preserved_and_never_relaxed(env):
    raw = request(env[2])
    raw["hard_requirements"] = ["必须只使用标签为校园的素材"]
    def forbidden():
        raise AssertionError("unsupported hard requirements must be clarified before any model call")
    snapshot = Planner(env[0], env[1], env[2]).run(raw, "real", forbidden)
    assert snapshot["status"] == "NEEDS_INPUT" and snapshot["termination_reason"] == "UNSUPPORTED_REQUIREMENT"
    assert snapshot["input"]["hard_requirements"] == raw["hard_requirements"]
    assert snapshot["model_turns"] == snapshot["tool_requests"] == 0 and snapshot["ledger"] == []
