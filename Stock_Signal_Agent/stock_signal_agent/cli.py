"""Komut satırı arayüzü.

Kullanım:
    python -m stock_signal_agent.cli train  --market all --out model.joblib
    python -m stock_signal_agent.cli scan   --market bist --model model.joblib
    python -m stock_signal_agent.cli explain --symbol THYAO.IS --model model.joblib
    python -m stock_signal_agent.cli backtest --symbol AAPL

İnternet yoksa her komuta --synthetic ekleyerek sentetik veriyle deneyebilirsin.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config as cfgmod
from .data import load_prices
from .dataset import build_training_set
from .model import SignalModel
from .screener import Screener
from .backtest import backtest_rule_score
from .features import latest_feature_row
from .rules import score_rules


def _resolve_symbols(args, cfg) -> list:
    if args.symbols:
        return [s.strip() for s in args.symbols.split(",") if s.strip()]
    return cfgmod.watchlist(cfg, args.market)


def cmd_train(args):
    cfg = cfgmod.load_config(args.config)
    symbols = _resolve_symbols(args, cfg)
    source = "synthetic" if args.synthetic else args.source
    print(f"[train] {len(symbols)} sembol, kaynak={source}, "
          f"horizon={cfg['horizon']}, eşik=%{cfg['rise_threshold']*100:.0f}")

    X, y, meta, failed = build_training_set(
        symbols, source=source, period=args.period or cfg["train_period"],
        horizon=cfg["horizon"], threshold=cfg["rise_threshold"],
        csv_dir=args.csv_dir, fallback_synthetic=args.synthetic or args.fallback_synthetic,
    )

    model = SignalModel()
    report = model.train(X, y)
    print("\n=== Eğitim Raporu ===")
    print(report.summary())

    out = args.out or "signal_model.joblib"
    model.save(out)
    print(f"\nModel kaydedildi: {out}")
    if failed:
        print(f"Çekilemeyen semboller: {[s for s, _ in failed]}")


def cmd_scan(args):
    cfg = cfgmod.load_config(args.config)
    symbols = _resolve_symbols(args, cfg)
    source = "synthetic" if args.synthetic else args.source

    model = None
    if args.model:
        if Path(args.model).exists():
            model = SignalModel.load(args.model)
            print(f"[scan] model yüklendi: {args.model}")
        else:
            print(f"[scan] UYARI: model bulunamadı ({args.model}), sadece kural modu")

    screener = Screener(
        model=model,
        model_weight=cfg["model_weight"], rule_weight=cfg["rule_weight"],
        source=source, period=args.period or cfg["scan_period"],
        csv_dir=args.csv_dir, fallback_synthetic=args.synthetic or args.fallback_synthetic,
    )

    min_score = args.min_score if args.min_score is not None else cfg["min_score"]
    signals = screener.scan(symbols, min_score=min_score)

    if not signals:
        print(f"\nEşiği (>= {min_score}) geçen sinyal yok.")
        return

    print(f"\n=== SİNYALLER (>= {min_score}) ===")
    print(f"{'SEMBOL':<12}{'SKOR':>6}{'MODEL':>7}{'KURAL':>7}  {'SEVİYE':<8}{'FİYAT':>10}  BELİRTİLER")
    print("-" * 100)
    for s in signals:
        m = "  -  " if s.model_proba is None else f"{s.model_proba:.2f}"
        reasons = "; ".join(s.reasons[:3]) or "-"
        print(f"{s.symbol:<12}{s.score:>6.2f}{m:>7}{s.rule_score:>7.2f}  "
              f"{s.level:<8}{s.price:>10.2f}  {reasons}")


def cmd_explain(args):
    cfg = cfgmod.load_config(args.config)
    source = "synthetic" if args.synthetic else args.source
    data = load_prices(args.symbol, source=source,
                       period=args.period or cfg["scan_period"],
                       csv_dir=args.csv_dir,
                       fallback_synthetic=args.synthetic or args.fallback_synthetic)
    row = latest_feature_row(data.df)
    rr = score_rules(row)

    print(f"\n=== {args.symbol} ({data.currency}) — son gün analizi ===")
    print(f"Fiyat: {data.df['close'].iloc[-1]:.2f}   Tarih: {data.df.index[-1].date()}")
    print(f"\nKural skoru: {rr.score:.2f}")
    print("Tetiklenen belirtiler:")
    for r in rr.fired:
        print(f"   ✓ {r}")
    if not rr.fired:
        print("   (belirgin yükseliş belirtisi yok)")

    if args.model and Path(args.model).exists():
        model = SignalModel.load(args.model)
        proba = model.predict_one(row)
        print(f"\nModel yükseliş olasılığı: {proba:.1%}")
        combined = cfg["model_weight"] * proba + cfg["rule_weight"] * rr.score
        print(f"Birleşik sinyal skoru   : {combined:.2f}")

    print("\nÖne çıkan gösterge değerleri:")
    for k in ["rsi_14", "vol_ratio", "sma_ratio_20_50", "dist_from_20d_high",
              "macd_hist_norm", "bb_width_pctile"]:
        v = row.get(k)
        if v is not None:
            print(f"   {k:<20}: {v:+.4f}")


def cmd_backtest(args):
    cfg = cfgmod.load_config(args.config)
    source = "synthetic" if args.synthetic else args.source
    data = load_prices(args.symbol, source=source,
                       period=args.period or cfg["train_period"],
                       csv_dir=args.csv_dir,
                       fallback_synthetic=args.synthetic or args.fallback_synthetic)
    res = backtest_rule_score(
        data.df, threshold_score=args.threshold,
        horizon=cfg["horizon"], rise_threshold=cfg["rise_threshold"],
    )
    print(f"\n=== {args.symbol} — kural sinyali backtest (skor >= {args.threshold}) ===")
    print(res.summary())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="stock_signal_agent",
        description="Yükseliş belirtisi gösteren hisseleri yakalayıp sinyal veren ajan.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--market", default="all", choices=["bist", "us", "all"],
                        help="hazır izleme listesi")
        sp.add_argument("--symbols", default=None,
                        help="virgülle sembol listesi (izleme listesini geçersiz kılar)")
        sp.add_argument("--source", default="yahoo", choices=["yahoo", "csv", "synthetic"])
        sp.add_argument("--csv-dir", default=None, help="csv kaynağı için dizin")
        sp.add_argument("--period", default=None, help="veri aralığı (örn 1y, 5y)")
        sp.add_argument("--config", default=None, help="config.yaml yolu")
        sp.add_argument("--synthetic", action="store_true",
                        help="sentetik veri kullan (internet yoksa demo)")
        sp.add_argument("--fallback-synthetic", action="store_true",
                        help="çekim başarısızsa sentetiğe düş")

    sp = sub.add_parser("train", help="model eğit")
    common(sp)
    sp.add_argument("--out", default=None, help="model çıktısı (.joblib)")
    sp.set_defaults(func=cmd_train)

    sp = sub.add_parser("scan", help="izleme listesini tara, sinyal ver")
    common(sp)
    sp.add_argument("--model", default=None, help="eğitilmiş model yolu")
    sp.add_argument("--min-score", type=float, default=None, help="minimum sinyal skoru")
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("explain", help="tek sembol için gerekçeli analiz")
    common(sp)
    sp.add_argument("--symbol", required=True)
    sp.add_argument("--model", default=None)
    sp.set_defaults(func=cmd_explain)

    sp = sub.add_parser("backtest", help="kural sinyalini geçmişte test et")
    common(sp)
    sp.add_argument("--symbol", required=True)
    sp.add_argument("--threshold", type=float, default=0.5, help="kural skor eşiği")
    sp.set_defaults(func=cmd_backtest)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\niptal edildi.")
        sys.exit(130)


if __name__ == "__main__":
    main()
