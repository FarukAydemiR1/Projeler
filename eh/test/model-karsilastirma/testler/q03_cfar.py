import numpy as np
from ortak import bitir, cozum_yukle, kontrol

c = cozum_yukle(4)
n, ne, nk, pfa = 200_000, 16, 2, 1e-3
rng = np.random.default_rng(1)
p = rng.exponential(1.0, n)
hedefler = [50_000, 100_000, 150_000]
p[hedefler] = 200.0
kenar = ne + nk


def maske():
    m = np.asarray(c.ca_cfar(p, ne, nk, pfa))
    assert m.shape == (n,), f"şekil {m.shape}"
    assert m.dtype == bool, f"tip {m.dtype}"
    return m


def tespit():
    m = maske()
    assert all(m[h] for h in hedefler), f"hedef tespitleri {[bool(m[h]) for h in hedefler]}"


def yanlis_alarm():
    m = maske().copy()
    for h in hedefler:
        m[h - kenar : h + kenar + 1] = False
    oran = m[kenar:-kenar].mean()
    assert pfa / 2.5 < oran < pfa * 2.5, f"yanlış alarm oranı {oran:.2e} (beklenen ~{pfa:.0e})"


def kenarlar():
    m = maske()
    assert not m[:kenar].any() and not m[-kenar:].any(), "pencere sığmayan kenar hücreleri False değil"


kontrol("maske_sekli_bool", maske)
kontrol("uc_hedef_tespiti", tespit)
kontrol("yanlis_alarm_orani", yanlis_alarm)
kontrol("kenar_hucreleri", kenarlar)
bitir()
