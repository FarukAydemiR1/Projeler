"""Katman A — deterministik sinyaller (0..1). Kodda hesaplanir, aciklanabilir kalir.

novelty_absence turkey_availability filtresinde doldurulur; burasi kalanlari ekler."""
from __future__ import annotations

from ..models import Candidate


def compute(candidates: list[Candidate], settings) -> None:
    price_cfg = settings.config["price_fit_tr"]
    for c in candidates:
        c.signals.setdefault("novelty_absence", 0.5)
        c.signals["trend_momentum"] = _trend_momentum(c)
        c.signals["cross_source_corroboration"] = min(1.0, len(c.also_seen) / 3.0)
        c.signals["price_fit_tr"] = _price_fit(c, price_cfg)
        c.signals["margin_proxy"] = _margin_proxy(c, price_cfg)


def _trend_momentum(c: Candidate) -> float:
    h = c.momentum_hints
    if h.get("breakout"):
        return 1.0
    upd = h.get("upvotes_per_day")
    if upd is not None:
        return min(1.0, upd / 500.0)  # gunde 500+ upvote = tam puan
    votes = h.get("votes") or h.get("upvotes")
    if votes is not None:
        return min(1.0, votes / 1000.0)
    return 0.4  # RSS gibi momentum verisi olmayan kaynaklar icin notr-alti varsayilan


def _price_fit(c: Candidate, cfg: dict) -> float:
    if c.price_usd is None:
        return 0.5  # bilinmiyor: notr
    retail_try = c.price_usd * cfg["usd_to_try"] * 2.0  # kaba perakende = maliyet x2
    lo, hi = cfg["ideal_min_try"], cfg["ideal_max_try"]
    if lo <= retail_try <= hi:
        return 1.0
    if retail_try < lo:
        return 0.7   # cok ucuz: marj dar ama impuls guclu
    return max(0.0, 1.0 - (retail_try - hi) / (hi * 3))


def _margin_proxy(c: Candidate, cfg: dict) -> float:
    if c.price_usd is None:
        return 0.5
    landed = c.price_usd * cfg["usd_to_try"] * 1.35  # kargo+gumruk kaba katsayisi
    retail = c.price_usd * cfg["usd_to_try"] * 2.0
    return max(0.0, min(1.0, (retail - landed) / retail * 2))
