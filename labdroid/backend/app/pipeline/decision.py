from __future__ import annotations

from app.models.report_models import CheckResult


def decide(checks: list[CheckResult]) -> tuple[str, float]:
    """Return deterministic result and confidence from check results."""
    critical_checks = [c for c in checks if c.critical]
    if not critical_checks:
        return "OK", 1.0

    failed_critical = [c for c in critical_checks if c.status == "fail"]
    result = "NOK" if failed_critical else "OK"

    pass_ratio = 1.0 - (len(failed_critical) / len(critical_checks))
    confidence = max(0.0, min(1.0, pass_ratio))
    return result, round(confidence, 4)
