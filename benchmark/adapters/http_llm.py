from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from benchmark.contracts import PromptEnvelope, RawProviderResponse, utc_now_iso


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int = 45) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body)


def call_openai(prompt: PromptEnvelope, env_key: str) -> RawProviderResponse:
    token = os.getenv(env_key)
    if not token:
        return RawProviderResponse(
            provider="openai",
            model=prompt.model,
            model_version=None,
            run_timestamp=utc_now_iso(),
            settings={"temperature": 0},
            tools_enabled=prompt.tools_enabled,
            latency_ms=None,
            citations=[],
            response_text="",
            response_json=None,
            error=f"Missing {env_key}",
            run_status="NOT_CONFIGURED",
        )

    payload = {
        "model": prompt.model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": prompt.system_prompt or ""},
            {"role": "user", "content": prompt.user_prompt},
        ],
    }

    start = time.time()
    try:
        _, data = _post_json(
            "https://api.openai.com/v1/chat/completions",
            payload,
            {"Authorization": f"Bearer {token}"},
        )
        latency_ms = int((time.time() - start) * 1000)
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return RawProviderResponse(
            provider="openai",
            model=prompt.model,
            model_version=data.get("model"),
            run_timestamp=utc_now_iso(),
            settings={"temperature": 0},
            tools_enabled=prompt.tools_enabled,
            latency_ms=latency_ms,
            citations=[],
            response_text=text,
            response_json=data,
            error=None,
            run_status="OK",
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        return RawProviderResponse(
            provider="openai",
            model=prompt.model,
            model_version=None,
            run_timestamp=utc_now_iso(),
            settings={"temperature": 0},
            tools_enabled=prompt.tools_enabled,
            latency_ms=None,
            citations=[],
            response_text="",
            response_json=None,
            error=f"HTTPError {exc.code}: {detail}",
            run_status="ERROR",
        )


def call_anthropic(prompt: PromptEnvelope, env_key: str) -> RawProviderResponse:
    token = os.getenv(env_key)
    if not token:
        return RawProviderResponse(
            provider="anthropic",
            model=prompt.model,
            model_version=None,
            run_timestamp=utc_now_iso(),
            settings={"temperature": 0},
            tools_enabled=prompt.tools_enabled,
            latency_ms=None,
            citations=[],
            response_text="",
            response_json=None,
            error=f"Missing {env_key}",
            run_status="NOT_CONFIGURED",
        )

    payload = {
        "model": prompt.model,
        "temperature": 0,
        "max_tokens": 1800,
        "system": prompt.system_prompt or "",
        "messages": [{"role": "user", "content": prompt.user_prompt}],
    }

    start = time.time()
    try:
        _, data = _post_json(
            "https://api.anthropic.com/v1/messages",
            payload,
            {
                "x-api-key": token,
                "anthropic-version": "2023-06-01",
            },
        )
        latency_ms = int((time.time() - start) * 1000)
        parts = data.get("content", [])
        text = "\n".join([p.get("text", "") for p in parts if p.get("type") == "text"])
        return RawProviderResponse(
            provider="anthropic",
            model=prompt.model,
            model_version=data.get("model"),
            run_timestamp=utc_now_iso(),
            settings={"temperature": 0},
            tools_enabled=prompt.tools_enabled,
            latency_ms=latency_ms,
            citations=[],
            response_text=text,
            response_json=data,
            error=None,
            run_status="OK",
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        return RawProviderResponse(
            provider="anthropic",
            model=prompt.model,
            model_version=None,
            run_timestamp=utc_now_iso(),
            settings={"temperature": 0},
            tools_enabled=prompt.tools_enabled,
            latency_ms=None,
            citations=[],
            response_text="",
            response_json=None,
            error=f"HTTPError {exc.code}: {detail}",
            run_status="ERROR",
        )


def call_gemini(prompt: PromptEnvelope, env_key: str) -> RawProviderResponse:
    key = os.getenv(env_key)
    if not key:
        return RawProviderResponse(
            provider="google",
            model=prompt.model,
            model_version=None,
            run_timestamp=utc_now_iso(),
            settings={"temperature": 0},
            tools_enabled=prompt.tools_enabled,
            latency_ms=None,
            citations=[],
            response_text="",
            response_json=None,
            error=f"Missing {env_key}",
            run_status="NOT_CONFIGURED",
        )

    payload = {
        "system_instruction": {"parts": [{"text": prompt.system_prompt or ""}]},
        "contents": [{"parts": [{"text": prompt.user_prompt}]}],
        "generationConfig": {"temperature": 0},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{prompt.model}:generateContent?key={key}"
    start = time.time()
    try:
        _, data = _post_json(url, payload, {})
        latency_ms = int((time.time() - start) * 1000)
        candidates = data.get("candidates", [])
        text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "\n".join([p.get("text", "") for p in parts])
        return RawProviderResponse(
            provider="google",
            model=prompt.model,
            model_version=prompt.model,
            run_timestamp=utc_now_iso(),
            settings={"temperature": 0},
            tools_enabled=prompt.tools_enabled,
            latency_ms=latency_ms,
            citations=[],
            response_text=text,
            response_json=data,
            error=None,
            run_status="OK",
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        return RawProviderResponse(
            provider="google",
            model=prompt.model,
            model_version=None,
            run_timestamp=utc_now_iso(),
            settings={"temperature": 0},
            tools_enabled=prompt.tools_enabled,
            latency_ms=None,
            citations=[],
            response_text="",
            response_json=None,
            error=f"HTTPError {exc.code}: {detail}",
            run_status="ERROR",
        )


def call_perplexity(prompt: PromptEnvelope, env_key: str) -> RawProviderResponse:
    token = os.getenv(env_key)
    if not token:
        return RawProviderResponse(
            provider="perplexity",
            model=prompt.model,
            model_version=None,
            run_timestamp=utc_now_iso(),
            settings={"temperature": 0},
            tools_enabled=prompt.tools_enabled,
            latency_ms=None,
            citations=[],
            response_text="",
            response_json=None,
            error=f"Missing {env_key}",
            run_status="NOT_CONFIGURED",
        )

    payload = {
        "model": prompt.model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": prompt.system_prompt or ""},
            {"role": "user", "content": prompt.user_prompt},
        ],
    }

    start = time.time()
    try:
        _, data = _post_json(
            "https://api.perplexity.ai/chat/completions",
            payload,
            {"Authorization": f"Bearer {token}"},
        )
        latency_ms = int((time.time() - start) * 1000)
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = [{"url": url, "source_type": "SEARCH_RESULT"} for url in data.get("citations", [])]
        return RawProviderResponse(
            provider="perplexity",
            model=prompt.model,
            model_version=data.get("model"),
            run_timestamp=utc_now_iso(),
            settings={"temperature": 0},
            tools_enabled=prompt.tools_enabled,
            latency_ms=latency_ms,
            citations=citations,
            response_text=text,
            response_json=data,
            error=None,
            run_status="OK",
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        return RawProviderResponse(
            provider="perplexity",
            model=prompt.model,
            model_version=None,
            run_timestamp=utc_now_iso(),
            settings={"temperature": 0},
            tools_enabled=prompt.tools_enabled,
            latency_ms=None,
            citations=[],
            response_text="",
            response_json=None,
            error=f"HTTPError {exc.code}: {detail}",
            run_status="ERROR",
        )
