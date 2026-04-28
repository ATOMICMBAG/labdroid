from __future__ import annotations

from urllib.parse import urlparse

from app.models.actuator_models import ActuatorRequest, ActuatorResult


async def fire_http(request: ActuatorRequest, *, timeout_s: float, host_allowlist: set[str]) -> ActuatorResult:
    import httpx

    parsed = urlparse(request.target)
    host = (parsed.hostname or "").lower()
    if not host:
        return ActuatorResult(
            ok=False,
            status="invalid_target",
            message="target URL has no host",
            target_type="http",
            target=request.target,
            simulation=request.simulation,
            timestamp="",
        )
    if host_allowlist and host not in host_allowlist:
        return ActuatorResult(
            ok=False,
            status="blocked_host",
            message=f"host '{host}' not in allowlist",
            target_type="http",
            target=request.target,
            simulation=request.simulation,
            timestamp="",
        )

    if request.simulation:
        return ActuatorResult(
            ok=True,
            status="simulated",
            message="HTTP actuator command simulated",
            target_type="http",
            target=request.target,
            simulation=True,
            timestamp="",
            details={"payload": request.payload},
        )

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(request.target, json=request.payload)
            ok = 200 <= resp.status_code < 300
            return ActuatorResult(
                ok=ok,
                status="ok" if ok else "http_error",
                message=f"HTTP status {resp.status_code}",
                target_type="http",
                target=request.target,
                simulation=False,
                timestamp="",
                details={
                    "status_code": resp.status_code,
                    "response_text": resp.text[:2000],
                },
            )
    except Exception as exc:  # noqa: BLE001
        return ActuatorResult(
            ok=False,
            status="exception",
            message=str(exc),
            target_type="http",
            target=request.target,
            simulation=False,
            timestamp="",
        )
