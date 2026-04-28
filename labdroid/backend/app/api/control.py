from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_container
from app.models.actuator_models import ActuatorRequest
from app.models.schemas import ActuatorCommandRequest, BaselineResetRequest, BaselineUpdateRequest
from app.state import AppContainer


router = APIRouter(prefix="/control", tags=["control"])


@router.post("/actuator/fire")
async def actuator_fire(payload: ActuatorCommandRequest, container: AppContainer = Depends(get_container)) -> dict:
    req = ActuatorRequest(
        target_type=payload.target_type,
        target=payload.target,
        payload=payload.payload,
        require_confirmation=payload.require_confirmation,
        confirmation_token=payload.confirmation_token,
        simulation=container.settings.actuator_simulation_default if payload.simulation is None else payload.simulation,
        cooldown_s=payload.cooldown_s or container.settings.actuator_cooldown_s,
        job_id=payload.job_id,
        domain=payload.domain,
        device_id=payload.device_id,
        metadata=payload.metadata,
    )
    result = await container.safety_layer.dispatch(req)
    return result.model_dump(mode="json")


@router.get("/actuator/audit")
async def actuator_audit(limit: int = Query(default=100, ge=1, le=1000), container: AppContainer = Depends(get_container)) -> dict:
    rows = container.safety_layer.read_audit_events(limit=limit)
    return {"count": len(rows), "events": rows}


@router.get("/baseline")
async def baseline_get(
    domain: str = Query(default="default"),
    device_id: str | None = Query(default=None),
    container: AppContainer = Depends(get_container),
) -> dict:
    stats = container.baseline_manager.compute_baseline_stats(domain=domain, device_id=device_id)
    return {"domain": domain, "device_id": device_id, "stats": stats}


@router.post("/baseline/update")
async def baseline_update(payload: BaselineUpdateRequest, container: AppContainer = Depends(get_container)) -> dict:
    bucket = container.baseline_manager.append_metrics(
        domain=payload.domain,
        device_id=payload.device_id,
        metrics=payload.metrics,
    )
    return {"status": "ok", "bucket": bucket}


@router.post("/baseline/reset")
async def baseline_reset(payload: BaselineResetRequest, container: AppContainer = Depends(get_container)) -> dict:
    container.baseline_manager.reset(domain=payload.domain, device_id=payload.device_id)
    return {"status": "ok", "domain": payload.domain, "device_id": payload.device_id}


@router.get("/plugins")
async def plugins_list(container: AppContainer = Depends(get_container)) -> dict:
    return {"plugins": container.plugin_manager.plugins}


@router.post("/plugins/reload")
async def plugins_reload(container: AppContainer = Depends(get_container)) -> dict:
    names = container.plugin_manager.load_plugins()
    return {"status": "ok", "plugins": names}


@router.post("/plugins/run")
async def plugins_run(payload: dict, container: AppContainer = Depends(get_container)) -> dict:
    try:
        results = container.plugin_manager.run_all(payload)
        return {"results": results}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
