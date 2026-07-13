#!/usr/bin/env python3
"""Telegram botu — @UrunuTAkibiBot arayuzu (long polling, async'siz).

Ozellikler:
  /tara   — anlik tarama baslat, sonuclari (top urunler + reklam) gonder
  /liste  — son taramanin urunlerini buton menusuyle gez
  /rapor  — son raporu dosya olarak gonder
  butonlar — urun detayi + reklam konsepti
  gunluk otomatik tarama (config.telegram.daily_scan.enabled)

Calistirma:
  1) .env icine TELEGRAM_BOT_TOKEN (BotFather'dan) ve tarama sonrasi /start ile
     ogrendiginiz TELEGRAM_CHAT_ID yazin.
  2) python bot.py

Guvenlik: yalnizca yetkili kullanicilar (TELEGRAM_CHAT_ID / TELEGRAM_ALLOWED_USERS)
komut calistirabilir. Token'i asla paylasmayin; sizarsa BotFather /revoke.
"""
from __future__ import annotations

import glob
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from vpa.settings import Settings
from vpa.cache import DiskCache
from vpa.llm.client import LLMClient
from vpa.models import Report
from vpa.pipeline import run_pipeline
from vpa.report import render
from vpa.notify import format as fmt
from vpa.notify.telegram import TelegramClient, TelegramError, inline_keyboard


