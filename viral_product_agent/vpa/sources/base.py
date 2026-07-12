"""Kaynak adaptoru arayuzu. Saglam (Reddit/RSS) ve kirilgan (scrape) kaynaklar ayni
sozlesmeyi uygular; kirilgan olanlar hata durumunda bos liste doner, run durmaz."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Candidate


class Source(ABC):
    name: str = "base"
    reliability: str = "medium"   # high / medium / low — rapora provenans olarak gecer

    def __init__(self, settings, cache):
        self.settings = settings
        self.cache = cache
        self.cfg = settings.source_cfg(self.name)

    @property
    def enabled(self) -> bool:
        return bool(self.cfg.get("enabled", False))

    def safe_fetch(self) -> tuple[list[Candidate], str]:
        """(adaylar, durum) doner. Hata yutulur ve durum stringine yazilir."""
        if not self.enabled:
            return [], "devre disi (config)"
        try:
            items = self.fetch()
            return items, f"ok ({len(items)} aday)"
        except Exception as e:  # tek kaynak cokse bile pipeline devam etmeli
            return [], f"hata: {type(e).__name__}: {e}"

    @abstractmethod
    def fetch(self) -> list[Candidate]:
        ...
