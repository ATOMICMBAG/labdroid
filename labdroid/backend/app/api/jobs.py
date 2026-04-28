from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_container
from app.models.schemas import JobRequest, ProviderSelectRequest
from app.reporting.replay import replay_report
from app.state import AppContainer


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/start")
async def start_job(payload: JobRequest, container: AppContainer = Depends(get_container)) -> dict:
    try:
        return await container.jobs.submit(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/provider/select")
async def select_provider(payload: ProviderSelectRequest, container: AppContainer = Depends(get_container)) -> dict:
    try:
        selected = container.providers.select(payload.provider, payload.model)
        return {"status": "ok", "selected": selected}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/provider/current")
async def current_provider(container: AppContainer = Depends(get_container)) -> dict:
    return container.providers.current()


@router.post("/{job_id}/replay")
async def replay_job(job_id: str, container: AppContainer = Depends(get_container)) -> dict:
    try:
        report = replay_report(container.report_writer, job_id)
        return {"status": "ok", "report": report.model_dump(mode="json")}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{job_id}/anomalies")
async def get_job_anomalies(job_id: str, container: AppContainer = Depends(get_container)) -> dict:
    try:
        report = replay_report(container.report_writer, job_id)
        return {
            "job_id": job_id,
            "domain": report.domain,
            "device_id": report.device_id,
            "anomalies": report.anomalies,
            "plugin_results": report.plugin_results,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
