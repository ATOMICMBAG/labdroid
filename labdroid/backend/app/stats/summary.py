from __future__ import annotations

from collections import Counter
from datetime import datetime

from app.models.report_models import InspectionReport


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def filter_reports(
    reports: list[InspectionReport],
    *,
    domain: str | None = None,
    device_id: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
) -> list[InspectionReport]:
    from_dt = _parse_timestamp(from_ts) if from_ts else None
    to_dt = _parse_timestamp(to_ts) if to_ts else None

    filtered: list[InspectionReport] = []
    for report in reports:
        if domain and report.domain != domain:
            continue
        if device_id and report.device_id != device_id:
            continue

        if from_dt or to_dt:
            try:
                ts = _parse_timestamp(report.timestamp)
            except ValueError:
                continue
            if from_dt and ts < from_dt:
                continue
            if to_dt and ts > to_dt:
                continue

        filtered.append(report)

    return filtered


def compute_summary(reports: list[InspectionReport]) -> dict:
    result_counter = Counter(r.result for r in reports)
    domain_counter = Counter(r.domain for r in reports)

    metrics_acc: dict[str, list[float]] = {}
    for report in reports:
        for key, value in report.metrics.items():
            metrics_acc.setdefault(key, []).append(float(value))

    metric_means = {
        metric: (sum(values) / len(values) if values else 0.0)
        for metric, values in metrics_acc.items()
    }

    return {
        "jobs_total": len(reports),
        "ok_total": result_counter.get("OK", 0),
        "nok_total": result_counter.get("NOK", 0),
        "by_domain": dict(domain_counter),
        "metrics_mean": metric_means,
    }
