"""Bildirim katmanı: tarama sonuçlarını raporlar ve Telegram'a gönderir.

Telegram için bir bot gerekir:
  1. Telegram'da @BotFather'a `/newbot` yaz, token'ı al.
  2. Botunla bir konuşma başlat (bir mesaj at), sonra chat id'ni öğren:
     https://api.telegram.org/bot<TOKEN>/getUpdates  →  chat.id alanı
  3. Ortam değişkeni olarak ver:
        export TELEGRAM_BOT_TOKEN="123456:ABC-..."
        export TELEGRAM_CHAT_ID="987654321"
     (veya config.yaml -> telegram: {chat_id: ...}; token'ı asla config'e yazma)

Token/chat id yoksa rapor sadece konsola basılır — ajan yine çalışır.
"""

from __future__ import annotations

import os
from datetime import date
from typing import List, Optional

import requests

from .screener import Signal

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
# Telegram tek mesajda en fazla 4096 karakter kabul eder.
_TELEGRAM_LIMIT = 4000

_LEVEL_EMOJI = {"GÜÇLÜ": "🚀", "AL": "📈", "İZLE": "👀", "ZAYIF": "·"}


def format_report(
    signals: List[Signal],
    min_score: float,
    title: str = "Hisse Sinyal Raporu",
    max_reasons: int = 3,
) -> str:
    """Sinyalleri Telegram/konsol dostu düz metin rapora çevirir."""
    lines = [f"📊 {title} — {date.today().isoformat()}"]
    passing = [s for s in signals if s.score >= min_score]

    if not passing:
        lines.append(f"\nBugün eşiği (≥{min_score:.2f}) geçen sinyal yok.")
        if signals:
            best = signals[0]
            lines.append(f"En yakın aday: {best.symbol} (skor {best.score:.2f})")
        return "\n".join(lines)

    lines.append(f"Eşik ≥{min_score:.2f} — {len(passing)} sinyal:\n")
    for s in passing:
        emoji = _LEVEL_EMOJI.get(s.level, "•")
        model_txt = "" if s.model_proba is None else f", model {s.model_proba:.0%}"
        lines.append(
            f"{emoji} {s.symbol}  [{s.level}]  skor {s.score:.2f}{model_txt}"
            f"  —  {s.price:.2f} {s.currency}".rstrip()
        )
        reasons = s.reasons[:max_reasons]
        if reasons:
            lines.append(f"    ↳ {'; '.join(reasons)}")

    lines.append("\n⚠️ Yatırım tavsiyesi değildir.")
    return "\n".join(lines)


class TelegramNotifier:
    """Telegram Bot API üzerinden mesaj gönderir."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = str(chat_id or os.environ.get("TELEGRAM_CHAT_ID", ""))

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, text: str) -> bool:
        """Mesajı gönderir; uzunsa parçalara böler. Başarı durumunu döner."""
        if not self.configured:
            return False
        ok = True
        for chunk in _split_chunks(text, _TELEGRAM_LIMIT):
            try:
                resp = requests.post(
                    _TELEGRAM_API.format(token=self.token),
                    json={"chat_id": self.chat_id, "text": chunk,
                          "disable_web_page_preview": True},
                    timeout=20,
                )
                ok = ok and resp.status_code == 200 and resp.json().get("ok", False)
            except Exception:
                ok = False
        return ok


def _split_chunks(text: str, limit: int) -> List[str]:
    """Metni satır sınırlarından bölerek limit altı parçalara ayırır."""
    if len(text) <= limit:
        return [text]
    chunks, current = [], []
    size = 0
    for line in text.split("\n"):
        # Tek satır bile limiti aşıyorsa sert kes
        while len(line) > limit:
            chunks.append(line[:limit])
            line = line[limit:]
        if size + len(line) + 1 > limit and current:
            chunks.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def deliver_report(
    text: str,
    telegram: Optional[TelegramNotifier] = None,
    quiet_console: bool = False,
) -> str:
    """Raporu iletir: Telegram yapılandırılmışsa gönderir, her durumda konsola
    da basar (quiet_console=True değilse). Nereye iletildiğini döner."""
    notifier = telegram or TelegramNotifier()
    sent = notifier.send(text) if notifier.configured else False

    if not quiet_console or not sent:
        print(text)

    if sent:
        return "telegram"
    if notifier.configured:
        return "console (telegram gönderimi BAŞARISIZ)"
    return "console (telegram yapılandırılmamış)"
