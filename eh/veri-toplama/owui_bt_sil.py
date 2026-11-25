#!/usr/bin/env python3
"""Open WebUI'de adı verilen bilgi tabanlarını siler.

- Yalnızca komut satırında adı tam olarak verilen bilgi tabanlarına dokunur.
- --evet verilmezse yalnızca ne yapılacağını gösterir.
- Tekrar çalıştırılabilir: zaten silinmiş olanlar "yok" diye geçilir.
- Her silme isteğinin bitmesini bekler (büyük bilgi tabanında dakikalar
  sürebilir); sonunda adların hiçbirinin kalmadığını doğrular. Tümü
  silinmişse çıkış kodu 0, değilse 1.

Bilgi tabanı silinince dosyaları sahipsiz kalır; onları
`owui_yukle.py --sahipsiz sil --beklenen N` temizler.

Kullanım:
    export OWUI_API_KEY=...
    python3 owui_bt_sil.py EH-sdr EH-dsp            # kuru: yalnız göster
    python3 owui_bt_sil.py --evet EH-sdr EH-dsp     # sil
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from owui_yukle import OWUI


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("adlar", nargs="+", help="silinecek bilgi tabanlarının tam adları")
    ap.add_argument("--evet", action="store_true", help="gerçekten sil")
    ap.add_argument("--url", default=os.environ.get("OWUI_URL", "http://127.0.0.1:3000"))
    a = ap.parse_args()

    anahtar = os.environ.get("OWUI_API_KEY")
    if not anahtar:
        print("HATA: OWUI_API_KEY ortam değişkeni yok.", file=sys.stderr)
        return 2
    owui = OWUI(a.url, anahtar)

    mevcut = owui.bilgi_tabanlari()
    hedef = {ad: mevcut[ad] for ad in a.adlar if ad in mevcut}
    for ad in a.adlar:
        print(f"{'silinecek' if ad in hedef else 'yok (zaten silinmiş)'}: {ad}")
    korunan = sorted(set(mevcut) - set(hedef))
    print(f"korunacak: {', '.join(korunan) or '-'}")
    if not a.evet:
        print("Kuru çalıştırma; silmek için --evet ekleyin.")
        return 0

    for ad, bt_id in hedef.items():
        t0 = time.time()
        print(f"siliniyor: {ad} ...", end="", flush=True)
        owui._istek("DELETE", f"/api/v1/knowledge/{bt_id}/delete", zaman=1800)
        print(f" tamam ({time.time() - t0:.0f} s)", flush=True)

    kalan = sorted(set(a.adlar) & set(owui.bilgi_tabanlari()))
    if kalan:
        print(f"HATA: hâlâ duruyor: {', '.join(kalan)}", file=sys.stderr)
        return 1
    print("Verilen bilgi tabanlarının hiçbiri kalmadı.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
