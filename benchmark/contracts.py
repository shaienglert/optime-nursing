from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
import hashlib
import json


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass
class PromptEnvelope:
    track: str
    case_id: str
    provider: str
    model: str
    system_prompt: str | None
    user_prompt: str
    prompt_hash: str
    generated_at: str
    tools_enabled: bool = False


@dataclass
class RawProviderResponse:
    provider: str
    model: str
    model_version: str | None
    run_timestamp: str
    settings: dict[str, Any]
    tools_enabled: bool
    latency_ms: int | None
    citations: list[dict[str, Any]]
    response_text: str
    response_json: dict[str, Any] | None
    error: str | None
    run_status: str
    fixture_label: str | None = None


@dataclass
class NormalizedTopFacility:
    facility_name: str
    location: str | None
    why_selected: str
    must_satisfied: list[str]
    must_failed: list[str]
    must_unknown: list[str]
    recommendation_alignment: str
    nice_to_have_alignment: str
    tradeoffs: list[str]
    evidence_gaps: list[str]
    sources: list[dict[str, Any]]
    confidence: str


@dataclass
class NormalizedResponse:
    understood_person_profile: dict[str, Any]
    explicit_needs: list[str]
    missing_information: list[str]
    clarifying_questions: list[str]
    must_requirements: list[str]
    professional_recommendations: list[str]
    nice_to_have: list[str]
    facilities_considered: list[str]
    top_5: list[NormalizedTopFacility]
    unsupported_or_unverified_claims: list[str]
    next_steps_for_family: list[str]


@dataclass
class BenchmarkRunRecord:
    benchmark_version: str
    run_id: str
    track: str
    case_id: str
    case_version: str
    optime_commit_hash: str
    provider: str
    model: str
    model_version: str | None
    run_timestamp: str
    prompt: PromptEnvelope
    raw_response: RawProviderResponse
    normalized_response: dict[str, Any]
    claim_source_audit: list[dict[str, Any]] = field(default_factory=list)
    hallucination_audit: dict[str, Any] = field(default_factory=dict)
    identity_resolution: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
