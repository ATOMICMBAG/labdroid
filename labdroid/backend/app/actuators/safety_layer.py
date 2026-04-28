from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.actuators.http_actuator import fire_http
from app.actuators.mqtt_actuator import fire_mqtt
from app.core.config import Settings
from app.models.actuator_models import ActuatorAuditEvent, ActuatorRequest, ActuatorResult


class SafetyLayer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._last_fire_by_target: dict[str, float] = {}
        self.settings.audit_log_file.parent.mkdir(parents=True, exist_ok=True)

    async def dispatch(self, request: ActuatorRequest) -> ActuatorResult:
        req = request.model_copy(deep=True)

        if req.simulation is None:
            req.simulation = self.settings.actuator_simulation_default
        if req.cooldown_s is None:
            req.cooldown_s = self.settings.actuator_cooldown_s

        confirmed = self._is_confirmed(req)
        if req.require_confirmation and not confirmed:
            result = self._mk_result(
                ok=False,
                status="confirmation_required",
                message="command blocked: missing/invalid confirmation token",
                req=req,
                details={"expected": "CONFIRM"},
            )
            self._audit(req, result)
            return result

        if self._is_cooldown_active(req.target, req.cooldown_s):
            result = self._mk_result(
                ok=False,
                status="cooldown_active",
                message=f"command blocked by cooldown ({req.cooldown_s:.2f}s)",
                req=req,
            )
            self._audit(req, result)
            return result

        if req.target_type == "http":
            result = await fire_http(
                req,
                timeout_s=self.settings.actuator_request_timeout_s,
                host_allowlist=self.settings.actuator_http_allowlist,
            )
        elif req.target_type == "mqtt":
            result = await fire_mqtt(
                req,
                enabled=self.settings.mqtt_enabled,
                broker=self.settings.mqtt_broker,
                topic_prefix=self.settings.mqtt_topic_prefix,
            )
        else:
            result = self._mk_result(
                ok=False,
                status="invalid_target_type",
                message=f"unsupported target_type '{req.target_type}'",
                req=req,
            )

        self._last_fire_by_target[req.target] = time.monotonic()
        result.timestamp = datetime.now(timezone.utc).isoformat()
        self._audit(req, result)
        return result

    def _is_confirmed(self, request: ActuatorRequest) -> bool:
        token = (request.confirmation_token or "").strip()
        return token in {"CONFIRM", "CONFIRM_ACTUATION"}

    def _is_cooldown_active(self, target: str, cooldown_s: float) -> bool:
        if cooldown_s <= 0:
            return False
        last = self._last_fire_by_target.get(target)
        if last is None:
            return False
        return (time.monotonic() - last) < cooldown_s

    def _mk_result(self, *, ok: bool, status: str, message: str, req: ActuatorRequest, details: dict | None = None) -> ActuatorResult:
        return ActuatorResult(
            ok=ok,
            status=status,
            message=message,
            target_type=req.target_type,
            target=req.target,
            simulation=req.simulation,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details or {},
        )

    def _audit(self, request: ActuatorRequest, result: ActuatorResult) -> None:
        event = ActuatorAuditEvent(
            event_id=uuid.uuid4().hex,
            request=request,
            result=result,
        )
        line = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
        self.settings.audit_log_file.open("a", encoding="utf-8").write(line + "\n")

    def read_audit_events(self, limit: int = 200) -> list[dict]:
        path: Path = self.settings.audit_log_file
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        rows = lines[-max(1, limit) :]
        output: list[dict] = []
        for line in rows:
            try:
                output.append(json.loads(line))
            except Exception:
                continue
        return output
