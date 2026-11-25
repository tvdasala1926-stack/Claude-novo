from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

from maquina.models import Product, VideoRef

_FIELD_ALIASES = {
    "name": {"nome", "name", "produto", "product"},
    "price": {"preco", "price", "valor"},
    "commission_rate": {"comissao", "commission", "commission_rate", "taxa de comissao"},
    "sales": {"vendas", "sales", "vendidos"},
    "rating": {"avaliacao", "rating", "nota"},
}


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def parse_number(text: str | None) -> float | None:
    """Parse Brazilian-style numbers ('R$ 1.299,90', '12,5 mil', '3k'). None if unreadable."""
    if text is None:
        return None
    s = _strip_accents(str(text)).lower().replace("r$", "").replace("%", "").strip()
    if not s:
        return None
    mult = 1.0
    m = re.search(r"\s*(mil|mi|k|m)$", s)
    if m:
        mult = 1e6 if m.group(1) in ("mi", "m") else 1e3
        s = s[: m.start()].strip()
    if not re.fullmatch(r"[\d.,]+", s):
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s) * mult
    except ValueError:
        return None


def _detect_delimiter(header_line: str) -> str:
    return max([";", "\t", ","], key=header_line.count)


def _canonical(header: str) -> str | None:
    h = _strip_accents(header).lower().strip()
    for field, aliases in _FIELD_ALIASES.items():
        if h in aliases:
            return field
    return None


def _merge(a: Product, b: Product) -> Product:
    first, second = (a, b) if (a.sales or -1) >= (b.sales or -1) else (b, a)
    for f in ("price", "commission_rate", "sales", "rating"):
        if getattr(first, f) is None:
            setattr(first, f, getattr(second, f))
    first.name = a.name
    return first


def load_products(path: Path) -> list[Product]:
    text = Path(path).read_text(encoding="utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    delim = _detect_delimiter(lines[0])
    reader = csv.reader(lines, delimiter=delim)
    headers = [_canonical(h) for h in next(reader)]
    products: dict[str, Product] = {}
    for row in reader:
        raw = {headers[i]: v for i, v in enumerate(row) if i < len(headers) and headers[i]}
        name = (raw.get("name") or "").strip()
        if not name:
            continue
        sales = parse_number(raw.get("sales"))
        product = Product(
            name=name,
            price=parse_number(raw.get("price")),
            commission_rate=parse_number(raw.get("commission_rate")),
            sales=None if sales is None else int(round(sales)),
            rating=parse_number(raw.get("rating")),
        )
        key = name.lower()
        products[key] = _merge(products[key], product) if key in products else product
    return list(products.values())


def load_video_refs(path: Path) -> list[VideoRef]:
    refs: list[VideoRef] = []
    seen: set[str] = set()
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        item = line.strip()
        if not item or item.startswith("#") or item in seen:
            continue
        seen.add(item)
        if item.lower().startswith(("http://", "https://")):
            refs.append(VideoRef(url=item))
        else:
            refs.append(VideoRef(path=item))
    return refs
