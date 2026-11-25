"""Referans çözüm."""
import numpy as np


def iq_oku(yol):
    ham = np.fromfile(yol, dtype="<i2").astype(np.float32) / 32768.0
    return (ham[0::2] + 1j * ham[1::2]).astype(np.complex64)


def ofset_kestir(x, fs):
    X = np.fft.fft(x)
    f = np.fft.fftfreq(len(x), 1 / fs)
    return float(f[np.argmax(np.abs(X))])


def ofset_duzelt(x, fs, f_ofset):
    n = np.arange(len(x))
    return (x * np.exp(-2j * np.pi * f_ofset * n / fs)).astype(np.complex64)
