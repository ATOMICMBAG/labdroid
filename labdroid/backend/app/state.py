from __future__ import annotations

from dataclasses import dataclass

from app.actuators.safety_layer import SafetyLayer
from app.baseline.manager import BaselineManager
from app.core.config import Settings
from app.core.rate_limit import WsRateLimiter
from app.plugins.loader import PluginManager
from app.processing.queue import JobService
from app.providers.registry import ProviderRegistry
from app.reporting.writer import ReportWriter


@dataclass
class AppContainer:
    settings: Settings
    providers: ProviderRegistry
    report_writer: ReportWriter
    jobs: JobService
    baseline_manager: BaselineManager
    plugin_manager: PluginManager
    safety_layer: SafetyLayer
    ws_rate_limiter: WsRateLimiter
