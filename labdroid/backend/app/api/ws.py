from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.actuator_models import ActuatorRequest
from app.models.schemas import ActuatorCommandRequest, JobRequest, ProviderSelectRequest, WsEnvelope
from app.state import AppContainer


router = APIRouter(tags=["ws"])


def _client_id(ws: WebSocket) -> str:
    if ws.client is None:
        return "unknown"
    return f"{ws.client.host}:{ws.client.port}"


@router.websocket("/ws")
async def websocket_inspection(ws: WebSocket) -> None:
    await ws.accept()
    container: AppContainer = ws.app.state.container

    try:
        while True:
            raw = await ws.receive_json()

            if not container.ws_rate_limiter.allow(_client_id(ws)):
                await ws.send_json(
                    {
                        "type": "error",
                        "error": "rate_limit_exceeded",
                        "detail": "too many requests per minute",
                    }
                )
                continue

            envelope = WsEnvelope.model_validate(raw)
            req_id = envelope.payload.get("_req_id") if isinstance(envelope.payload, dict) else None

            if envelope.type in {"inspect", "job_start"}:
                request = JobRequest.model_validate(envelope.payload)
                result = await container.jobs.submit(request)
                if req_id:
                    result["_req_id"] = req_id
                await ws.send_json({"type": "job_result", "payload": result})
            elif envelope.type == "provider_select":
                selection = ProviderSelectRequest.model_validate(envelope.payload)
                selected = container.providers.select(selection.provider, selection.model)
                if req_id:
                    selected = {**selected, "_req_id": req_id}
                await ws.send_json({"type": "provider_selected", "payload": selected})
            elif envelope.type == "provider_current":
                current = container.providers.current()
                if req_id:
                    current = {**current, "_req_id": req_id}
                await ws.send_json({"type": "provider_current", "payload": current})
            elif envelope.type == "actuator_fire":
                command = ActuatorCommandRequest.model_validate(envelope.payload)
                actuator_request = ActuatorRequest(
                    target_type=command.target_type,
                    target=command.target,
                    payload=command.payload,
                    require_confirmation=command.require_confirmation,
                    confirmation_token=command.confirmation_token,
                    simulation=container.settings.actuator_simulation_default if command.simulation is None else command.simulation,
                    cooldown_s=command.cooldown_s or container.settings.actuator_cooldown_s,
                    job_id=command.job_id,
                    domain=command.domain,
                    device_id=command.device_id,
                    metadata=command.metadata,
                )
                result = await container.safety_layer.dispatch(request=actuator_request)
                payload = result.model_dump(mode="json")
                if req_id:
                    payload["_req_id"] = req_id
                await ws.send_json({"type": "actuator_result", "payload": payload})
            else:
                await ws.send_json(
                    {
                        "type": "error",
                        "error": "unsupported_message",
                        "detail": f"unsupported ws message type '{envelope.type}'",
                    }
                )

    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        await ws.send_json({"type": "error", "error": "internal_error", "detail": str(exc)})
        await ws.close()
