from __future__ import annotations

import base64
import binascii
import io
import wave
from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass
class PreprocessedInput:
    image: np.ndarray | None
    audio: np.ndarray | None


def _decode_base64(data_b64: str | None) -> bytes | None:
    if not data_b64:
        return None
    try:
        return base64.b64decode(data_b64)
    except (binascii.Error, ValueError):
        return None


def decode_image(image_b64: str | None) -> np.ndarray | None:
    raw = _decode_base64(image_b64)
    if not raw:
        return None
    with Image.open(io.BytesIO(raw)) as img:
        rgb = img.convert("RGB")
        arr = np.asarray(rgb, dtype=np.float32) / 255.0
        return arr


def decode_audio(audio_b64: str | None) -> np.ndarray | None:
    raw = _decode_base64(audio_b64)
    if not raw:
        return None

    # Preferred path: WAV container.
    try:
        with wave.open(io.BytesIO(raw), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frames = wav_file.readframes(wav_file.getnframes())
            if sample_width != 2:
                return None
            samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            if channels > 1:
                samples = samples.reshape(-1, channels).mean(axis=1)
            return samples
    except wave.Error:
        # Fallback: raw int16 PCM buffer.
        if len(raw) % 2 != 0:
            return None
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return samples


def preprocess_inputs(image_b64: str | None, audio_b64: str | None) -> PreprocessedInput:
    return PreprocessedInput(image=decode_image(image_b64), audio=decode_audio(audio_b64))
