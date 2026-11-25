from pathlib import Path

from maquina.discover import load_profiles, list_profile_videos, top_by_views
from maquina.models import VideoRef


def test_load_profiles_normalizes_dedups_and_skips_junk(tmp_path: Path):
    f = tmp_path / "perfis.txt"
    f.write_text(
        "# comentário\n@scout2015\nhttps://www.tiktok.com/@scout2015\n\n  @outro  \nsemarroba\n",
        encoding="utf-8",
    )
    assert load_profiles(f) == [
        "https://www.tiktok.com/@scout2015",
        "https://www.tiktok.com/@outro",
    ]


def test_top_by_views_orders_desc_and_puts_unknown_last():
    refs = [VideoRef(url="a", views=10), VideoRef(url="b", views=None),
            VideoRef(url="c", views=500), VideoRef(url="d", views=70)]
    assert [r.url for r in top_by_views(refs, 3)] == ["c", "d", "a"]
    assert [r.url for r in top_by_views(refs, 10)][-1] == "b"


def test_list_profile_videos_real_profile_has_metrics():
    refs = list_profile_videos("https://www.tiktok.com/@scout2015", limit=3)
    assert 1 <= len(refs) <= 3
    assert all(r.url and "/video/" in r.url for r in refs)
    assert any(r.views is not None for r in refs)


def test_filter_product_videos_keeps_only_product_titles():
    from maquina.discover import filter_product_videos

    refs = [VideoRef(url="a", title="PC de 4000 Reais !!! #setupgamer"),
            VideoRef(url="b", title="Fortnitemares 2026 💀 #edit"),
            VideoRef(url="c", title="DEU RUIM... mas o HAVIT H668BT resolveu #publi"),
            VideoRef(url="d", title=None)]
    assert [r.url for r in filter_product_videos(refs)] == ["a", "c"]
