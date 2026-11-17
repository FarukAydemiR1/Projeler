#!/usr/bin/env python3
"""EH laboratuvarı eğitim verisi toplayıcı.

kaynaklar.toml içindeki her depoyu belirtilen sürüm etiketinden indirir,
belge, örnek kod, test ve not defterlerini seçer ve her dosyayı sürüm
etiketli bir JSONL kaydına dönüştürür. Çıktı yerel bilgi bankasına (RAG)
yüklemeye ve ileride ince ayar veri setine temel olmaya hazırdır.

Yalnızca Python standart kütüphanesi ve git kullanır.

Kullanım:
    python3 topla.py --hedef /depo/egitim-verisi
    python3 topla.py --hedef /depo/egitim-verisi --sadece sigmf-python torchsig
    python3 topla.py --hedef /depo/egitim-verisi --liste
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

BURASI = Path(__file__).resolve().parent

# Alınacak dosya türleri: uzantı -> (tür, dil)
UZANTILAR = {
    ".py": ("kod", "python"),
    ".ipynb": ("defter", "python"),
    ".grc": ("akis_semasi", "grc-yaml"),
    ".c": ("kod", "c"),
    ".cc": ("kod", "cpp"),
    ".cpp": ("kod", "cpp"),
    ".h": ("kod", "c-baslik"),
    ".hpp": ("kod", "cpp-baslik"),
    ".m": ("kod", "matlab"),
    ".sh": ("kod", "bash"),
    ".md": ("belge", "markdown"),
    ".rst": ("belge", "rst"),
    ".dox": ("belge", "doxygen"),
    ".txt": ("belge", "metin"),
    ".conf": ("yapilandirma", "conf"),
    ".ini": ("yapilandirma", "ini"),
    ".yml": ("yapilandirma", "yaml"),
    ".yaml": ("yapilandirma", "yaml"),
}

AZAMI_BOYUT = 512 * 1024  # bayt; daha büyük dosyalar atlanır (veri, üretilmiş kod vb.)
ATLANACAK_KLASORLER = {".git", "__pycache__", "build", "dist", ".ipynb_checkpoints", "node_modules"}


def calistir(komut: list[str], cwd: Path | None = None) -> str:
    sonuc = subprocess.run(komut, cwd=cwd, capture_output=True, text=True)
    if sonuc.returncode != 0:
        raise RuntimeError(f"{' '.join(komut)}\n{sonuc.stderr.strip()}")
    return sonuc.stdout.strip()


def depoyu_indir(depo: dict, ham_klasor: Path, yeniden: bool) -> tuple[Path, str]:
    """Depoyu sığ (depth=1) olarak indirir; (klasör, commit) döndürür."""
    hedef = ham_klasor / depo["ad"]
    if hedef.exists() and yeniden:
        shutil.rmtree(hedef)
    if not hedef.exists():
        komut = ["git", "clone", "--depth", "1", "--quiet"]
        if depo["ref"] != "HEAD":
            komut += ["--branch", depo["ref"]]
        komut += [depo["url"], str(hedef)]
        calistir(komut)
    commit = calistir(["git", "rev-parse", "HEAD"], cwd=hedef)
    return hedef, commit


def secilen_dosyalar(kok: Path, desenler: list[str]) -> list[Path]:
    secilen: set[Path] = set()
    for desen in desenler:
        for yol in kok.glob(desen):
            if yol.is_dir():
                adaylar = yol.rglob("*")
            else:
                adaylar = [yol]
            for aday in adaylar:
                if not aday.is_file():
                    continue
                if ATLANACAK_KLASORLER.intersection(aday.relative_to(kok).parts):
                    continue
                if aday.suffix.lower() in UZANTILAR or aday.name.upper().startswith("README"):
                    secilen.add(aday)
    return sorted(secilen)


def defteri_metne_cevir(ham: str) -> str:
    """Jupyter defterinden markdown ve kod hücrelerini alır, çıktıları atar."""
    defter = json.loads(ham)
    parcalar = []
    for hucre in defter.get("cells", []):
        kaynak = "".join(hucre.get("source", []))
        if not kaynak.strip():
            continue
        if hucre.get("cell_type") == "code":
            parcalar.append(f"```python\n{kaynak}\n```")
        else:
            parcalar.append(kaynak)
    return "\n\n".join(parcalar)


def dosyayi_oku(yol: Path) -> str | None:
    if yol.stat().st_size > AZAMI_BOYUT:
        return None
    ham = yol.read_bytes()
    if b"\x00" in ham[:8192]:
        return None  # ikili dosya
    try:
        metin = ham.decode("utf-8")
    except UnicodeDecodeError:
        metin = ham.decode("latin-1")
    if yol.suffix.lower() == ".ipynb":
        try:
            metin = defteri_metne_cevir(metin)
        except (json.JSONDecodeError, TypeError):
            return None
    return metin if metin.strip() else None


def depoyu_isle(depo: dict, hedef: Path, surum_seti: dict, yeniden: bool) -> dict:
    ham_klasor = hedef / "ham"
    kayit_klasor = hedef / "kayitlar"
    ham_klasor.mkdir(parents=True, exist_ok=True)
    kayit_klasor.mkdir(parents=True, exist_ok=True)

    kok, commit = depoyu_indir(depo, ham_klasor, yeniden)
    dosyalar = secilen_dosyalar(kok, depo["dahil"])
    tarih = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sayac = {"dosya": 0, "atlanan": 0}
    turler: dict[str, int] = {}

    cikti = kayit_klasor / f"{depo['ad']}.jsonl"
    with cikti.open("w", encoding="utf-8") as f:
        for yol in dosyalar:
            icerik = dosyayi_oku(yol)
            if icerik is None:
                sayac["atlanan"] += 1
                continue
            goreli = yol.relative_to(kok).as_posix()
            tur, dil = UZANTILAR.get(yol.suffix.lower(), ("belge", "metin"))
            kayit = {
                "id": hashlib.sha1(f"{depo['ad']}:{commit}:{goreli}".encode()).hexdigest(),
                "kaynak": depo["ad"],
                "url": depo["url"],
                "ref": depo["ref"],
                "commit": commit,
                "yol": goreli,
                "kaynak_link": depo["url"].removesuffix(".git") + f"/blob/{commit}/{goreli}",
                "tur": tur,
                "dil": dil,
                "kategori": depo["kategori"],
                "lisans": depo["lisans"],
                "surum_seti": surum_seti["kimlik"]["etiket"],
                "toplama_tarihi": tarih,
                "icerik": icerik,
            }
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
            sayac["dosya"] += 1
            turler[tur] = turler.get(tur, 0) + 1

    return {"ad": depo["ad"], "ref": depo["ref"], "commit": commit, "lisans": depo["lisans"],
            "kategori": depo["kategori"], **sayac, "turler": turler}


def lisans_raporu_yaz(hedef: Path, ozetler: list[dict]) -> None:
    satirlar = [
        "# Toplanan kaynakların lisansları",
        "",
        "Bu tablo depoların bildirdiği lisanslardır; hukuki değerlendirme değildir.",
        "NC (ticari olmayan) ve GPL lisanslı içerikle model ince ayarı yapmadan önce kurumunuzun hukuk birimine danışın.",
        "",
        "| Kaynak | Sürüm | Commit | Lisans | Dosya |",
        "|---|---|---|---|---|",
    ]
    for o in ozetler:
        satirlar.append(f"| {o['ad']} | {o['ref']} | {o['commit'][:10]} | {o['lisans']} | {o['dosya']} |")
    (hedef / "LISANSLAR.md").write_text("\n".join(satirlar) + "\n", encoding="utf-8")


def main() -> int:
    ayrac = argparse.ArgumentParser(description="EH laboratuvarı eğitim verisi toplayıcı")
    ayrac.add_argument("--hedef", type=Path, required=True, help="çıktı klasörü, ör. /depo/egitim-verisi")
    ayrac.add_argument("--kaynaklar", type=Path, default=BURASI / "kaynaklar.toml")
    ayrac.add_argument("--surumler", type=Path, default=BURASI / "surumler.toml")
    ayrac.add_argument("--sadece", nargs="*", help="yalnızca bu adlardaki depoları işle")
    ayrac.add_argument("--yeniden", action="store_true", help="indirilmiş depoları silip yeniden indir")
    ayrac.add_argument("--liste", action="store_true", help="kaynakları listele ve çık")
    arg = ayrac.parse_args()

    depolar = tomllib.loads(arg.kaynaklar.read_text(encoding="utf-8"))["depo"]
    surum_seti = tomllib.loads(arg.surumler.read_text(encoding="utf-8"))

    if arg.liste:
        for d in depolar:
            print(f"{d['ad']:35} {d['ref']:20} {d['kategori']:9} {d['lisans']}")
        return 0

    if arg.sadece:
        bilinmeyen = set(arg.sadece) - {d["ad"] for d in depolar}
        if bilinmeyen:
            print(f"Bilinmeyen kaynak: {', '.join(sorted(bilinmeyen))}", file=sys.stderr)
            return 2
        depolar = [d for d in depolar if d["ad"] in arg.sadece]

    arg.hedef.mkdir(parents=True, exist_ok=True)
    ozetler, hatalar = [], []
    for i, depo in enumerate(depolar, 1):
        print(f"[{i}/{len(depolar)}] {depo['ad']} ({depo['ref']}) ...", flush=True)
        try:
            ozet = depoyu_isle(depo, arg.hedef, surum_seti, arg.yeniden)
            ozetler.append(ozet)
            print(f"    {ozet['dosya']} dosya alındı, {ozet['atlanan']} atlandı, commit {ozet['commit'][:10]}")
        except Exception as hata:  # bir depo hatası diğerlerini durdurmasın
            hatalar.append({"ad": depo["ad"], "hata": str(hata)})
            print(f"    HATA: {hata}", file=sys.stderr)

    ozet_dosyasi = arg.hedef / "ozet.json"
    eski = json.loads(ozet_dosyasi.read_text(encoding="utf-8")) if ozet_dosyasi.exists() else {"kaynaklar": []}
    birlesik = {o["ad"]: o for o in eski.get("kaynaklar", [])}
    birlesik.update({o["ad"]: o for o in ozetler})
    tum = sorted(birlesik.values(), key=lambda o: o["ad"])
    ozet_dosyasi.write_text(json.dumps({
        "guncelleme": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "surum_seti": surum_seti,
        "kaynaklar": tum,
        "son_calisma_hatalari": hatalar,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    lisans_raporu_yaz(arg.hedef, tum)

    toplam = sum(o["dosya"] for o in tum)
    print(f"\nBitti: {len(tum)} kaynak, {toplam} kayıt. Hata: {len(hatalar)}.")
    print(f"Kayıtlar: {arg.hedef / 'kayitlar'}  ·  Özet: {ozet_dosyasi}  ·  Lisanslar: {arg.hedef / 'LISANSLAR.md'}")
    return 1 if hatalar else 0


if __name__ == "__main__":
    sys.exit(main())
