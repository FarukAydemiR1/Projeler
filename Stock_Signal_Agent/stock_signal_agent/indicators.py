"""Teknik göstergeler.

Hepsi vektörel (pandas) ve NEDENSEL'dir: t günündeki değer yalnızca t ve
öncesindeki fiyatları kullanır (ileriye bakma / lookahead yok). Bu yüzden
üretilen özellikler geçmişe dönük eğitimde güvenle kullanılabilir.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=window).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Wilder RSI (0-100)."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    # avg_loss==0 iken RSI=100
    out = out.where(avg_loss != 0, 100.0)
    return out


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD çizgisi, sinyal çizgisi ve histogram döner."""
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger(close: pd.Series, window: int = 20, num_std: float = 2.0):
    """Bollinger üst/orta/alt bant, %B ve bant genişliği döner."""
    mid = sma(close, window)
    std = close.rolling(window, min_periods=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    width = (upper - lower) / mid.replace(0, np.nan)
    pct_b = (close - lower) / (upper - lower).replace(0, np.nan)
    return upper, mid, lower, pct_b, width


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    ranges = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    )
    return ranges.max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    direction = np.sign(close.diff().fillna(0.0))
    return (direction * volume).fillna(0.0).cumsum()


def roc(series: pd.Series, window: int) -> pd.Series:
    """Rate of change (yüzde getiri) — window gün önceye göre."""
    return series.pct_change(window)


def rolling_max(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=1).max()


def rolling_min(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=1).min()


def slope(series: pd.Series, window: int) -> pd.Series:
    """Bir pencere üzerindeki normalize edilmiş doğrusal eğim (trend yönü)."""
    def _fit(vals: np.ndarray) -> float:
        n = len(vals)
        if n < 2 or np.all(np.isnan(vals)):
            return np.nan
        x = np.arange(n)
        # normalize: seri ortalamasına böl -> ölçekten bağımsız eğim
        denom = np.nanmean(vals)
        if denom == 0 or np.isnan(denom):
            return np.nan
        try:
            coef = np.polyfit(x, vals, 1)[0]
        except Exception:
            return np.nan
        return coef / denom

    return series.rolling(window, min_periods=window).apply(_fit, raw=True)
