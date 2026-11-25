from pathlib import Path

import pytest

from maquina.fetch import FetchError, fetch_video
from maquina.models import VideoRef


def test_local_path_returns_same_path(sample_video: Path, tmp_path: Path):
    out = fetch_video(VideoRef(path=str(sample_video)), tmp_path / "dl")
    assert out == sample_video


def test_missing_local_path_raises(tmp_path: Path):
    with pytest.raises(FetchError):
        fetch_video(VideoRef(path=str(tmp_path / "nao_existe.mp4")), tmp_path)


def test_invalid_tiktok_url_raises_readable_error(tmp_path: Path):
    ref = VideoRef(url="https://www.tiktok.com/@x/video/1")
    with pytest.raises(FetchError) as exc:
        fetch_video(ref, tmp_path, retries=2, backoff=0.1)
    assert str(exc.value).strip()
