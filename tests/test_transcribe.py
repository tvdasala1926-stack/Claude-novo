import shutil
import subprocess
import unicodedata
from pathlib import Path

import pytest

from maquina.transcribe import transcribe


def _plain(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn"
    ).strip(" .,!?")


def test_silent_video_returns_empty_list(silent_video: Path):
    assert transcribe(silent_video) == []


@pytest.mark.skipif(shutil.which("espeak-ng") is None, reason="espeak-ng ausente")
def test_portuguese_speech_gets_word_timestamps(tmp_path: Path):
    wav = tmp_path / "fala.wav"
    subprocess.run(
        ["espeak-ng", "-v", "pt-br", "-s", "130", "compre agora pelo link na bio", "-w", str(wav)],
        check=True,
    )
    video = tmp_path / "fala.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=gray:s=320x568:r=30",
         "-i", str(wav), "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
         str(video)],
        check=True,
    )
    words = transcribe(video)
    assert words, "nenhuma palavra transcrita"
    assert all(w.start < w.end for w in words)
    starts = [w.start for w in words]
    assert starts == sorted(starts)
    assert "link" in {_plain(w.text) for w in words}
