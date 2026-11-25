import json

from maquina.models import (
    Product, Segment, VideoAnalysis, VideoProbe, VideoRef, Word,
)


def test_product_keeps_missing_metrics_as_none():
    d = Product("x", None, None, None, None).to_dict()
    assert d["price"] is None and d["sales"] is None


def test_video_analysis_is_json_serializable():
    analysis = VideoAnalysis(
        ref=VideoRef(url="https://x", path=None, product=None),
        probe=VideoProbe(6.0, 320, 568, 30.0, True),
        cuts=[2.0, 4.0],
        words=[Word("oi", 0.1, 0.4)],
        segments=[Segment("gancho", 0.0, 3.0)],
        hook_text="oi",
        first3s_text="oi",
        cuts_per_minute=20.0,
    )
    assert json.loads(json.dumps(analysis.to_dict()))["cuts"] == [2.0, 4.0]
