from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    data_dir: Path
    reports_dir: Path
    evidence_dir: Path
    default_provider: str
    provider_allowlist: set[str]
    model_timeout_s: float
    tts_timeout_s: float
    ws_rate_limit_per_minute: int
    ollama_base_url: str
    ollama_default_model: str
    openrouter_base_url: str
    openrouter_api_key: str | None
    openrouter_default_model: str
    baseline_file: Path
    baseline_min_samples: int
    plugin_dir: Path
    actuator_simulation_default: bool
    actuator_cooldown_s: float
    actuator_http_allowlist: set[str]
    actuator_request_timeout_s: float
    mqtt_enabled: bool
    mqtt_broker: str
    mqtt_topic_prefix: str
    audit_log_file: Path
    domain_thresholds: dict[str, dict[str, float]]


def _resolve_dir(env_name: str, fallback: Path) -> Path:
    raw = os.getenv(env_name)
    if raw:
        return Path(raw).expanduser().resolve()
    return fallback.resolve()


def get_settings() -> Settings:
    base_dir = _resolve_dir("LABDROID_BASE_DIR", Path.cwd())
    data_dir = _resolve_dir("LABDROID_DATA_DIR", base_dir / "data")
    reports_dir = _resolve_dir("LABDROID_REPORTS_DIR", base_dir / "reports")
    evidence_dir = _resolve_dir("LABDROID_EVIDENCE_DIR", base_dir / "evidence")
    plugin_dir = _resolve_dir("LABDROID_PLUGIN_DIR", base_dir / "plugins")
    baseline_file = _resolve_dir("LABDROID_BASELINE_FILE", data_dir / "baselines.json")
    audit_log_file = _resolve_dir("LABDROID_AUDIT_LOG_FILE", reports_dir / "actuator_audit.log")

    allowlist_raw = os.getenv("LABDROID_PROVIDER_ALLOWLIST", "litert,ollama,openrouter")
    provider_allowlist = {item.strip().lower() for item in allowlist_raw.split(",") if item.strip()}

    actuator_allowlist_raw = os.getenv(
        "LABDROID_ACTUATOR_HTTP_ALLOWLIST",
        "localhost,127.0.0.1",
    )
    actuator_http_allowlist = {
        item.strip().lower() for item in actuator_allowlist_raw.split(",") if item.strip()
    }

    return Settings(
        base_dir=base_dir,
        data_dir=data_dir,
        reports_dir=reports_dir,
        evidence_dir=evidence_dir,
        default_provider=os.getenv("LABDROID_DEFAULT_PROVIDER", "litert").strip().lower(),
        provider_allowlist=provider_allowlist,
        model_timeout_s=float(os.getenv("LABDROID_MODEL_TIMEOUT_S", "20")),
        tts_timeout_s=float(os.getenv("LABDROID_TTS_TIMEOUT_S", "10")),
        ws_rate_limit_per_minute=int(os.getenv("LABDROID_WS_RATE_LIMIT_PER_MINUTE", "120")),
        ollama_base_url=os.getenv("LABDROID_OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        ollama_default_model=os.getenv("LABDROID_OLLAMA_DEFAULT_MODEL", "llama3.1:8b"),
        openrouter_base_url=os.getenv("LABDROID_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/"),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        openrouter_default_model=os.getenv("LABDROID_OPENROUTER_DEFAULT_MODEL", "openai/gpt-4o-mini"),
        baseline_file=baseline_file,
        baseline_min_samples=int(os.getenv("LABDROID_BASELINE_MIN_SAMPLES", "10")),
        plugin_dir=plugin_dir,
        actuator_simulation_default=os.getenv("LABDROID_ACTUATOR_SIMULATION_DEFAULT", "true").strip().lower()
        in {"1", "true", "yes", "on"},
        actuator_cooldown_s=float(os.getenv("LABDROID_ACTUATOR_COOLDOWN_S", "5")),
        actuator_http_allowlist=actuator_http_allowlist,
        actuator_request_timeout_s=float(os.getenv("LABDROID_ACTUATOR_REQUEST_TIMEOUT_S", "5")),
        mqtt_enabled=os.getenv("LABDROID_MQTT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"},
        mqtt_broker=os.getenv("LABDROID_MQTT_BROKER", "localhost"),
        mqtt_topic_prefix=os.getenv("LABDROID_MQTT_TOPIC_PREFIX", "labdroid"),
        audit_log_file=audit_log_file,
        domain_thresholds={
            "default": {
                "brightness_min": 0.10,
                "brightness_max": 0.95,
                "edge_density_min": 0.01,
                "audio_rms_min": 0.005,
                "audio_rms_max": 0.85,
            },
            "pcb": {
                "brightness_min": 0.15,
                "brightness_max": 0.90,
                "edge_density_min": 0.03,
                "audio_rms_min": 0.005,
                "audio_rms_max": 0.75,
            },
            "motor": {
                "brightness_min": 0.08,
                "brightness_max": 0.98,
                "edge_density_min": 0.005,
                "audio_rms_min": 0.02,
                "audio_rms_max": 0.65,
            },
            "wafer": {
                "brightness_min": 0.20,
                "brightness_max": 0.92,
                "edge_density_min": 0.02,
                "audio_rms_min": 0.003,
                "audio_rms_max": 0.70,
            },
        },
    )
