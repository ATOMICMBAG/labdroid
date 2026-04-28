from __future__ import annotations

import re
from pathlib import Path


_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def sanitize_job_id(value: str) -> str:
    sanitized = _SAFE_ID_RE.sub("_", value).strip("._-")
    return sanitized or "job"


def safe_join(base_dir: Path, *parts: str) -> Path:
    target = (base_dir / Path(*parts)).resolve()
    base_resolved = base_dir.resolve()
    try:
        target.relative_to(base_resolved)
    except ValueError:
        raise ValueError("unsafe path: potential path traversal")
    return target


def ensure_provider_allowed(provider: str, allowlist: set[str]) -> str:
    normalized = provider.strip().lower()
    if normalized not in allowlist:
        raise ValueError(f"provider '{provider}' is not allowed")
    return normalized


def ensure_metric_allowed(metric: str, allowed_metrics: set[str]) -> str:
    normalized = metric.strip().lower()
    if normalized not in allowed_metrics:
        raise ValueError(f"metric '{metric}' is not supported")
    return normalized
