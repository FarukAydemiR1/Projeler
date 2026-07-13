"""Kural motoru: anlaşılır teknik "yükseliş belirtileri".

Model bir kara-kutu olasılık üretir; kural motoru ise İNSAN OKUYABİLİR
gerekçe üretir ("hacim patlaması + 20g direnç kırılımı"). Her kural son
gündeki özellik satırına bakar, tetiklenirse belirtinin adını ve bir puan
katkısını döner.

Nihai sinyal skoru = model olasılığı ile kural skorunun ağırlıklı birleşimi
(bkz. screener.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

import numpy as np
import pandas as pd


@dataclass
class Rule:
    name: str            # kısa kod (golden_trend)
    label: str           # Türkçe açıklama
    weight: float        # 0..1 katkı
    test: Callable[[pd.Series], bool]


def _get(row: pd.Series, key: str, default=np.nan) -> float:
    val = row.get(key, default)
    return default if val is None else val


# Kurallar: her biri (isim, açıklama, ağırlık, test fonksiyonu).
# Ağırlıklar toplamı normalize edilerek 0..1 kural skoru üretilir.
RULES: List[Rule] = [
    Rule(
        "volume_surge", "Hacim patlaması (20g ort. üstü)", 1.0,
        lambda r: _get(r, "vol_ratio") > 1.8,
    ),
    Rule(
        "volume_building", "Hacim ivmesi (5g > 20g)", 0.6,
        lambda r: _get(r, "vol_trend") > 1.2,
    ),
    Rule(
        "golden_trend", "Yükselen trend (SMA20 > SMA50)", 0.9,
        lambda r: _get(r, "sma_ratio_20_50") > 0 and _get(r, "price_vs_sma50") > 0,
    ),
    Rule(
        "above_200", "Uzun vade yükseliş (fiyat > SMA200)", 0.7,
        lambda r: _get(r, "price_vs_sma200") > 0,
    ),
    Rule(
        "macd_bullish", "MACD pozitif kesişim", 0.8,
        lambda r: _get(r, "macd_above_signal") >= 1 and _get(r, "macd_hist_norm") > 0,
    ),
    Rule(
        "rsi_momentum", "RSI momentum bölgesi (50-68)", 0.7,
        lambda r: 50 <= _get(r, "rsi_14", 0) <= 68 and _get(r, "ret_5") > 0,
    ),
    Rule(
        "breakout_20d", "20 günlük dirence kırılım", 1.0,
        lambda r: _get(r, "dist_from_20d_high") > -0.02,
    ),
    Rule(
        "near_52w_high", "52 hafta zirvesine yakın", 0.6,
        lambda r: _get(r, "dist_from_52w_high") > -0.08,
    ),
    Rule(
        "squeeze_release", "Sıkışma sonrası genişleme", 0.8,
        lambda r: _get(r, "bb_width_pctile", 1) < 0.35 and _get(r, "bb_pct_b") > 0.7,
    ),
    Rule(
        "obv_uptrend", "OBV (para akışı) yükseliyor", 0.6,
        lambda r: _get(r, "obv_slope") > 0,
    ),
    Rule(
        "healthy_momentum", "Sağlıklı momentum (aşırı alım değil)", 0.5,
        lambda r: _get(r, "ret_20") > 0.03 and _get(r, "rsi_14", 100) < 78,
    ),
]

_TOTAL_WEIGHT = sum(r.weight for r in RULES)


@dataclass
class RuleResult:
    score: float                 # 0..1 normalize kural skoru
    fired: List[str]             # tetiklenen kuralların Türkçe açıklamaları
    fired_codes: List[str]       # kısa kodlar

    def reasons(self) -> str:
        return "; ".join(self.fired) if self.fired else "belirgin sinyal yok"


def score_rules(row: pd.Series) -> RuleResult:
    """Bir özellik satırına kural motorunu uygular."""
    fired, codes, wsum = [], [], 0.0
    for rule in RULES:
        try:
            ok = bool(rule.test(row))
        except Exception:
            ok = False
        if ok:
            fired.append(rule.label)
            codes.append(rule.name)
            wsum += rule.weight
    score = wsum / _TOTAL_WEIGHT if _TOTAL_WEIGHT else 0.0
    return RuleResult(score=score, fired=fired, fired_codes=codes)
