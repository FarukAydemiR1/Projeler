"""Varsayılan yapılandırma: izleme listeleri ve parametreler.

`config.yaml` varsa oradan okur, yoksa buradaki varsayılanları kullanır.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

import yaml

# Örnek izleme listeleri — kendi listeni config.yaml ile değiştirebilirsin.
DEFAULT_BIST: List[str] = [
    "THYAO.IS", "ASELS.IS", "SISE.IS", "KCHOL.IS", "EREGL.IS",
    "GARAN.IS", "AKBNK.IS", "TUPRS.IS", "BIMAS.IS", "FROTO.IS",
    "SAHOL.IS", "PGSUS.IS", "TCELL.IS", "ISCTR.IS", "YKBNK.IS",
    "TOASO.IS", "KRDMD.IS", "PETKM.IS", "HEKTS.IS", "OYAKC.IS",
]

DEFAULT_US: List[str] = [
    "AAPL", "MSFT", "NVDA", "AMD", "TSLA",
    "AMZN", "META", "GOOGL", "NFLX", "AVGO",
    "PLTR", "SMCI", "CRM", "UBER", "COIN",
    "SHOP", "MU", "INTC", "QCOM", "ARM",
]

DEFAULTS = {
    "horizon": 10,          # kaç gün ileriye bakılıyor
    "rise_threshold": 0.08, # yükseliş olayı eşiği (%8)
    "model_weight": 0.6,
    "rule_weight": 0.4,
    "train_period": "5y",
    "scan_period": "1y",
    "min_score": 0.45,
}


def load_dotenv(path: Optional[str | Path] = None) -> Optional[str]:
    """`.env` dosyasını okuyup os.environ'a yükler (best-effort, bağımlılıksız).

    GÜVENLİK: Telegram token'ı gibi gizli bilgiler .env dosyasına yazılır ve
    bu dosya .gitignore'da olduğu için repoya ASLA gönderilmez. Zaten tanımlı
    olan ortam değişkenlerinin üzerine yazmaz (gerçek ortam önceliklidir).

    Yüklenen dosyanın yolunu döner (bir şey yüklendiyse), aksi halde None.
    """
    candidates = []
    if path:
        candidates.append(Path(path))
    candidates.append(Path.cwd() / ".env")
    candidates.append(Path(__file__).resolve().parent.parent / ".env")

    for cand in candidates:
        if not cand or not cand.exists():
            continue
        try:
            for raw in cand.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                # opsiyonel `export KEY=...` biçimini de kabul et
                if key.startswith("export "):
                    key = key[len("export "):].strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
            return str(cand)
        except Exception:
            return None  # .env okunamadıysa sessizce geç
    return None


def load_config(path: str | None = None) -> dict:
    """config.yaml'ı yükler (varsa), varsayılanlarla birleştirir.

    Ayrıca varsa `.env` dosyasını ortam değişkenlerine yükler (gizli bilgiler
    için — bkz. load_dotenv)."""
    load_dotenv()
    cfg = {
        "bist": list(DEFAULT_BIST),
        "us": list(DEFAULT_US),
        **DEFAULTS,
    }
    candidates = []
    if path:
        candidates.append(Path(path))
    candidates.append(Path.cwd() / "config.yaml")
    candidates.append(Path(__file__).resolve().parent.parent / "config.yaml")

    for cand in candidates:
        if cand and cand.exists():
            with open(cand, "r", encoding="utf-8") as fh:
                user = yaml.safe_load(fh) or {}
            cfg.update({k: v for k, v in user.items() if v is not None})
            cfg["_config_path"] = str(cand)
            break
    return cfg


def watchlist(cfg: dict, market: str) -> List[str]:
    """market: 'bist' | 'us' | 'all'"""
    market = market.lower()
    if market == "bist":
        return list(cfg.get("bist", []))
    if market == "us":
        return list(cfg.get("us", []))
    if market == "all":
        return list(cfg.get("bist", [])) + list(cfg.get("us", []))
    raise ValueError(f"Bilinmeyen market: {market} (bist|us|all)")
