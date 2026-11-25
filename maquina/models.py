from __future__ import annotations

from dataclasses import asdict, dataclass, field


class _Serializable:
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Product(_Serializable):
    name: str
    price: float | None = None
    commission_rate: float | None = None
    sales: int | None = None
    rating: float | None = None


@dataclass
class VideoRef(_Serializable):
    url: str | None = None
    path: str | None = None
    product: str | None = None
    title: str | None = None
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    published: int | None = None  # unix timestamp, when the platform provides it


@dataclass
class Word(_Serializable):
    text: str
    start: float
    end: float


@dataclass
class VideoProbe(_Serializable):
    duration: float
    width: int
    height: int
    fps: float
    has_audio: bool


@dataclass
class Segment(_Serializable):
    name: str
    start: float
    end: float


@dataclass
class VideoAnalysis(_Serializable):
    ref: VideoRef
    probe: VideoProbe
    cuts: list[float] = field(default_factory=list)
    words: list[Word] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    hook_text: str = ""
    first3s_text: str = ""
    cuts_per_minute: float = 0.0
