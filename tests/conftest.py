import subprocess
from pathlib import Path

import pytest


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


@pytest.fixture
def sample_video(tmp_path: Path) -> Path:
    """6 s: white 0-2, black 2-4, white 4-6; sine tone; cuts at 2 s and 4 s."""
    out = tmp_path / "sample.mp4"
    inputs = []
    for color in ("white", "black", "white"):
        inputs += ["-f", "lavfi", "-i", f"color=c={color}:s=320x568:r=30:d=2"]
    inputs += ["-f", "lavfi", "-i", "sine=frequency=440:duration=6"]
    _ffmpeg(
        *inputs,
        "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
        "-map", "[v]", "-map", "3:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(out),
    )
    return out


@pytest.fixture
def silent_video(tmp_path: Path) -> Path:
    """4 s of a single color, no audio track."""
    out = tmp_path / "silent.mp4"
    _ffmpeg(
        "-f", "lavfi", "-i", "color=c=gray:s=320x568:r=30:d=4",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out),
    )
    return out
