"""Basit ileri-yönlü (walk-forward) backtest.

Sinyalin gerçekten işe yarayıp yaramadığını ölçer: geçmişte belirli bir skorun
üstündeki günlerde `horizon` gün sonra ortalama getiri ne olmuş, "yükseldi"
etiketini ne oranda yakalamış (precision).

Not: Bu, işlem maliyeti/slippage içermeyen kaba bir değerlendirmedir; amaç
sinyalin ayırt ediciliğini görmek, gerçek getiriyi vaat etmek değil.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from .features import build_features
from .labeling import label_rise_events, forward_return_at
from .rules import score_rules


@dataclass
class BacktestResult:
    n_signals: int
    n_days: int
    precision: float          # sinyal verilen günlerde yükseliş yakalama oranı
    avg_fwd_return: float      # sinyal günlerinde ort. horizon getirisi
    baseline_return: float     # tüm günlerde ort. horizon getirisi (kıyas)
    baseline_rate: float       # tüm günlerde taban yükseliş oranı
    hit_lift: float            # precision / baseline_rate

    def summary(self) -> str:
        return (
            f"Sinyal günü        : {self.n_signals} / {self.n_days}\n"
            f"İsabet (precision) : %{self.precision*100:.1f}  (taban %{self.baseline_rate*100:.1f})\n"
            f"Lift               : {self.hit_lift:.2f}x\n"
            f"Sinyal ort. getiri : %{self.avg_fwd_return*100:.2f}  (taban %{self.baseline_return*100:.2f})"
        )


def backtest_rule_score(
    df: pd.DataFrame,
    threshold_score: float = 0.5,
    horizon: int = 10,
    rise_threshold: float = 0.08,
) -> BacktestResult:
    """Kural skoruna dayalı sinyalleri geçmişte test eder."""
    feats = build_features(df)
    labels = label_rise_events(df["close"], horizon=horizon, threshold=rise_threshold)
    fwd = forward_return_at(df["close"], horizon)

    scores = feats.apply(lambda r: score_rules(r).score, axis=1)

    valid = labels.notna() & scores.notna() & fwd.notna()
    scores, labels, fwd = scores[valid], labels[valid], fwd[valid]

    signal_mask = scores >= threshold_score
    n_sig = int(signal_mask.sum())
    n_days = int(len(scores))

    precision = float(labels[signal_mask].mean()) if n_sig else 0.0
    avg_fwd = float(fwd[signal_mask].mean()) if n_sig else 0.0
    baseline_rate = float(labels.mean()) if n_days else 0.0
    baseline_return = float(fwd.mean()) if n_days else 0.0
    lift = (precision / baseline_rate) if baseline_rate > 0 else 0.0

    return BacktestResult(
        n_signals=n_sig, n_days=n_days, precision=precision,
        avg_fwd_return=avg_fwd, baseline_return=baseline_return,
        baseline_rate=baseline_rate, hit_lift=lift,
    )
