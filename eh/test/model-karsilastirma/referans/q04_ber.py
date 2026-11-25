"""Referans çözüm."""
import numpy as np


def ber_simulasyonu(mod, ebn0_db, n_bit, seed=0):
    rng = np.random.default_rng(seed)
    k = 1 if mod == "bpsk" else 2
    n_bit = n_bit // k * k
    sonuc = []
    for e in np.atleast_1d(ebn0_db):
        bit = rng.integers(0, 2, n_bit)
        if k == 1:
            s = 1 - 2.0 * bit
        else:
            s = ((1 - 2.0 * bit[0::2]) + 1j * (1 - 2.0 * bit[1::2])) / np.sqrt(2)
        n0 = 1 / (k * 10 ** (e / 10))
        if k == 1:
            r = s + np.sqrt(n0 / 2) * rng.standard_normal(len(s))
            kb = (r < 0).astype(int)
        else:
            r = s + np.sqrt(n0 / 2) * (rng.standard_normal(len(s)) + 1j * rng.standard_normal(len(s)))
            kb = np.empty(n_bit, dtype=int)
            kb[0::2] = r.real < 0
            kb[1::2] = r.imag < 0
        sonuc.append(np.mean(kb != bit))
    return np.array(sonuc)
