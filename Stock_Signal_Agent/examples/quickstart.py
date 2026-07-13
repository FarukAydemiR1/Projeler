"""Hızlı başlangıç: sentetik veriyle eğit + tara (internet gerektirmez).

Çalıştır:
    cd Stock_Signal_Agent
    python examples/quickstart.py
"""

import sys
from pathlib import Path

# examples/ alt klasöründen çalıştırıldığında proje kökünü path'e ekle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stock_signal_agent.dataset import build_training_set
from stock_signal_agent.model import SignalModel
from stock_signal_agent.screener import Screener

# Gerçek kullanımda source="yahoo" ve gerçek semboller ("THYAO.IS", "AAPL"...) kullan.
SYMBOLS = [f"SYN{i}" for i in range(12)]


def main():
    print(">> Eğitim seti kuruluyor (sentetik)...")
    X, y, meta, failed = build_training_set(SYMBOLS, source="synthetic", verbose=False)

    print(">> Model eğitiliyor...")
    model = SignalModel()
    report = model.train(X, y)
    print(report.summary())

    print("\n>> Tarama (kural + model)...")
    screener = Screener(model=model, source="synthetic")
    signals = screener.scan(SYMBOLS, min_score=0.0)

    print(f"\n{'SEMBOL':<8}{'SKOR':>6}{'SEVİYE':>9}   BELİRTİLER")
    for s in signals[:10]:
        print(f"{s.symbol:<8}{s.score:>6.2f}{s.level:>9}   {'; '.join(s.reasons[:3]) or '-'}")


if __name__ == "__main__":
    main()
