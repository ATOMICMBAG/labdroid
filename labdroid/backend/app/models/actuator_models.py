from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ActuatorRequest(BaseModel):
    target_type: Literal["http", "mqtt"] = "http"
    target: str
    payload: dict[str, Any] = Field(default_factory=dict)
    require_confirmation: bool = True
    confirmation_token: str | None = None
    simulation: bool = True
    cooldown_s: float = 5.0
    job_id: str | None = None
    domain: str | None = None
    device_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActuatorResult(BaseModel):
    ok: bool
    status: str
    message: str
    target_type: str
    target: str
    simulation: bool
    timestamp: str
    details: dict[str, Any] = Field(default_factory=dict)


class ActuatorAuditEvent(BaseModel):
    event_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    request: ActuatorRequest
    result: ActuatorResult
