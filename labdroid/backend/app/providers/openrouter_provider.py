from __future__ import annotations

import time
from typing import Any

from app.providers.base import ModelProvider


class OpenRouterProvider(ModelProvider):
    provider_name = "openrouter"

    def __init__(self, base_url: str, api_key: str | None, default_model: str, timeout_s: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.timeout_s = timeout_s

    async def generate(self, inputs: dict[str, Any], model: str | None = None) -> dict[str, Any]:
        t0 = time.perf_counter()
        chosen_model = model or self.default_model
        prompt = str(inputs.get("prompt") or inputs.get("text") or "")

        if not self.api_key:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "text": f"[OpenRouter missing key:{chosen_model}] {prompt[:300]}",
                "latency_ms": round(latency_ms, 2),
                "provider": self.provider_name,
                "model": chosen_model,
                "raw": {"error": "OPENROUTER_API_KEY not configured", "fallback": True},
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": chosen_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }

        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
        except Exception as exc:  # noqa: BLE001
            text = f"[OpenRouter fallback:{chosen_model}] {prompt[:300]}"
            data = {"error": str(exc), "fallback": True}

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "text": text,
            "latency_ms": round(latency_ms, 2),
            "provider": self.provider_name,
            "model": chosen_model,
            "raw": data,
        }
