import numpy as np
from scipy.special import erfc
from ortak import bitir, cozum_yukle, kontrol

c = cozum_yukle(4)
ebn0 = np.array([0.0, 2.0, 4.0, 6.0, 8.0])
teori = 0.5 * erfc(np.sqrt(10 ** (ebn0 / 10)))
sonuc = {}


def al(mod):
    if mod not in sonuc:
        sonuc[mod] = np.asarray(c.ber_simulasyonu(mod, ebn0, 2_000_000, seed=0), dtype=float)
    return sonuc[mod]


def sekil():
    b = al("bpsk")
    assert b.shape == ebn0.shape, f"şekil {b.shape}"
    assert np.all(np.diff(b) < 0), f"BER azalan değil: {b}"


def teoriye_uyum(mod):
    b = al(mod)
    hata = np.abs(b - teori) / teori
    assert np.all(hata < 0.15), f"{mod} BER {b} teori {teori.round(6)} göreli hata {hata.round(3)}"


def qpsk_sekil():
    b = al("qpsk")
    assert b.shape == ebn0.shape and np.all(np.diff(b) < 0), f"QPSK BER şekli/azalma: {b}"


kontrol("bpsk_sekil_azalan", sekil)
kontrol("bpsk_teori", lambda: teoriye_uyum("bpsk"))
kontrol("qpsk_teori_gray", lambda: teoriye_uyum("qpsk"))
kontrol("qpsk_sekil_azalan", qpsk_sekil)
bitir()
