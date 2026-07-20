from __future__ import annotations

from typing import Any

from benchmark.adapters.base import ProviderAdapter
from benchmark.adapters.http_llm import call_anthropic
from benchmark.contracts import PromptEnvelope, RawProviderResponse


class AnthropicAdapter(ProviderAdapter):
    provider = "anthropic"

    def run(self, prompt: PromptEnvelope, *, case_payload: dict[str, Any], live: bool) -> RawProviderResponse:
        if not live:
            return self.not_configured(prompt, "LIVE_EXECUTION_DISABLED")
        return call_anthropic(prompt, "ANTHROPIC_API_KEY")
