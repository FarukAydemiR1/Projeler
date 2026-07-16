"""Diske JSON cache. Her dis cagri (HTTP/LLM) buradan gecer: re-run ucuz, kota korunur."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable


class DiskCache:
    def __init__(self, cache_dir: Path, ttl_hours: float = 24):
        self.dir = cache_dir
        self.ttl = ttl_hours * 3600
        self.dir.mkdir(exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.dir / (hashlib.sha256(key.encode()).hexdigest()[:32] + ".json")

    def get(self, key: str) -> Any | None:
        p = self._path(key)
        if not p.exists():
            return None
        try:
            entry = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if time.time() - entry["ts"] > self.ttl:
            return None
        return entry["value"]

    def set(self, key: str, value: Any) -> None:
        self._path(key).write_text(
            json.dumps({"ts": time.time(), "value": value}, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_or(self, key: str, fn: Callable[[], Any]) -> Any:
        hit = self.get(key)
        if hit is not None:
            return hit
        value = fn()
        if value is not None:
            self.set(key, value)
        return value
