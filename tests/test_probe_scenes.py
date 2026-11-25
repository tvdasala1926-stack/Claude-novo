from pathlib import Path

import pytest

from maquina.probe import probe_video
from maquina.scenes import detect_scenes


def test_probe_sample_video(sample_video: Path):
    p = probe_video(sample_video)
    assert p.duration == pytest.approx(6.0, abs=0.2)
    assert p.has_audio is True
    assert (p.width, p.height) == (320, 568)
    assert p.fps == pytest.approx(30.0, abs=0.5)


def test_probe_silent_video_has_no_audio(silent_video: Path):
    assert probe_video(silent_video).has_audio is False


def test_probe_missing_file_raises_value_error(tmp_path: Path):
    with pytest.raises(ValueError):
        probe_video(tmp_path / "nada.mp4")


def test_detect_scenes_finds_two_cuts(sample_video: Path):
    cuts = detect_scenes(sample_video)
    assert len(cuts) == 2
    assert cuts[0] == pytest.approx(2.0, abs=0.2)
    assert cuts[1] == pytest.approx(4.0, abs=0.2)


def test_detect_scenes_single_shot_is_empty(silent_video: Path):
    assert detect_scenes(silent_video) == []
