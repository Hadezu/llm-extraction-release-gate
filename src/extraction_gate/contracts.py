"""Strict contracts. Labels are local, reviewed fixtures, never sent to the model."""

import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, max_length=6000)]
Name = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


def canonical(value) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_json(text: str):
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError("Duplicate JSON key")
            obj[key] = value
        return obj

    def bad_constant(value):
        raise ValueError("Non-finite JSON number")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=bad_constant)


class Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)


class Evidence(Strict):
    source: Text | None
    target: Text | None
    deadline: Text | None


class Extraction(Strict):
    action: Literal["integration", "migration", "reporting", "unknown"]
    source: Text | None
    target: Text | None
    deadline: Text | None
    review_required: bool
    evidence: Evidence


class Expected(Strict):
    action: Literal["integration", "migration", "reporting", "unknown"]
    source: Text | None
    target: Text | None
    deadline: Text | None
    review_required: bool


class Case(Strict):
    id: Name
    slice: Name
    critical: bool
    input: Text
    expected: Expected
    rationale: Text


class Suite(Strict):
    version: Name
    disclosure: Text
    cases: Annotated[list[Case], Field(min_length=1, max_length=500)]

    @model_validator(mode="after")
    def unique_ids(self):
        if len({c.id for c in self.cases}) != len(self.cases):
            raise ValueError("Duplicate case IDs")
        for case in self.cases:
            for field in ("source", "target", "deadline"):
                value = getattr(case.expected, field)
                if value is not None and value not in case.input:
                    raise ValueError(f"Unverifiable label: {case.id}/{field}")
        return self


class Settings(Strict):
    model: Text
    model_revision: Text
    runtime: Text
    temperature: Annotated[float, Field(ge=0, le=2)] = 0.0
    seed: Annotated[int, Field(ge=0, le=2147483647)] = 42
    max_tokens: Annotated[int, Field(ge=16, le=2048)] = 320
    repeats: Annotated[int, Field(ge=1, le=10)] = 2
    max_calls: Annotated[int, Field(ge=1, le=5000)] = 100
    timeout_seconds: Annotated[float, Field(gt=0, le=300)] = 60.0


class Record(Strict):
    case_id: Name
    repeat: Annotated[int, Field(ge=0)]
    status: Literal[
        "OK",
        "TIMEOUT",
        "HTTP_ERROR",
        "TRANSPORT_ERROR",
        "MALFORMED_RESPONSE",
        "OVERSIZED_RESPONSE",
        "TRUNCATED",
        "REFUSAL",
        "BUDGET_SKIPPED",
    ]
    raw: Annotated[str, Field(max_length=131072)] | None = None
    http_status: Annotated[int, Field(ge=100, le=599)] | None = None
    response_model: Text | None = None
    finish_reason: Text | None = None
    latency_ms: Annotated[float, Field(ge=0)] = 0.0
    input_tokens: Annotated[int, Field(ge=0)] | None = None
    output_tokens: Annotated[int, Field(ge=0)] | None = None


class Manifest(Strict):
    format: Literal["extraction-run-v1"] = "extraction-run-v1"
    kind: Literal["LIVE_LOCAL_MODEL", "CONTROL_FIXTURE"]
    label: Name
    started_at: Text
    finished_at: Text | None = None
    complete: bool = False
    suite: Suite
    suite_sha256: Digest
    prompt: Text
    prompt_sha256: Digest
    settings: Settings
    evaluator: Literal["extraction-contract-v1"] = "extraction-contract-v1"
    files: dict[
        Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,80}--[0-9]$")], Digest
    ] = Field(default_factory=dict)
