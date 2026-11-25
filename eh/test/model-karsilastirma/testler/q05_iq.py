import os
import tempfile

import numpy as np
from ortak import bitir, cozum_yukle, esit, kontrol

c = cozum_yukle(5)
fs, n = 250e3, 65536
t = np.arange(n) / fs
rng = np.random.default_rng(2)


def dosya(f0):
    x = 0.6 * np.exp(2j * np.pi * f0 * t) + 0.01 * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
    iq = np.empty(2 * n, dtype="<i2")
    iq[0::2] = np.round(x.real * 32767)
    iq[1::2] = np.round(x.imag * 32767)
    yol = os.path.join(tempfile.mkdtemp(), f"ton_{int(f0)}.iq")
    iq.tofile(yol)
    beklenen = (iq[0::2] + 1j * iq[1::2]) / 32768.0
    return yol, beklenen


yol1, bek1 = dosya(12345.0)
yol2, _ = dosya(-30000.0)


def oku():
    y = np.asarray(c.iq_oku(yol1))
    assert y.dtype == np.complex64, f"tip {y.dtype}"
    assert len(y) == n, f"uzunluk {len(y)}"
    assert np.max(np.abs(y - bek1)) < 1e-4, "ölçekleme ya da I/Q sırası yanlış (int16/32768 bekleniyor)"


def kestir():
    esit(float(c.ofset_kestir(np.asarray(c.iq_oku(yol1)), fs)), 12345.0, 10.0, "ofset kestirimi")


def negatif():
    esit(float(c.ofset_kestir(np.asarray(c.iq_oku(yol2)), fs)), -30000.0, 10.0, "negatif ofset kestirimi")


def duzelt():
    y = np.asarray(c.iq_oku(yol1))
    z = np.asarray(c.ofset_duzelt(y, fs, 12345.0))
    assert len(z) == n and np.iscomplexobj(z), "çıkış uzunluğu/tipi"
    esit(abs(np.mean(z)), 0.6, 0.02, "düzeltme sonrası DC genliği (işaret ya da zaman ekseni yanlış olabilir)")


def zincir():
    y = np.asarray(c.iq_oku(yol2))
    z = np.asarray(c.ofset_duzelt(y, fs, c.ofset_kestir(y, fs)))
    esit(float(c.ofset_kestir(z, fs)), 0.0, 10.0, "kestir+düzelt sonrası kalan ofset")


kontrol("iq_oku_int16_olcek", oku)
kontrol("ofset_kestir_pozitif", kestir)
kontrol("ofset_kestir_negatif", negatif)
kontrol("ofset_duzelt_dc", duzelt)
kontrol("kestir_duzelt_zinciri", zincir)
bitir()
