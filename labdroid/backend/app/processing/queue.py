from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.baseline.manager import BaselineManager
from app.core.config import Settings
from app.plugins.loader import PluginManager
from app.core.security import sanitize_job_id
from app.models.schemas import JobRequest
from app.processing.worker import process_inspection_job
from app.providers.registry import ProviderRegistry
from app.reporting.writer import ReportWriter


@dataclass
class JobEnvelope:
    request: JobRequest
    future: asyncio.Future


class JobService:
    def __init__(
        self,
        *,
        settings: Settings,
        providers: ProviderRegistry,
        report_writer: ReportWriter,
        baseline_manager: BaselineManager,
        plugin_manager: PluginManager,
    ) -> None:
        self.settings = settings
        self.providers = providers
        self.report_writer = report_writer
        self.baseline_manager = baseline_manager
        self.plugin_manager = plugin_manager
        self._queue: asyncio.Queue[JobEnvelope] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    def start(self) -> None:
        if self._worker_task and not self._worker_task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        self._worker_task = loop.create_task(self._worker_loop(), name="labdroid-job-worker")

    async def stop(self) -> None:
        if not self._worker_task:
            return
        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass

    async def submit(self, request: JobRequest) -> dict:
        if self._worker_task is None or self._worker_task.done():
            self.start()
        if not request.job_id:
            request.job_id = sanitize_job_id(f"{request.domain}-{asyncio.get_running_loop().time():.6f}")
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        await self._queue.put(JobEnvelope(request=request, future=future))
        return await future

    async def _worker_loop(self) -> None:
        while True:
            envelope = await self._queue.get()
            try:
                result = await process_inspection_job(
                    settings=self.settings,
                    providers=self.providers,
                    report_writer=self.report_writer,
                    baseline_manager=self.baseline_manager,
                    plugin_manager=self.plugin_manager,
                    request=envelope.request,
                )
                if not envelope.future.done():
                    envelope.future.set_result(result)
            except Exception as exc:  # noqa: BLE001
                if not envelope.future.done():
                    envelope.future.set_exception(exc)
            finally:
                self._queue.task_done()
