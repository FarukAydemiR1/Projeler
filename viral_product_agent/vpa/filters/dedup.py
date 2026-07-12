"""Kaynaklar arasi tekillestirme: rapidfuzz token-set benzerligi ile kumeleme.

Ayni urun birden fazla kaynakta gorunuyorsa bu ASLINDA iyi bir sinyaldir
(cross_source_corroboration); kanonik adaya digerlerinin URL'leri eklenir."""
from __future__ import annotations

from rapidfuzz import fuzz

from ..models import Candidate

SIMILARITY_THRESHOLD = 87  # token_set_ratio; deneysel olarak iyi bir baslangic


def dedup(candidates: list[Candidate]) -> list[Candidate]:
    canonical: list[Candidate] = []
    for cand in candidates:
        if not cand.title:
            continue
        match = None
        for existing in canonical:
            if fuzz.token_set_ratio(cand.key(), existing.key()) >= SIMILARITY_THRESHOLD:
                match = existing
                break
        if match:
            match.also_seen.append(cand.url)
            # daha zengin aciklama/gorsel varsa kanonige tasi
            if len(cand.description) > len(match.description):
                match.description = cand.description
            if cand.image_url and not match.image_url:
                match.image_url = cand.image_url
            if cand.price_usd and not match.price_usd:
                match.price_usd = cand.price_usd
        else:
            canonical.append(cand)
    return canonical
