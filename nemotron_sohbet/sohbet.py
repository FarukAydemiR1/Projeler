#!/usr/bin/env python3
"""NVIDIA Nemotron 3 Ultra ile terminalden sohbet — Claude kotasini harcamadan.

Kullanim:
    python sohbet.py                  # sohbet baslat
    python sohbet.py "soru"           # tek soru sor, yaniti yaz, cik (script/pipe icin)
    python sohbet.py --dusun          # reasoning modu acik baslat
    cat dosya.txt | python sohbet.py "bu kodu acikla"   # borudan gelen metni ekler

Sohbet icindeki komutlar: /yeni  /dusun  /kaydet  /yardim  /cik
Anahtar: .env icindeki NVIDIA_API_KEY (veya ayni isimli ortam degiskeni).
Tek dis bagimlilik: requests.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

BASE_URL = os.environ.get("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL = os.environ.get("LLM_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
ROOT = Path(__file__).resolve().parent
KAYIT_DIZINI = ROOT / "kayitlar"

SISTEM = ("Sen yardimci bir asistansin. Kullanici Turkce yaziyorsa Turkce yanitla. "
          "Kisa ve net ol; gereksiz tekrar yapma. Emin olmadigin seyi uydurma, bilmiyorum de.")

YARDIM = """
Komutlar:
  /yeni     sohbeti sifirla (gecmisi unut)
  /dusun    reasoning modunu ac/kapa (yavaslar ama zor sorularda daha iyi)
  /kaydet   bu sohbeti kayitlar/ klasorune .md olarak yaz
  /yardim   bu liste
  /cik      cikis (Ctrl+C de olur)
