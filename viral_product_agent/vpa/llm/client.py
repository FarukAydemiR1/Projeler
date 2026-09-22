"""Saglayicidan bagimsiz LLM sarmalayicisi (Nemotron 3 Ultra, Claude, yerel uclar).

Anahtar varsa gercek cagri yapar; yoksa "devre disi" moduna duser:
- json_call() None doner, cagiran taraf deterministik fallback kullanir,
- doldurulamayan promptlar output/pending_llm_prompts.md dosyasina yazilir ki
  anahtar eklendiginde (veya bir Claude oturumunda elle) tamamlanabilsin.

Saglayici/model secimi vpa/llm/providers.py icindedir (config.yaml llm bolumu + .env).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..cache import DiskCache
from . import providers

# Ust uste bu kadar basarisiz cagridan sonra LLM o run icin kapatilir: yanlis anahtarla
# 60 aday x timeout beklemek yerine deterministik moda duseriz.
MAX_CONSECUTIVE_FAILURES = 3

_THINK_BLOCK = re.compile(r"<think>.*?(?:</think>|\Z)", re.DOTALL | re.IGNORECASE)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class LLMClient:
    def __init__(self, cfg: providers.LLMConfig | None, cache: DiskCache, output_dir: Path):
        self.cfg = cfg
        self.cache = cache
        self.pending_file = output_dir / "pending_llm_prompts.md"
        self._backend = providers.build(cfg) if cfg else None
        self._failures = 0
        self._dead = False

    @classmethod
    def from_settings(cls, settings, cache: DiskCache, *, disabled: bool = False,
                      provider: str = "") -> "LLMClient":
        """run.py/bot.py giris noktasi: ayarlardan saglayiciyi cozer ve istemciyi kurar."""
        cfg = None
        if not disabled:
            try:
                cfg = settings.resolve_llm(provider)
            except ValueError as exc:
                print(f"[llm] {exc} — LLM devre disi.")
        return cls(cfg, cache, settings.output_dir)

    @property
    def enabled(self) -> bool:
        return self._backend is not None and not self._dead

    @property
    def label(self) -> str:
        return self.cfg.describe() if self.cfg else "devre disi"

    def json_call(self, prompt: str, label: str = "") -> dict | list | None:
        """Prompt gonderir, yanittaki ilk JSON blogunu parse eder. Devre disi ise None."""
        if not self.enabled:
            self._record_pending(label, prompt)
            return None
        cache_key = f"llm:{self.cfg.fingerprint}:{prompt}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        text = self._backend.complete(prompt)
        if text is None:
            self._on_failure(label, prompt, "yanit alinamadi")
            return None
        parsed = extract_json(text)
        if parsed is None:
            self._on_failure(label, prompt, "yanit JSON'a cevrilemedi")
            return None

        self._failures = 0
        self.cache.set(cache_key, parsed)
        return parsed

    def _on_failure(self, label: str, prompt: str, reason: str) -> None:
        self._failures += 1
        self._record_pending(label, prompt)
        if self._failures >= MAX_CONSECUTIVE_FAILURES:
            self._dead = True
            print(f"[llm] {self.label}: {self._failures} cagri ust uste basarisiz ({reason}). "
                  "Bu run icin LLM kapatildi; deterministik siralamaya gecildi.")

    def _record_pending(self, label: str, prompt: str) -> None:
        with open(self.pending_file, "a", encoding="utf-8") as f:
            f.write(f"\n\n## {label}\n\n```\n{prompt}\n```\n")


def as_text(value) -> str:
    """Metin beklenen alan liste/sozluk gelebilir (modelden modele degisir) — duzlestirir.

    Ham repr ("[{'time': '0-2sn', ...}]") rapora/Telegram'a dusmesin diye.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return "evet" if value else "hayir"
    if isinstance(value, dict):
        return ", ".join(f"{k}: {as_text(v)}" for k, v in value.items() if as_text(v))
    if isinstance(value, (list, tuple)):
        return " | ".join(part for part in (as_text(v) for v in value) if part)
    return str(value)


def as_mapping(value) -> dict[str, str]:
    """Sozluk beklenen alan string/liste gelirse bos doner — cagiran .get() ile cakilmasin."""
    if not isinstance(value, dict):
        return {}
    return {str(k): as_text(v) for k, v in value.items()}


_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")


def as_score(value) -> float | None:
    """0-10 beklenen alan 8, "8", "8/10" veya "8 puan" gelebilir; cozulemezse None."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        match = _NUMBER.search(str(value))
        if not match:
            return None
        number = float(match.group().replace(",", "."))
    return min(max(number, 0.0), 10.0)


def extract_json(text: str) -> dict | list | None:
    """Serbest metin icindeki ilk gecerli JSON nesnesini/dizisini cikarir.

    Dusunen modeller (Nemotron gibi) JSON'un onune <think> blogu, arkasina da aciklama
    ekleyebilir; bu yuzden dengeli parantez taramasi yapilir, ham json.loads yetmez.
    """
    if not text:
        return None
    cleaned = _THINK_BLOCK.sub("", text)
    fenced = _FENCE.search(cleaned)
    for candidate in ([fenced.group(1)] if fenced else []) + [cleaned]:
        parsed = _scan(candidate)
        if parsed is not None:
            return parsed
    return None


def _scan(text: str) -> dict | list | None:
    for i, ch in enumerate(text):
        if ch in "{[":
            parsed = _balanced(text, i)
            if parsed is not None:
                return parsed
    return None


def _balanced(text: str, start: int) -> dict | list | None:
    """text[start] konumundaki parantezi esleyip araligi JSON olarak cozmeyi dener."""
    opener = text[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None
