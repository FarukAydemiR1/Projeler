"""Etiketleme: "yükseliş olayı" nedir?

Modelin öğrenmesi için her günü (t) geleceğe bakarak etiketleriz:
  * horizon gün içinde kapanışın t gününe göre EN YÜKSEK getirisi
    threshold'u (örn. +%8) aşarsa  -> etiket 1 ("yükseldi")
  * aksi halde -> 0

Not: Bu etiketleme ileriye bakar; SADECE eğitim verisi hazırlarken kullanılır.
Özellikler (features.py) ise asla ileriye bakmaz. Böylece "geçmişte bu
belirtiler varken hisse yükseldi mi?" sorusunu doğru kurarız.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def forward_max_return(close: pd.Series, horizon: int) -> pd.Series:
    """t gününden sonraki `horizon` gün (t+1 .. t+horizon) içindeki en yüksek getiri.

    Seriyi ters çevirip rolling-max alarak ileriye bakan pencereyi hesaplar,
    sonra shift(-1) ile t gününün kendisini pencereden çıkarır.
    """
    fwd_max = close[::-1].rolling(horizon, min_periods=1).max()[::-1].shift(-1)
    return fwd_max / close - 1.0


def label_rise_events(
    close: pd.Series,
    horizon: int = 10,
    threshold: float = 0.08,
) -> pd.Series:
    """İkili etiket: horizon içinde >= threshold yükseliş oldu mu?

    Son `horizon` gün geleceği bilinmediğinden NaN olur ve eğitimden düşülür.
    """
    fwd = forward_max_return(close, horizon)
    label = (fwd >= threshold).astype(float)
    # Geleceği tam gözlemlenemeyen son satırları geçersiz kıl
    label.iloc[-horizon:] = np.nan
    return label


def forward_return_at(close: pd.Series, horizon: int) -> pd.Series:
    """Backtest için: tam olarak `horizon` gün sonraki getiri (max değil)."""
    return close.shift(-horizon) / close - 1.0
