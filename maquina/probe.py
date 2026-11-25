from __future__ import annotations

import json
import subprocess
from pathlib import Path

from maquina.models import VideoProbe


def _fraction(text: str) -> float:
    num, _, den = text.partition("/")
    try:
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def probe_video(path: Path) -> VideoProbe:
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"arquivo não encontrado: {path}")
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise ValueError(f"ffprobe falhou para {path}: {proc.stderr.strip()}")
    info = json.loads(proc.stdout)
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    if video is None:
        raise ValueError(f"sem trilha de vídeo: {path}")
    duration = float(info["format"].get("duration") or video.get("duration") or 0)
    return VideoProbe(
        duration=duration,
        width=int(video["width"]),
        height=int(video["height"]),
        fps=_fraction(video.get("avg_frame_rate", "0/1")),
        has_audio=any(s["codec_type"] == "audio" for s in info["streams"]),
    )


def has_audio(path: Path) -> bool:
    """True if the file has an audio stream (works for audio-only files too)."""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"arquivo não encontrado: {path}")
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise ValueError(f"ffprobe falhou para {path}: {proc.stderr.strip()}")
    return bool(proc.stdout.strip())
