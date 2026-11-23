#!/usr/bin/env python3
"""kayitlar/*.jsonl içeriğini Open WebUI bilgi tabanlarına yükler.

Her kategori için ayrı bir bilgi tabanı açılır ("EH-sdr", "EH-dsp" ...).
Her kayıt tek bir belge olarak yüklenir: kod dosyaları bölünmez, belgenin
başında kaynak, sürüm, lisans ve kaynak_link başlığı bulunur. Open WebUI
gömme (embedding) için belgeyi kendi içinde parçalara ayırır; bu ayar
yönetici panelindeki Belgeler (Documents) bölümündedir.

Lisansı belirsiz kaynaklar varsayılan olarak atlanır (--lisanssizlari-al
ile alınır). Yüklenen kayıtlar bir durum dosyasında tutulur; betik yeniden
çalıştırıldığında yalnızca yeni veya değişmiş kayıtlar yüklenir.

Yalnızca Python standart kütüphanesi kullanır.

Kullanım:
    export OWUI_API_KEY=...            # yönetici panelinden oluşturulan anahtar
    python3 owui_yukle.py --kuru --kategori fpga          # ağsız deneme
    python3 owui_yukle.py --kategori fpga --sinir 10      # küçük deneme
    python3 owui_yukle.py                                 # tüm kategoriler
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections import defaultdict
from pathlib import Path

KATEGORILER = ["sdr", "dsp", "ml", "gnss", "radar", "df", "olcum", "em", "fpga", "yayilim", "standart"]

# Lisansı belirsiz; kullanıcı onayı olmadan yüklenmez.
LISANSSIZ = {
    "RadarBook",
    "LoRa_RFFI",
    "RadCharSSL",
    "RadSeg",
    "turing-deinterleaving-challenge",
}

KATEGORI_ACIKLAMA = {
    "sdr": "SDR donanım/yazılım (GNU Radio, SoapySDR, libiio, UHD, bladeRF ...)",
    "dsp": "Sayısal sinyal işleme",
    "ml": "RF için makine öğrenmesi",
    "gnss": "GNSS alıcı yazılımı",
    "radar": "Radar sinyal işleme",
    "df": "Yön bulma (DF)",
    "olcum": "Ölçüm cihazı otomasyonu (SCPI, VISA)",
    "em": "Elektromanyetik benzetim",
    "fpga": "FPGA / RFSoC",
    "yayilim": "Yayılım modelleri (ITU-R ...)",
    "standart": "Veri ve arayüz standartları (SigMF, DIFI)",
}

# Markdown kod bloğu için dil adı
DIL_ETIKETI = {"c-baslik": "c", "cpp-baslik": "cpp", "grc-yaml": "yaml"}


def belge_olustur(r: dict) -> str:
    """Kaydı başlıklı tek bir Markdown belgesine çevirir."""
    baslik = (
        f"<!-- EH-RAG kaydi {r['id']} -->\n"
        f"# {r['kaynak']}: {r['yol']}\n\n"
        f"- kaynak: {r['kaynak']}\n"
        f"- surum: {r.get('surum_seti', '')} (ref {r.get('ref', '')}, commit {r.get('commit', '')[:12]})\n"
        f"- lisans: {r['lisans']}\n"
        f"- kaynak_link: {r['kaynak_link']}\n"
        f"- kategori: {r['kategori']} · tur: {r['tur']} · dil: {r['dil']}\n\n"
    )
    icerik = r["icerik"]
    # Defterler topla.py'de zaten Markdown + kod bloğuna çevrildi.
    if r["tur"] == "defter" or (r["tur"] == "belge" and r["dil"] in ("markdown", "md")):
        return baslik + icerik
    dil = DIL_ETIKETI.get(r["dil"], r["dil"])
    cit = "````" if "```" in icerik else "```"
    return f"{baslik}{cit}{dil}\n{icerik}\n{cit}\n"


def dosya_adi(r: dict) -> str:
    ad = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{r['kaynak']}__{r['yol']}")
    return ad[:180] + ".md"


def ozet(metin: str) -> str:
    return hashlib.sha256(metin.encode()).hexdigest()


class OWUI:
    def __init__(self, url: str, anahtar: str):
        self.url = url.rstrip("/")
        self.anahtar = anahtar

    def _istek(self, yontem, yol, veri=None, govde=None, tur="application/json", zaman=600):
        if veri is not None:
            govde = json.dumps(veri).encode()
        ist = urllib.request.Request(self.url + yol, data=govde, method=yontem)
        ist.add_header("Authorization", f"Bearer {self.anahtar}")
        ist.add_header("Accept", "application/json")
        if govde is not None:
            ist.add_header("Content-Type", tur)
        try:
            with urllib.request.urlopen(ist, timeout=zaman) as y:
                metin = y.read().decode()
                return json.loads(metin) if metin else None
        except urllib.error.HTTPError as h:
            ayrinti = h.read().decode(errors="replace")[:300]
            raise RuntimeError(f"{yontem} {yol}: HTTP {h.code} {ayrinti}") from None

    def bilgi_tabanlari(self) -> dict[str, str]:
        sonuc, sayfa = {}, 1
        while True:
            y = self._istek("GET", f"/api/v1/knowledge/?page={sayfa}")
            ogeler = y.get("items", []) if isinstance(y, dict) else (y or [])
            for k in ogeler:
                sonuc.setdefault(k["name"], k["id"])
            if not ogeler or len(sonuc) >= (y.get("total", 0) if isinstance(y, dict) else 0):
                return sonuc
            sayfa += 1

    def bilgi_tabani_ac(self, ad: str, aciklama: str) -> str:
        y = self._istek("POST", "/api/v1/knowledge/create", {"name": ad, "description": aciklama})
        return y["id"]

    def dosya_yukle(self, ad: str, metin: str) -> str:
        sinir = uuid.uuid4().hex
        govde = (
            f"--{sinir}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{ad}"\r\n'
            f"Content-Type: text/markdown\r\n\r\n"
        ).encode() + metin.encode() + f"\r\n--{sinir}--\r\n".encode()
        y = self._istek(
            "POST",
            "/api/v1/files/?process=true&process_in_background=false",
            govde=govde,
            tur=f"multipart/form-data; boundary={sinir}",
        )
        durum = (y.get("data") or {}).get("status")
        if durum == "failed":
            raise RuntimeError(f"işleme hatası: {(y.get('data') or {}).get('error')}")
        return y["id"]

    def dosya_ekle(self, bt_id: str, dosya_id: str):
        self._istek("POST", f"/api/v1/knowledge/{bt_id}/file/add", {"file_id": dosya_id})


def kayitlari_oku(klasor: Path, kategoriler, kaynaklar, lisanssiz_al):
    secilen, atlanan = defaultdict(list), defaultdict(int)
    for f in sorted(klasor.glob("*.jsonl")):
        for satir in f.open(encoding="utf-8"):
            r = json.loads(satir)
            if kaynaklar and r["kaynak"] not in kaynaklar:
                continue
            if r["kategori"] not in kategoriler:
                atlanan[f"kategori dışı ({r['kategori']})"] += 1
                continue
            if r["kaynak"] in LISANSSIZ and not lisanssiz_al:
                atlanan[f"lisanssız ({r['kaynak']})"] += 1
                continue
            if not r["icerik"].strip():
                atlanan["boş içerik"] += 1
                continue
            secilen[r["kategori"]].append(r)
    return secilen, atlanan


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kayitlar", default="/depo/egitim-verisi/kayitlar", type=Path)
    ap.add_argument("--url", default=os.environ.get("OWUI_URL", "http://127.0.0.1:3000"))
    ap.add_argument("--kategori", nargs="+", choices=KATEGORILER, default=KATEGORILER)
    ap.add_argument("--kaynak", nargs="+", help="yalnız bu kaynaklar")
    ap.add_argument("--sinir", type=int, help="her kategoriden en fazla N belge (deneme için)")
    ap.add_argument("--onek", default="EH-", help="bilgi tabanı adı öneki")
    ap.add_argument("--lisanssizlari-al", action="store_true", help="lisansı belirsiz kaynakları da yükle")
    ap.add_argument("--durum", type=Path, default=Path("/depo/egitim-verisi/owui-durum.json"))
    ap.add_argument("--kuru", nargs="?", const="", metavar="KLASOR",
                    help="ağa bağlanma; belgeleri istenirse KLASOR'e yaz, yalnız sayıları göster")
    a = ap.parse_args()

    secilen, atlanan = kayitlari_oku(a.kayitlar, set(a.kategori), set(a.kaynak or []), a.lisanssizlari_al)
    for neden, n in sorted(atlanan.items()):
        print(f"atlandı: {n:5d}  {neden}")

    durum = json.loads(a.durum.read_text()) if a.durum.exists() else {}
    owui = None
    if a.kuru is None:
        anahtar = os.environ.get("OWUI_API_KEY")
        if not anahtar:
            print("HATA: OWUI_API_KEY ortam değişkeni yok.", file=sys.stderr)
            return 2
        owui = OWUI(a.url, anahtar)
        mevcut = owui.bilgi_tabanlari()

    toplam_hata = 0
    for kat in a.kategori:
        kayitlar = secilen.get(kat, [])
        # Aynı içerik (ör. kopya dosyalar) bir kez yüklenir.
        gorulen, tekil = set(), []
        for r in kayitlar:
            belge = belge_olustur(r)
            h = ozet(r["icerik"])
            if h in gorulen:
                continue
            gorulen.add(h)
            tekil.append((r, belge, ozet(belge)))
        if a.sinir:
            tekil = tekil[: a.sinir]
        bt_adi = f"{a.onek}{kat}"
        print(f"\n[{bt_adi}] {len(kayitlar)} kayıt, {len(tekil)} belge yüklenecek "
              f"({sum(len(b) for _, b, _ in tekil) / 1e6:.1f} MB)")

        if owui is None:
            if a.kuru:
                hedef = Path(a.kuru) / kat
                hedef.mkdir(parents=True, exist_ok=True)
                for r, belge, _ in tekil:
                    (hedef / dosya_adi(r)).write_text(belge, encoding="utf-8")
            continue

        bt_id = mevcut.get(bt_adi) or owui.bilgi_tabani_ac(bt_adi, KATEGORI_ACIKLAMA[kat])
        mevcut[bt_adi] = bt_id
        kat_durum = durum.setdefault(bt_id, {})
        yuklenen = atlanan_eski = hata = 0
        t0 = time.time()
        for i, (r, belge, h) in enumerate(tekil, 1):
            if kat_durum.get(r["id"], {}).get("ozet") == h:
                atlanan_eski += 1
                continue
            try:
                dosya_id = owui.dosya_yukle(dosya_adi(r), belge)
                owui.dosya_ekle(bt_id, dosya_id)
            except Exception as e:  # noqa: BLE001 - bir belge hatası tümünü durdurmasın
                hata += 1
                print(f"  HATA {r['kaynak']}/{r['yol']}: {e}", file=sys.stderr)
                continue
            kat_durum[r["id"]] = {"ozet": h, "dosya_id": dosya_id, "yol": f"{r['kaynak']}/{r['yol']}"}
            yuklenen += 1
            if yuklenen % 10 == 0:
                a.durum.write_text(json.dumps(durum, ensure_ascii=False, indent=1))
                print(f"  {i}/{len(tekil)}  {(time.time() - t0) / yuklenen:.1f} s/belge", flush=True)
        a.durum.write_text(json.dumps(durum, ensure_ascii=False, indent=1))
        toplam_hata += hata
        print(f"  yüklendi {yuklenen}, zaten vardı {atlanan_eski}, hata {hata}, "
              f"süre {time.time() - t0:.0f} s")

    return 1 if toplam_hata else 0


if __name__ == "__main__":
    sys.exit(main())
