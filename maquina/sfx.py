"""Original, synthesized sound effects and music (no third-party audio, no license issues)."""
from __future__ import annotations

import subprocess
from pathlib import Path

# kind -> (ffmpeg lavfi source expression, duration, extra audio filters)
KINDS: dict[str, tuple[str, float, str]] = {
    "whoosh": ("anoisesrc=d=0.6:c=pink:a=0.9", 0.6,
               "highpass=f=300,lowpass=f=7000,afade=t=in:d=0.3,afade=t=out:st=0.3:d=0.3,volume=0.9"),
    "click": ("anoisesrc=d=0.08:c=white:a=0.9", 0.08,
              "highpass=f=1800,lowpass=f=9000,afade=t=out:st=0.01:d=0.07,volume=0.8"),
    "ding": ("aevalsrc='0.6*sin(2*PI*1320*t)+0.3*sin(2*PI*1980*t)':d=0.9", 0.9,
             "afade=t=in:d=0.005,afade=t=out:st=0.05:d=0.85,volume=0.7"),
    "impact": ("aevalsrc='0.9*sin(2*PI*(70-30*t)*t)+0.25*random(0)':d=0.7", 0.7,
               "lowpass=f=900,afade=t=out:st=0.05:d=0.65,volume=1.0"),
    "pop": ("aevalsrc='0.8*sin(2*PI*(500+1500*t)*t)':d=0.15", 0.15,
            "afade=t=out:st=0.02:d=0.13,volume=0.7"),
}


def _run(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def make_sfx(kind: str, out: Path) -> Path:
    if kind not in KINDS:
        raise ValueError(f"efeito desconhecido: {kind} (disponíveis: {sorted(KINDS)})")
    src, _, flt = KINDS[kind]
    _run(["-f", "lavfi", "-i", src, "-af", flt, "-ar", "44100", "-ac", "2", str(out)])
    return Path(out)


def music_bed(out: Path, duration: float, bpm: int = 100) -> Path:
    """Dark ambient pad (A minor) with a soft pulse, synthesized from scratch."""
    beat = 60.0 / bpm
    pad = ("aevalsrc='0.10*sin(2*PI*110*t)+0.08*sin(2*PI*164.81*t)+0.07*sin(2*PI*220*t)"
           f"+0.05*sin(2*PI*261.63*t)':d={duration}")
    pulse = f"aevalsrc='0.55*sin(2*PI*52*t)*exp(-7*mod(t,{beat:.4f}))':d={duration}"
    _run(["-f", "lavfi", "-i", pad, "-f", "lavfi", "-i", pulse, "-filter_complex",
          "[0:a]lowpass=f=900,tremolo=f=0.25:d=0.4[p];[1:a]lowpass=f=140[k];"
          f"[p][k]amix=inputs=2:normalize=0,afade=t=in:d=1.0,afade=t=out:st={max(duration - 1.5, 0):.2f}:d=1.5,"
          "volume=1.0[m]", "-map", "[m]", "-ar", "44100", "-ac", "2", "-t", f"{duration}", str(out)])
    return Path(out)


def place_sfx(events: list[dict], total: float, out: Path, work_dir: Path) -> Path:
    """Mix sfx events [{t, kind, gain?}] into one stereo track of length `total`."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    inputs = ["-f", "lavfi", "-t", f"{total}", "-i", "anullsrc=r=44100:cl=stereo"]
    chains, labels = [], ["[0:a]"]
    for i, ev in enumerate(events, start=1):
        wav = make_sfx(ev["kind"], work_dir / f"sfx_{ev['kind']}.wav")
        inputs += ["-i", str(wav)]
        ms = max(int(ev["t"] * 1000), 0)
        chains.append(f"[{i}:a]adelay={ms}|{ms},volume={ev.get('gain', 1.0)}[s{i}]")
        labels.append(f"[s{i}]")
    graph = ";".join(chains + [f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first[o]"])
    _run([*inputs, "-filter_complex", graph, "-map", "[o]", "-t", f"{total}", str(out)])
    return Path(out)
