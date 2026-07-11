"""Tarayıcı: model + kural motorunu birleştirip sinyal üretir.

Her sembol için:
  1. güncel veriyi çeker,
  2. son gün özellik satırını üretir,
  3. ML modelinden yükseliş olasılığı alır,
  4. kural motorundan anlaşılır belirtiler + skor alır,
  5. ikisini ağırlıklı birleştirip nihai skor + gerekçe verir.

Model olmadan da çalışır (sadece kural modu).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

import pandas as pd

from .data import load_prices, DataError
from .features import latest_feature_row
from .rules import score_rules, RuleResult
from .model import SignalModel


@dataclass
class Signal:
    symbol: str
    score: float                 # 0..1 nihai sinyal skoru
    model_proba: Optional[float]
    rule_score: float
    reasons: List[str]
    price: float
    currency: str = ""
    level: str = "izle"          # güçlü / al / izle / zayıf
    error: Optional[str] = None

    def as_row(self) -> dict:
        return {
            "sembol": self.symbol,
            "skor": round(self.score, 3),
            "model": None if self.model_proba is None else round(self.model_proba, 3),
            "kural": round(self.rule_score, 3),
            "seviye": self.level,
            "fiyat": round(self.price, 2),
            "para": self.currency,
            "belirtiler": "; ".join(self.reasons),
        }


def _level(score: float) -> str:
    if score >= 0.75:
        return "GÜÇLÜ"
    if score >= 0.6:
        return "AL"
    if score >= 0.45:
        return "İZLE"
    return "ZAYIF"


class Screener:
    """Sinyal üretici.

    model_weight + rule_weight = 1.0. Model yoksa kural skoru %100 kullanılır.
    """

    def __init__(
        self,
        model: Optional[SignalModel] = None,
        model_weight: float = 0.6,
        rule_weight: float = 0.4,
        source: str = "yahoo",
        period: str = "1y",
        csv_dir: Optional[str] = None,
        fallback_synthetic: bool = False,
    ):
        self.model = model
        total = model_weight + rule_weight
        self.model_weight = model_weight / total if total else 0.5
        self.rule_weight = rule_weight / total if total else 0.5
        self.source = source
        self.period = period
        self.csv_dir = csv_dir
        self.fallback_synthetic = fallback_synthetic

    def evaluate(self, symbol: str) -> Signal:
        """Tek bir sembolü değerlendirir."""
        try:
            data = load_prices(
                symbol, source=self.source, period=self.period,
                csv_dir=self.csv_dir, fallback_synthetic=self.fallback_synthetic,
            )
        except DataError as exc:
            return Signal(symbol, 0.0, None, 0.0, [], 0.0, error=str(exc), level="HATA")

        df = data.df
        if len(df) < 60:
            return Signal(symbol, 0.0, None, 0.0, [], float(df["close"].iloc[-1]),
                          currency=data.currency, error="yetersiz veri", level="HATA")

        row = latest_feature_row(df)
        rule_res: RuleResult = score_rules(row)

        model_proba = None
        if self.model is not None:
            try:
                model_proba = self.model.predict_one(row)
            except Exception:
                model_proba = None

        if model_proba is not None:
            score = self.model_weight * model_proba + self.rule_weight * rule_res.score
        else:
            score = rule_res.score

        return Signal(
            symbol=symbol,
            score=float(score),
            model_proba=model_proba,
            rule_score=rule_res.score,
            reasons=rule_res.fired,
            price=float(df["close"].iloc[-1]),
            currency=data.currency,
            level=_level(score),
        )

    def scan(self, symbols: Iterable[str], min_score: float = 0.0) -> List[Signal]:
        """Bir sembol listesini tarar, skora göre azalan sıralar."""
        signals = [self.evaluate(s) for s in symbols]
        valid = [s for s in signals if s.error is None and s.score >= min_score]
        valid.sort(key=lambda s: s.score, reverse=True)
        return valid

    def scan_report(self, symbols: Iterable[str], min_score: float = 0.0) -> pd.DataFrame:
        rows = [s.as_row() for s in self.scan(symbols, min_score=min_score)]
        return pd.DataFrame(rows)
