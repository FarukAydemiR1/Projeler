"""Turkiye kapisi: urun TR pazar yerlerinde zaten yaygin mi?

Yontem (MVP): her pazar yeri icin site-hedefli arama ("site:trendyol.com <urun>")
ve isabet sayisindan novelty_absence = 1 - normalize(isabet) skoru.
Bu sezgisel bir kontroldur: arama engellenirse veya urun TR'de farkli adla
satiliyorsa yanlis "yeni" sonucu verebilir — bu yuzden guven etiketi dusuk olan
adaylar raporda "manuel dogrula" bolumune duser, korlemesine guvenilmez."""
from __future__ import annotations

from ..models import Candidate
from ..sources.web_search import ddg_search


def check(candidates: list[Candidate], settings, cache) -> None:
    cfg = settings.config["turkey_availability"]
    if not cfg.get("enabled", True):
        for c in candidates:
            c.signals["novelty_absence"] = 0.5
            c.availability_confidence = "low"
        return

    marketplaces: list[str] = cfg["marketplaces"]
    for cand in candidates:
        query_name = _search_name(cand.title)
        total_hits = 0
        answered = 0
        for site in marketplaces:
            results = ddg_search(cache, f"site:{site} {query_name}", max_results=5)
            if results is not None:
                answered += 1
                # yalnizca gercekten o siteden gelen sonuclari say
                total_hits += sum(1 for r in results if site in r.get("url", ""))
        if answered == 0:
            # arama tamamen engellendi: notr skor + dusuk guven
            cand.signals["novelty_absence"] = 0.5
            cand.availability_confidence = "low"
            continue
        max_possible = answered * 5
        availability = min(1.0, total_hits / max(1, max_possible) * 2.5)
        cand.signals["novelty_absence"] = round(1.0 - availability, 3)
        cand.availability_confidence = "high" if answered >= 3 else "low"


def gate(candidates: list[Candidate], novelty_gate: float) -> tuple[list[Candidate], list[Candidate]]:
    """Sert kapi: TR'de zaten yaygin urunler elenir. (kalanlar, elenenler) doner."""
    kept, eliminated = [], []
    for c in candidates:
        if c.signals.get("novelty_absence", 0.5) < novelty_gate:
            c.eliminated = True
            c.elimination_reason = (
                f"Turkiye'de zaten yaygin gorunuyor (novelty_absence="
                f"{c.signals['novelty_absence']:.2f} < {novelty_gate})"
            )
            eliminated.append(c)
        else:
            kept.append(c)
    return kept, eliminated


def _search_name(title: str) -> str:
    """Baslik curufunu temizle: ilk ~6 anlamli kelime yeterli arama sorgusudur."""
    words = [w for w in title.split() if len(w) > 2][:6]
    return " ".join(words) if words else title
