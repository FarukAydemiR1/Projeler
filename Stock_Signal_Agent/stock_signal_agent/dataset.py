"""Eğitim veri seti kurucu.

Birden çok sembol için OHLCV çeker, her biri için özellik matrisi + yükseliş
etiketi üretir ve hepsini tek bir eğitim tablosunda birleştirir. Model bu
tablodan "yükseliş öncesi neye benziyor?" öğrenir.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

import pandas as pd

from .data import load_prices, DataError
from .features import build_features, FEATURE_COLUMNS
from .labeling import label_rise_events


def build_training_set(
    symbols: Iterable[str],
    source: str = "yahoo",
    period: str = "5y",
    horizon: int = 10,
    threshold: float = 0.08,
    csv_dir: Optional[str] = None,
    fallback_synthetic: bool = False,
    verbose: bool = True,
):
    """Semboller için (X, y, meta) döner.

    X: özellik matrisi (NaN'ler düşülmüş), y: 0/1 etiket, meta: kaynak sembol.
    """
    frames_X: List[pd.DataFrame] = []
    frames_y: List[pd.Series] = []
    meta: List[pd.Series] = []
    failed = []

    for sym in symbols:
        try:
            data = load_prices(
                sym, source=source, period=period, csv_dir=csv_dir,
                fallback_synthetic=fallback_synthetic,
            )
        except DataError as exc:
            failed.append((sym, str(exc)))
            if verbose:
                print(f"  atlandı {sym}: {exc}")
            continue

        df = data.df
        if len(df) < 260:  # ~1 yıldan az veri işe yaramaz
            failed.append((sym, "yetersiz geçmiş"))
            continue

        feats = build_features(df)
        labels = label_rise_events(df["close"], horizon=horizon, threshold=threshold)

        joined = feats.copy()
        joined["_label"] = labels
        joined = joined.dropna()
        if joined.empty:
            continue

        frames_X.append(joined[FEATURE_COLUMNS])
        frames_y.append(joined["_label"])
        meta.append(pd.Series(sym, index=joined.index, name="symbol"))
        if verbose:
            pos = int(joined["_label"].sum())
            print(f"  {sym}: {len(joined)} satır, {pos} yükseliş olayı")

    if not frames_X:
        raise DataError("Hiç eğitim verisi toplanamadı. Semboller/kaynak doğru mu?")

    X = pd.concat(frames_X)
    y = pd.concat(frames_y)
    m = pd.concat(meta)
    if verbose:
        print(f"Toplam: {len(X)} satır, {int(y.sum())} pozitif (%{y.mean()*100:.1f}), "
              f"{len(frames_X)} sembol")
    return X, y, m, failed
