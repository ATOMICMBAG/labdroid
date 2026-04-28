from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.core.config import Settings


def _series_key(domain: str, device_id: str | None) -> str:
    return f"{domain}::{device_id or 'any'}"


@dataclass
class BaselineManager:
    settings: Settings

    def __post_init__(self) -> None:
        self.settings.baseline_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_store(self) -> dict:
        path = self.settings.baseline_file
        if not path.exists():
            return {"series": {}}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"series": {}}

    def _save_store(self, store: dict) -> None:
        self.settings.baseline_file.write_text(
            json.dumps(store, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def append_metrics(self, *, domain: str, device_id: str | None, metrics: dict[str, float]) -> dict:
        store = self._load_store()
        series = store.setdefault("series", {})
        key = _series_key(domain, device_id)
        bucket = series.setdefault(key, {"domain": domain, "device_id": device_id, "values": {}})

        for metric, value in metrics.items():
            arr = bucket.setdefault("values", {}).setdefault(metric, [])
            arr.append(float(value))
            if len(arr) > 2000:
                del arr[:-2000]

        self._save_store(store)
        return bucket

    def compute_baseline_stats(self, *, domain: str, device_id: str | None) -> dict[str, dict[str, float]]:
        store = self._load_store()
        series = store.get("series", {})
        key = _series_key(domain, device_id)
        bucket = series.get(key)
        if not bucket:
            return {}

        output: dict[str, dict[str, float]] = {}
        for metric, values in bucket.get("values", {}).items():
            if not values:
                continue
            arr = np.asarray(values, dtype=np.float64)
            output[metric] = {
                "count": float(arr.size),
                "mean": float(arr.mean()),
                "std": float(arr.std(ddof=0)),
                "min": float(arr.min()),
                "max": float(arr.max()),
            }
        return output

    def detect_anomalies(
        self,
        *,
        domain: str,
        device_id: str | None,
        metrics: dict[str, float],
    ) -> dict[str, dict[str, float | bool]]:
        baseline = self.compute_baseline_stats(domain=domain, device_id=device_id)
        anomalies: dict[str, dict[str, float | bool]] = {}

        for metric, actual in metrics.items():
            b = baseline.get(metric)
            if not b or b["count"] < self.settings.baseline_min_samples:
                anomalies[metric] = {
                    "enough_data": False,
                    "is_anomaly": False,
                    "actual": float(actual),
                    "mean": float(b["mean"]) if b else 0.0,
                    "std": float(b["std"]) if b else 0.0,
                    "z_score": 0.0,
                }
                continue

            std = max(float(b["std"]), 1e-9)
            mean = float(b["mean"])
            z = (float(actual) - mean) / std
            anomalies[metric] = {
                "enough_data": True,
                "is_anomaly": abs(z) > 2.0,
                "actual": float(actual),
                "mean": mean,
                "std": std,
                "z_score": float(z),
            }

        return anomalies

    def reset(self, *, domain: str, device_id: str | None) -> None:
        store = self._load_store()
        key = _series_key(domain, device_id)
        series = store.setdefault("series", {})
        if key in series:
            del series[key]
            self._save_store(store)

    def export_all(self) -> dict:
        return self._load_store()
