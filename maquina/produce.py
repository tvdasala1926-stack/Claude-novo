"""End-to-end video production: voice -> timeline -> captions -> audio mix -> 3D render -> assemble -> QA."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from maquina.captions import _norm, time_words, to_ass, to_srt
from maquina.models import Word
from maquina.qa import check_caption_sync, check_video, render_report
from maquina.sfx import music_bed, place_sfx
from maquina.transcribe import transcribe
from maquina.voice import build_narration, export_mp3

ROOT = Path(__file__).resolve().parent.parent
FORMATS = {"9x16": (1080, 1920), "16x9": (1920, 1080), "1x1": (1080, 1080)}
TAIL = 0.7  # seconds of closing after the last word


def _run(cmd: list[str], **kw) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} falhou: {proc.stderr.strip()[-600:]}")


def prepare(project: dict, work: Path) -> dict:
    """Voice, caption timing, scene timeline and sfx events (all format-independent)."""
    work.mkdir(parents=True, exist_ok=True)
    lines = project["lines"]
    wav, line_times = build_narration(lines, work / "voice", project["voice"], project.get("speed", 1.0))
    export_mp3(wav, work / "narracao.mp3")
    heard = transcribe(wav)  # real word timings of the synthesized narration

    words: list[Word] = []
    per_line: list[list[Word]] = []
    for line, win in zip(lines, line_times):
        in_win = [w for w in heard if win["start"] - 0.05 <= w.start <= win["end"] + 0.05]
        timed = time_words(line["display"].split(), line["spoken"].split(), in_win, (win["start"], win["end"]))
        per_line.append(timed)
        words += timed

    total = line_times[-1]["end"] + TAIL
    scenes = []
    for i, (line, win) in enumerate(zip(lines, line_times)):
        start = 0.0 if i == 0 else line_times[i - 1]["end"] + lines[i - 1].get("pause_after", 0) / 2
        end = total if i == len(lines) - 1 else win["end"] + line.get("pause_after", 0) / 2
        scenes.append({"id": line["scene"], "start": round(start, 3), "end": round(end, 3),
                       "data": project["scene_data"].get(line["scene"], {})})

    cues = []
    for cue in project.get("cues", []):
        idx = next(i for i, l in enumerate(lines) if l["scene"] == cue["scene"])
        hit = next((w for w in per_line[idx] if _norm(w.text) == _norm(cue["match"])), None)
        if hit is None:
            raise ValueError(f"cue '{cue['match']}' não encontrada na cena {cue['scene']}")
        cues.append({"t": hit.start, "text": cue["text"], "scene": cue["scene"]})
    cues.sort(key=lambda c: c["t"])

    sfx = [{"t": 0.0, "kind": "impact", "gain": 0.7}]
    sfx += [{"t": max(s["start"] - 0.12, 0), "kind": "whoosh", "gain": 0.75} for s in scenes[1:]]
    sfx += [{"t": c["t"], "kind": "pop", "gain": 0.7} for c in cues]
    for rule in project.get("sfx_words", []):
        hit = next((w for w in words if _norm(w.text) == _norm(rule["match"])), None)
        if hit:
            sfx.append({"t": hit.start, "kind": rule["kind"], "gain": 0.8})

    timeline = {"duration": round(total, 3), "fps": 30, "scenes": scenes, "cues": cues}
    (work / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"wav": wav, "words": words, "timeline": timeline, "sfx": sfx, "total": total}


def mix_audio(project: dict, prep: dict, work: Path) -> Path:
    total = prep["total"]
    sfx_track = place_sfx(prep["sfx"], total, work / "sfx.wav", work / "sfx")
    music = music_bed(work / "musica.wav", total, project.get("music_bpm", 100))
    out = work / "audio_final.wav"
    graph = (
        f"[0:a]aformat=channel_layouts=stereo,aresample=44100,apad=whole_dur={total}[n0];[n0]asplit=2[n][sc];"
        "[2:a]volume=0.5[m];[m][sc]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[duck];"
        "[1:a]volume=0.6[s];[n]volume=1.0[nn];"
        f"[nn][s][duck]amix=inputs=3:normalize=0:duration=longest,atrim=0:{total},loudnorm=I=-14:TP=-1.5:LRA=11[o]"
    )
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(prep["wav"]), "-i", str(sfx_track), "-i", str(music),
          "-filter_complex", graph, "-map", "[o]", "-ar", "44100", str(out)])
    return out


def render_video(timeline: Path, size: tuple[int, int], out: Path, fps: int = 30) -> Path:
    env = {**os.environ, "NODE_PATH": subprocess.check_output(["npm", "root", "-g"], text=True).strip()}
    _run(["node", "render.js", "--timeline", str(timeline.resolve()), "--out", str(out.resolve()),
          "--w", str(size[0]), "--h", str(size[1]), "--fps", str(fps)], cwd=ROOT / "render3d", env=env)
    return out


def assemble(silent: Path, audio: Path, ass: Path, out: Path, total: float) -> Path:
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent.name, "-i", audio.name,
          "-vf", f"ass={ass.name}", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
          "-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}",
          str(out.resolve())], cwd=silent.parent)
    return out


def produce(project_path: Path, out_dir: Path, formats: tuple[str, ...] = ("9x16",),
            max_attempts: int = 2) -> dict:
    project = json.loads(Path(project_path).read_text(encoding="utf-8"))
    name = project["name"]
    work = ROOT / "work" / name
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    prep = prepare(project, work)
    audio = mix_audio(project, prep, work)
    shutil.copy(work / "narracao.mp3", out_dir / "narracao.mp3")
    (out_dir / "legendas.srt").write_text(to_srt(prep["words"]), encoding="utf-8")
    caption_sync = check_caption_sync(audio, prep["words"])

    reports, results = [], {}
    for fmt in formats:
        size = FORMATS[fmt]
        ass = work / f"legendas_{fmt}.ass"
        ass.write_text(to_ass(prep["words"], size[0], size[1]), encoding="utf-8")
        shutil.copy(ass, out_dir / f"legendas_{fmt}.ass")
        final = out_dir / f"{name}_{fmt}.mp4"
        boundaries = [s["start"] for s in prep["timeline"]["scenes"][1:]]
        silent = work / f"video_mudo_{fmt}.mp4"
        stamp = work / f"video_mudo_{fmt}.sha"
        digest = hashlib.sha256(((work / "timeline.json").read_text() + str(size)
                                 + (ROOT / "render3d" / "engine.js").read_text()).encode()).hexdigest()
        for attempt in range(1, max_attempts + 1):
            cached = attempt == 1 and silent.is_file() and stamp.is_file() and stamp.read_text() == digest
            if not cached:  # render only when inputs changed (or when a retry is needed)
                render_video(work / "timeline.json", size, silent)
                stamp.write_text(digest)
            assemble(silent, audio, ass, final, prep["total"])
            res = check_video(final, prep["total"], size, 30, expected_cuts=boundaries)
            res["attempts"] = attempt
            if res["ok"]:
                break
        res["checks"].append(caption_sync)  # depends on audio/captions, not on rendering: no retry
        res["ok"] = all(c["status"] != "falha" for c in res["checks"])
        results[fmt] = res
        reports.append(render_report(f"{name} ({fmt}, tentativa {res['attempts']})", res))
    (out_dir / "conferencia.md").write_text("\n".join(reports), encoding="utf-8")

    scenes_doc = []
    for s, line in zip(prep["timeline"]["scenes"], project["lines"]):
        spec = project["scene_specs"][s["id"]]
        scenes_doc.append({"cena": s["id"], "inicio": s["start"], "fim": s["end"],
                           "duracao": round(s["end"] - s["start"], 2), "fala": line["display"], **spec})
    (out_dir / "cenas_prompts.json").write_text(json.dumps(scenes_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"out_dir": out_dir, "results": results, "duration": prep["total"]}