class Bot:
    def __init__(self):
        self.settings = Settings()
        self.cache = DiskCache(self.settings.cache_dir, self.settings.config["cache"]["ttl_hours"])
        self.tg = TelegramClient(self.settings.telegram_bot_token)
        self.last_report: Report | None = _load_latest_report(self.settings.output_dir)
        self.offset: int | None = None
        self.next_scan = _compute_next_scan(self.settings.telegram_cfg)

    # ---------- ana dongu ----------
    def run(self) -> None:
        me = self.tg.get_me()
        print(f"[bot] @{me.get('username')} calisiyor. Durdurmak icin Ctrl+C.")
        if self.next_scan:
            print(f"[bot] gunluk otomatik tarama: {self.next_scan}")
        while True:
            try:
                self._maybe_daily_scan()
                updates = self.tg.get_updates(self.offset, poll_timeout=25)
                for upd in updates:
                    self.offset = upd["update_id"] + 1
                    self._handle(upd)
            except TelegramError as e:
                print(f"[bot] telegram hatasi: {e}; 5sn sonra tekrar.")
                time.sleep(5)
            except KeyboardInterrupt:
                print("\n[bot] kapatiliyor.")
                return

    # ---------- guncelleme yonlendirme ----------
    def _handle(self, upd: dict) -> None:
        if "callback_query" in upd:
            self._on_callback(upd["callback_query"])
        elif "message" in upd and "text" in upd["message"]:
            self._on_message(upd["message"])

    def _on_message(self, msg: dict) -> None:
        chat_id = msg["chat"]["id"]
        user_id = msg.get("from", {}).get("id", 0)
        text = msg["text"].strip()
        cmd = text.split()[0].lstrip("/").split("@")[0].lower()

        if cmd in ("start", "help"):
            self._cmd_help(chat_id, user_id)
            return

        # buradan sonrasi yetki ister
        if not self.settings.is_allowed_user(user_id):
            self.tg.send_message(chat_id,
                "⛔ Bu botu yalnızca sahibi kullanabilir.\n"
                f"Sizin kullanıcı id'niz: <code>{user_id}</code>\n"
                "Sahibiyseniz bu id'yi <code>TELEGRAM_ALLOWED_USERS</code>'a ekleyin.")
            return

        if cmd == "tara":
            self._cmd_scan(chat_id)
        elif cmd == "liste":
            self._cmd_list(chat_id)
        elif cmd == "rapor":
            self._cmd_report_file(chat_id)
        else:
            self.tg.send_message(chat_id, "Bilinmeyen komut. /help yazın.")

    def _on_callback(self, cq: dict) -> None:
        user_id = cq.get("from", {}).get("id", 0)
        chat_id = cq["message"]["chat"]["id"]
        data = cq.get("data", "")
        self.tg.answer_callback_query(cq["id"])
        if not self.settings.is_allowed_user(user_id):
            return
        if not self.last_report:
            self.tg.send_message(chat_id, "Önce /tara ile bir tarama yapın.")
            return
        kind, _, idx = data.partition(":")
        try:
            i = int(idx)
        except ValueError:
            return
        if kind == "urun" and 0 <= i < len(self.last_report.ranked):
            cand = self.last_report.ranked[i]
            caption = fmt.format_candidate(cand, i + 1)
            kb = self._ad_button(cand, i)
            if cand.image_url:
                try:
                    self.tg.send_photo(chat_id, cand.image_url, caption=caption, reply_markup=kb)
                    return
                except TelegramError:
                    pass
            self.tg.send_message(chat_id, caption, reply_markup=kb)
        elif kind == "reklam":
            ad = self._ad_for(i)
            if ad:
                self.tg.send_message(chat_id, fmt.format_ad(ad))
            else:
                self.tg.send_message(chat_id, "Bu ürün için reklam konsepti üretilmemiş.")

    # ---------- komutlar ----------
    def _cmd_help(self, chat_id: int, user_id: int) -> None:
        self.tg.send_message(chat_id,
            "<b>🇹🇷 Viral Ürün Keşif Botu</b>\n\n"
            "/tara — yeni tarama başlat, sonuçları gönder\n"
            "/liste — son taramanın ürünlerini buton menüsüyle gez\n"
            "/rapor — son raporu dosya olarak al\n\n"
            f"Sohbet id'niz: <code>{chat_id}</code>\n"
            "(Otomatik gönderim için bunu <code>TELEGRAM_CHAT_ID</code>'ye yazın.)")

    def _cmd_scan(self, chat_id: int) -> None:
        self.tg.send_message(chat_id, "🔎 Tarıyorum, birkaç dakika sürebilir…")
        llm = LLMClient(self.settings.anthropic_api_key, self.cache, self.settings.output_dir)
        report = run_pipeline(self.settings, self.cache, llm)
        self.last_report = report
        render.write(report, self.settings.output_dir, report.generated_at)
        cfg = self.settings.telegram_cfg
        if report.ranked:
            self.tg.push_report(report, chat_id, top_n=cfg.get("push_top_n", 5),
                                send_images=cfg.get("send_images", True))
            self._cmd_list(chat_id)
        else:
            self.tg.send_message(chat_id,
                fmt.format_summary(report) +
                "\n\n⚠️ Aday bulunamadı (kaynaklar engellenmiş olabilir). "
                "Botu kendi bilgisayarınızda çalıştırmayı deneyin.")

    def _cmd_list(self, chat_id: int) -> None:
        if not self.last_report or not self.last_report.ranked:
            self.tg.send_message(chat_id, "Henüz ürün yok. /tara ile tarama yapın.")
            return
        rows = []
        for i, c in enumerate(self.last_report.ranked[:15]):
            label = f"{i + 1}. {c.title[:40]} ({c.final_score:.2f})"
            rows.append([(label, f"urun:{i}")])
        self.tg.send_message(chat_id, "📋 <b>Ürünler</b> — detay için dokun:",
                             reply_markup=inline_keyboard(rows))

    def _cmd_report_file(self, chat_id: int) -> None:
        md = _latest_file(self.settings.output_dir, "*_report.md")
        if not md:
            self.tg.send_message(chat_id, "Rapor dosyası yok. Önce /tara yapın.")
            return
        try:
            self.tg.send_document(chat_id, md, caption="Son tarama raporu")
        except TelegramError as e:
            self.tg.send_message(chat_id, f"Dosya gönderilemedi: {e}")

    # ---------- yardimcilar ----------
    def _ad_for(self, product_index: int):
        if not self.last_report or product_index >= len(self.last_report.ranked):
            return None
        title = self.last_report.ranked[product_index].title
        for ad in self.last_report.ads:
            if ad.product_title == title:
                return ad
        return None

    def _ad_button(self, cand, i: int) -> dict | None:
        return inline_keyboard([[("📣 Reklam konsepti", f"reklam:{i}")]]) if self._ad_for(i) else None

    def _maybe_daily_scan(self) -> None:
        if not self.next_scan or datetime.now() < self.next_scan:
            return
        chat_id = self.settings.telegram_chat_id
        if chat_id:
            print("[bot] gunluk otomatik tarama basliyor.")
            self._cmd_scan(int(chat_id) if str(chat_id).lstrip("-").isdigit() else chat_id)
        # bir sonraki gune kur
        self.next_scan = _compute_next_scan(self.settings.telegram_cfg, after=self.next_scan)


def _compute_next_scan(tg_cfg: dict, after: datetime | None = None) -> datetime | None:
    daily = tg_cfg.get("daily_scan", {})
    if not daily.get("enabled"):
        return None
    hour = int(daily.get("hour", 9))
    base = (after or datetime.now())
    nxt = base.replace(hour=hour, minute=0, second=0, microsecond=0)
    if nxt <= datetime.now():
        nxt += timedelta(days=1)
    return nxt


def _latest_file(output_dir: Path, pattern: str) -> str | None:
    files = sorted(glob.glob(str(output_dir / pattern)))
    return files[-1] if files else None


def _load_latest_report(output_dir: Path) -> Report | None:
    path = _latest_file(output_dir, "*_report.json")
    if not path:
        return None
    try:
        return Report.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError, TypeError):
        return None


def main() -> int:
    settings = Settings()
    if not settings.telegram_bot_token:
        print("HATA: TELEGRAM_BOT_TOKEN tanimli degil.\n"
              "1) @BotFather'dan token alin (sizdiysa /revoke ile yenileyin).\n"
              "2) viral_product_agent/.env dosyasina TELEGRAM_BOT_TOKEN=... yazin.\n"
              "3) Tekrar: python bot.py")
        return 1
    Bot().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
