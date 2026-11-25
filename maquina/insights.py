from __future__ import annotations

import json
from pathlib import Path

# Rubric: points available per component (total 100).
MAX_POINTS = {"gancho": 25, "ritmo": 20, "problema_solucao": 20,
              "prova": 15, "cta": 10, "desempenho": 10}
_REQUIRED = ("video", "hook", "first3s", "problem", "solution", "retention",
             "pacing", "relevance", "breakdown", "score", "why")


def validate_insights(data: dict, n_videos: int) -> None:
    videos = data.get("videos")
    if not isinstance(videos, list):
        raise ValueError("insights: campo 'videos' ausente")
    for e in videos:
        missing = [k for k in _REQUIRED if k not in e]
        if missing:
            raise ValueError(f"insights: vídeo {e.get('video')} sem {missing}")
        if not 1 <= e["video"] <= n_videos:
            raise ValueError(f"insights: vídeo {e['video']} fora do intervalo 1..{n_videos}")
        for key, cap in MAX_POINTS.items():
            pts = e["breakdown"].get(key)
            if pts is None or not 0 <= pts <= cap:
                raise ValueError(f"insights: vídeo {e['video']} componente {key} inválido (0..{cap})")
        if e["score"] != sum(e["breakdown"].values()):
            raise ValueError(f"insights: vídeo {e['video']} nota difere da soma dos componentes")
    known = {e["video"] for e in videos}
    if any(i not in known for i in data.get("top5", [])):
        raise ValueError("insights: top5 referencia vídeo sem análise")


def load_insights(path: Path, n_videos: int) -> dict | None:
    path = Path(path)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_insights(data, n_videos)
    return data
