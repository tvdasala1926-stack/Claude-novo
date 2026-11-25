"""Automatic pre-delivery checks on a rendered video."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from maquina.probe import probe_video


def _ff(args: list[str]) -> str:
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args], capture_output=True, text=True).stderr


def _check(name: str, ok: bool, detail: str, warn: bool = False) -> dict:
    return {"name": name, "status": "ok" if ok else ("aviso" if warn else "falha"), "detail": detail}


def check_video(path: Path, expected_duration: float, expected_size: tuple[int, int],
                expected_fps: float = 30.0, expected_cuts: list[float] | None = None) -> dict:
    """Run all checks; returns {"ok": bool, "checks": [...]}. A 'falha' makes ok False."""
    path = Path(path)
    checks: list[dict] = []
    probe = probe_video(path)

    checks.append(_check("duracao", abs(probe.duration - expected_duration) <= 0.2,
                         f"{probe.duration:.2f}s (esperado {expected_duration:.2f}s)"))
    fmt_ok = (probe.width, probe.height) == tuple(expected_size) and abs(probe.fps - expected_fps) < 0.5
    checks.append(_check("formato", fmt_ok,
                         f"{probe.width}x{probe.height} @ {probe.fps:.1f}fps (esperado {expected_size[0]}x{expected_size[1]} @ {expected_fps:g})"))

    if not probe.has_audio:
        checks.append(_check("audio", False, "sem trilha de áudio"))
    else:
        err = _ff(["-i", str(path), "-af", "volumedetect", "-vn", "-f", "null", "-"])
        mean = re.search(r"mean_volume: (-?[\d.]+) dB", err)
        peak = re.search(r"max_volume: (-?[\d.]+) dB", err)
        m, pk = (float(mean.group(1)), float(peak.group(1))) if mean and peak else (-99.0, -99.0)
        checks.append(_check("audio", m > -40 and pk < -0.1, f"volume médio {m:.1f} dB, pico {pk:.1f} dB"))

    err = _ff(["-i", str(path), "-vf", "blackdetect=d=0.15:pix_th=0.12", "-an", "-f", "null", "-"])
    black = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)
    checks.append(_check("telas_pretas", not black,
                         "nenhuma" if not black else "; ".join(f"{a}s a {b}s" for a, b in black)))

    err = _ff(["-i", str(path), "-vf", "freezedetect=n=-60dB:d=1.2", "-an", "-f", "null", "-"])
    frozen = re.findall(r"freeze_start: ([\d.]+)", err)
    checks.append(_check("quadros_congelados", not frozen,
                         "nenhum" if not frozen else f"congelado a partir de {', '.join(frozen)}s", warn=True))

    if expected_cuts is not None:
        from maquina.scenes import detect_scenes

        found = detect_scenes(path, threshold=0.45)
        stray = [c for c in found if all(abs(c - e) > 0.35 for e in expected_cuts)]
        checks.append(_check("cortes_bruscos", not stray,
                             "só nas transições previstas" if not stray else f"cortes fora do previsto: {[round(c, 2) for c in stray]}",
                             warn=True))

    return {"ok": all(c["status"] != "falha" for c in checks), "checks": checks}


def check_caption_sync(audio: Path, caption_words, tolerance: float = 0.3) -> dict:
    """Re-transcribe the final audio and compare each caption word's start with what was heard."""
    import difflib

    from maquina.captions import _norm
    from maquina.transcribe import transcribe

    heard = transcribe(Path(audio))
    a = [_norm(w.text) for w in caption_words]
    b = [_norm(w.text) for w in heard]
    diffs = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            diffs += [abs(caption_words[i1 + k].start - heard[j1 + k].start) for k in range(i2 - i1)]
    if len(diffs) < max(3, len(a) // 3):
        return _check("sincronia_legendas", False, f"só {len(diffs)} de {len(a)} palavras conferidas", warn=True)
    mean = sum(diffs) / len(diffs)
    worst = max(diffs)
    return _check("sincronia_legendas", mean <= tolerance and worst <= tolerance * 3,
                  f"desvio médio {mean:.2f}s, pior {worst:.2f}s ({len(diffs)} palavras conferidas)")


def render_report(title: str, results: dict) -> str:
    lines = [f"# Relatório de conferência — {title}", "",
             f"Resultado: **{'APROVADO' if results['ok'] else 'REPROVADO'}**", "",
             "| Verificação | Status | Detalhe |", "|---|---|---|"]
    lines += [f"| {c['name']} | {c['status']} | {c['detail']} |" for c in results["checks"]]
    return "\n".join(lines) + "\n"
