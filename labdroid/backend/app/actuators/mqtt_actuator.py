from __future__ import annotations

from app.models.actuator_models import ActuatorRequest, ActuatorResult


async def fire_mqtt(request: ActuatorRequest, *, enabled: bool, broker: str, topic_prefix: str) -> ActuatorResult:
    topic = f"{topic_prefix}/{request.target}".strip("/")

    if request.simulation or not enabled:
        return ActuatorResult(
            ok=True,
            status="simulated",
            message="MQTT actuator command simulated",
            target_type="mqtt",
            target=topic,
            simulation=True,
            timestamp="",
            details={
                "broker": broker,
                "topic": topic,
                "payload": request.payload,
                "mqtt_enabled": enabled,
            },
        )

    # Prepared for real hardware integration.
    # You can replace this with a paho-mqtt or async-mqtt publish implementation.
    return ActuatorResult(
        ok=False,
        status="not_implemented",
        message="MQTT publish not wired yet; enable simulation or add broker client",
        target_type="mqtt",
        target=topic,
        simulation=False,
        timestamp="",
        details={
            "broker": broker,
            "topic": topic,
            "payload": request.payload,
        },
    )
