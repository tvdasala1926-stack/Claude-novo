from __future__ import annotations

import subprocess
import wave
from pathlib import Path

VOICES_DIR = Path(__file__).resolve().parent.parent / "assets" / "voices"
_CACHE: dict[str, object] = {}


def list_voices() -> list[str]:
    return sorted(p.name.removesuffix(".onnx") for p in VOICES_DIR.glob("*.onnx"))


def _load(voice: str):
    if voice not in _CACHE:
        from piper import PiperVoice

        model = VOICES_DIR / f"{voice}.onnx"
        if not model.is_file():
            raise ValueError(f"voz não instalada: {voice} (instaladas: {list_voices()})")
        _CACHE[voice] = PiperVoice.load(str(model))
    return _CACHE[voice]


def synthesize_line(text: str, out_wav: Path, voice: str, speed: float = 1.0) -> float:
    """Synthesize `text` to a WAV file; returns duration in seconds. speed>1 is faster."""
    from piper import SynthesisConfig

    cfg = SynthesisConfig(length_scale=1.0 / speed)
    with wave.open(str(out_wav), "wb") as w:
        _load(voice).synthesize_wav(text, w, syn_config=cfg)
    with wave.open(str(out_wav), "rb") as r:
        return r.getnframes() / r.getframerate()


def build_narration(
    lines: list[dict], out_dir: Path, voice: str, speed: float = 1.0
) -> tuple[Path, list[dict]]:
    """Synthesize each line, join with silences. Returns (wav, [{start,end}, ...])."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timeline: list[dict] = []
    frames: list[bytes] = []
    params = None
    cursor = 0.0
    for i, line in enumerate(lines):
        part = out_dir / f"line_{i:02d}.wav"
        dur = synthesize_line(line["spoken"], part, voice, speed)
        with wave.open(str(part), "rb") as r:
            params = params or r.getparams()
            frames.append(r.readframes(r.getnframes()))
        timeline.append({"start": round(cursor, 3), "end": round(cursor + dur, 3)})
        cursor += dur
        pause = float(line.get("pause_after", 0.0))
        if pause > 0:
            frames.append(b"\x00" * int(params.framerate * pause) * params.sampwidth * params.nchannels)
            cursor += pause
    wav_path = out_dir / "narration.wav"
    with wave.open(str(wav_path), "wb") as w:
        w.setparams(params)
        for f in frames:
            w.writeframes(f)
    return wav_path, timeline


def export_mp3(wav: Path, mp3: Path) -> Path:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                    "-codec:a", "libmp3lame", "-q:a", "2", str(mp3)], check=True)
    return Path(mp3)
