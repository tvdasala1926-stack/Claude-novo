from __future__ import annotations

import json
import time
from pathlib import Path

from maquina.discover import enrich_comments, filter_product_videos, list_profile_videos, load_profiles, top_by_views
from maquina.fetch import FetchError, fetch_video
from maquina.importer import load_products, load_video_refs
from maquina.models import VideoAnalysis, VideoRef
from maquina.probe import probe_video
from maquina.rank import rank_products
from maquina.report import build_report
from maquina.scenes import detect_scenes
from maquina.structure import cuts_per_minute, first_seconds_text, split_structure
from maquina.transcribe import transcribe


def analyze_video(ref: VideoRef, work_dir: Path) -> VideoAnalysis:
    path = fetch_video(ref, Path(work_dir) / "downloads")
    probe = probe_video(path)
    cuts = detect_scenes(path)
    words = transcribe(path)
    segments = split_structure(probe.duration, words, cuts)
    hook_end = segments[0].end
    return VideoAnalysis(
        ref=ref,
        probe=probe,
        cuts=cuts,
        words=words,
        segments=segments,
        hook_text=" ".join(w.text for w in words if w.start < hook_end),
        first3s_text=first_seconds_text(words),
        cuts_per_minute=cuts_per_minute(probe.duration, cuts),
    )


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_pipeline(
    products_file: Path | None,
    videos_file: Path | None,
    out_root: Path,
    run_id: str | None = None,
    *,
    profiles_file: Path | None = None,
    per_profile: int = 10,
    top: int = 30,
    only_products: bool = False,
) -> Path:
    run_dir = Path(out_root) / (run_id or time.strftime("%Y%m%d-%H%M%S"))
    run_dir.mkdir(parents=True, exist_ok=True)
    refs = load_video_refs(videos_file) if videos_file else []
    errors: list[dict] = []
    if profiles_file:
        found: list[VideoRef] = []
        for profile in load_profiles(profiles_file):
            try:
                found += list_profile_videos(profile, limit=per_profile)
            except FetchError as e:
                errors.append({"video": profile, "error": str(e)})
        if only_products:
            found = filter_product_videos(found)
        known = {r.url for r in refs}
        refs += [enrich_comments(r) for r in top_by_views(
            [r for r in found if r.url not in known], top)]
    state = {"stage": "starting", "videos_done": 0, "videos_total": len(refs)}
    _write_json(run_dir / "state.json", state)

    ranked: list[dict] = []
    if products_file:
        ranked = rank_products(load_products(products_file))
    _write_json(run_dir / "products_ranked.json", [
        {**r, "product": r["product"].to_dict()} for r in ranked
    ])

    analyses: list[VideoAnalysis] = []
    for n, ref in enumerate(refs, start=1):
        state.update(stage=f"analyzing video {n}/{len(refs)}")
        _write_json(run_dir / "state.json", state)
        label = ref.url or ref.path or "?"
        try:
            analysis = analyze_video(ref, run_dir)
            analyses.append(analysis)
            _write_json(run_dir / "videos" / str(n) / "analysis.json", analysis.to_dict())
        except (FetchError, ValueError) as e:
            errors.append({"video": label, "error": str(e)})
        except Exception as e:  # one broken video must not stop the batch
            errors.append({"video": label, "error": f"{type(e).__name__}: {e}"})
        state["videos_done"] = n

    _write_json(run_dir / "errors.json", errors)
    (run_dir / "report.md").write_text(build_report(ranked, analyses, errors), encoding="utf-8")
    state.update(stage="done")
    _write_json(run_dir / "state.json", state)
    return run_dir
