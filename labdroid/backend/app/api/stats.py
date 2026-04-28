from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import ensure_metric_allowed
from app.dependencies import get_container
from app.state import AppContainer
from app.stats.constants import SUPPORTED_METRICS
from app.stats.histogram import compute_histogram
from app.stats.summary import compute_summary, filter_reports
from app.stats.timeseries import compute_timeseries


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary")
async def stats_summary(
    domain: str | None = Query(default=None),
    device: str | None = Query(default=None),
    from_ts: str | None = Query(default=None, alias="from"),
    to_ts: str | None = Query(default=None, alias="to"),
    container: AppContainer = Depends(get_container),
) -> dict:
    reports = container.report_writer.list_reports()
    filtered = filter_reports(reports, domain=domain, device_id=device, from_ts=from_ts, to_ts=to_ts)
    return compute_summary(filtered)


@router.get("/histogram")
async def stats_histogram(
    metric: str,
    bins: int = 10,
    domain: str | None = Query(default=None),
    device: str | None = Query(default=None),
    from_ts: str | None = Query(default=None, alias="from"),
    to_ts: str | None = Query(default=None, alias="to"),
    container: AppContainer = Depends(get_container),
) -> dict:
    try:
        metric_name = ensure_metric_allowed(metric, SUPPORTED_METRICS)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    reports = container.report_writer.list_reports()
    filtered = filter_reports(reports, domain=domain, device_id=device, from_ts=from_ts, to_ts=to_ts)
    return compute_histogram(filtered, metric=metric_name, bins=bins)


@router.get("/timeseries")
async def stats_timeseries(
    metric: str,
    domain: str | None = Query(default=None),
    device: str | None = Query(default=None),
    from_ts: str | None = Query(default=None, alias="from"),
    to_ts: str | None = Query(default=None, alias="to"),
    container: AppContainer = Depends(get_container),
) -> dict:
    try:
        metric_name = ensure_metric_allowed(metric, SUPPORTED_METRICS)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    reports = container.report_writer.list_reports()
    filtered = filter_reports(reports, domain=domain, device_id=device, from_ts=from_ts, to_ts=to_ts)
    return compute_timeseries(filtered, metric=metric_name)
