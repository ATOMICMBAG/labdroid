from __future__ import annotations

from app.core.config import Settings
from app.models.report_models import CheckResult


def _check_range(
    name: str,
    metric: str,
    value: float,
    minimum: float,
    maximum: float,
    critical: bool,
) -> CheckResult:
    if value < minimum:
        return CheckResult(
            name=name,
            metric=metric,
            status="fail",
            critical=critical,
            actual=value,
            threshold_min=minimum,
            threshold_max=maximum,
            reason=f"{metric} below minimum ({value:.4f} < {minimum:.4f})",
        )
    if value > maximum:
        return CheckResult(
            name=name,
            metric=metric,
            status="fail",
            critical=critical,
            actual=value,
            threshold_min=minimum,
            threshold_max=maximum,
            reason=f"{metric} above maximum ({value:.4f} > {maximum:.4f})",
        )
    return CheckResult(
        name=name,
        metric=metric,
        status="pass",
        critical=critical,
        actual=value,
        threshold_min=minimum,
        threshold_max=maximum,
        reason="within threshold",
    )


def _check_min(name: str, metric: str, value: float, minimum: float, critical: bool) -> CheckResult:
    if value < minimum:
        return CheckResult(
            name=name,
            metric=metric,
            status="fail",
            critical=critical,
            actual=value,
            threshold_min=minimum,
            reason=f"{metric} below minimum ({value:.4f} < {minimum:.4f})",
        )
    return CheckResult(
        name=name,
        metric=metric,
        status="pass",
        critical=critical,
        actual=value,
        threshold_min=minimum,
        reason="within threshold",
    )


def run_rules(
    *,
    settings: Settings,
    domain: str,
    metrics: dict[str, float],
    has_image: bool,
    has_audio: bool,
) -> list[CheckResult]:
    thresholds = settings.domain_thresholds.get(domain, settings.domain_thresholds["default"])
    checks: list[CheckResult] = []

    if has_image:
        checks.append(
            _check_range(
                "Image brightness range",
                "brightness_mean",
                metrics.get("brightness_mean", 0.0),
                thresholds["brightness_min"],
                thresholds["brightness_max"],
                critical=True,
            )
        )
        checks.append(
            _check_min(
                "Image edge density",
                "edge_density",
                metrics.get("edge_density", 0.0),
                thresholds["edge_density_min"],
                critical=True,
            )
        )
    else:
        checks.append(
            CheckResult(
                name="Image brightness range",
                metric="brightness_mean",
                status="pass",
                critical=False,
                actual=metrics.get("brightness_mean", 0.0),
                reason="no image provided; check skipped",
            )
        )
        checks.append(
            CheckResult(
                name="Image edge density",
                metric="edge_density",
                status="pass",
                critical=False,
                actual=metrics.get("edge_density", 0.0),
                reason="no image provided; check skipped",
            )
        )

    if has_audio:
        checks.append(
            _check_range(
                "Audio RMS range",
                "audio_rms",
                metrics.get("audio_rms", 0.0),
                thresholds["audio_rms_min"],
                thresholds["audio_rms_max"],
                critical=True,
            )
        )
    else:
        checks.append(
            CheckResult(
                name="Audio RMS range",
                metric="audio_rms",
                status="pass",
                critical=False,
                actual=metrics.get("audio_rms", 0.0),
                reason="no audio provided; check skipped",
            )
        )

    return checks
