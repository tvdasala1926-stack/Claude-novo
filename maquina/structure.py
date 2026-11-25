from __future__ import annotations

import unicodedata

from maquina.models import Segment, Word

_CTA_KEYWORDS = {"link", "carrinho", "compre", "clique", "garanta", "comenta",
                 "segue", "aproveita"}
_MIDDLE = [("introducao", 8), ("desenvolvimento", 17), ("problema", 25),
           ("virada", 15), ("climax", 25), ("conclusao", 10)]
_HOOK_SECONDS = 3.0
_DEFAULT_CTA_FRACTION = 0.85
_SNAP_WINDOW = 0.10


def _plain(text: str) -> str:
    stripped = "".join(
        c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn"
    )
    return stripped.strip(" .,!?:;\"'")


def _cta_start(duration: float, words: list[Word], floor: float) -> float:
    for w in words:
        if w.start >= duration / 2 and _plain(w.text) in _CTA_KEYWORDS:
            return max(w.start, floor)
    return max(duration * _DEFAULT_CTA_FRACTION, floor)


def split_structure(duration: float, words: list[Word], cuts: list[float]) -> list[Segment]:
    hook_end = min(_HOOK_SECONDS, duration)
    cta_start = min(_cta_start(duration, words, hook_end), duration)
    span = cta_start - hook_end
    window = span * _SNAP_WINDOW

    bounds = [hook_end]
    acc = 0.0
    for _, pct in _MIDDLE[:-1]:
        acc += pct
        target = hook_end + span * acc / 100
        near = [c for c in cuts if abs(c - target) <= window and bounds[-1] <= c <= cta_start]
        bounds.append(min(near, key=lambda c: abs(c - target)) if near else max(target, bounds[-1]))
    bounds.append(cta_start)

    segments = [Segment("gancho", 0.0, hook_end)]
    for (name, _), start, end in zip(_MIDDLE, bounds, bounds[1:]):
        segments.append(Segment(name, start, end))
    segments.append(Segment("cta", cta_start, duration))
    return segments


def first_seconds_text(words: list[Word], seconds: float = 3.0) -> str:
    return " ".join(w.text for w in words if w.start < seconds)


def cuts_per_minute(duration: float, cuts: list[float]) -> float:
    return 0.0 if duration <= 0 else len(cuts) / duration * 60
