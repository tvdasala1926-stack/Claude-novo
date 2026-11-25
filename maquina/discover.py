from __future__ import annotations

import re
from pathlib import Path

from maquina.fetch import FetchError
from maquina.models import VideoRef


def _normalize_profile(text: str) -> str | None:
    t = text.strip()
    if t.lower().startswith(("http://", "https://")):
        return t.rstrip("/") if "/@" in t else None
    if t.startswith("@") and len(t) > 1:
        return f"https://www.tiktok.com/{t}"
    return None


def load_profiles(path: Path) -> list[str]:
    seen: list[str] = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        url = _normalize_profile(line)
        if url and url not in seen:
            seen.append(url)
    return seen


def list_profile_videos(profile_url: str, limit: int = 10) -> list[VideoRef]:
    """Public videos of a profile, with whatever metrics TikTok exposes (else None)."""
    import yt_dlp

    opts = {"quiet": True, "no_warnings": True, "extract_flat": True,
            "playlistend": limit, "noprogress": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(profile_url, download=False)
    except Exception as e:
        raise FetchError(f"falha ao listar {profile_url}: {e}") from e
    refs = []
    for e in info.get("entries") or []:
        if not e.get("url"):
            continue
        refs.append(VideoRef(
            url=e["url"], title=e.get("title"), views=e.get("view_count"),
            likes=e.get("like_count"), comments=e.get("comment_count"),
            published=e.get("timestamp"),
        ))
    return refs[:limit]


def enrich_comments(ref: VideoRef) -> VideoRef:
    """Best effort: fetch the comment count (not in profile listings)."""
    import yt_dlp

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(ref.url, download=False)
        ref.comments = info.get("comment_count", ref.comments)
        ref.views = ref.views if ref.views is not None else info.get("view_count")
        ref.likes = ref.likes if ref.likes is not None else info.get("like_count")
    except Exception:
        pass
    return ref


def top_by_views(refs: list[VideoRef], n: int) -> list[VideoRef]:
    ordered = sorted(refs, key=lambda r: (r.views is not None, r.views or 0), reverse=True)
    return ordered[:n]


PRODUCT_KEYWORDS = re.compile(
    r"teclado|mouse|headset|fone|setup|mousepad|gamer|periférico|periferico|tiktokshop|"
    r"tiktok shop|achadinho|achados|publi|review|unboxing|link na bio|cupom|promo|oferta|"
    r"black ?friday|compre|comprei|monitor|cadeira|\bpc\b",
    re.I,
)


def filter_product_videos(refs: list[VideoRef]) -> list[VideoRef]:
    """Keep videos whose title mentions a product/review/ad keyword."""
    return [r for r in refs if r.title and PRODUCT_KEYWORDS.search(r.title)]
