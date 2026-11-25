from __future__ import annotations

import re
import subprocess
from pathlib import Path


def detect_scenes(path: Path, threshold: float = 0.3) -> list[float]:
    """Timestamps (s) of scene cuts, via ffmpeg scene-change score."""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"arquivo não encontrado: {path}")
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path),
         "-vf", f"select='gt(scene,{threshold})',showinfo",
         "-an", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise ValueError(f"ffmpeg falhou para {path}: {proc.stderr.strip()[-200:]}")
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", proc.stderr)]
