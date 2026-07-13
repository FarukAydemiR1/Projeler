"""Ham Telegram Bot API istemcisi (requests + long polling).

python-telegram-bot/async bagimliligi yok; mevcut vpa.http oturumu (proxy/CA-farkinda)
yeniden kullanilir. Inline butonlar reply_markup JSON ile desteklenir."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .. import http
from ..models import Report
from . import format as fmt

API_BASE = "https://api.telegram.org/bot{token}/{method}"


class TelegramError(Exception):
    pass


class TelegramClient:
    def __init__(self, token: str, timeout: int = 30):
        if not token:
            raise TelegramError("TELEGRAM_BOT_TOKEN bos.")
        self.token = token
        self.timeout = timeout

    # ---- dusuk seviye ----
    def _api(self, method: str, payload: dict | None = None, *,
             files: dict | None = None, timeout: int | None = None) -> Any:
        """Telegram metodunu cagirir; result doner. Hata durumunda TelegramError."""
        url = API_BASE.format(token=self.token, method=method)
        to = timeout or self.timeout
        backoff = 2.0
        last_err = "bilinmiyor"
        for attempt in range(3):
            try:
                if files:
                    r = http.session().post(url, data=payload, files=files, timeout=to)
                else:
                    r = http.session().post(url, json=payload or {}, timeout=to)
                data = r.json()
                if data.get("ok"):
                    return data.get("result")
                # 429: rate limit -> retry_after kadar bekle
                if data.get("error_code") == 429:
                    retry = data.get("parameters", {}).get("retry_after", int(backoff))
                    time.sleep(retry)
                    continue
                last_err = data.get("description", str(data))
                # kalici hata (400/403 vb.) -> tekrar denemenin anlami yok
                raise TelegramError(f"{method}: {last_err}")
            except (ValueError, OSError) as e:  # JSON/ag hatasi -> retry
                last_err = str(e)
            if attempt < 2:
                time.sleep(backoff)
                backoff *= 2
        raise TelegramError(f"{method}: {last_err}")

    # ---- yuksek seviye ----
    def get_me(self) -> dict:
        return self._api("getMe")

    def send_message(self, chat_id: str | int, text: str, *,
                     reply_markup: dict | None = None, parse_mode: str = "HTML",
                     disable_preview: bool = True) -> dict:
        payload = {
            "chat_id": chat_id, "text": fmt.clip(text),
            "parse_mode": parse_mode, "disable_web_page_preview": disable_preview,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._api("sendMessage", payload)

    def send_photo(self, chat_id: str | int, photo_url: str, *,
                   caption: str = "", parse_mode: str = "HTML",
                   reply_markup: dict | None = None) -> dict:
        payload = {"chat_id": chat_id, "photo": photo_url,
                   "caption": fmt.clip(caption, 1024), "parse_mode": parse_mode}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._api("sendPhoto", payload)

    def send_document(self, chat_id: str | int, file_path: str | Path, *,
                      caption: str = "") -> dict:
        path = Path(file_path)
        with open(path, "rb") as f:
            return self._api("sendDocument", {"chat_id": chat_id, "caption": fmt.clip(caption, 1024)},
                             files={"document": (path.name, f)})

    def answer_callback_query(self, callback_id: str, text: str = "") -> Any:
        return self._api("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})

    def get_updates(self, offset: int | None = None, poll_timeout: int = 25) -> list[dict]:
        payload = {"timeout": poll_timeout, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            payload["offset"] = offset
        # long polling: HTTP timeout, poll_timeout'tan biraz uzun olmali
        return self._api("getUpdates", payload, timeout=poll_timeout + 10) or []

    # ---- rapor gonderimi (run.py --telegram ve bot /tara) ----
    def push_report(self, report: Report, chat_id: str | int, *,
                    top_n: int = 5, send_images: bool = True) -> bool:
        """Ozet + en iyi top_n urun (foto+caption) + reklam konseptlerini gonderir."""
        try:
            self.send_message(chat_id, fmt.format_summary(report))
            for i, cand in enumerate(report.ranked[:top_n], 1):
                caption = fmt.format_candidate(cand, i)
                if send_images and cand.image_url:
                    try:
                        self.send_photo(chat_id, cand.image_url, caption=caption)
                        continue
                    except TelegramError:
                        pass  # gorsel gecersizse metne dus
                self.send_message(chat_id, caption)
            for ad in report.ads[:top_n]:
                self.send_message(chat_id, fmt.format_ad(ad))
            return True
        except TelegramError as e:
            print(f"[telegram] push_report hatasi: {e}")
            return False


def inline_keyboard(rows: list[list[tuple[str, str]]]) -> dict:
    """[[(etiket, callback_data)]] -> Telegram inline klavye JSON."""
    return {"inline_keyboard": [
        [{"text": label, "callback_data": data} for label, data in row] for row in rows
    ]}
