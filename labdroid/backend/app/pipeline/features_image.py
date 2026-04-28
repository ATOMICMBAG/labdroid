from __future__ import annotations

import numpy as np


def extract_image_features(image: np.ndarray | None) -> dict[str, float]:
    if image is None or image.size == 0:
        return {"brightness_mean": 0.0, "edge_density": 0.0}

    # Brightness (mean gray value, normalized to 0..1)
    gray = image.mean(axis=2)
    brightness_mean = float(np.clip(gray.mean(), 0.0, 1.0))

    # Edge density via simple gradient magnitude threshold
    gy, gx = np.gradient(gray)
    grad_mag = np.sqrt(gx * gx + gy * gy)
    edge_density = float((grad_mag > 0.08).mean())

    return {
        "brightness_mean": round(brightness_mean, 6),
        "edge_density": round(edge_density, 6),
    }
