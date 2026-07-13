"""Sentetik veriyle uçtan uca testler (internet gerektirmez)."""

import numpy as np
import pandas as pd
import pytest

from stock_signal_agent.data import synthetic_prices, load_prices, DataError
from stock_signal_agent import indicators as ind
from stock_signal_agent.features import build_features, FEATURE_COLUMNS, latest_feature_row
from stock_signal_agent.labeling import label_rise_events, forward_max_return
from stock_signal_agent.rules import score_rules
from stock_signal_agent.dataset import build_training_set
from stock_signal_agent.model import SignalModel
from stock_signal_agent.screener import Screener
from stock_signal_agent.backtest import backtest_rule_score


@pytest.fixture
def price_df():
    return synthetic_prices("TEST", days=600, seed=7).df


# --------------------------- veri ---------------------------------------- #
def test_synthetic_shape(price_df):
    assert len(price_df) > 500
    assert list(price_df.columns) == ["open", "high", "low", "close", "volume"]
    assert price_df["close"].notna().all()
    assert (price_df["high"] >= price_df["low"]).all()


def test_synthetic_deterministic():
    a = synthetic_prices("ABC", days=200, seed=1).df
    b = synthetic_prices("ABC", days=200, seed=1).df
    pd.testing.assert_frame_equal(a, b)


def test_load_synthetic_source():
    data = load_prices("XYZ", source="synthetic")
    assert data.source == "synthetic"
    assert len(data.df) > 100


# --------------------------- göstergeler --------------------------------- #
def test_rsi_bounds(price_df):
    r = ind.rsi(price_df["close"], 14).dropna()
    assert r.between(0, 100).all()


def test_macd_hist_relation(price_df):
    line, sig, hist = ind.macd(price_df["close"])
    ok = (hist - (line - sig)).abs().dropna() < 1e-9
    assert ok.all()


def test_atr_positive(price_df):
    a = ind.atr(price_df["high"], price_df["low"], price_df["close"]).dropna()
    assert (a >= 0).all()


# --------------------------- özellikler ---------------------------------- #
def test_features_columns(price_df):
    feats = build_features(price_df)
    assert list(feats.columns) == FEATURE_COLUMNS
    assert len(feats) == len(price_df)


def test_features_no_lookahead(price_df):
    """Bir günün özelliği, sonraki günleri kesip yeniden hesaplayınca değişmemeli."""
    full = build_features(price_df)
    cut = build_features(price_df.iloc[:400])
    # 300. satır her iki hesapta da yalnızca geçmişe baktığından aynı olmalı
    common = full.iloc[300].dropna()
    other = cut.iloc[300]
    for col in common.index:
        if pd.notna(other[col]):
            assert abs(full.iloc[300][col] - other[col]) < 1e-9, col


def test_latest_feature_row(price_df):
    row = latest_feature_row(price_df)
    assert set(row.index) == set(FEATURE_COLUMNS)


# --------------------------- etiketleme ---------------------------------- #
def test_forward_max_return_simple():
    close = pd.Series([10, 11, 12, 9, 8], dtype=float)
    fwd = forward_max_return(close, horizon=2)
    # t=0: sonraki 2 gün max(11,12)=12 -> 0.2
    assert abs(fwd.iloc[0] - 0.2) < 1e-9
    # t=1: max(12,9)=12 -> 12/11-1
    assert abs(fwd.iloc[1] - (12 / 11 - 1)) < 1e-9


def test_label_tail_nan():
    close = pd.Series(np.linspace(10, 20, 100))
    labels = label_rise_events(close, horizon=10, threshold=0.05)
    assert labels.iloc[-10:].isna().all()
    assert labels.iloc[:-10].notna().all()


def test_label_detects_rise():
    # sürekli yükselen seri -> çoğu gün pozitif
    close = pd.Series([100 * (1.02 ** i) for i in range(120)])
    labels = label_rise_events(close, horizon=10, threshold=0.08)
    assert labels.dropna().mean() > 0.8


# --------------------------- kurallar ------------------------------------ #
def test_rules_on_flat_series():
    flat = pd.Series(100.0, index=range(400))
    df = pd.DataFrame({"open": flat, "high": flat, "low": flat,
                       "close": flat, "volume": pd.Series(1e6, index=range(400))})
    row = latest_feature_row(df)
    res = score_rules(row)
    assert 0.0 <= res.score <= 1.0


def test_rules_reasons_type(price_df):
    row = latest_feature_row(price_df)
    res = score_rules(row)
    assert isinstance(res.fired, list)
    assert 0.0 <= res.score <= 1.0


# --------------------------- model / dataset ----------------------------- #
def test_training_and_model():
    symbols = [f"SYN{i}" for i in range(8)]
    X, y, meta, failed = build_training_set(
        symbols, source="synthetic", horizon=10, threshold=0.08, verbose=False
    )
    assert len(X) > 500
    assert set(X.columns) == set(FEATURE_COLUMNS)
    assert y.isin([0, 1]).all()

    model = SignalModel()
    report = model.train(X, y)
    assert report.n_samples == len(X)
    assert model.is_fitted

    proba = model.predict_proba(X.head(20))
    assert ((proba >= 0) & (proba <= 1)).all()


def test_model_save_load(tmp_path):
    symbols = [f"SYN{i}" for i in range(6)]
    X, y, *_ = build_training_set(symbols, source="synthetic", verbose=False)
    model = SignalModel()
    model.train(X, y)
    p = tmp_path / "m.joblib"
    model.save(p)
    loaded = SignalModel.load(p)
    row = X.iloc[-1]
    assert abs(loaded.predict_one(row) - model.predict_one(row)) < 1e-9


# --------------------------- screener ------------------------------------ #
def test_screener_rule_only():
    sc = Screener(model=None, source="synthetic")
    signals = sc.scan([f"SYN{i}" for i in range(5)])
    assert all(0.0 <= s.score <= 1.0 for s in signals)
    # skora göre azalan sıralı
    scores = [s.score for s in signals]
    assert scores == sorted(scores, reverse=True)


def test_screener_with_model(tmp_path):
    symbols = [f"SYN{i}" for i in range(8)]
    X, y, *_ = build_training_set(symbols, source="synthetic", verbose=False)
    model = SignalModel()
    model.train(X, y)
    sc = Screener(model=model, source="synthetic")
    sig = sc.evaluate("SYN0")
    assert sig.model_proba is not None
    assert sig.error is None
    row = sig.as_row()
    assert "belirtiler" in row


# --------------------------- backtest ------------------------------------ #
def test_backtest_runs(price_df):
    res = backtest_rule_score(price_df, threshold_score=0.5)
    assert res.n_days > 0
    assert 0.0 <= res.precision <= 1.0
    assert 0.0 <= res.baseline_rate <= 1.0
