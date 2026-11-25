"""Referans çözüm."""
import numpy as np


def ca_cfar(p, n_egitim, n_koruma, pfa):
    p = np.asarray(p, dtype=float)
    n = len(p)
    N = 2 * n_egitim
    alfa = N * (pfa ** (-1 / N) - 1)
    k = n_egitim + n_koruma
    cs = np.concatenate(([0.0], np.cumsum(p)))
    maske = np.zeros(n, dtype=bool)
    i = np.arange(k, n - k)
    sol = cs[i - n_koruma] - cs[i - k]
    sag = cs[i + k + 1] - cs[i + n_koruma + 1]
    maske[i] = p[i] > alfa * (sol + sag) / N
    return maske
