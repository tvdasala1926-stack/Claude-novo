from __future__ import annotations

import subprocess
from pathlib import Path

from maquina.models import Word
from maquina.probe import probe_video

_MODELS: dict[str, object] = {}


def _load_model(size: str):
    if size not in _MODELS:
        from faster_whisper import WhisperModel

        _MODELS[size] = WhisperModel(size, device="cpu", compute_type="int8")
    return _MODELS[size]


def _decode_audio(video: Path):
    """Mono 16 kHz float32 samples via ffmpeg (avoids faster-whisper's PyAV path)."""
    import numpy as np

    proc = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(video),
         "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise ValueError(f"falha ao extrair áudio de {video}: {proc.stderr.decode().strip()}")
    return np.frombuffer(proc.stdout, dtype=np.float32)


def transcribe(path: Path, model_size: str = "base", language: str = "pt") -> list[Word]:
    """Word-level transcription. Videos without an audio track return []."""
    path = Path(path)
    if not probe_video(path).has_audio:
        return []
    audio = _decode_audio(path)
    if audio.size == 0:
        return []
    segments, _ = _load_model(model_size).transcribe(
        audio, language=language, word_timestamps=True
    )
    return [
        Word(text=w.word.strip(), start=float(w.start), end=float(w.end))
        for seg in segments
        for w in (seg.words or [])
        if w.word.strip()
    ]
