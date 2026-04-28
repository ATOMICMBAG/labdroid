from __future__ import annotations

import time
from typing import Any

from app.providers.base import ModelProvider


class LiteRTProvider(ModelProvider):
    """Local provider placeholder for LiteRT integration.

    MVP note: this provider currently returns deterministic explanatory text
    and keeps a stable contract. Real LiteRT wiring can replace this module
    without touching the rest of the system.
    """

    provider_name = "litert"
    default_model = "litert-local-default"

    async def generate(self, inputs: dict[str, Any], model: str | None = None) -> dict[str, Any]:
        t0 = time.perf_counter()
        prompt = str(inputs.get("prompt") or inputs.get("text") or "No prompt provided")
        chosen_model = model or self.default_model
        text = f"[LiteRT:{chosen_model}] {prompt[:400]}"
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "text": text,
            "latency_ms": round(latency_ms, 2),
            "provider": self.provider_name,
            "model": chosen_model,
            "raw": {"mode": "stub"},
        }
