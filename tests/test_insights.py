import json
from pathlib import Path

import pytest

from maquina.insights import MAX_POINTS, validate_insights
from maquina.pipeline import rebuild_report, run_pipeline


def _entry(index=1, **over):
    e = {
        "video": index,
        "hook": "pergunta direta", "first3s": "texto na tela + rosto", "problem": "sem som",
        "solution": "fone sem fio", "retention": ["cortes rápidos"], "pacing": "rápido",
        "relevance": "alta",
        "breakdown": {"gancho": 20, "ritmo": 15, "problema_solucao": 15, "prova": 10, "cta": 8, "desempenho": 7},
        "score": 75, "why": "porque sim",
    }
    e.update(over)
    return e


def test_valid_insights_pass():
    validate_insights({"videos": [_entry()], "top5": [1]}, n_videos=1)


def test_score_must_equal_breakdown_sum():
    with pytest.raises(ValueError, match="soma"):
        validate_insights({"videos": [_entry(score=99)], "top5": [1]}, n_videos=1)


def test_component_above_maximum_rejected():
    bad = _entry()
    bad["breakdown"]["cta"] = MAX_POINTS["cta"] + 1
    bad["score"] = sum(bad["breakdown"].values())
    with pytest.raises(ValueError, match="cta"):
        validate_insights({"videos": [bad], "top5": [1]}, n_videos=1)


def test_top5_must_reference_existing_videos():
    with pytest.raises(ValueError, match="top5"):
        validate_insights({"videos": [_entry()], "top5": [7]}, n_videos=1)


def test_rebuild_report_includes_qualitative_sections(tmp_path: Path, sample_video: Path):
    vids = tmp_path / "v.txt"
    vids.write_text(f"{sample_video}\n", encoding="utf-8")
    run_dir = run_pipeline(None, vids, tmp_path / "runs", run_id="q1")
    (run_dir / "insights.json").write_text(
        json.dumps({"videos": [_entry()], "top5": [1]}, ensure_ascii=False), encoding="utf-8")
    text = rebuild_report(run_dir).read_text(encoding="utf-8")
    assert "Os 5 melhores exemplos" in text and "porque sim" in text and "75/100" in text
