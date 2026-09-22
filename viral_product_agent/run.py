#!/usr/bin/env python3
"""Viral Urun Kesif Ajani — CLI giris noktasi.

Kullanim:
    python run.py                 # tam pipeline (.env'de LLM anahtari varsa LLM'li)
    python run.py --provider nvidia   # NVIDIA Nemotron 3 Ultra ile puanla
    python run.py --llm-check     # sadece LLM baglantisini test et, cikis
    python run.py --no-llm        # LLM adimlarini zorla atla (deterministik rapor)
    python run.py --learn         # once rubric'i yeniden ogren (trait mining)
    python run.py --max 30        # aday sayisini sinirla
    python run.py --inject-test   # Turkiye kapisini test icin bilinen yaygin urun enjekte et
    python run.py --telegram      # rapor kurulunca Telegram'a (TELEGRAM_CHAT_ID) gonder

Cekirdek akis vpa/pipeline.run_pipeline() icindedir; bot.py de ayni fonksiyonu cagirir.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from vpa.settings import Settings
from vpa.cache import DiskCache
from vpa.llm.client import LLMClient
from vpa.llm.providers import PROVIDER_NAMES
from vpa.pipeline import run_pipeline
from vpa.report import render


def main() -> int:
    ap = argparse.ArgumentParser(description="Turkiye icin viral urun kesif ajani")
    ap.add_argument("--no-llm", action="store_true", help="LLM adimlarini atla")
    ap.add_argument("--provider", choices=PROVIDER_NAMES, default="",
                    help="LLM saglayicisi (varsayilan: config.yaml/.env)")
    ap.add_argument("--llm-check", action="store_true",
                    help="LLM baglantisini tek kucuk cagri ile test et ve cik")
    ap.add_argument("--learn", action="store_true", help="rubric'i yeniden ogren")
    ap.add_argument("--max", type=int, default=None, help="max aday sayisi")
    ap.add_argument("--inject-test", action="store_true",
                    help="TR kapisi testi icin bilinen yaygin urun enjekte et")
    ap.add_argument("--telegram", action="store_true",
                    help="rapor kurulunca Telegram'a (TELEGRAM_CHAT_ID) gonder")
    ap.add_argument("--repeat-ok", action="store_true",
                    help="daha once gosterilen urunler de gelebilsin (gecmis filtresini kapat)")
    args = ap.parse_args()

    settings = Settings()
    cache = DiskCache(settings.cache_dir, settings.config["cache"]["ttl_hours"])
    llm = LLMClient.from_settings(settings, cache, disabled=args.no_llm,
                                  provider=args.provider)
    print(f"[llm] {llm.label}")

    if args.llm_check:
        return _llm_check(llm)

    report = run_pipeline(
        settings, cache, llm,
        max_candidates=args.max, inject_test=args.inject_test, learn=args.learn,
        allow_repeats=args.repeat_ok,
    )

    # RAPOR (JSON + Markdown)
    json_p, md_p = render.write(report, settings.output_dir, date.today().isoformat())
    print(f"[rapor] {md_p}\n[rapor] {json_p}")

    # TELEGRAM (istege bagli)
    if args.telegram:
        _push_telegram(settings, report)

    return 0 if report.ranked else 1


def _llm_check(llm) -> int:
    """Anahtar/uc dogru mu? Tek kucuk JSON cagrisi yapar, ucuzdur."""
    if not llm.enabled:
        print("[llm-check] LLM kapali: .env'e anahtar ekleyin "
              "(NVIDIA_API_KEY / OPENROUTER_API_KEY / ANTHROPIC_API_KEY).")
        return 1
    print(f"[llm-check] {llm.cfg.provider} -> {llm.cfg.base_url or 'anthropic SDK'}")
    result = llm.json_call(
        'Sadece su JSON\'u don, baska hicbir sey yazma: '
        '{"ok": true, "model": "<kullandigin modelin adi>"}',
        label="llm-check",
    )
    if result is None:
        print("[llm-check] BASARISIZ — yukaridaki hata mesajina bakin.")
        return 1
    print(f"[llm-check] BASARILI — yanit: {result}")
    return 0


def _push_telegram(settings, report) -> None:
    from vpa.notify.telegram import TelegramClient

    if not settings.telegram_bot_token:
        print("[telegram] TELEGRAM_BOT_TOKEN yok — gonderim atlandi (.env'e ekleyin).")
        return
    if not settings.telegram_chat_id:
        print("[telegram] TELEGRAM_CHAT_ID yok — /start ile chat id'nizi ogrenip .env'e ekleyin.")
        return
    client = TelegramClient(settings.telegram_bot_token)
    cfg = settings.telegram_cfg
    ok = client.push_report(
        report, settings.telegram_chat_id,
        top_n=cfg.get("push_top_n", 5), send_images=cfg.get("send_images", True),
    )
    print(f"[telegram] gonderim {'basarili' if ok else 'basarisiz'}.")


if __name__ == "__main__":
    sys.exit(main())
