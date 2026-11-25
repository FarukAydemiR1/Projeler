"""Referans çözüm: testlerin doğruluğunu sınamak için (calistir.py oz-dogrula)."""
import numpy as np
from scipy.signal import get_window


def psd_dbfs(x, fs, nfft=1024, window="hann"):
    x = np.asarray(x)
    k = len(x) // nfft
    w = get_window(window, nfft)
    seg = x[: k * nfft].reshape(k, nfft) * w
    X = np.fft.fft(seg, axis=1) / w.sum()
    p = np.mean(np.abs(X) ** 2, axis=0)
    f = np.fft.fftshift(np.fft.fftfreq(nfft, 1 / fs))
    return f, 10 * np.log10(np.fft.fftshift(p) + 1e-20)
