from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.security import ensure_provider_allowed
from app.providers.base import ModelProvider
from app.providers.litert_provider import LiteRTProvider
from app.providers.ollama_provider import OllamaProvider
from app.providers.openrouter_provider import OpenRouterProvider


class ProviderRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._providers: dict[str, ModelProvider] = {
            "litert": LiteRTProvider(),
            "ollama": OllamaProvider(
                base_url=settings.ollama_base_url,
                default_model=settings.ollama_default_model,
                timeout_s=settings.model_timeout_s,
            ),
            "openrouter": OpenRouterProvider(
                base_url=settings.openrouter_base_url,
                api_key=settings.openrouter_api_key,
                default_model=settings.openrouter_default_model,
                timeout_s=settings.model_timeout_s,
            ),
        }
        default_provider = settings.default_provider
        if default_provider not in settings.provider_allowlist:
            default_provider = sorted(settings.provider_allowlist)[0]
        self._active_provider = default_provider
        self._active_model: str | None = None

    def select(self, provider: str, model: str | None = None) -> dict[str, str | None]:
        normalized = ensure_provider_allowed(provider, self.settings.provider_allowlist)
        if normalized not in self._providers:
            raise ValueError(f"provider '{provider}' is configured as allowed but not implemented")
        self._active_provider = normalized
        self._active_model = model.strip() if model else None
        return self.current()

    def current(self) -> dict[str, str | None]:
        return {
            "provider": self._active_provider,
            "model": self._active_model or self._providers[self._active_provider].default_model,
        }

    async def generate(
        self,
        inputs: dict[str, Any],
        provider: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        chosen_provider = provider or self._active_provider
        normalized = ensure_provider_allowed(chosen_provider, self.settings.provider_allowlist)
        impl = self._providers[normalized]
        chosen_model = model or (self._active_model if normalized == self._active_provider else None)
        return await impl.generate(inputs=inputs, model=chosen_model)
