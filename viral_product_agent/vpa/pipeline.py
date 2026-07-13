"""Cekirdek pipeline — hem run.py (CLI) hem bot.py (Telegram) buradan cagirir.

Akis: KESFET -> TEKILLESTIR -> TURKIYE KAPISI -> SINYALLER -> (LLM PUAN) -> HARMAN
      -> REKLAM. Tek kaynak cokse run durmaz; Report.source_status'a not duser.
Rapor dosyaya YAZILMAZ burada — cagiran taraf (run.py) istedigi gibi render eder;
boylece bot da ayni Report nesnesini alip Telegram'a formatlar."""
from __future__ import annotations

from datetime import date

from .models import Candidate, Report
from .sources.reddit import RedditSource
from .sources.producthunt import ProductHuntSource
from .sources.rss_feeds import RssSource
from .sources.google_trends import GoogleTrendsSource
from .sources.web_search import WebSearchSource
from .filters import dedup as dedup_mod
from .filters import turkey_availability
from .scoring import signals, scorer
from .learn import trait_miner
from .ads import ad_generator

SOURCES = [RedditSource, ProductHuntSource, RssSource, GoogleTrendsSource, WebSearchSource]


def run_pipeline(settings, cache, llm, *, max_candidates: int | None = None,
                 inject_test: bool = False, learn: bool = False,
                 on_progress=None) -> Report:
    """Tam kesif->puanlama->reklam hattini calistirir ve Report doner.

    on_progress: opsiyonel callable(str) — ilerleme mesajlari (bot 'yaziyor...' icin)."""
    def progress(msg: str) -> None:
        print(msg)
        if on_progress:
            try:
                on_progress(msg)
            except Exception:
                pass  # ilerleme bildirimi asla akisi bozmasin

    report = Report(generated_at=date.today().isoformat())
    if not llm.enabled:
        report.notes.append(
            "LLM devre disi (anahtar yok veya --no-llm): oznel viralite boyutlari puanlanmadi; "
            "bu TASLAK siralamadir. Promptlar output/pending_llm_prompts.md dosyasina yazildi.")

    # 0) OGREN (istege bagli)
    if learn:
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
        progress(f"[kaynak] {src.name}: {status}")

    if inject_test:
        candidates.append(Candidate(
            title="selfie stick tripod", description="test: TR'de zaten yaygin urun",
            url="https://example.com", source="inject_test"))

    # 2) TEKILLESTIR
    candidates = dedup_mod.dedup(candidates)
    max_n = max_candidates or settings.config["run"]["max_candidates"]
    candidates = candidates[:max_n]
    progress(f"[dedup] {len(candidates)} kanonik aday")

    if not candidates:
        report.notes.append("Hicbir kaynaktan aday gelmedi — ag erisimini kontrol edin.")
        return report

    # 3) TURKIYE KAPISI
    turkey_availability.check(candidates, settings, cache)
    kept, eliminated = turkey_availability.gate(candidates, settings.novelty_gate)
    report.eliminated = eliminated
    progress(f"[tr-kapisi] {len(kept)} gecti, {len(eliminated)} elendi")

    # 4-6) SINYALLER + PUAN + HARMAN
    signals.compute(kept, settings)
    scorer.score_all(kept, settings, llm)
    report.ranked = kept

    # 7) REKLAM (top N)
    top_n = settings.config["run"]["top_ads"]
    report.ads = ad_generator.generate(kept[:top_n], llm)
    progress(f"[reklam] {len(report.ads)} konsept uretildi")

    return report
