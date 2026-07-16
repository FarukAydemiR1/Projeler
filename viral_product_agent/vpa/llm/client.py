"""Anthropic SDK sarmalayicisi.

ANTHROPIC_API_KEY varsa gercek cagri yapar; yoksa "devre disi" moduna duser:
- json_call() None doner, cagiran taraf deterministik fallback kullanir,
- doldurulamayan promptlar output/pending_llm_prompts.md dosyasina yazilir ki
  anahtar eklendiginde (veya bir Claude oturumunda elle) tamamlanabilsin.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..cache import DiskCache

MODEL = "claude-sonnet-5"  # tek sabit: model degisimi tek satir


class LLMClient:
    def __init__(self, api_key: str, cache: DiskCache, output_dir: Path):
        self.enabled = bool(api_key)
        self.cache = cache
        self.pending_file = output_dir / "pending_llm_prompts.md"
        self._client = None
        if self.enabled:
            import anthropic  # sadece anahtar varsa import et
            self._client = anthropic.Anthropic(api_key=api_key)

    def json_call(self, prompt: str, label: str = "") -> dict | list | None:
        """Prompt gonderir, yanittaki ilk JSON blogunu parse eder. Devre disi ise None."""
        if not self.enabled:
            self._record_pending(label, prompt)
            return None
        cache_key = f"llm:{MODEL}:{prompt}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        msg = self._client.messages.create(
            model=MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text")
        parsed = self._extract_json(text)
        if parsed is not None:
            self.cache.set(cache_key, parsed)
        return parsed

    @staticmethod
    def _extract_json(text: str):
        m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        raw = m.group(1) if m else text
        start = min((i for i in (raw.find("{"), raw.find("[")) if i >= 0), default=-1)
        if start < 0:
            return None
        try:
            return json.loads(raw[start:])
        except json.JSONDecodeError:
            return None

    def _record_pending(self, label: str, prompt: str) -> None:
        with open(self.pending_file, "a", encoding="utf-8") as f:
            f.write(f"\n\n## {label}\n\n```\n{prompt}\n```\n")
