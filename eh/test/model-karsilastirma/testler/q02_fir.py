import numpy as np
from scipy import signal
from ortak import bitir, cozum_yukle, kontrol

c = cozum_yukle(5)
fs, fc, ntaps = 48000.0, 4000.0, 101


def katsayi():
    h = np.asarray(c.fir_lowpass(fs, fc, ntaps))
    assert h.shape == (ntaps,), f"şekil {h.shape}"
    assert np.isrealobj(h), "katsayılar gerçel değil"
    assert np.allclose(h, h[::-1], atol=1e-9), "simetrik değil (doğrusal faz yok)"


def dc_kazanc():
    h = np.asarray(c.fir_lowpass(fs, fc, ntaps))
    assert abs(h.sum() - 1) < 0.01, f"DC kazancı {h.sum():.4f}"


def gecirme_bandi():
    h = np.asarray(c.fir_lowpass(fs, fc, ntaps))
    _, H = signal.freqz(h, worN=[1000.0], fs=fs)
    db = 20 * np.log10(abs(H[0]))
    assert db > -1, f"1 kHz'de {db:.2f} dB"


def durdurma_bandi():
    h = np.asarray(c.fir_lowpass(fs, fc, ntaps))
    _, H = signal.freqz(h, worN=[8000.0, 12000.0], fs=fs)
    db = 20 * np.log10(np.abs(H) + 1e-15)
    assert np.all(db < -40), f"8/12 kHz'de {db.round(1)} dB"


def uygula():
    h = np.asarray(c.fir_lowpass(fs, fc, ntaps))
    x = np.random.default_rng(1).standard_normal(5000)
    y = np.asarray(c.fir_uygula(x, h))
    assert y.shape == x.shape, f"çıkış şekli {y.shape}"
    assert np.allclose(y, signal.lfilter(h, 1.0, x), atol=1e-6), "nedensel süzgeç (lfilter) çıktısıyla aynı değil"


kontrol("katsayi_sekli_simetri", katsayi)
kontrol("dc_kazanci_1", dc_kazanc)
kontrol("gecirme_bandi_1kHz", gecirme_bandi)
kontrol("durdurma_bandi_-40dB", durdurma_bandi)
kontrol("fir_uygula_lfilter", uygula)
bitir()
