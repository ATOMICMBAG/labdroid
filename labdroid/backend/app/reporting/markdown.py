from __future__ import annotations

from app.models.report_models import InspectionReport


def render_markdown(report: InspectionReport) -> str:
    lines: list[str] = []
    lines.append(f"# Inspection Report `{report.job_id}`")
    lines.append("")
    lines.append(f"- **Timestamp:** {report.timestamp}")
    lines.append(f"- **Domain:** {report.domain}")
    lines.append(f"- **Result:** {report.result}")
    lines.append(f"- **Confidence:** {report.confidence:.4f}")
    lines.append(f"- **Provider/Model:** {report.provider} / {report.model}")
    if report.device_id:
        lines.append(f"- **Device:** {report.device_id}")
    lines.append("")

    lines.append("## Metrics")
    lines.append("")
    if report.metrics:
        for key, value in sorted(report.metrics.items()):
            lines.append(f"- `{key}`: {value:.6f}")
    else:
        lines.append("- _(none)_")
    lines.append("")

    lines.append("## Checks")
    lines.append("")
    for check in report.checks:
        marker = "✅" if check.status == "pass" else "❌"
        critical = "critical" if check.critical else "non-critical"
        lines.append(f"- {marker} **{check.name}** (`{check.metric}`, {critical})")
        lines.append(f"  - Reason: {check.reason}")
        if check.actual is not None:
            lines.append(f"  - Actual: {check.actual:.6f}")
        if check.threshold_min is not None:
            lines.append(f"  - Min: {check.threshold_min:.6f}")
        if check.threshold_max is not None:
            lines.append(f"  - Max: {check.threshold_max:.6f}")
    if not report.checks:
        lines.append("- _(none)_")
    lines.append("")

    lines.append("## Explanation")
    lines.append("")
    lines.append(report.explanation or "No explanation generated.")
    lines.append("")

    lines.append("## Timings")
    lines.append("")
    if report.timings:
        for key, value in sorted(report.timings.items()):
            lines.append(f"- `{key}`: {value:.4f}s")
    else:
        lines.append("- _(none)_")
    lines.append("")

    lines.append("## Evidence")
    lines.append("")
    images = report.evidence_refs.get("images", [])
    audio = report.evidence_refs.get("audio", [])
    lines.append(f"- Images: {images if images else '[]'}")
    lines.append(f"- Audio: {audio if audio else '[]'}")
    lines.append("")

    return "\n".join(lines)
