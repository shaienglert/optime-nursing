from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from benchmark.adapters.base import ProviderAdapter
from benchmark.contracts import PromptEnvelope, RawProviderResponse, utc_now_iso


class OptimeAdapter(ProviderAdapter):
    provider = "optime"

    def run(self, prompt: PromptEnvelope, *, case_payload: dict[str, Any], live: bool) -> RawProviderResponse:
        if not live:
            return self.not_configured(prompt, "LIVE_EXECUTION_DISABLED")

        repo_root = Path(__file__).resolve().parents[2]
        runner = repo_root / "benchmark" / "adapters" / "optime_runtime_runner.cjs"

        try:
            result = subprocess.run(
                ["node", str(runner), json.dumps(case_payload)],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=240,
            )
            payload = json.loads((result.stdout or "{}").strip() or "{}")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
            return RawProviderResponse(
                provider=self.provider,
                model=prompt.model,
                model_version=None,
                run_timestamp=utc_now_iso(),
                settings={"mode": "production"},
                tools_enabled=False,
                latency_ms=None,
                citations=[],
                response_text="",
                response_json=None,
                error=f"CHAIN_BREAK: {error}",
                run_status="CHAIN_BREAK",
            )

        run_status = payload.get("run_status", "CHAIN_BREAK")
        response_text = json.dumps(payload, ensure_ascii=True)
        err = payload.get("error")

        return RawProviderResponse(
            provider=self.provider,
            model=prompt.model,
            model_version="frontend/src/lib/optime-v2-engine.ts",
            run_timestamp=utc_now_iso(),
            settings={"mode": "production"},
            tools_enabled=False,
            latency_ms=None,
            citations=[],
            response_text=response_text,
            response_json=payload,
            error=err,
            run_status=run_status,
        )
