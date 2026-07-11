"""Veri katmanı: OHLCV fiyat verisi çekme.

Üç kaynak destekler ve otomatik olarak birinden diğerine düşer:
  * Yahoo Finance   -> canlı veri (BIST için ".IS", ABD için düz sembol)
  * CSV             -> çevrimdışı, kendi indirdiğin dosyalar
  * Sentetik        -> internetin olmadığı ortamlarda demo/test için

Yahoo çekimi bilerek `requests` ile yapılır (yfinance'in curl_cffi'si aksine
kurumsal proxy'yi ve CA sertifikasını kullanır), böylece kısıtlı ortamlarda
da çalışır.
"""

from __future__ import annotations

import io
import os
import time
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# Diskteki önbellek dizini (tekrar tekrar çekmeyi önler)
CACHE_DIR = Path(os.environ.get("SSA_CACHE_DIR", Path.home() / ".cache" / "stock_signal_agent"))
_YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_USER_AGENT = "Mozilla/5.0 (compatible; StockSignalAgent/0.1)"

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


class DataError(RuntimeError):
    """Veri çekilemediğinde fırlatılır."""


@dataclass
class PriceData:
    """Bir sembolün fiyat serisi + üst bilgisi."""

    symbol: str
    df: pd.DataFrame          # index: DatetimeIndex, kolonlar: OHLCV_COLUMNS
    currency: str = ""
    source: str = ""


