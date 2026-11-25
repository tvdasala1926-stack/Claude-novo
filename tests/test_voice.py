import subprocess
from pathlib import Path

import pytest

from maquina.voice import build_narration, export_mp3, list_voices, synthesize_line

VOICE = "pt_BR-faber-medium"


def test_list_voices_finds_installed_voice():
    assert VOICE in list_voices()


def test_synthesize_line_creates_audio(tmp_path: Path):
    dur = synthesize_line("Teclado mecânico.", tmp_path / "a.wav", VOICE)
    assert (tmp_path / "a.wav").is_file() and dur > 0.5


def test_higher_speed_is_shorter(tmp_path: Path):
    slow = synthesize_line("Esse teclado é mecânico de verdade.", tmp_path / "s.wav", VOICE, speed=1.0)
    fast = synthesize_line("Esse teclado é mecânico de verdade.", tmp_path / "f.wav", VOICE, speed=1.3)
    assert fast < slow * 0.9


def test_build_narration_timeline_includes_pauses(tmp_path: Path):
    lines = [{"spoken": "Primeira frase.", "pause_after": 0.4}, {"spoken": "Segunda frase.", "pause_after": 0.0}]
    wav, timeline = build_narration(lines, tmp_path, VOICE)
    assert len(timeline) == 2
    assert timeline[0]["start"] == 0.0
    assert timeline[1]["start"] == pytest.approx(timeline[0]["end"] + 0.4, abs=0.01)
    total = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)]))
    assert total == pytest.approx(timeline[1]["end"], abs=0.1)


def test_export_mp3(tmp_path: Path):
    wav, _ = build_narration([{"spoken": "Teste.", "pause_after": 0}], tmp_path, VOICE)
    mp3 = export_mp3(wav, tmp_path / "n.mp3")
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(mp3)])
    assert out.decode().strip() == "mp3"
