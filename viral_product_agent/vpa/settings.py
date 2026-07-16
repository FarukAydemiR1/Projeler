"""Ayar yukleme: .env + config.yaml. Eksik anahtar = ilgili ozellik kapali, crash yok."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv opsiyonel; yoksa sadece ortam degiskenleri okunur
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent


class Settings:
    def __init__(self, config_path: Path | None = None):
        if load_dotenv:
            load_dotenv(ROOT / ".env")
        path = config_path or ROOT / "config.yaml"
        with open(path, encoding="utf-8") as f:
            self.config: dict = yaml.safe_load(f)

        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        self.producthunt_token = os.environ.get("PRODUCTHUNT_TOKEN", "").strip()

        # Telegram (bot.py + run.py --telegram). Token .env'de tutulur, ASLA commit edilmez.
        self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        self.telegram_allowed_users = _parse_id_csv(os.environ.get("TELEGRAM_ALLOWED_USERS", ""))

        self.llm_enabled = bool(self.anthropic_api_key)
        self.output_dir = ROOT / "output"
        self.cache_dir = ROOT / ".cache"
        self.data_dir = ROOT / "data"
        self.output_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)

    def source_cfg(self, name: str) -> dict:
        return self.config.get("sources", {}).get(name, {})

    @property
    def weights(self) -> dict[str, float]:
        return self.config["weights"]

    @property
    def novelty_gate(self) -> float:
        return self.config["turkey_availability"]["novelty_gate"]

    @property
    def telegram_cfg(self) -> dict:
        return self.config.get("telegram", {})

    def is_allowed_user(self, user_id: int) -> bool:
        """Botu yalnizca owner kullanabilsin. allowed_users bossa TELEGRAM_CHAT_ID esas alinir."""
        if self.telegram_allowed_users:
            return user_id in self.telegram_allowed_users
        if self.telegram_chat_id:
            return str(user_id) == self.telegram_chat_id
        return False  # ne allowlist ne chat_id -> guvenli varsayilan: kimseye izin yok


def _parse_id_csv(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in raw.replace(" ", "").split(","):
        if part.lstrip("-").isdigit():
            ids.add(int(part))
    return ids
