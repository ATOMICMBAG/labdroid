from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class InspectionPlugin(ABC):
    name: str = "unnamed-plugin"

    @abstractmethod
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run plugin logic and return structured result."""
