from __future__ import annotations

from maquina.models import Product

DEFAULT_WEIGHTS = {"sales": 0.6, "commission_rate": 0.3, "rating": 0.1}


def rank_products(
    products: list[Product], weights: dict[str, float] | None = None
) -> list[dict]:
    """Score products using only the metrics each one actually has.

    Each metric is min-max normalized among products that have it. Missing
    metrics are skipped and the remaining weights renormalized: nothing is invented.
    """
    w = weights or DEFAULT_WEIGHTS
    ranges: dict[str, tuple[float, float]] = {}
    for field in w:
        values = [getattr(p, field) for p in products if getattr(p, field) is not None]
        if values:
            ranges[field] = (min(values), max(values))

    ranked = []
    for p in products:
        used, missing, parts = [], [], []
        for field, weight in w.items():
            value = getattr(p, field)
            if value is None:
                missing.append(field)
                continue
            used.append(field)
            lo, hi = ranges[field]
            parts.append((weight, 1.0 if hi == lo else (value - lo) / (hi - lo)))
        total = sum(weight for weight, _ in parts)
        score = sum(weight * norm for weight, norm in parts) / total if total > 0 else 0.0
        ranked.append({"product": p, "score": score,
                       "used_fields": used, "missing_fields": missing})
    return sorted(ranked, key=lambda r: (bool(r["used_fields"]), r["score"]), reverse=True)
