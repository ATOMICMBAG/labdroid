from __future__ import annotations

import numpy as np


def extract_audio_features(audio: np.ndarray | None) -> dict[str, float]:
    if audio is None or audio.size == 0:
        return {"audio_rms": 0.0}

    rms = float(np.sqrt(np.mean(np.square(audio))))
    return {"audio_rms": round(max(rms, 0.0), 6)}
