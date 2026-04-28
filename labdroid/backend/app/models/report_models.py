from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CheckResult(BaseModel):
    name: str
    metric: str
    status: Literal["pass", "fail"]
    critical: bool = True
    actual: float | None = None
    threshold_min: float | None = None
    threshold_max: float | None = None
    reason: str


class InspectionReport(BaseModel):
    job_id: str
    timestamp: str
    domain: str
    device_id: str | None = None
    provider: str
    model: str
    result: Literal["OK", "NOK"]
    confidence: float
    metrics: dict[str, float] = Field(default_factory=dict)
    checks: list[CheckResult] = Field(default_factory=list)
    evidence_refs: dict[str, list[str]] = Field(default_factory=lambda: {"images": [], "audio": []})
    anomalies: dict[str, dict[str, float | bool]] = Field(default_factory=dict)
    plugin_results: list[dict[str, Any]] = Field(default_factory=list)
    timings: dict[str, float] = Field(default_factory=dict)
    explanation: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
