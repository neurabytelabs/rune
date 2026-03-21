"""
🔌 OpenAI-Compatible Provider — Works with OpenAI, Gemini, xAI, Anthropic, local proxies.
Single provider for all OpenAI-compatible endpoints.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Iterator, Optional

import requests

from rune.providers.base import LLMProvider, LLMRequest, LLMResponse


class OpenAICompatProvider(LLMProvider):
    """Provider for any OpenAI-compatible API endpoint."""

    def __init__(
        self,
        api_url: str,
        api_key: str = "",
        timeout: int = 180,
        max_retries: int = 3,
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def name(self) -> str:
        # Detect provider from URL
        url_lower = self.api_url.lower()
        if "x.ai" in url_lower or "xai" in url_lower:
            return "xAI"
        elif "googleapis" in url_lower or "gemini" in url_lower:
            return "Google"
        elif "anthropic" in url_lower:
            return "Anthropic"
        elif "openai" in url_lower:
            return "OpenAI"
        elif "127.0.0.1" in url_lower or "localhost" in url_lower:
            return "Local"
        return "OpenAI-Compatible"

    def _build_payload(self, request: LLMRequest) -> Dict[str, Any]:
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        return {
            "model": request.model,
            "messages": messages,
            "stream": request.stream,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def call(self, request: LLMRequest) -> LLMResponse:
        """Send a non-streaming request."""
        payload = self._build_payload(request)
        payload["stream"] = False

        resp = None
        t0 = time.monotonic()
        for attempt in range(self.max_retries):
            try:
                resp = requests.post(
                    self.api_url,
                    json=payload,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                break
            except requests.ConnectionError:
                if attempt == self.max_retries - 1:
                    raise ConnectionError(f"Cannot connect to {self.api_url}")
                time.sleep(2 * (attempt + 1))
            except requests.HTTPError:
                if resp is not None and resp.status_code in (429, 503) and attempt < self.max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise
        elapsed = time.monotonic() - t0

        if resp is None:
            raise ConnectionError(f"No response from {self.api_url}")

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=request.model,
            tokens_in=usage.get("prompt_tokens", len(request.prompt) // 4),
            tokens_out=usage.get("completion_tokens", len(content) // 4),
            elapsed_sec=round(elapsed, 2),
            raw=data,
        )

    def stream(self, request: LLMRequest) -> Iterator[str]:
        """Stream tokens from a request."""
        payload = self._build_payload(request)
        payload["stream"] = True

        resp = requests.post(
            self.api_url,
            json=payload,
            headers=self._headers(),
            stream=True,
            timeout=self.timeout,
        )
        resp.raise_for_status()

        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    yield token
            except json.JSONDecodeError:
                continue


def create_provider_from_config(config: Dict[str, Any]) -> OpenAICompatProvider:
    """Create a provider from RUNE config dict."""
    return OpenAICompatProvider(
        api_url=config.get("api_url", "http://127.0.0.1:8045/v1/chat/completions"),
        api_key=config.get("api_key", ""),
        timeout=config.get("timeout", 180),
    )
