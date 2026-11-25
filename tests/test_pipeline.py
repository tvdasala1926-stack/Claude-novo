import json
import subprocess
import sys
from pathlib import Path

from maquina.models import Product
from maquina.pipeline import run_pipeline
from maquina.rank import rank_products
from maquina.report import build_report


def _videos_file(tmp_path: Path, sample_video: Path) -> Path:
    f = tmp_path / "videos.txt"
    f.write_text(f"{sample_video}\n{tmp_path / 'nao_existe.mp4'}\n", encoding="utf-8")
    return f


def test_pipeline_survives_one_bad_video(tmp_path: Path, sample_video: Path):
    products = tmp_path / "p.csv"
    products.write_text("nome;vendas\nTeclado X;100\nMouse Y;300\n", encoding="utf-8")
    run_dir = run_pipeline(products, _videos_file(tmp_path, sample_video), tmp_path / "runs", run_id="t1")

    analysis = json.loads((run_dir / "videos" / "1" / "analysis.json").read_text())
    assert len(analysis["segments"]) == 8
    assert len(analysis["cuts"]) == 2
    errors = json.loads((run_dir / "errors.json").read_text())
    assert len(errors) == 1 and errors[0]["error"]
    state = json.loads((run_dir / "state.json").read_text())
    assert state["stage"] == "done" and state["videos_done"] == 2 and state["videos_total"] == 2
    ranked = json.loads((run_dir / "products_ranked.json").read_text())
    assert ranked[0]["product"]["name"] == "Mouse Y"
    report = (run_dir / "report.md").read_text()
    assert "Mouse Y" in report and "gancho" in report


def test_report_with_no_valid_videos_does_not_break():
    ranked = rank_products([Product("x", sales=1)])
    text = build_report(ranked, [], [{"video": "v", "error": "falhou"}])
    assert "Nenhum vídeo" in text and "falhou" in text


def test_cli_prints_existing_report_path(tmp_path: Path, sample_video: Path):
    proc = subprocess.run(
        [sys.executable, "-m", "maquina.cli", "--videos", str(_videos_file(tmp_path, sample_video)),
         "--out", str(tmp_path / "runs")],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip().splitlines()[-1]).is_file()


def test_silent_single_shot_video_is_analyzed(tmp_path: Path, silent_video: Path):
    from maquina.models import VideoRef
    from maquina.pipeline import analyze_video

    a = analyze_video(VideoRef(path=str(silent_video)), tmp_path)
    assert a.words == [] and a.cuts == [] and a.cuts_per_minute == 0.0
    assert len(a.segments) == 8 and a.segments[-1].end == a.probe.duration