"""


def anahtar_bul() -> str:
    """Once ortam degiskeni, sonra .env dosyasi. Bulunamazsa bos doner."""
    key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if key:
        return key
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("NVIDIA_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def yanit_akit(mesajlar: list[dict], anahtar: str, dusun: bool) -> str:
    """Yaniti parca parca ekrana basar ve tam metni doner. Hata olursa bos doner."""
    govde = {
        "model": MODEL,
        "messages": mesajlar,
        "temperature": 1.0 if dusun else 0.6,
        "top_p": 0.95,
        "max_tokens": 16000 if dusun else 4000,
        "stream": True,
        "chat_template_kwargs": {"enable_thinking": dusun},
    }
    basliklar = {"Authorization": f"Bearer {anahtar}", "Accept": "text/event-stream"}

    try:
        r = requests.post(f"{BASE_URL.rstrip('/')}/chat/completions", json=govde,
                          headers=basliklar, stream=True, timeout=300)
    except requests.RequestException as exc:
        print(f"\n[hata] baglanti kurulamadi: {exc}\n")
        return ""

    if r.status_code != 200:
        print(f"\n[hata] HTTP {r.status_code}: {r.text[:300]}\n")
        if r.status_code in (401, 403):
            print("Anahtar yanlis veya suresi dolmus. build.nvidia.com'dan yenisini alin.\n")
        elif r.status_code == 429:
            print("Kota siniri. Birkac dakika bekleyip tekrar deneyin.\n")
        return ""

    parcalar: list[str] = []
    dusunce_basladi = False
    with r:
        for satir in r.iter_lines(decode_unicode=True):
            if not satir or not satir.startswith("data: "):
                continue
            veri = satir[6:]
            if veri.strip() == "[DONE]":
                break
            try:
                delta = json.loads(veri)["choices"][0]["delta"]
            except (ValueError, KeyError, IndexError):
                continue
            # reasoning_content = modelin dusunme adimlari; soluk gosterip yanittan ayiriyoruz
            dusunce = delta.get("reasoning_content")
            if dusunce:
                if not dusunce_basladi:
                    print("\033[2m[dusunuyor] ", end="", flush=True)
                    dusunce_basladi = True
                print(f"\033[2m{dusunce}\033[0m", end="", flush=True)
            metin = delta.get("content")
            if metin:
                if dusunce_basladi:
                    print("\033[0m\n")
                    dusunce_basladi = False
                print(metin, end="", flush=True)
                parcalar.append(metin)
    print("\n")
    return "".join(parcalar)


def sohbeti_kaydet(mesajlar: list[dict]) -> Path | None:
    konusma = [m for m in mesajlar if m["role"] != "system"]
    if not konusma:
        print("[kayit] Kaydedilecek bir sey yok.\n")
        return None
    KAYIT_DIZINI.mkdir(exist_ok=True)
    yol = KAYIT_DIZINI / f"sohbet_{datetime.now():%Y-%m-%d_%H%M%S}.md"
    satirlar = [f"# Nemotron sohbeti — {datetime.now():%Y-%m-%d %H:%M}", ""]
    for m in konusma:
        satirlar += [f"**{'Sen' if m['role'] == 'user' else 'Nemotron'}:**", "", m["content"], ""]
    yol.write_text("\n".join(satirlar), encoding="utf-8")
    print(f"[kayit] {yol}\n")
    return yol


def main() -> int:
    argümanlar = [a for a in sys.argv[1:] if a not in ("--dusun", "-d")]
    dusun = any(a in ("--dusun", "-d") for a in sys.argv[1:])

    anahtar = anahtar_bul()
    if not anahtar:
        print("HATA: NVIDIA_API_KEY bulunamadi.\n\n"
              "1) build.nvidia.com adresine girin, 'Get API Key' ile anahtar alin\n"
              "2) Bu klasordeki .env dosyasini acin\n"
              "3) NVIDIA_API_KEY=nvapi-... satirini doldurup kaydedin\n")
        return 1

    # Borudan gelen metin (cat dosya.txt | python sohbet.py "ozetle") soruya eklenir
    borudan = "" if sys.stdin.isatty() else sys.stdin.read().strip()
    mesajlar = [{"role": "system", "content": SISTEM}]

    # Tek seferlik mod: soru argumanla ve/veya borudan gelmisse sor, yaz, cik.
    # (Borudan metin varken sohbet dongusune girilemez: input() hemen EOF alir.)
    if argümanlar or borudan:
        soru = " ".join(argümanlar)
        if borudan:
            soru = f"{soru}\n\n---\n{borudan}" if soru else borudan
        mesajlar.append({"role": "user", "content": soru})
        return 0 if yanit_akit(mesajlar, anahtar, dusun) else 1

    print(f"Nemotron 3 Ultra — {MODEL}")
    print(f"Dusunme modu: {'ACIK' if dusun else 'kapali'} (/dusun ile degistir) | /yardim\n")

    while True:
        try:
            girdi = input("\033[1msen>\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGorusuruz.")
            return 0
        if not girdi:
            continue

        komut = girdi.lower()
        if komut in ("/cik", "/quit", "/exit"):
            print("Gorusuruz.")
            return 0
        if komut == "/yardim":
            print(YARDIM)
            continue
        if komut == "/yeni":
            mesajlar = [{"role": "system", "content": SISTEM}]
            print("[yeni] Gecmis temizlendi.\n")
            continue
        if komut == "/dusun":
            dusun = not dusun
            print(f"[dusunme] {'ACIK — yavas ama daha iyi' if dusun else 'kapali — hizli'}\n")
            continue
        if komut == "/kaydet":
            sohbeti_kaydet(mesajlar)
            continue

        mesajlar.append({"role": "user", "content": girdi})
        print("\033[1mnemotron>\033[0m ", end="", flush=True)
        yanit = yanit_akit(mesajlar, anahtar, dusun)
        if yanit:
            mesajlar.append({"role": "assistant", "content": yanit})
        else:
            mesajlar.pop()  # basarisiz turu gecmise yazma


if __name__ == "__main__":
    sys.exit(main())
