"""Gecmis hafizasi — ajanin AYNI urunu iki kez getirmemesi icin.

data/history.json'da daha once GOSTERILEN urunlerin normalize anahtarlari + run
sayaci tutulur. Her tarama once bu anahtarlari haric tutar (fresh), sonra yeni
gosterilenleri kaydeder. Boylece her tarama oncekinden farkli urunler verir.

Yerel/kisisel durum dosyasidir (git-ignored) — her kullanicinin kendi gecmisi olur."""
from __future__ import annotations

import json
from pathlib import Path

from .models import Candidate

MAX_KEEP = 3000  # hafiza sinirsiz buyumesin; en eski anahtarlar dusurulur


class HistoryStore:
    def __init__(self, path: Path):
        self.path = path
        self.seen: list[str] = []      # sirali (eskiden yeniye) — kirpma icin
        self.run_count: int = 0
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.seen = list(data.get("seen", []))
            self.run_count = int(data.get("run_count", 0))
        except (json.JSONDecodeError, OSError, ValueError):
            pass  # bozuk gecmis dosyasi akisi bozmasin; sifirdan baslar

    @property
    def seen_set(self) -> set[str]:
        return set(self.seen)

    def filter_unseen(self, candidates: list[Candidate]) -> tuple[list[Candidate], int]:
        """Daha once gosterilmemis adaylari doner. (fresh, atlanan_sayisi)."""
        seen = self.seen_set
        fresh = [c for c in candidates if c.key() not in seen]
        return fresh, len(candidates) - len(fresh)

    def record(self, candidates: list[Candidate]) -> None:
        """Bu taramada gosterilen urunleri hafizaya ekle ve run sayacini artir."""
        seen = self.seen_set
        for c in candidates:
            k = c.key()
            if k and k not in seen:
                self.seen.append(k)
                seen.add(k)
        if len(self.seen) > MAX_KEEP:
            self.seen = self.seen[-MAX_KEEP:]
        self.run_count += 1
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text(
            json.dumps({"seen": self.seen, "run_count": self.run_count},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
