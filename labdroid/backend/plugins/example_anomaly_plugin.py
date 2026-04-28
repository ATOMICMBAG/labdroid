from __future__ import annotations

from app.plugins.base import InspectionPlugin


class HighRmsHintPlugin(InspectionPlugin):
    name = "high-rms-hint"

    def run(self, input_data: dict) -> dict:
        metrics = input_data.get("metrics", {})
        audio_rms = float(metrics.get("audio_rms", 0.0))
        hint = "normal"
        if audio_rms > 0.5:
            hint = "high_noise_or_possible_mechanical_issue"
        return {
            "audio_rms": audio_rms,
            "hint": hint,
        }
