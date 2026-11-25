from __future__ import annotations

import time
from pathlib import Path

from maquina.models import VideoRef


class FetchError(Exception):
    """Video could not be obtained; message explains why."""


def fetch_video(
    ref: VideoRef, out_dir: Path, *, retries: int = 3, backoff: float = 2.0
) -> Path:
    if ref.path:
        p = Path(ref.path)
        if not p.is_file():
            raise FetchError(f"arquivo não encontrado: {ref.path}")
        return p
    if not ref.url:
        raise FetchError("referência sem url nem caminho")

    import yt_dlp  # imported lazily: heavy and only needed for URLs

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "format": "mp4/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(ref.url, download=True)
                path = Path(ydl.prepare_filename(info))
            if path.is_file():
                return path
            last = FileNotFoundError(f"download não gerou arquivo: {path}")
        except Exception as e:  # yt-dlp raises many types
            last = e
        if attempt < retries - 1:
            time.sleep(backoff * (attempt + 1))
    msg = str(last).replace("\x1b[0;31mERROR:\x1b[0m", "").strip() or type(last).__name__
    raise FetchError(f"falha ao baixar {ref.url}: {msg}")
