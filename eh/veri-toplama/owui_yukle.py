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


def surum(r: dict) -> str:
    """Kısa sürüm: etiket varsa etiket, yoksa commit'in ilk 12 hanesi."""
    ref = r.get("ref") or ""
    return ref if ref and ref != "HEAD" else (r.get("commit") or "")[:12]


def belge_meta(r: dict) -> dict:
    """Open WebUI'nin her parçaya kopyaladığı dosya meta verisi.

    RAG_SOURCE_METADATA_KEYS=kaynak,surum,lisans,kaynak_link ile bu alanlar
    sohbette modele <source ...> öznitelikleri olarak gider.
    """
    return {"kaynak": r["kaynak"], "surum": surum(r), "lisans": r["lisans"], "kaynak_link": r["kaynak_link"]}


def belge_olustur(r: dict) -> str:
    """Kaydı başlıklı tek bir Markdown belgesine çevirir."""
    baslik = (
        f"# {r['kaynak']}: {r['yol']}\n\n"
        f"- kaynak: {r['kaynak']}\n"
        f"- surum: {surum(r)} (sürüm seti {r.get('surum_seti', '')}, commit {r.get('commit', '')[:12]})\n"
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

    def dosya_yukle(self, ad: str, metin: str, meta: dict | None = None) -> str:
        sinir = uuid.uuid4().hex
        meta_alani = (
            f"--{sinir}\r\n"
            f'Content-Disposition: form-data; name="metadata"\r\n\r\n'
            f"{json.dumps(meta, ensure_ascii=False)}\r\n"
        ).encode() if meta else b""
        govde = meta_alani + (
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

    def bt_dosyalari(self, bt_id: str) -> dict[str, str]:
        """Bilgi tabanındaki dosyalar: dosya adı -> dosya kimliği."""
        sonuc, sayfa = {}, 1
        while True:
            y = self._istek("GET", f"/api/v1/knowledge/{bt_id}/files?page={sayfa}&limit=500")
            ogeler = y.get("items", [])
            for d in ogeler:
                sonuc.setdefault(d["filename"], d["id"])
            if not ogeler or sayfa * 500 >= y.get("total", 0):
                return sonuc
            sayfa += 1

    def tum_dosyalar(self) -> list[dict]:
        sonuc, sayfa = [], 1
        while True:
            y = self._istek("GET", f"/api/v1/files/?page={sayfa}&content=false")
            ogeler = y.get("items", []) if isinstance(y, dict) else (y or [])
            sonuc += ogeler
            if not ogeler or (isinstance(y, dict) and len(sonuc) >= y.get("total", 0)):
                return sonuc
            sayfa += 1

    def dosya_sil(self, dosya_id: str):
        self._istek("DELETE", f"/api/v1/files/{dosya_id}")


KOPYA_HATASI = "Duplicate content"


def sahipsizler(owui: OWUI, bt_idleri: list[str]) -> list[dict]:
    """Hiçbir bilgi tabanına bağlı olmayan, bu betiğin adlandırma biçimindeki dosyalar."""
    bagli = set()
    for bt_id in bt_idleri:
        bagli |= set(owui.bt_dosyalari(bt_id).values())
    return [
        d for d in owui.tum_dosyalar()
        if d["id"] not in bagli and d.get("filename", "").endswith(".md") and "__" in d.get("filename", "")
    ]


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
    ap.add_argument("--sahipsiz", choices=["listele", "sil"],
                    help="bilgi tabanına bağlı olmayan yüklenmiş dosyaları listele veya sil; yükleme yapmaz")
    ap.add_argument("--beklenen", type=int,
                    help="--sahipsiz sil ile: sahipsiz dosya sayısı bu değilse hiçbir şey silme")
    a = ap.parse_args()

    if a.sahipsiz:
        anahtar = os.environ.get("OWUI_API_KEY")
        if not anahtar:
            print("HATA: OWUI_API_KEY ortam değişkeni yok.", file=sys.stderr)
            return 2
        owui = OWUI(a.url, anahtar)
        # Bağlılık tüm bilgi tabanlarına göre belirlenir (yalnız --onek ile başlayanlara değil);
        # böylece test veya başka bilgi tabanlarındaki dosyalar sahipsiz sayılmaz.
        liste = sahipsizler(owui, list(owui.bilgi_tabanlari().values()))
        for d in liste:
            print(f"{d['id']}  {d['filename']}")
        print(f"sahipsiz dosya: {len(liste)}")
        if a.sahipsiz == "sil":
            if a.beklenen is None or a.beklenen != len(liste):
                print(f"HATA: silinmedi. --beklenen {a.beklenen} ile bulunan {len(liste)} tutmuyor "
                      "(sil için --beklenen zorunlu).", file=sys.stderr)
                return 1
            for d in liste:
                owui.dosya_sil(d["id"])
            print(f"silindi: {len(liste)}")
        return 0

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
              f"({sum(len(b) for _, b, _ in tekil) / 1e6:.1f} MB)", flush=True)

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
        # Durum dosyasına yazılamadan kesilen önceki çalıştırmalardan kalan
        # dosyalar yeniden yüklenmesin diye bilgi tabanındaki adlara da bakılır.
        bt_dosya = owui.bt_dosyalari(bt_id)
        yuklenen = atlanan_eski = hata = 0
        t0 = time.time()

        def kaydet():
            a.durum.write_text(json.dumps(durum, ensure_ascii=False, indent=1))

        for i, (r, belge, h) in enumerate(tekil, 1):
            yol = f"{r['kaynak']}/{r['yol']}"
            if kat_durum.get(r["id"], {}).get("ozet") == h:
                atlanan_eski += 1
                continue
            if r["id"] not in kat_durum and dosya_adi(r) in bt_dosya:
                kat_durum[r["id"]] = {"ozet": h, "dosya_id": bt_dosya[dosya_adi(r)], "yol": yol}
                atlanan_eski += 1
                kaydet()
                continue
            dosya_id = None
            try:
                dosya_id = owui.dosya_yukle(dosya_adi(r), belge, belge_meta(r))
                owui.dosya_ekle(bt_id, dosya_id)
            except Exception as e:  # noqa: BLE001 - bir belge hatası tümünü durdurmasın
                if KOPYA_HATASI in str(e):
                    # Aynı içerik bu bilgi tabanında zaten var; yeni yüklenen dosya sahipsiz kalır.
                    kat_durum[r["id"]] = {"ozet": h, "dosya_id": bt_dosya.get(dosya_adi(r)), "yol": yol, "kopya": True}
                    if dosya_id:
                        durum.setdefault("_sahipsiz", []).append({"dosya_id": dosya_id, "yol": yol})
                    atlanan_eski += 1
                    kaydet()
                    print(f"  zaten vardı (kopya içerik): {yol}", flush=True)
                    continue
                hata += 1
                print(f"  HATA {yol}: {e}", file=sys.stderr, flush=True)
                continue
            kat_durum[r["id"]] = {"ozet": h, "dosya_id": dosya_id, "yol": yol}
            yuklenen += 1
            kaydet()  # her belgeden sonra: kesilirse kopya yükleme olmasın
            if yuklenen % 10 == 0:
                print(f"  {i}/{len(tekil)}  {(time.time() - t0) / yuklenen:.1f} s/belge", flush=True)
        kaydet()
        toplam_hata += hata
        print(f"  yüklendi {yuklenen}, zaten vardı {atlanan_eski}, hata {hata}, "
              f"süre {time.time() - t0:.0f} s")

    return 1 if toplam_hata else 0


if __name__ == "__main__":
    sys.exit(main())