def _validate_frame(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCV çerçevesini normalize et: kolon adları küçük harf, index tarih, sıralı, NaN temiz."""
    df = df.rename(columns={c: c.lower() for c in df.columns})
    missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
    if missing:
        raise DataError(f"Eksik kolonlar: {missing}. Beklenen: {OHLCV_COLUMNS}")
    df = df[OHLCV_COLUMNS].copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    # Kapanışı olmayan satırlar işe yaramaz
    df = df.dropna(subset=["close"])
    df["volume"] = df["volume"].fillna(0)
    return df


# --------------------------------------------------------------------------- #
# Yahoo Finance                                                               #
# --------------------------------------------------------------------------- #
def fetch_yahoo(
    symbol: str,
    period: str = "2y",
    interval: str = "1d",
    session: Optional[requests.Session] = None,
    retries: int = 3,
) -> PriceData:
    """Yahoo Finance chart API'sinden OHLCV çeker.

    period örn: '6mo', '1y', '2y', '5y', 'max'
    interval örn: '1d', '1wk', '1h'
    """
    url = _YAHOO_BASE.format(symbol=symbol)
    params = {"range": period, "interval": interval, "includePrePost": "false"}
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
    sess = session or requests.Session()

    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = sess.get(url, params=params, headers=headers, timeout=25)
            if resp.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                last_err = DataError("Yahoo 429 (çok fazla istek)")
                continue
            resp.raise_for_status()
            payload = resp.json()
            return _parse_yahoo_chart(symbol, payload)
        except Exception as exc:  # ağ / json / yapı hataları
            last_err = exc
            time.sleep(0.8 * (attempt + 1))
    raise DataError(f"Yahoo çekimi başarısız [{symbol}]: {last_err}")


def _parse_yahoo_chart(symbol: str, payload: dict) -> PriceData:
    chart = payload.get("chart", {})
    if chart.get("error"):
        raise DataError(f"Yahoo hata [{symbol}]: {chart['error']}")
    results = chart.get("result")
    if not results:
        raise DataError(f"Yahoo boş sonuç [{symbol}]")
    res = results[0]
    timestamps = res.get("timestamp")
    quote = res.get("indicators", {}).get("quote", [{}])[0]
    if not timestamps or "close" not in quote:
        raise DataError(f"Yahoo veri yok [{symbol}] (sembol geçerli mi?)")

    index = pd.to_datetime([datetime.fromtimestamp(t, tz=timezone.utc).date() for t in timestamps])
    df = pd.DataFrame(
        {
            "open": quote.get("open"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "close": quote.get("close"),
            "volume": quote.get("volume"),
        },
        index=index,
    )
    df = _validate_frame(df)
    currency = res.get("meta", {}).get("currency", "")
    return PriceData(symbol=symbol, df=df, currency=currency, source="yahoo")


# --------------------------------------------------------------------------- #
# CSV                                                                         #
# --------------------------------------------------------------------------- #
def fetch_csv(symbol: str, csv_dir: str | Path) -> PriceData:
    """`<csv_dir>/<symbol>.csv` dosyasından okur.

    CSV en az şu kolonları içermeli (büyük/küçük harf serbest):
      date, open, high, low, close, volume
    """
    path = Path(csv_dir) / f"{symbol}.csv"
    if not path.exists():
        raise DataError(f"CSV bulunamadı: {path}")
    df = pd.read_csv(path)
    date_col = next((c for c in df.columns if c.lower() in ("date", "tarih", "datetime")), None)
    if date_col is None:
        raise DataError(f"CSV'de tarih kolonu yok: {path}")
    df = df.set_index(date_col)
    df = _validate_frame(df)
    return PriceData(symbol=symbol, df=df, source="csv")


# --------------------------------------------------------------------------- #
# Sentetik (çevrimdışı demo / test)                                          #
# --------------------------------------------------------------------------- #
def synthetic_prices(symbol: str, days: int = 750, seed: Optional[int] = None) -> PriceData:
    """Gerçekçi görünümlü sentetik OHLCV üretir (rejim + hacim patlamaları içerir).

    İçine kasıtlı olarak "yükseliş öncesi" desenler ekler: düşük volatilite
    sıkışması + hacim artışı ardından ralli. Böylece model/kurallar test
    edilebilir. Deterministiktir (seed).
    """
    import numpy as np

    if seed is None:
        # Sembol adından süreçler arası KARARLI bir tohum türet
        # (Python hash() rastgeleleştirildiği için hashlib kullanılır).
        import hashlib

        digest = hashlib.sha256(symbol.encode("utf-8")).hexdigest()
        seed = int(digest[:8], 16)
    rng = np.random.default_rng(seed)

    price = 100.0
    prices, highs, lows, opens, vols = [], [], [], [], []
    base_vol = rng.uniform(5e5, 5e6)
    drift = rng.normal(0.0003, 0.0002)
    vol_regime = 0.015

    i = 0
    while i < days:
        # Ara sıra "sıkışma sonrası ralli" rejimi ekle
        if rng.random() < 0.02:
            squeeze = rng.integers(8, 15)
            for _ in range(min(squeeze, days - i)):
                r = rng.normal(0, vol_regime * 0.4)
                price *= (1 + r)
                _append_bar(rng, price, base_vol * 0.7, opens, highs, lows, prices, vols, r)
                i += 1
            rally = rng.integers(6, 12)
            surge = rng.uniform(1.8, 3.5)
            for k in range(min(rally, days - i)):
                r = abs(rng.normal(0.012, 0.008)) + 0.004
                price *= (1 + r)
                _append_bar(rng, price, base_vol * surge * (1 - k / (rally + 2)),
                            opens, highs, lows, prices, vols, r)
                i += 1
            continue
        r = rng.normal(drift, vol_regime)
        price *= (1 + r)
        price = max(price, 1.0)
        _append_bar(rng, price, base_vol, opens, highs, lows, prices, vols, r)
        i += 1

    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=len(prices))
    df = pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": prices, "volume": vols},
        index=index,
    )
    df = _validate_frame(df)
    return PriceData(symbol=symbol, df=df, currency="SYN", source="synthetic")


def _append_bar(rng, close, vol, opens, highs, lows, prices, vols, r):
    import numpy as np

    o = close / (1 + r) if (1 + r) != 0 else close
    hi = max(o, close) * (1 + abs(rng.normal(0, 0.004)))
    lo = min(o, close) * (1 - abs(rng.normal(0, 0.004)))
    opens.append(o)
    highs.append(hi)
    lows.append(lo)
    prices.append(close)
    vols.append(float(max(vol * (1 + rng.normal(0, 0.3)), 1000)))


# --------------------------------------------------------------------------- #
# Üst seviye yükleyici                                                        #
# --------------------------------------------------------------------------- #
def load_prices(
    symbol: str,
    source: str = "yahoo",
    period: str = "2y",
    interval: str = "1d",
    csv_dir: Optional[str | Path] = None,
    use_cache: bool = True,
    fallback_synthetic: bool = False,
    session: Optional[requests.Session] = None,
) -> PriceData:
    """Bir sembol için fiyat verisi yükler (önbellekli).

    source: 'yahoo' | 'csv' | 'synthetic'
    fallback_synthetic=True ise yahoo/csv başarısız olursa sentetiğe düşer
    (üretimde değil, sadece demo/test için önerilir).
    """
    if source == "synthetic":
        return synthetic_prices(symbol)

    if use_cache and source == "yahoo":
        cached = _read_cache(symbol, interval)
        if cached is not None:
            return cached

    try:
        if source == "yahoo":
            data = fetch_yahoo(symbol, period=period, interval=interval, session=session)
            if use_cache:
                _write_cache(data, interval)
            return data
        elif source == "csv":
            if csv_dir is None:
                raise DataError("csv kaynağı için csv_dir gerekli")
            return fetch_csv(symbol, csv_dir)
        else:
            raise DataError(f"Bilinmeyen kaynak: {source}")
    except DataError:
        if fallback_synthetic:
            return synthetic_prices(symbol)
        raise


def _cache_path(symbol: str, interval: str) -> Path:
    safe = symbol.replace("/", "_").replace("\\", "_")
    return CACHE_DIR / f"{safe}__{interval}.csv"


def _read_cache(symbol: str, interval: str, max_age_hours: float = 12.0) -> Optional[PriceData]:
    path = _cache_path(symbol, interval)
    if not path.exists():
        return None
    age_h = (time.time() - path.stat().st_mtime) / 3600.0
    if age_h > max_age_hours:
        return None
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        df = _validate_frame(df)
        return PriceData(symbol=symbol, df=df, source="cache")
    except Exception:
        return None


def _write_cache(data: PriceData, interval: str) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data.df.to_csv(_cache_path(data.symbol, interval))
    except Exception:
        pass  # önbellek yazımı best-effort
