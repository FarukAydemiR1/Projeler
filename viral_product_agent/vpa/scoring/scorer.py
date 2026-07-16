"""Nihai skor: deterministik sinyaller + LLM boyutlarinin agirlikli harmani.

final = SUM(w_i * signal_i) + SUM(w_j * llm_dim_j / 10), aktif agirliklara normalize.
LLM devre disi ise yalnizca deterministik katman kullanilir ve rapor bunu belirtir."""
from __future__ import annotations

import json

from ..llm import prompts
from ..models import Candidate

LLM_DIMS = ["problem_or_emotion", "demonstrability", "cultural_fit_tr",
            "seasonality", "shareability", "sourcing_feasibility"]


def score_all(candidates: list[Candidate], settings, llm) -> None:
    weights = settings.weights
    for c in candidates:
        if llm.enabled:
            _llm_score(c, llm)
        c.final_score = _blend(c, weights, llm_used=llm.enabled)
    candidates.sort(key=lambda c: c.final_score, reverse=True)


def _llm_score(c: Candidate, llm) -> None:
    result = llm.json_call(
        prompts.SCORE_CANDIDATE.format(
            title=c.title, description=c.description or "-",
            source=c.source, url=c.url,
            price=c.price_usd if c.price_usd is not None else "bilinmiyor",
        ),
        label=f"score:{c.title[:60]}",
    )
    if isinstance(result, dict):
        scores = result.get("scores", {})
        c.llm_scores = {k: float(scores.get(k, 0)) for k in LLM_DIMS if k in scores}
        c.llm_rationale = result.get("rationale", {})


def _blend(c: Candidate, weights: dict[str, float], llm_used: bool) -> float:
    total, active_weight = 0.0, 0.0
    for name, w in weights.items():
        if w <= 0:
            continue
        if name in c.signals:
            total += w * c.signals[name]
            active_weight += w
        elif llm_used and name in c.llm_scores:
            total += w * (c.llm_scores[name] / 10.0)
            active_weight += w
    # aktif agirliga normalize: LLM kapaliyken skorlar yine 0..1 araliginda kalir
    return round(total / active_weight, 4) if active_weight else 0.0
