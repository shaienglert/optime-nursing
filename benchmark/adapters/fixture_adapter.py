from __future__ import annotations

from typing import Any

from benchmark.adapters.base import ProviderAdapter
from benchmark.contracts import PromptEnvelope, RawProviderResponse, utc_now_iso


class FixtureAdapter(ProviderAdapter):
    def __init__(self, provider: str, fixture_payload: dict[str, Any]) -> None:
        self.provider = provider
        self.fixture_payload = fixture_payload

    def run(self, prompt: PromptEnvelope, *, case_payload: dict[str, Any], live: bool) -> RawProviderResponse:
        return RawProviderResponse(
            provider=self.provider,
            model=prompt.model,
            model_version="fixture-v1",
            run_timestamp=utc_now_iso(),
            settings={"temperature": 0, "fixture": True},
            tools_enabled=prompt.tools_enabled,
            latency_ms=12,
            citations=self.fixture_payload.get("citations", []),
            response_text=self.fixture_payload.get("response_text", ""),
            response_json=self.fixture_payload.get("response_json"),
            error=None,
            run_status="OK",
            fixture_label="TEST_FIXTURE_NOT_REAL_AI_RESULT",
        )
