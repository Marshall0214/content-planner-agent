"""Validated public tool contracts. Trusted state never comes from model status text."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Request(Contract):
    request_key: str = Field(min_length=1, max_length=160)
    theme: str = Field(min_length=1, max_length=2000)
    budget_units: StrictInt | None = Field(default=None, ge=0)
    deadline_at: datetime | None = None
    materials_catalog: str = "materials-v1"
    cost_catalog: str = "cost-v1"
    hard_requirements: list[str] = Field(default_factory=list, max_length=20)
    preferences: list[str] = Field(default_factory=list, max_length=20)
    parent_request_key: str | None = None

    @field_validator("request_key", "theme")
    @classmethod
    def nonblank(cls, value):
        value = unicodedata.normalize("NFC", value.strip())
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("deadline_at", mode="before")
    @classmethod
    def explicit_time_zone(cls, value):
        if isinstance(value, str):
            if not re.search(r"T.+(?:Z|[+-]\d{2}:\d{2})$", value):
                raise ValueError("deadline requires a time and explicit UTC offset")
        elif value is not None and not isinstance(value, datetime):
            raise ValueError("deadline must be an ISO timestamp, not an epoch number")
        return value

    @field_validator("deadline_at")
    @classmethod
    def aware(cls, value):
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("deadline requires timezone")
            return value.astimezone(timezone.utc)
        return value

    @field_validator("hard_requirements", "preferences")
    @classmethod
    def normalize_lists(cls, values):
        if any(not v.strip() or len(v) > 2000 for v in values):
            raise ValueError("list entries must be nonblank and <= 2000 characters")
        return sorted(set(unicodedata.normalize("NFC", v.strip()) for v in values))


class CandidateSpec(Contract):
    material_ids: list[str] = Field(min_length=1, max_length=5)
    mode: Literal["basic", "premium"]
    creative_brief: str = Field(min_length=1, max_length=2000)

    @field_validator("material_ids")
    @classmethod
    def sorted_ids(cls, values):
        return sorted(set(values))

    @field_validator("creative_brief")
    @classmethod
    def clean_brief(cls, value):
        value = unicodedata.normalize("NFC", value.strip())
        if not value:
            raise ValueError("creative brief must not be blank")
        return value


class SearchFilters(Contract):
    tags: list[str]
    allowed_usage: str | None


class SearchArgs(Contract):
    query: str = Field(min_length=1, max_length=300)
    filters: SearchFilters
    limit: StrictInt = Field(ge=1, le=5)
    decision_summary: str = Field(min_length=1, max_length=500)

    @field_validator("query")
    @classmethod
    def clean_query(cls, value):
        value = unicodedata.normalize("NFC", value.strip())
        if not value:
            raise ValueError("query must not be blank")
        return value


class EstimateArgs(Contract):
    new_spec: CandidateSpec | None
    quote_id: str | None
    stage: Literal["pre_generation", "post_generation"]
    script_artifact_id: str | None
    decision_summary: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def exclusive(self):
        if (self.new_spec is None) == (self.quote_id is None):
            raise ValueError("exactly one of new_spec / quote_id is required")
        if self.new_spec is not None and self.stage != "pre_generation":
            raise ValueError("new specs must use pre_generation")
        if self.stage == "post_generation" and not self.script_artifact_id:
            raise ValueError("post_generation requires successful script artifact")
        if self.stage == "pre_generation" and self.script_artifact_id is not None:
            raise ValueError("pre_generation must not specify script artifact")
        return self


class GenerateArgs(Contract):
    quote_id: str
    decision_summary: str = Field(min_length=1, max_length=500)


class CampaignTask(Contract):
    task_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    depends_on: list[str]
    owner_role: str = Field(min_length=1)
    relative_schedule: str = Field(min_length=1)


class CampaignDraft(Contract):
    title: str = Field(min_length=1, max_length=300)
    objective: str = Field(min_length=1, max_length=2000)
    audience: str = Field(min_length=1, max_length=1000)
    key_message: str = Field(min_length=1, max_length=2000)
    channels: list[str] = Field(min_length=1, max_length=10)
    script_artifact_id: str
    material_refs: list[str] = Field(min_length=1, max_length=5)
    campaign_tasks: list[CampaignTask] = Field(min_length=1, max_length=12)
    risks: list[str] = Field(min_length=1)
    assumptions: list[str] = Field(min_length=1)

    @field_validator("title", "objective", "audience", "key_message")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("draft field must not be blank")
        return value.strip()


class SaveArgs(Contract):
    quote_id: str
    script_artifact_id: str
    draft: CampaignDraft
    decision_summary: str = Field(min_length=1, max_length=500)


class StopDecision(Contract):
    action: Literal["stop", "need_input"]
    decision_summary: str = Field(min_length=1, max_length=500)
    reason_code: str
    missing_fields: list[str]
    pending_items: list[str]


TOOL_MODELS = {
    "search_materials": SearchArgs,
    "estimate_plan": EstimateArgs,
    "generate_script": GenerateArgs,
    "save_plan": SaveArgs,
}
DESCRIPTIONS = {
    "search_materials": "Search synthetic materials; new successful search costs 1 unit/60 simulated seconds.",
    "estimate_plan": "Register a new immutable candidate OR quote an existing quote's candidate using fresh ledger/clock. Free. Over-budget is valid feedback.",
    "generate_script": "Generate by quote reference. Reuse identical successful spec for zero new cost/time. basic=6/240s; premium=10/480s.",
    "save_plan": "Save full campaign and script using post-generation quote. 1 unit/60s. Confirmed success immediately terminates the agent.",
}


def tool_definitions():
    return [
        {"type": "function", "name": name, "description": DESCRIPTIONS[name],
         "strict": True, "parameters": model.model_json_schema()}
        for name, model in TOOL_MODELS.items()
    ]

