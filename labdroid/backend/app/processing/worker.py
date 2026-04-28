from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter

from app.baseline.manager import BaselineManager
from app.core.config import Settings
from app.models.report_models import InspectionReport
from app.models.schemas import JobRequest
from app.plugins.loader import PluginManager
from app.pipeline.decision import decide
from app.pipeline.explain import build_explanation_prompt, fallback_explanation
from app.pipeline.features_audio import extract_audio_features
from app.pipeline.features_image import extract_image_features
from app.pipeline.preprocess import preprocess_inputs
from app.pipeline.rule_engine import run_rules
from app.processing.timeout import run_with_timeout
from app.providers.registry import ProviderRegistry
from app.reporting.writer import ReportWriter


async def process_inspection_job(
    *,
    settings: Settings,
    providers: ProviderRegistry,
    report_writer: ReportWriter,
    baseline_manager: BaselineManager,
    plugin_manager: PluginManager,
    request: JobRequest,
) -> dict:
    t_job_start = perf_counter()
    timings: dict[str, float] = {}

    t0 = perf_counter()
    prepared = preprocess_inputs(request.image_b64, request.audio_b64)
    timings["preprocess_s"] = round(perf_counter() - t0, 4)

    metrics: dict[str, float] = {}

    t0 = perf_counter()
    metrics.update(extract_image_features(prepared.image))
    metrics.update(extract_audio_features(prepared.audio))
    timings["feature_extraction_s"] = round(perf_counter() - t0, 4)

    t0 = perf_counter()
    checks = run_rules(
        settings=settings,
        domain=request.domain,
        metrics=metrics,
        has_image=prepared.image is not None,
        has_audio=prepared.audio is not None,
    )
    timings["rule_engine_s"] = round(perf_counter() - t0, 4)

    t0 = perf_counter()
    if request.update_baseline:
        baseline_manager.append_metrics(domain=request.domain, device_id=request.device_id, metrics=metrics)
    timings["baseline_update_s"] = round(perf_counter() - t0, 4)

    t0 = perf_counter()
    anomalies = baseline_manager.detect_anomalies(
        domain=request.domain,
        device_id=request.device_id,
        metrics=metrics,
    )
    timings["anomaly_detection_s"] = round(perf_counter() - t0, 4)

    t0 = perf_counter()
    plugin_results = plugin_manager.run_all(
        {
            "domain": request.domain,
            "device_id": request.device_id,
            "metrics": metrics,
            "checks": [c.model_dump(mode="json") for c in checks],
            "text": request.text,
            "metadata": request.metadata,
        }
    )
    timings["plugins_s"] = round(perf_counter() - t0, 4)

    t0 = perf_counter()
    result, confidence = decide(checks)
    timings["decision_s"] = round(perf_counter() - t0, 4)

    t0 = perf_counter()
    prompt = build_explanation_prompt(domain=request.domain, result=result, checks=checks, metrics=metrics)
    timings["prompt_build_s"] = round(perf_counter() - t0, 4)

    provider_info = providers.current()
    provider_name = request.provider or str(provider_info["provider"])
    model_name = request.model or str(provider_info["model"])
    explanation = fallback_explanation(domain=request.domain, result=result, checks=checks)

    t0 = perf_counter()
    try:
        llm_output = await run_with_timeout(
            providers.generate(
                {
                    "prompt": prompt,
                    "text": request.text,
                    "domain": request.domain,
                    "metrics": metrics,
                    "result": result,
                },
                provider=request.provider,
                model=request.model,
            ),
            timeout_s=settings.model_timeout_s,
            message="model inference timeout",
        )
        provider_name = str(llm_output.get("provider", provider_name))
        model_name = str(llm_output.get("model", model_name))
        explanation = str(llm_output.get("text") or explanation)
    except Exception:
        # Deterministic decision/report still completes without provider response.
        pass
    timings["provider_generate_s"] = round(perf_counter() - t0, 4)

    job_id = request.job_id or "job"
    report = InspectionReport(
        job_id=job_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        domain=request.domain,
        device_id=request.device_id,
        provider=provider_name,
        model=model_name,
        result=result,
        confidence=confidence,
        metrics=metrics,
        checks=checks,
        anomalies=anomalies,
        plugin_results=plugin_results,
        timings=timings,
        explanation=explanation,
        metadata=request.metadata,
    )

    timings["total_s"] = round(perf_counter() - t_job_start, 4)
    report.timings = timings

    paths = report_writer.save_report(report, image_b64=request.image_b64, audio_b64=request.audio_b64)

    return {
        "job_id": report.job_id,
        "status": "done",
        "result": report.result,
        "confidence": report.confidence,
        "timings": timings,
        "report": report.model_dump(mode="json"),
        "paths": paths,
    }
