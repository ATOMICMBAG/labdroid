from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class JobRequest(BaseModel):
    job_id: str | None = None
    domain: str = "default"
    device_id: str | None = None
    provider: str | None = None
    model: str | None = None
    text: str | None = None
    image_b64: str | None = None
    audio_b64: str | None = None
    update_baseline: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderSelectRequest(BaseModel):
    provider: str
    model: str | None = None


class ActuatorCommandRequest(BaseModel):
    target_type: str = "http"  # http | mqtt
    target: str
    payload: dict[str, Any] = Field(default_factory=dict)
    require_confirmation: bool = True
    confirmation_token: str | None = None
    simulation: bool | None = None
    cooldown_s: float | None = None
    job_id: str | None = None
    domain: str | None = None
    device_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaselineUpdateRequest(BaseModel):
    domain: str = "default"
    device_id: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)


class BaselineResetRequest(BaseModel):
    domain: str = "default"
    device_id: str | None = None


class WsEnvelope(BaseModel):
    type: str = "inspect"
    payload: dict[str, Any] = Field(default_factory=dict)
