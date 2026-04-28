from __future__ import annotations

import time
from typing import Any

from app.providers.base import ModelProvider


class OllamaProvider(ModelProvider):
    provider_name = "ollama"

    def __init__(self, base_url: str, default_model: str, timeout_s: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout_s = timeout_s

    async def generate(self, inputs: dict[str, Any], model: str | None = None) -> dict[str, Any]:
        t0 = time.perf_counter()
        chosen_model = model or self.default_model
        prompt = str(inputs.get("prompt") or inputs.get("text") or "")

        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": chosen_model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                text = str(data.get("response", "")).strip()
        except Exception as exc:  # noqa: BLE001
            text = f"[Ollama fallback:{chosen_model}] {prompt[:300]}"
            data = {"error": str(exc), "fallback": True}

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "text": text,
            "latency_ms": round(latency_ms, 2),
            "provider": self.provider_name,
            "model": chosen_model,
            "raw": data,
        }
