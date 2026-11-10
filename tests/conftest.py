from datetime import timedelta
import pytest

from content_planner.accounting import FrozenClock, digest, iso
from content_planner.agent import Planner, Limits
from content_planner.model import OfflineModel
from content_planner.schemas import Request
from content_planner.store import Store
from content_planner.tools import Catalog, Toolbox, initial_snapshot


@pytest.fixture
def env(tmp_path):
    store = Store(tmp_path / "planner.sqlite3")
    catalog = Catalog()
    clock = FrozenClock("2026-11-10T10:00:00+08:00")
    yield store, catalog, clock
    store.close()


def request(clock, key="test", budget=10, minutes=30):
    return {"request_key": key, "theme": "毕业季：旧照片的回忆", "budget_units": budget,
            "deadline_at": iso(clock.now() + timedelta(minutes=minutes)),
            "materials_catalog": "materials-v1", "cost_catalog": "cost-v1",
            "hard_requirements": [], "preferences": [], "parent_request_key": None}


def make_toolbox(env, budget=10, fixture="no_fault", key="tools", minutes=30, max_attempts=2):
    store, catalog, clock = env
    req = Request.model_validate(request(clock, key, budget, minutes)).model_dump(mode="json")
    s = initial_snapshot(req, "offline_mock", catalog, fixture)
    s["status"] = "RUNNING"
    store.bind(key, digest({"input": req}), s)
    return Toolbox(store, s["request_id"], catalog, clock, fixture, max_attempts)


def call(tb, name, **args):
    return tb.dispatch(name, {**args, "decision_summary": "确定性测试动作，非模型决策证据"})


def search(tb):
    return call(tb, "search_materials", query="照片",
                filters={"tags": [], "allowed_usage": None}, limit=3)


def quote(tb, mode="basic", **extra):
    return call(tb, "estimate_plan",
                new_spec={"material_ids": ["mat-001"], "mode": mode, "creative_brief": "温暖的毕业回忆"},
                quote_id=None, stage="pre_generation", script_artifact_id=None, **extra)


def prepare(tb, mode="basic"):
    assert search(tb)["outcome"] == "SUCCESS"
    q1 = quote(tb, mode)["data"]
    generated = call(tb, "generate_script", quote_id=q1["quote_id"])
    assert generated["outcome"] == "SUCCESS", generated
    script = generated["data"]
    q2 = call(tb, "estimate_plan", new_spec=None, quote_id=q1["quote_id"],
              stage="post_generation", script_artifact_id=script["artifact_id"])["data"]
    return q1, script, q2


def run_agent(env, *, fixture="no_fault", scenario="basic", limits=None, raw=None, model=None):
    store, catalog, clock = env
    model = model or OfflineModel(scenario)
    planner = Planner(store, catalog, clock, limits or Limits())
    s = planner.run(raw or request(clock), "offline_mock", lambda: model, fixture)
    return planner, model, s

