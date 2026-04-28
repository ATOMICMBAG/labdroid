from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_container
from app.state import AppContainer


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{job_id}")
async def get_report(job_id: str, container: AppContainer = Depends(get_container)) -> dict:
    try:
        report = container.report_writer.load_report(job_id)
        return report.model_dump(mode="json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{job_id}/markdown")
async def get_report_markdown(job_id: str, container: AppContainer = Depends(get_container)) -> dict:
    try:
        return {
            "job_id": job_id,
            "markdown": container.report_writer.load_markdown(job_id),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
