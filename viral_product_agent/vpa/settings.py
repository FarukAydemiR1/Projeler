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
