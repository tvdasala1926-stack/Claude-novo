import re
import subprocess
from pathlib import Path

import pytest

from maquina.sfx import KINDS, make_sfx, music_bed, place_sfx


def _dur(p: Path) -> float:
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))


def _mean_db(p: Path) -> float:
    err = subprocess.run(["ffmpeg", "-i", str(p), "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.search(r"mean_volume: (-?[\d.]+) dB", err).group(1))


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_each_sfx_kind_is_audible(kind, tmp_path: Path):
    p = make_sfx(kind, tmp_path / f"{kind}.wav")
    assert p.is_file() and 0.05 < _dur(p) < 2.0
    assert _mean_db(p) > -60


def test_unknown_sfx_kind_raises(tmp_path: Path):
    with pytest.raises(ValueError):
        make_sfx("explosao_nuclear", tmp_path / "x.wav")


def test_music_bed_has_requested_duration_and_sound(tmp_path: Path):
    p = music_bed(tmp_path / "m.wav", duration=6.0)
    assert _dur(p) == pytest.approx(6.0, abs=0.1) and _mean_db(p) > -50


def test_place_sfx_builds_track_of_total_length(tmp_path: Path):
    track = place_sfx([{"t": 0.5, "kind": "whoosh"}, {"t": 2.0, "kind": "ding", "gain": 0.8}],
                      total=4.0, out=tmp_path / "sfx.wav", work_dir=tmp_path)
    assert _dur(track) == pytest.approx(4.0, abs=0.1) and _mean_db(track) > -60
