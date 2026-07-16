"""Gereksinim #1: viral urunlerin ortak yonlerini ogren -> data/rubric.json.

Ara sira calistirilir (her run'da degil): seed ornekler LLM'e verilir, ortak
ozellikler + puanlama boyutlari cikarilir ve DISKTE SAKLANIR — boylece 'ogrenme'
kara kutu degil, insanin gozden gecirip duzeltebildigi bir dosyadir."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from ..llm import prompts


def mine(settings, llm) -> dict | None:
    seed_path = settings.data_dir / "seed_viral_products.yaml"
    if not seed_path.exists():
        return None
    seed = yaml.safe_load(seed_path.read_text(encoding="utf-8"))
    result = llm.json_call(
        prompts.TRAIT_MINING.format(seed_data=yaml.safe_dump(seed, allow_unicode=True)),
        label="trait_mining",
    )
    if isinstance(result, dict) and result.get("dimensions"):
        out = settings.data_dir / "rubric.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    return None
