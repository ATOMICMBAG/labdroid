from __future__ import annotations

from datetime import datetime

from app.models.report_models import InspectionReport


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def compute_timeseries(reports: list[InspectionReport], metric: str) -> dict:
    rows: list[dict] = []
    for report in reports:
        if metric not in report.metrics:
            continue
        ts = _parse_timestamp(report.timestamp)
        if ts is None:
            continue
        rows.append(
            {
                "timestamp": ts.isoformat(),
                "job_id": report.job_id,
                "domain": report.domain,
                "device_id": report.device_id,
                "value": float(report.metrics[metric]),
            }
        )

    rows.sort(key=lambda item: item["timestamp"])
    return {"metric": metric, "count": len(rows), "points": rows}
