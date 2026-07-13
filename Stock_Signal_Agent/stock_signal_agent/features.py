"""Özellik mühendisliği: göstergeleri "yükseliş öncesi parmak izi"ne çevirir.

`build_features` bir OHLCV çerçevesinden, her gün için (t) yalnızca o güne
kadarki bilgiyi kullanan bir özellik matrisi üretir. Bu özellikler hem ML
modelini eğitmek hem de kural motorunu beslemek için kullanılır.

Özelliklerin çoğu ölçekten bağımsız (oran/yüzde) tutulur ki farklı fiyat
seviyelerindeki BIST ve ABD hisseleri karşılaştırılabilsin.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind

# Modelin kullanacağı özellik kolonlarının kanonik listesi/sırası.
FEATURE_COLUMNS = [
    "ret_1", "ret_5", "ret_10", "ret_20",
    "rsi_14",
    "macd_hist_norm", "macd_above_signal",
    "sma_ratio_20_50", "price_vs_sma20", "price_vs_sma50", "price_vs_sma200",
    "bb_pct_b", "bb_width", "bb_width_pctile",
    "vol_ratio", "vol_trend", "obv_slope",
    "atr_pct",
    "dist_from_20d_high", "dist_from_52w_high", "dist_above_20d_low",
    "roc_10", "trend_slope_20",
    "gap_up",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCV çerçevesinden özellik matrisi üretir.

    Dönen çerçevenin index'i girdi ile aynıdır; ilk satırlar (gösterge ısınma
    süresi) NaN içerebilir — eğitim/tahmin öncesi çağıran taraf dropna yapar.
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    feat = pd.DataFrame(index=df.index)

    # --- Momentum / getiri ---
    feat["ret_1"] = close.pct_change(1)
    feat["ret_5"] = close.pct_change(5)
    feat["ret_10"] = close.pct_change(10)
    feat["ret_20"] = close.pct_change(20)
    feat["roc_10"] = ind.roc(close, 10)

    # --- RSI ---
    feat["rsi_14"] = ind.rsi(close, 14)

    # --- MACD ---
    macd_line, signal_line, hist = ind.macd(close)
    feat["macd_hist_norm"] = hist / close.replace(0, np.nan)  # fiyata göre normalize
    feat["macd_above_signal"] = (macd_line > signal_line).astype(float)

    # --- Hareketli ortalamalar / trend ---
    sma20 = ind.sma(close, 20)
    sma50 = ind.sma(close, 50)
    sma200 = ind.sma(close, 200)
    feat["sma_ratio_20_50"] = sma20 / sma50 - 1.0
    feat["price_vs_sma20"] = close / sma20 - 1.0
    feat["price_vs_sma50"] = close / sma50 - 1.0
    feat["price_vs_sma200"] = close / sma200 - 1.0
    feat["trend_slope_20"] = ind.slope(close, 20)

    # --- Bollinger / volatilite sıkışması ---
    _, _, _, pct_b, width = ind.bollinger(close, 20, 2.0)
    feat["bb_pct_b"] = pct_b
    feat["bb_width"] = width
    # Bant genişliğinin son 1 yıldaki yüzdelik dilimi (0=en sıkışık, 1=en geniş)
    feat["bb_width_pctile"] = width.rolling(252, min_periods=40).apply(
        lambda w: (w[-1] >= w).mean(), raw=True
    )

    # --- Hacim ---
    vol_avg20 = volume.rolling(20, min_periods=20).mean()
    vol_avg5 = volume.rolling(5, min_periods=5).mean()
    feat["vol_ratio"] = volume / vol_avg20.replace(0, np.nan)      # bugünkü hacim / 20g ort.
    feat["vol_trend"] = vol_avg5 / vol_avg20.replace(0, np.nan)    # kısa vadeli hacim ivmesi
    obv = ind.obv(close, volume)
    feat["obv_slope"] = ind.slope(obv, 20)

    # --- Volatilite ---
    feat["atr_pct"] = ind.atr(high, low, close, 14) / close.replace(0, np.nan)

    # --- Kırılım yakınlığı ---
    high20 = ind.rolling_max(high, 20)
    high52w = ind.rolling_max(high, 252)
    low20 = ind.rolling_min(low, 20)
    feat["dist_from_20d_high"] = close / high20.replace(0, np.nan) - 1.0   # 0'a yakın = kırılımda
    feat["dist_from_52w_high"] = close / high52w.replace(0, np.nan) - 1.0
    feat["dist_above_20d_low"] = close / low20.replace(0, np.nan) - 1.0

    # --- Gap ---
    prev_close = close.shift(1)
    feat["gap_up"] = (df["open"] / prev_close - 1.0).clip(-0.2, 0.2)

    # Kanonik kolon sırasını garanti et
    for col in FEATURE_COLUMNS:
        if col not in feat.columns:
            feat[col] = np.nan
    return feat[FEATURE_COLUMNS]


def latest_feature_row(df: pd.DataFrame) -> pd.Series:
    """En güncel (son gün) özellik satırını döner — canlı tarama için."""
    feats = build_features(df)
    if feats.empty:
        raise ValueError("Özellik üretilemedi (yetersiz veri)")
    return feats.iloc[-1]
