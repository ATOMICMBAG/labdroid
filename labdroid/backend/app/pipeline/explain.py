from __future__ import annotations

from app.models.report_models import CheckResult


def build_explanation_prompt(*, domain: str, result: str, checks: list[CheckResult], metrics: dict[str, float]) -> str:
    failed = [c for c in checks if c.status == "fail"]
    failed_text = "; ".join(f"{c.name}: {c.reason}" for c in failed) if failed else "No failing checks"
    return (
        f"Create a concise inspection summary for domain '{domain}'. "
        f"Result: {result}. Failing checks: {failed_text}. "
        f"Metrics: {metrics}. Keep it factual and short."
    )


def fallback_explanation(*, domain: str, result: str, checks: list[CheckResult]) -> str:
    failed = [c for c in checks if c.status == "fail"]
    if failed:
        reasons = "; ".join(f"{c.metric}: {c.reason}" for c in failed)
        return f"Inspection in domain '{domain}' finished with {result}. Key findings: {reasons}."
    return f"Inspection in domain '{domain}' finished with {result}. All critical checks passed."
