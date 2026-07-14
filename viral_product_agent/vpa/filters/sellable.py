"""Satilabilirlik filtresi — tek somut URUN olmayanlari eler.

Kaynaklar (ozellikle RSS/haber) cogu zaman liste/editoryal basliklar dondurur:
"En iyi 8 mutfak aleti", "2026'nin en iyi 10 gadget'i", "... rehberi", "... vs ..."
Bunlar satilabilir tek urun degildir. Bu filtre acik liste/editoryal kaliplari
duserur ve tek urun gibi gorunenleri tutar. LLM acikken bu zaten skorlamada
pekistirilir; kapaliyken bu heuristik kaliteyi korur."""
from __future__ import annotations

import re

from ..models import Candidate

# Liste/editoryal/haber sinyalleri (baslik bunlardan birini icerirse ele)
_BLOCK_PATTERNS = [
    r"^\s*\d+\s",                         # "8 Best...", "10 gadgets..."
    r"\b(top|best)\s+\d+",                # "top 10", "best 5"
    r"\b\d+\s+(best|top|coolest|genius|must[- ]?have|things|gadgets|products|tools|items|ways|reasons)\b",
    r"\bbest\b.*\b(of|for|in|under)\b",   # "best X for Y" listicle
    r"\b(round[- ]?up|guide|deals?|sale|discount|review|reviews|vs\.?|versus)\b",
    r"\bhow to\b|\bwhy\b.*\?|\bwhat (is|are)\b",
    r"\b(everything|things) (you|we)\b",
    r"\b(gift guide|wishlist|favou?rites|our picks)\b",
]
_BLOCK_RE = re.compile("|".join(_BLOCK_PATTERNS), re.IGNORECASE)


def looks_like_product(title: str) -> bool:
    """Baslik tek somut urun gibi mi? (Kabaca — heuristik.)"""
    t = (title or "").strip()
    if not (8 <= len(t) <= 140):          # cok kisa/cok uzun basliklar supheli
        return False
    if _BLOCK_RE.search(t):
        return False
    if t.count(",") >= 3:                 # "X, Y, Z, W" -> liste gibi
        return False
    return True


def filter_sellable(candidates: list[Candidate]) -> tuple[list[Candidate], list[Candidate]]:
    """(satilabilir gorunenler, elenenler) doner."""
    keep, drop = [], []
    for c in candidates:
        if looks_like_product(c.title):
            keep.append(c)
        else:
            c.eliminated = True
            c.elimination_reason = "satilabilir tek urun gibi gorunmuyor (liste/haber/editoryal baslik)"
            drop.append(c)
    return keep, drop
