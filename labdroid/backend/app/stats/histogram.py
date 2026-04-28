from __future__ import annotations

import numpy as np

from app.models.report_models import InspectionReport


def compute_histogram(reports: list[InspectionReport], metric: str, bins: int = 10) -> dict:
    values = np.array([float(r.metrics[metric]) for r in reports if metric in r.metrics], dtype=np.float64)
    if values.size == 0:
        return {
            "metric": metric,
            "bins": max(1, bins),
            "count": 0,
            "histogram": [],
        }

    counts, edges = np.histogram(values, bins=max(1, bins))
    rows = []
    for i, count in enumerate(counts):
        rows.append(
            {
                "start": float(edges[i]),
                "end": float(edges[i + 1]),
                "count": int(count),
            }
        )

    return {
        "metric": metric,
        "bins": int(len(counts)),
        "count": int(values.size),
        "min": float(values.min()),
        "max": float(values.max()),
        "mean": float(values.mean()),
        "histogram": rows,
    }
