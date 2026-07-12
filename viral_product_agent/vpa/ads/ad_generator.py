"""Gereksinim #6: en iyi urunler icin reklam konsepti (kanca + 15sn senaryo + platform + kitle).

LLM aciksa Claude uretir; kapaliysa urun bilgisinden doldurulmus sablon-iskelet
uretilir ve prompt pending dosyasina yazilir (anahtar gelince kaliteli versiyon alinir)."""
from __future__ import annotations

from ..llm import prompts
from ..models import AdConcept, Candidate


def generate(top: list[Candidate], llm) -> list[AdConcept]:
    ads = []
    for c in top:
        result = llm.json_call(
            prompts.AD_CONCEPT.format(
                title=c.title, description=c.description or "-",
                rationale="; ".join(c.llm_rationale.values()) or "yuksek viralite skoru",
            ),
            label=f"ad:{c.title[:60]}",
        )
        if isinstance(result, dict) and result.get("hook"):
            ads.append(AdConcept(
                product_title=c.title,
                hook=result.get("hook", ""),
                video_script=result.get("video_script", ""),
                platform=result.get("platform", ""),
                audience=result.get("audience", ""),
            ))
        else:
            ads.append(_template_fallback(c))
    return ads


def _template_fallback(c: Candidate) -> AdConcept:
    return AdConcept(
        product_title=c.title,
        hook=f'"Bunu daha once neden kimse yapmadi?" — {c.title}',
        video_script=(
            "0-2sn: Urun kullanim aninda, yakin cekim 'vay be' ani. "
            "2-7sn: Cozdugu sorun karsilastirmali gosterilir (oncesi/sonrasi). "
            "7-12sn: 2-3 farkli kullanim senaryosu hizli kesme. "
            "12-15sn: Fiyat + 'stoklar sinirli' + magaza linki CTA."
        ),
        platform="TikTok (kesif algoritmasi yeni urunlerde en gucludur)",
        audience="18-34 TR, gadget/pratik-cozum icerigi izleyenler, impuls alisveris davranisi",
        note="SABLON (LLM devre disi) — anahtar ekleyince gercek konsept uretilir",
    )
