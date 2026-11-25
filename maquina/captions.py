from __future__ import annotations

import difflib
import re
import unicodedata

from maquina.models import Word

HIGHLIGHT_BGR = "2A6AFF"  # orange #ff6a2a in ASS (BGR)
_END_PUNCT = ("?", "!", ".", ",", ";", ":")


def _norm(t: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", s)


def time_words(
    display: list[str], spoken: list[str], whisper: list[Word], window: tuple[float, float]
) -> list[Word]:
    """Give each display word a start/end, using whisper timestamps where tokens match
    and interpolating the rest inside `window`."""
    lo, hi = window
    sp = [_norm(t) for t in spoken]
    wh = [_norm(w.text) for w in whisper]
    sp_time: dict[int, float] = {}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, sp, wh, autojunk=False).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                sp_time[i1 + k] = whisper[j1 + k].start

    nd, ns = len(display), len(spoken)
    starts: list[float | None] = []
    for i in range(nd):
        j = i if nd == ns else round(i * (ns - 1) / max(nd - 1, 1))
        starts.append(sp_time.get(j))

    # interpolate unknown starts between known neighbours (or window edges)
    known = [(-1, lo)] + [(i, s) for i, s in enumerate(starts) if s is not None] + [(nd, hi)]
    for (ia, ta), (ib, tb) in zip(known, known[1:]):
        for i in range(ia + 1, ib):
            starts[i] = ta + (tb - ta) * (i - ia) / (ib - ia) if ia >= 0 or ib < nd else lo + (hi - lo) * i / nd
    # enforce monotonic non-decreasing starts inside the window
    prev = lo
    for i in range(nd):
        starts[i] = min(max(starts[i], prev), hi)
        prev = starts[i]

    words = []
    for i, text in enumerate(display):
        end = starts[i + 1] if i + 1 < nd else hi
        if end <= starts[i]:
            end = starts[i] + 0.05
        words.append(Word(text, round(starts[i], 3), round(end, 3)))
    return words


def chunk_words(words: list[Word], max_words: int = 3) -> list[list[Word]]:
    chunks: list[list[Word]] = []
    cur: list[Word] = []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or w.text.endswith(_END_PUNCT):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def _ts_ass(t: float) -> str:
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _ts_srt(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def to_ass(words: list[Word], width: int = 1080, height: int = 1920, max_words: int = 3,
           font: str = "Inter", font_size: int | None = None, margin_v: int | None = None) -> str:
    size = font_size or round(height * 0.042)
    mv = margin_v if margin_v is not None else round(height * 0.22)
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,"
        f"{max(3, size // 14)},2,2,60,60,{mv},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = []
    for chunk in chunk_words(words, max_words):
        for i, w in enumerate(chunk):
            end = chunk[i + 1].start if i + 1 < len(chunk) else w.end
            parts = []
            for j, other in enumerate(chunk):
                t = other.text.upper()
                if j == i:
                    parts.append(f"{{\\c&H{HIGHLIGHT_BGR}&\\i1}}{t}{{\\c&HFFFFFF&\\i0}}")
                else:
                    parts.append(t)
            events.append(f"Dialogue: 0,{_ts_ass(w.start)},{_ts_ass(end)},Default,,0,0,0,,{' '.join(parts)}")
    return header + "\n".join(events) + "\n"


def to_srt(words: list[Word], max_words: int = 3) -> str:
    out = []
    for n, chunk in enumerate(chunk_words(words, max_words), start=1):
        out.append(f"{n}\n{_ts_srt(chunk[0].start)} --> {_ts_srt(chunk[-1].end)}\n"
                   f"{' '.join(w.text for w in chunk)}\n")
    return "\n".join(out)
