"""Kod sorusu testleri için ortak yardımcı.

Test dosyası, modelin kodunu `cozum.py` olarak aynı klasörde bulur. Her kontrol
"GECTI: ad" ya da "KALDI: ad - neden" satırı basar; en sonda "SONUC x/y".
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_sonuc = []


def cozum_yukle(toplam):
    try:
        import cozum  # noqa: F401
    except BaseException as e:  # SystemExit dahil
        print(f"KALDI: import - {type(e).__name__}: {str(e)[:300]}")
        print(f"SONUC 0/{toplam}")
        sys.exit(0)
    return sys.modules["cozum"]


def kontrol(ad, f):
    try:
        f()
        print(f"GECTI: {ad}")
        _sonuc.append(True)
    except BaseException as e:
        print(f"KALDI: {ad} - {type(e).__name__}: {str(e)[:300]}")
        _sonuc.append(False)


def bitir():
    print(f"SONUC {sum(_sonuc)}/{len(_sonuc)}")


def esit(a, b, tol, ne=""):
    if not abs(a - b) <= tol:
        raise AssertionError(f"{ne}: {a!r} beklenen {b!r} ± {tol}")
