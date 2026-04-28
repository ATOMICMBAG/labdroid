from __future__ import annotations

import base64
import binascii
import json
from pathlib import Path

from app.core.config import Settings
from app.core.security import safe_join, sanitize_job_id
from app.models.report_models import InspectionReport
from app.reporting.markdown import render_markdown


class ReportWriter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.reports_dir.mkdir(parents=True, exist_ok=True)
        self.settings.evidence_dir.mkdir(parents=True, exist_ok=True)

    def _report_json_path(self, job_id: str) -> Path:
        safe_id = sanitize_job_id(job_id)
        return safe_join(self.settings.reports_dir, f"{safe_id}.json")

    def _report_md_path(self, job_id: str) -> Path:
        safe_id = sanitize_job_id(job_id)
        return safe_join(self.settings.reports_dir, f"{safe_id}.md")

    def _decode_b64(self, payload: str | None) -> bytes | None:
        if not payload:
            return None
        try:
            return base64.b64decode(payload)
        except (binascii.Error, ValueError):
            return None

    def _to_reference(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.settings.base_dir))
        except ValueError:
            return str(path)

    def save_evidence(self, *, job_id: str, image_b64: str | None, audio_b64: str | None) -> dict[str, list[str]]:
        refs: dict[str, list[str]] = {"images": [], "audio": []}
        evidence_root = safe_join(self.settings.evidence_dir, sanitize_job_id(job_id))
        evidence_root.mkdir(parents=True, exist_ok=True)

        image_raw = self._decode_b64(image_b64)
        if image_raw:
            image_path = safe_join(evidence_root, "image_001.jpg")
            image_path.write_bytes(image_raw)
            refs["images"].append(self._to_reference(image_path))

        audio_raw = self._decode_b64(audio_b64)
        if audio_raw:
            audio_path = safe_join(evidence_root, "audio_001.wav")
            audio_path.write_bytes(audio_raw)
            refs["audio"].append(self._to_reference(audio_path))

        return refs

    def save_report(
        self,
        report: InspectionReport,
        *,
        image_b64: str | None = None,
        audio_b64: str | None = None,
    ) -> dict[str, str]:
        report.evidence_refs = self.save_evidence(job_id=report.job_id, image_b64=image_b64, audio_b64=audio_b64)

        report_json_path = self._report_json_path(report.job_id)
        report_md_path = self._report_md_path(report.job_id)

        report_json_path.write_text(
            json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        report_md_path.write_text(render_markdown(report), encoding="utf-8")

        return {
            "json": str(report_json_path),
            "markdown": str(report_md_path),
        }

    def load_report(self, job_id: str) -> InspectionReport:
        path = self._report_json_path(job_id)
        if not path.exists():
            raise FileNotFoundError(f"report '{job_id}' not found")
        return InspectionReport.model_validate_json(path.read_text(encoding="utf-8"))

    def load_markdown(self, job_id: str) -> str:
        path = self._report_md_path(job_id)
        if not path.exists():
            raise FileNotFoundError(f"report markdown '{job_id}' not found")
        return path.read_text(encoding="utf-8")

    def list_reports(self) -> list[InspectionReport]:
        reports: list[InspectionReport] = []
        for path in sorted(self.settings.reports_dir.glob("*.json")):
            try:
                reports.append(InspectionReport.model_validate_json(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return reports
