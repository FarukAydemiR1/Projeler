"""Puanlama cetveli (rubric) yukleme. data/rubric.json trait_miner tarafindan
uretilir/yenilenir; insan gozden gecirip elle duzeltebilir (seffaf ogrenme)."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_DIMENSIONS = [
    "problem_or_emotion", "demonstrability", "cultural_fit_tr",
    "seasonality", "shareability", "sourcing_feasibility",
]


def load(data_dir: Path) -> dict:
    path = data_dir / "rubric.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"traits": [], "dimensions": [{"name": d} for d in DEFAULT_DIMENSIONS]}
