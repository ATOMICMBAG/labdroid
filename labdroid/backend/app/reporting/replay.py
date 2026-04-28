from __future__ import annotations

from app.models.report_models import InspectionReport
from app.reporting.writer import ReportWriter


def replay_report(writer: ReportWriter, job_id: str) -> InspectionReport:
    return writer.load_report(job_id)
