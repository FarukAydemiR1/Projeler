#!/usr/bin/env python3
"""Viral Urun Kesif Ajani — pipeline orkestratoru.

Kullanim:
    python run.py                 # tam pipeline (ANTHROPIC_API_KEY varsa LLM'li)
    python run.py --no-llm        # LLM adimlarini zorla atla (deterministik rapor)
    python run.py --learn         # once rubric'i yeniden ogren (trait mining)
    python run.py --max 30        # aday sayisini sinirla
    python run.py --inject-test   # Turkiye kapisini test icin bilinen yaygin urun enjekte et

Akis: KESFET -> TEKILLESTIR -> TURKIYE KAPISI -> SINYALLER -> (LLM PUAN) -> HARMAN
      -> RAPOR -> REKLAM. Tek kaynak cokse run durmaz; rapora not duser.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from vpa.settings import Settings
from vpa.cache import DiskCache
from vpa.models import Candidate, Report
from vpa.llm.client import LLMClient
from vpa.sources.reddit import RedditSource
from vpa.sources.producthunt import ProductHuntSource
from vpa.sources.rss_feeds import RssSource
from vpa.sources.google_trends import GoogleTrendsSource
from vpa.sources.web_search import WebSearchSource
from vpa.filters import dedup as dedup_mod
from vpa.filters import turkey_availability
from vpa.scoring import signals, scorer
from vpa.learn import trait_miner
from vpa.ads import ad_generator
from vpa.report import render

SOURCES = [RedditSource, ProductHuntSource, RssSource, GoogleTrendsSource, WebSearchSource]


def main() -> int:
    ap = argparse.ArgumentParser(description="Turkiye icin viral urun kesif ajani")
    ap.add_argument("--no-llm", action="store_true", help="LLM adimlarini atla")
    ap.add_argument("--learn", action="store_true", help="rubric'i yeniden ogren")
    ap.add_argument("--max", type=int, default=None, help="max aday sayisi")
    ap.add_argument("--inject-test", action="store_true",
                    help="TR kapisi testi icin bilinen yaygin urun enjekte et")
    args = ap.parse_args()

    settings = Settings()
    cache = DiskCache(settings.cache_dir, settings.config["cache"]["ttl_hours"])
    api_key = "" if args.no_llm else settings.anthropic_api_key
    llm = LLMClient(api_key, cache, settings.output_dir)

    report = Report(generated_at=date.today().isoformat())
    if not llm.enabled:
        report.notes.append(
            "LLM devre disi (anahtar yok veya --no-llm): oznel viralite boyutlari puanlanmadi; "
            "bu TASLAK siralamadir. Promptlar output/pending_llm_prompts.md dosyasina yazildi.")

    # 0) OGREN (istege bagli)
    if args.learn:
        mined = trait_miner.mine(settings, llm)
        report.notes.append("Rubric " + ("yeniden ogrenildi." if mined else
                                         "ogrenilemedi (LLM kapali olabilir); mevcut/varsayilan kullanildi."))

    # 1) KESFET
    candidates: list[Candidate] = []
    for source_cls in SOURCES:
        src = source_cls(settings, cache)
        items, status = src.safe_fetch()
        report.source_status[src.name] = status
        candidates.extend(items)
        print(f"[kaynak] {src.name}: {status}")

    if args.inject_test:
        candidates.append(Candidate(
            title="selfie stick tripod", description="test: TR'de zaten yaygin urun",
            url="https://example.com", source="inject_test"))

    # 2) TEKILLESTIR
    candidates = dedup_mod.dedup(candidates)
    max_n = args.max or settings.config["run"]["max_candidates"]
    candidates = candidates[:max_n]
    print(f"[dedup] {len(candidates)} kanonik aday")

    if not candidates:
        report.notes.append("Hicbir kaynaktan aday gelmedi — ag erisimini kontrol edin.")
        json_p, md_p = render.write(report, settings.output_dir, date.today().isoformat())
        print(f"[rapor] {md_p}")
        return 1

    # 3) TURKIYE KAPISI
    turkey_availability.check(candidates, settings, cache)
    kept, eliminated = turkey_availability.gate(candidates, settings.novelty_gate)
    report.eliminated = eliminated
    print(f"[tr-kapisi] {len(kept)} gecti, {len(eliminated)} elendi")

    # 4-6) SINYALLER + PUAN + HARMAN
    signals.compute(kept, settings)
    scorer.score_all(kept, settings, llm)
    report.ranked = kept

    # 7) REKLAM (top N)
    top_n = settings.config["run"]["top_ads"]
    report.ads = ad_generator.generate(kept[:top_n], llm)

    # 8) RAPOR
    json_p, md_p = render.write(report, settings.output_dir, date.today().isoformat())
    print(f"[rapor] {md_p}\n[rapor] {json_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
