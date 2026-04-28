from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.jobs import router as jobs_router
from app.api.reports import router as reports_router
from app.api.stats import router as stats_router
from app.api.ws import router as ws_router
from app.api.control import router as control_router
from app.actuators.safety_layer import SafetyLayer
from app.baseline.manager import BaselineManager
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.rate_limit import WsRateLimiter
from app.plugins.loader import PluginManager
from app.processing.queue import JobService
from app.providers.registry import ProviderRegistry
from app.reporting.writer import ReportWriter
from app.state import AppContainer


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    providers = ProviderRegistry(settings)
    writer = ReportWriter(settings)

    baseline_manager = BaselineManager(settings)
    plugin_manager = PluginManager(settings.plugin_dir)
    plugin_manager.load_plugins()
    safety_layer = SafetyLayer(settings)

    jobs = JobService(
        settings=settings,
        providers=providers,
        report_writer=writer,
        baseline_manager=baseline_manager,
        plugin_manager=plugin_manager,
    )
    jobs.start()

    app.state.container = AppContainer(
        settings=settings,
        providers=providers,
        report_writer=writer,
        jobs=jobs,
        baseline_manager=baseline_manager,
        plugin_manager=plugin_manager,
        safety_layer=safety_layer,
        ws_rate_limiter=WsRateLimiter(settings.ws_rate_limit_per_minute),
    )
    yield
    await jobs.stop()


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="Audio and Visio Labdroid Backend", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    app.include_router(ws_router)
    app.include_router(jobs_router)
    app.include_router(control_router)
    app.include_router(reports_router)
    app.include_router(stats_router)
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
