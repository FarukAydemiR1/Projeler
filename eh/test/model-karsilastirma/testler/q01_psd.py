import numpy as np
from ortak import bitir, cozum_yukle, esit, kontrol

c = cozum_yukle(5)
fs, nfft = 1.024e6, 1024
n = nfft * 64
t = np.arange(n) / fs
rng = np.random.default_rng(0)
gurultu = 1e-4 * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
x = (0.5 * np.exp(2j * np.pi * 100e3 * t) + gurultu).astype(np.complex64)
y = (1.0 * np.exp(-2j * np.pi * 200e3 * t) + gurultu).astype(np.complex64)
bin_hz = fs / nfft


def sekil():
    f, p = c.psd_dbfs(x, fs, nfft=nfft, window="hann")
    f, p = np.asarray(f), np.asarray(p)
    assert len(f) == nfft and len(p) == nfft, f"uzunluk {len(f)}, {len(p)}"
    assert np.all(np.diff(f) > 0), "frekans ekseni artan değil (fftshift?)"
    esit(f[0], -fs / 2, bin_hz, "ilk frekans")


def tepe_frekans():
    f, p = c.psd_dbfs(x, fs, nfft=nfft, window="hann")
    esit(np.asarray(f)[np.argmax(p)], 100e3, bin_hz, "tepe frekansı")


def tepe_seviye():
    f, p = c.psd_dbfs(x, fs, nfft=nfft, window="hann")
    esit(float(np.max(p)), 20 * np.log10(0.5), 0.5, "0,5 genlikli ton dBFS")


def negatif_ton():
    f, p = c.psd_dbfs(y, fs, nfft=nfft, window="hann")
    esit(np.asarray(f)[np.argmax(p)], -200e3, bin_hz, "negatif ton frekansı")
    esit(float(np.max(p)), 0.0, 0.5, "tam ölçek ton dBFS")


def baska_pencere():
    f, p = c.psd_dbfs(x, fs, nfft=nfft, window="blackman")
    esit(float(np.max(p)), 20 * np.log10(0.5), 0.5, "blackman pencere kazancı düzeltmesi")


kontrol("sekil_ve_eksen", sekil)
kontrol("tepe_frekans", tepe_frekans)
kontrol("tepe_seviye_dBFS", tepe_seviye)
kontrol("negatif_frekans_tam_olcek", negatif_ton)
kontrol("blackman_pencere", baska_pencere)
bitir()
