import subprocess
from pathlib import Path

import pytest

from maquina.qa import check_video


def _make(path: Path, vf: str, audio: bool = True, dur: float = 4.0, size="320x568"):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc2=s={size}:r=30:d={dur}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=300:duration={dur}", "-c:a", "aac", "-shortest"]
    cmd += ["-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(cmd, check=True)
    return path


def _status(report, name):
    return next(c["status"] for c in report["checks"] if c["name"] == name)


def test_good_video_passes_core_checks(tmp_path: Path):
    v = _make(tmp_path / "ok.mp4", "format=yuv420p")
    r = check_video(v, expected_duration=4.0, expected_size=(320, 568), expected_fps=30)
    for name in ("duracao", "formato", "audio", "telas_pretas"):
        assert _status(r, name) == "ok", r


def test_black_screen_is_detected(tmp_path: Path):
    v = _make(tmp_path / "black.mp4", "drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='between(t,1,2.5)'")
    r = check_video(v, expected_duration=4.0, expected_size=(320, 568), expected_fps=30)
    assert _status(r, "telas_pretas") == "falha"
    assert r["ok"] is False


def test_missing_audio_and_wrong_duration_fail(tmp_path: Path):
    v = _make(tmp_path / "mute.mp4", "format=yuv420p", audio=False)
    r = check_video(v, expected_duration=9.0, expected_size=(320, 568), expected_fps=30)
    assert _status(r, "audio") == "falha" and _status(r, "duracao") == "falha"


def test_wrong_resolution_fails(tmp_path: Path):
    v = _make(tmp_path / "small.mp4", "format=yuv420p")
    r = check_video(v, expected_duration=4.0, expected_size=(1080, 1920), expected_fps=30)
    assert _status(r, "formato") == "falha"
