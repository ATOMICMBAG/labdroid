from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ModelProvider(ABC):
    provider_name: str = "base"
    default_model: str = "unknown"

    @abstractmethod
    async def generate(self, inputs: dict[str, Any], model: str | None = None) -> dict[str, Any]:
        """Return unified provider output with at least text/provider/model fields."""
