from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from benchmark.contracts import PromptEnvelope, RawProviderResponse, utc_now_iso


class ProviderAdapter(ABC):
    provider: str

    @abstractmethod
    def run(self, prompt: PromptEnvelope, *, case_payload: dict[str, Any], live: bool) -> RawProviderResponse:
        raise NotImplementedError

    def not_configured(self, prompt: PromptEnvelope, reason: str) -> RawProviderResponse:
        return RawProviderResponse(
            provider=self.provider,
            model=prompt.model,
            model_version=None,
            run_timestamp=utc_now_iso(),
            settings={"temperature": None},
            tools_enabled=prompt.tools_enabled,
            latency_ms=None,
            citations=[],
            response_text="",
            response_json=None,
            error=reason,
            run_status="NOT_CONFIGURED",
        )
