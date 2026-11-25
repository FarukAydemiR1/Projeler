#!/usr/bin/env python3
"""Yerel LLM hız ve kalite testi (gpt-oss-120b, GLM-5.3-Flash, Qwen3-Coder için ortak).

Yalnızca standart kütüphane. Çalışan llama-server servisine /v1/chat/completions
isteği atar; modeli ikinci kez belleğe yüklemez. RAG yok: ham model ölçülür.

Alt komutlar:
  hiz         ~500 / 4K / 16K / 28K token girişte 256 token üretim; her ayar 3 kez, ortanca
  kalite      sorular.jsonl'daki 15 soruyu bir kez sorar, yanıtları kaydeder
  hepsi       hiz + kalite (aynı sonuç dosyasına)
  puanla      kod sorularını ayrı venv'de, ağsız, 60 s sınırla çalıştırır; API adlarını
              ve C kodunu statik denetler; sonucu sonuç dosyasına "otomatik" olarak yazar
  puan-sablon puanlar/<model>-<tarih>.json taslağını otomatik puanlarla oluşturur (elle doldurulur)
  rapor       RAPOR-<model>.md üretir (sonuç + puanlar dosyasından)
  oz-dogrula  referans/ çözümlerini testlerden geçirir (testlerin kendisi doğru mu)

API anahtarı: servis istiyorsa LLAMA_KEY ortam değişkeninden okunur (dosyadan okunmaz):
  read -rs LLAMA_KEY && export LLAMA_KEY
  nohup python3 calistir.py hepsi --profil gpt-oss-120b > sonuclar/gpt-oss-120b.log 2>&1 &

Not: Test sırasında servise başka istek gelmemeli (Open WebUI'yi kullanmayın); owui
yüklemesi gibi işlemci yükü varken hız testi yapılmamalı.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent
SONUCLAR = KOK / "sonuclar"
PUANLAR = KOK / "puanlar"
TESTLER = KOK / "testler"
KAYITLAR = Path("/depo/egitim-verisi/kayitlar")
BAGLAM_DOSYASI = KOK / "baglam.json"
VENV_PY = Path(os.environ.get("TEST_VENV_PY", str(Path.home() / ".venv-model-test/bin/python")))

SEVIYELER = {"500": 500, "4k": 4000, "16k": 16000, "28k": 28000}
URETIM = 256
TEKRAR = 3
SEED = 42
HIZ_ISTEMI = "Aşağıdaki GNU Radio kaynak kodlarını incele ve ne yaptıklarını Türkçe özetle.\n\n```python\n{metin}\n```"

# Her model için servis adresi, systemd servisi (tepe bellek için), akıl yürütme düzeyleri
# ve model kartındaki önerilen örnekleme ayarları.
PROFILLER = {
    "gpt-oss-120b": {
        "url": "http://127.0.0.1:8081",
        "servis": "llama-gptoss",
        "efor_hiz": ["low", "medium"],
        "efor_kalite": "medium",
        "ornekleme": {"temperature": 1.0, "top_p": 1.0},
    },
    # GLM sohbet şablonu yalnız low/high tanır; başka değer "max" sayılır.
    "glm-5.3-flash": {
        "url": "http://127.0.0.1:8085",
        "servis": "llama-glm",
        "efor_hiz": ["low", "high"],
        "efor_kalite": "high",
        "ornekleme": {"temperature": 1.0, "top_p": 0.95},
    },
    # Qwen3-Coder akıl yürütme modu olmayan (instruct) model: efor gönderilmez.
    "qwen3-coder-30b": {
        "url": "http://127.0.0.1:8080",
        "servis": "llama-server",
        "efor_hiz": [None],
        "efor_kalite": None,
        "ornekleme": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "repeat_penalty": 1.05},
    },
}


# ----------------------------------------------------------------- yardımcılar
def simdi():
    return dt.datetime.now().strftime("%H:%M:%S")


def log(*a):
    print(simdi(), *a, flush=True)


def json_yaz(yol: Path, veri):
    gecici = yol.with_suffix(yol.suffix + ".tmp")
    gecici.write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
    gecici.replace(yol)


def sorular():
    with open(KOK / "sorular.jsonl", encoding="utf-8") as f:
        return [json.loads(s) for s in f if s.strip()]


def ortanca(d):
    d = [x for x in d if x is not None]
    return statistics.median(d) if d else None


class Istemci:
    def __init__(self, url: str, anahtar: str | None):
        self.url = url.rstrip("/")
        self.anahtar = anahtar

    def _istek(self, yol, govde=None, zaman=3600):
        basliklar = {"Content-Type": "application/json"}
        if self.anahtar:
            basliklar["Authorization"] = f"Bearer {self.anahtar}"
        veri = json.dumps(govde).encode() if govde is not None else None
        return urllib.request.urlopen(urllib.request.Request(self.url + yol, data=veri, headers=basliklar), timeout=zaman)

    def json(self, yol, govde=None, zaman=3600):
        with self._istek(yol, govde, zaman) as y:
            return json.loads(y.read())

    def token_say(self, metin):
        return len(self.json("/tokenize", {"content": metin}, 600)["tokens"])

    def akis(self, govde, zaman=3600):
        """Akışlı sohbet isteği: ilk token süresi istemci tarafında ölçülür."""
        govde = dict(govde, stream=True)
        t0 = time.monotonic()
        ilk = None
        icerik, akil, timings, son = [], [], None, None
        with self._istek("/v1/chat/completions", govde, zaman) as y:
            for ham in y:
                satir = ham.decode("utf-8", "replace").strip()
                if not satir.startswith("data:"):
                    continue
                yuk = satir[5:].strip()
                if yuk == "[DONE]":
                    break
                obj = json.loads(yuk)
                if "timings" in obj:
                    timings = obj["timings"]
                for c in obj.get("choices") or []:
                    d = c.get("delta") or {}
                    for alan, hedef in (("content", icerik), ("reasoning_content", akil)):
                        if d.get(alan):
                            if ilk is None:
                                ilk = time.monotonic() - t0
                            hedef.append(d[alan])
                    son = c.get("finish_reason") or son
        return {
            "ilk_token_s": ilk,
            "toplam_s": time.monotonic() - t0,
            "icerik": "".join(icerik),
            "akil": "".join(akil),
            "timings": timings,
            "bitis": son,
        }


class BellekOrnekleyici(threading.Thread):
    """Servis sürecinin VmRSS değerini 0,25 s'de bir okur, tepeyi tutar."""

    def __init__(self, pid):
        super().__init__(daemon=True)
        self.pid, self.tepe, self._dur = pid, 0, threading.Event()

    def _oku(self, alan):
        try:
            for s in open(f"/proc/{self.pid}/status"):
                if s.startswith(alan + ":"):
                    return int(s.split()[1]) * 1024
        except (OSError, TypeError):
            pass
        return 0

    def run(self):
        while not self._dur.is_set():
            self.tepe = max(self.tepe, self._oku("VmRSS"))
            self._dur.wait(0.25)

    def durdur(self):
        self._dur.set()
        self.join()
        return self.tepe


def servis_pid(servis):
    try:
        pid = int(subprocess.run(["systemctl", "show", "-p", "MainPID", "--value", servis], capture_output=True, text=True).stdout.strip() or 0)
        return pid or None
    except Exception:
        return None


def servis_komutu(servis):
    try:
        cikti = subprocess.run(["systemctl", "cat", servis], capture_output=True, text=True).stdout
    except Exception:
        return None
    m = re.search(r"^ExecStart=(.*?)(?:\n(?!\s)|\Z)", cikti, re.S | re.M)
    return re.sub(r"\s*\\\n\s*", " ", m.group(1)).strip() if m else None


# ----------------------------------------------------------------- bağlam metni
def kaynak_metin():
    """Toplanmış kayıtlardan gerçek kod: gnuradio Python dosyaları, id sırasıyla."""
    parcalar = []
    with open(KAYITLAR / "gnuradio.jsonl", encoding="utf-8") as f:
        for s in f:
            r = json.loads(s)
            if r["tur"] == "kod" and r["dil"] == "python":
                parcalar.append((r["id"], f"# dosya: gnuradio/{r['yol']}\n{r['icerik']}\n"))
    parcalar.sort()
    return "".join(p for _, p in parcalar)


def baglam_metinleri(istemci, yeniden=False):
    """Her seviye için metin. Karakter sayıları baglam.json'da saklanır; böylece
    tüm modeller aynı metni alır (token sayısı tokenizer'a göre biraz değişir)."""
    metin = kaynak_metin()
    ozet = hashlib.sha256(metin.encode()).hexdigest()[:16]
    kayit = json.loads(BAGLAM_DOSYASI.read_text()) if BAGLAM_DOSYASI.exists() else None
    if kayit and not yeniden:
        if kayit["kaynak_sha"] != ozet:
            sys.exit("HATA: kayıtlar değişmiş (baglam.json sha uyuşmuyor). --yeniden-kalibre ile yeniden ölçün; modeller arası karşılaştırma bozulur.")
        return {k: metin[: v["karakter"]] for k, v in kayit["seviyeler"].items()}, kayit

    log("bağlam kalibrasyonu (/tokenize) ...")
    oran = len(metin[:200_000]) / istemci.token_say(metin[:200_000])
    seviyeler = {}
    for ad, hedef in SEVIYELER.items():
        n = int(hedef * oran)
        for _ in range(8):
            t = istemci.token_say(HIZ_ISTEMI.format(metin=metin[:n]))
            if abs(t - hedef) / hedef < 0.01:
                break
            n = int(n * hedef / t)
        seviyeler[ad] = {"karakter": n, "token_kalibrasyon": t}
        log(f"  {ad}: {n} karakter = {t} token")
    kayit = {"kaynak": "gnuradio.jsonl (kod/python, id sırası)", "kaynak_sha": ozet, "istem": HIZ_ISTEMI, "kalibre_eden": None, "seviyeler": seviyeler}
    return {k: metin[: v["karakter"]] for k, v in seviyeler.items()}, kayit


# ----------------------------------------------------------------- hız
def govde_yap(profil, mesaj, efor, max_tokens, ignore_eos):
    g = {
        "messages": [{"role": "user", "content": mesaj}],
        "max_tokens": max_tokens,
        "seed": SEED,
        "cache_prompt": False,
        **profil["ornekleme"],
    }
    if ignore_eos:
        g["ignore_eos"] = True
    if efor:
        g["chat_template_kwargs"] = {"reasoning_effort": efor}
    return g


def hiz_testi(istemci, profil, sonuc, dosya, args):
    metinler, kayit = baglam_metinleri(istemci, args.yeniden_kalibre)
    if not BAGLAM_DOSYASI.exists() or args.yeniden_kalibre:
        kayit["kalibre_eden"] = args.profil
        json_yaz(BAGLAM_DOSYASI, kayit)
    eforlar = args.efor.split(",") if args.efor else profil["efor_hiz"]
    eforlar = [None if e in (None, "yok") else e for e in eforlar]
    seviyeler = args.seviye.split(",") if args.seviye else list(SEVIYELER)
    pid = args.pid or servis_pid(profil["servis"])
    sonuc.setdefault("hiz", [])
    for sev in seviyeler:
        for efor in eforlar:
            for tekrar in range(1, args.tekrar + 1):
                if any(o["seviye"] == sev and o["efor"] == efor and o["tekrar"] == tekrar and "hata" not in o for o in sonuc["hiz"]):
                    continue  # devam ettirilen çalıştırmada yapılmış ölçüm
                g = govde_yap(profil, HIZ_ISTEMI.format(metin=metinler[sev]), efor, URETIM, True)
                ornek = BellekOrnekleyici(pid)
                ornek.start()
                try:
                    r = istemci.akis(g)
                    hata = None
                except Exception as e:  # noqa: BLE001
                    r, hata = {}, f"{type(e).__name__}: {e}"
                tepe = ornek.durdur()
                t = r.get("timings") or {}
                o = {
                    "seviye": sev, "efor": efor, "tekrar": tekrar,
                    "prompt_n": t.get("prompt_n"), "predicted_n": t.get("predicted_n"),
                    "pp_ts": t.get("prompt_per_second"), "tg_ts": t.get("predicted_per_second"),
                    "prompt_ms": t.get("prompt_ms"), "predicted_ms": t.get("predicted_ms"),
                    "ilk_token_s": r.get("ilk_token_s"), "toplam_s": r.get("toplam_s"),
                    "rss_tepe_gib": round(tepe / 2**30, 2) if tepe else None,
                }
                if hata:
                    o["hata"] = hata
                sonuc["hiz"].append(o)
                json_yaz(dosya, sonuc)
                if hata:
                    log(f"hız {sev} efor={efor} #{tekrar}: HATA {hata}")
                else:
                    log(f"hız {sev} efor={efor} #{tekrar}: giriş {o['prompt_n']} tok, işleme {o['pp_ts']:.1f} t/s, üretim {o['tg_ts']:.2f} t/s, ilk token {o['ilk_token_s']:.1f} s, toplam {o['toplam_s']:.1f} s, RSS {o['rss_tepe_gib']} GiB")
    sonuc["hiz_ozet"] = hiz_ozet(sonuc["hiz"])
    if pid:
        try:
            hwm = next(int(s.split()[1]) for s in open(f"/proc/{pid}/status") if s.startswith("VmHWM:"))
            sonuc["servis_vmhwm_gib"] = round(hwm * 1024 / 2**30, 2)
        except Exception:
            pass
    json_yaz(dosya, sonuc)


def hiz_ozet(olcumler):
    gruplar = {}
    for o in olcumler:
        if "hata" in o:
            continue
        gruplar.setdefault((o["seviye"], o["efor"]), []).append(o)
    ozet = []
    for (sev, efor), oo in gruplar.items():
        ozet.append({
            "seviye": sev, "efor": efor, "olcum": len(oo),
            **{k: ortanca([o[k] for o in oo]) for k in ("prompt_n", "pp_ts", "tg_ts", "ilk_token_s", "toplam_s", "rss_tepe_gib")},
        })
    sira = list(SEVIYELER)
    ozet.sort(key=lambda x: (str(x["efor"]), sira.index(x["seviye"]) if x["seviye"] in sira else 99))
    return ozet


# ----------------------------------------------------------------- kalite
def kalite_testi(istemci, profil, sonuc, dosya, args):
    efor = args.efor_kalite if args.efor_kalite is not None else profil["efor_kalite"]
    efor = None if efor in (None, "yok") else efor
    sonuc.setdefault("kalite", [])
    yapilan = {k["id"] for k in sonuc["kalite"] if "hata" not in k}
    sonuc["kalite"] = [k for k in sonuc["kalite"] if "hata" not in k]
    for s in sorular():
        if s["id"] in yapilan or (args.soru and s["id"] not in args.soru.split(",")):
            continue
        g = govde_yap(profil, s["soru"], efor, args.max_tokens, False)
        try:
            r = istemci.akis(g)
            t = r.get("timings") or {}
            k = {
                "id": s["id"], "efor": efor, "yanit": r["icerik"], "akil_yurutme": r["akil"],
                "bitis": r["bitis"], "toplam_s": round(r["toplam_s"], 1),
                "ilk_token_s": round(r["ilk_token_s"], 1) if r["ilk_token_s"] else None,
                "prompt_n": t.get("prompt_n"), "predicted_n": t.get("predicted_n"), "tg_ts": t.get("predicted_per_second"),
            }
            log(f"kalite {s['id']} ({s['konu']}): {k['predicted_n']} token, {k['toplam_s']} s, bitiş {k['bitis']}")
        except Exception as e:  # noqa: BLE001
            k = {"id": s["id"], "hata": f"{type(e).__name__}: {e}"}
            log(f"kalite {s['id']}: HATA {k['hata']}")
        sonuc["kalite"].append(k)
        json_yaz(dosya, sonuc)


# ----------------------------------------------------------------- puanlama
def kod_blogu(metin, diller):
    bloklar = re.findall(r"```([A-Za-z0-9_+-]*)[^\n]*\n(.*?)```", metin or "", re.S)
    uygun = [b for d, b in bloklar if d.lower() in diller]
    if not uygun:
        uygun = [b for d, b in bloklar if d == ""]
    return max(uygun, key=len) if uygun else None


def agsiz_calistir(komut, klasor, zaman=60):
    """sudo unshare -n ile ağsız ad alanında, kendi kullanıcımızla, zaman sınırlı."""
    kullanici = os.environ.get("USER") or subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()
    tam = ["sudo", "-n", "unshare", "-n", "sudo", "-n", "-u", kullanici, "timeout", str(zaman)] + komut
    t0 = time.monotonic()
    try:
        p = subprocess.run(tam, cwd=klasor, capture_output=True, text=True, timeout=zaman + 30)
        return p.returncode, p.stdout, p.stderr, time.monotonic() - t0
    except subprocess.TimeoutExpired:
        return 124, "", "zaman aşımı", time.monotonic() - t0


def kod_testi_calistir(kod, test_dosyasi):
    with tempfile.TemporaryDirectory(prefix="modeltest-") as d:
        Path(d, "cozum.py").write_text(kod, encoding="utf-8")
        shutil.copy(TESTLER / "ortak.py", d)
        shutil.copy(TESTLER / test_dosyasi, d)
        os.chmod(d, 0o755)
        kod_, out, err, sure = agsiz_calistir([str(VENV_PY), "-E", "-s", test_dosyasi], d)
    m = re.search(r"SONUC (\d+)/(\d+)", out)
    gecen, toplam = (int(m.group(1)), int(m.group(2))) if m else (0, None)
    return {
        "cikis_kodu": kod_, "sure_s": round(sure, 1), "gecen": gecen, "toplam": toplam,
        "satirlar": [s for s in out.splitlines() if s.startswith(("GECTI", "KALDI"))],
        "stderr_son": err.strip().splitlines()[-5:] if err.strip() else [],
        "zaman_asimi": kod_ == 124,
    }


def api_denetle(kod):
    with tempfile.TemporaryDirectory(prefix="apikontrol-") as d:
        yol = Path(d, "cozum.py")
        yol.write_text(kod, encoding="utf-8")
        os.chmod(d, 0o755)
        kod_, out, err, _ = agsiz_calistir([str(VENV_PY), "-E", "-s", str(KOK / "api_kontrol.py"), str(yol)], d)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"hata": (err or out)[-500:]}


def c_denetle(kod):
    with tempfile.TemporaryDirectory(prefix="ckontrol-") as d:
        Path(d, "cozum.c").write_text(kod, encoding="utf-8")
        p = subprocess.run(
            ["gcc", "-fsyntax-only", "-std=gnu11", "-Wall", "-Werror=implicit-function-declaration", "cozum.c"],
            cwd=d, capture_output=True, text=True, timeout=60,
        )
    hatalar = [s for s in p.stderr.splitlines() if "error" in s]
    return {"derlenir": p.returncode == 0, "hatalar": hatalar[:10], "uyari_sayisi": p.stderr.count("warning:")}


def kurallar(s, metin):
    m = metin or ""
    return {
        "olmali_eksik": [r for r in s["olmali"] if not re.search(r, m, re.I)],
        "olmali_toplam": len(s["olmali"]),
        "olmamali_bulunan": [r for r in s["olmamali"] if re.search(r, m, re.I)],
    }


def oneri_puan(s, o):
    """Otomatik öneri puanı. Kod soruları için testten; diğerleri elle verilir."""
    if s["tur"] == "kod_test":
        k = o.get("kod_testi")
        if not k or not k.get("toplam"):
            return 0
        oran = k["gecen"] / k["toplam"]
        p = 3 if oran == 1 else 2 if oran >= 0.6 else 1 if oran > 0 else 0
        if o.get("api", {}).get("yok"):
            p -= 1
        return max(p, -1)
    return None


def puanla(args):
    dosya = Path(args.sonuc)
    sonuc = json.loads(dosya.read_text())
    if subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode != 0:
        sys.exit("HATA: ağsız çalıştırma için parolasız sudo gerekiyor (sudo unshare -n).")
    if not VENV_PY.exists():
        sys.exit(f"HATA: test venv'i yok: {VENV_PY}")
    soru_haritasi = {s["id"]: s for s in sorular()}
    otomatik = {}
    for k in sonuc.get("kalite", []):
        s = soru_haritasi.get(k["id"])
        if not s or "hata" in k:
            continue
        o = {"kurallar": kurallar(s, k["yanit"])}
        py = kod_blogu(k["yanit"], {"python", "py", "python3"})
        c = kod_blogu(k["yanit"], {"c"})
        if s["tur"] == "kod_test":
            o["kod_testi"] = kod_testi_calistir(py, s["test"]) if py else {"gecen": 0, "toplam": None, "not": "python kod bloğu yok"}
        if s["tur"] == "statik_c":
            o["c"] = c_denetle(c) if c else {"derlenir": False, "not": "c kod bloğu yok"}
        if py:
            o["api"] = api_denetle(py)
        o["oneri_puan"] = oneri_puan(s, o)
        otomatik[k["id"]] = o
        ozet = o.get("kod_testi") and f"test {o['kod_testi'].get('gecen')}/{o['kod_testi'].get('toplam')}"
        log(f"puanla {k['id']}: {ozet or ''} api-yok={o.get('api', {}).get('yok')} kural-eksik={len(o['kurallar']['olmali_eksik'])} öneri={o['oneri_puan']}")
    sonuc["otomatik"] = otomatik
    json_yaz(dosya, sonuc)


def puan_sablon(args):
    dosya = Path(args.sonuc)
    sonuc = json.loads(dosya.read_text())
    hedef = PUANLAR / dosya.name
    if hedef.exists() and not args.uzerine:
        sys.exit(f"{hedef} zaten var (--uzerine ile ezilir).")
    oto = sonuc.get("otomatik", {})
    taslak = {
        "sonuc_dosyasi": dosya.name,
        "puanlayan": "",
        "sorular": {s["id"]: {"puan": oto.get(s["id"], {}).get("oneri_puan"), "not": ""} for s in sorular()},
        "guclu": [], "zayif": [], "uydurma": [],
    }
    PUANLAR.mkdir(exist_ok=True)
    json_yaz(hedef, taslak)
    print(hedef)


# ----------------------------------------------------------------- rapor
def f1(x, b=1):
    return "-" if x is None else f"{x:.{b}f}"


def rapor(args):
    dosya = Path(args.sonuc)
    sonuc = json.loads(dosya.read_text())
    puan = json.loads((PUANLAR / dosya.name).read_text()) if (PUANLAR / dosya.name).exists() else {"sorular": {}}
    model = sonuc["model"]
    S = []
    S.append(f"# Model testi: {model}\n")
    S.append(f"- Tarih: {sonuc['tarih']}  |  Sonuç dosyası: `sonuclar/{dosya.name}`")
    if sonuc.get("sunucu_komutu"):
        komut = re.sub(r"--api-key-file \S+", "--api-key-file …", sonuc["sunucu_komutu"])
        S.append(f"- Sunucu: `{komut}`")
    S.append(f"- Örnekleme: `{json.dumps(sonuc['profil']['ornekleme'])}`, seed {SEED}; RAG yok.")
    S.append(f"- Donanım: {sonuc.get('donanim', '-')}\n")

    oz = sonuc.get("hiz_ozet") or []
    if oz:
        S.append(f"## Hız (her satır {max(o['olcum'] for o in oz)} ölçümün ortancası, {URETIM} token üretim)\n")
        S.append("| giriş | efor | giriş token | işleme t/s | üretim t/s | ilk token s | toplam s | tepe RSS GiB |")
        S.append("|---|---|---|---|---|---|---|---|")
        for o in oz:
            S.append(f"| {o['seviye']} | {o['efor'] or '-'} | {f1(o['prompt_n'], 0)} | {f1(o['pp_ts'])} | {f1(o['tg_ts'], 2)} | {f1(o['ilk_token_s'])} | {f1(o['toplam_s'])} | {f1(o['rss_tepe_gib'])} |")
        S.append("\n**Uzun bağlamda düşüş** (~500 token girişe göre):\n")
        S.append("| giriş | efor | işleme | üretim |")
        S.append("|---|---|---|---|")
        taban = {o["efor"]: o for o in oz if o["seviye"] == "500"}
        for o in oz:
            b = taban.get(o["efor"])
            if not b or o["seviye"] == "500":
                continue
            S.append(f"| {o['seviye']} | {o['efor'] or '-'} | %{100 * (o['pp_ts'] / b['pp_ts'] - 1):+.0f} | %{100 * (o['tg_ts'] / b['tg_ts'] - 1):+.0f} |")
        hatali = [o for o in sonuc.get("hiz", []) if "hata" in o]
        if hatali:
            S.append(f"\nHatalı ölçüm: {len(hatali)} (ör. {hatali[0]['seviye']}: {hatali[0]['hata'][:120]})")
        if sonuc.get("servis_vmhwm_gib"):
            S.append(f"\nServisin ömür boyu tepe belleği (VmHWM): {sonuc['servis_vmhwm_gib']} GiB")
        S.append("")

    kalite = {k["id"]: k for k in sonuc.get("kalite", [])}
    oto = sonuc.get("otomatik", {})
    if kalite:
        S.append(f"## Kalite (15 soru, efor={sonuc.get('kalite', [{}])[0].get('efor') or '-'}, her soru 0–3; tuzak −1…3)\n")
        S.append("| # | konu | puan | otomatik kontrol | süre s | not |")
        S.append("|---|---|---|---|---|---|")
        toplam, en_fazla = 0, 0
        for s in sorular():
            k = kalite.get(s["id"], {})
            o = oto.get(s["id"], {})
            p = puan.get("sorular", {}).get(s["id"], {})
            pv = p.get("puan", o.get("oneri_puan"))
            en_fazla += s["puan_araligi"][1]
            toplam += pv or 0
            kont = []
            if o.get("kod_testi"):
                kont.append(f"test {o['kod_testi'].get('gecen')}/{o['kod_testi'].get('toplam') or '?'}")
            if o.get("c"):
                kont.append("derlenir" if o["c"].get("derlenir") else "derlenmez")
            if o.get("api", {}).get("yok"):
                kont.append("olmayan ad: " + ", ".join(o["api"]["yok"][:3]))
            kr = o.get("kurallar")
            if kr and kr["olmali_toplam"]:
                kont.append(f"kural {kr['olmali_toplam'] - len(kr['olmali_eksik'])}/{kr['olmali_toplam']}")
            if kr and kr["olmamali_bulunan"]:
                kont.append("yasak: " + ", ".join(kr["olmamali_bulunan"]))
            if "hata" in k:
                kont.append("İSTEK HATASI")
            S.append(f"| {s['id']} | {s['konu']} | {'?' if pv is None else pv} | {'; '.join(kont) or '-'} | {k.get('toplam_s', '-')} | {p.get('not', '')} |")
        S.append(f"\n**Toplam: {toplam} / {en_fazla}**\n")
    for baslik, anahtar in (("Güçlü yönler", "guclu"), ("Zayıf yönler", "zayif"), ("Uydurma örnekleri", "uydurma")):
        if puan.get(anahtar):
            S.append(f"## {baslik}\n")
            S.extend(f"- {x}" for x in puan[anahtar])
            S.append("")

    S.append("## GLM ve Qwen ile karşılaştırma için hazır\n")
    S.append("Aynı betik, aynı sorular ve aynı bağlam metni (baglam.json'daki karakter sayıları) kullanılır:\n")
    S.append("```bash\ncd ~/lab/Projeler/eh/test/model-karsilastirma")
    S.append("read -rs LLAMA_KEY && export LLAMA_KEY")
    S.append("# GLM servisi 8085'te çalışırken (profil: efor low/high, temp 1.0, top_p 0.95):")
    S.append("nohup python3 calistir.py hepsi --profil glm-5.3-flash > sonuclar/glm.log 2>&1 &")
    S.append("# Qwen (8080, efor yok, temp 0.7 / top_p 0.8 / top_k 20 / repeat_penalty 1.05):")
    S.append("nohup python3 calistir.py hepsi --profil qwen3-coder-30b > sonuclar/qwen.log 2>&1 &")
    S.append("# Sonra (anahtar gerekmez):")
    S.append("python3 calistir.py puanla --sonuc sonuclar/<model>-<tarih>.json")
    S.append("python3 calistir.py puan-sablon --sonuc sonuclar/<model>-<tarih>.json   # elle puanla")
    S.append("python3 calistir.py rapor --sonuc sonuclar/<model>-<tarih>.json\n```\n")
    S.append("Adres/servis farklıysa `--url` ve `--servis` verilir. Hız testi sırasında Open WebUI kullanılmamalı.")
    hedef = KOK / f"RAPOR-{model}.md"
    hedef.write_text("\n".join(S) + "\n", encoding="utf-8")
    print(hedef)


# ----------------------------------------------------------------- öz doğrulama
def oz_dogrula(_args):
    hata = 0
    for s in sorular():
        if s["tur"] != "kod_test":
            continue
        kod = (KOK / "referans" / s["test"]).read_text()
        r = kod_testi_calistir(kod, s["test"])
        print(f"{s['id']}: {r['gecen']}/{r['toplam']} ({r['sure_s']} s) {r['satirlar'] if r['gecen'] != r['toplam'] else ''} {r['stderr_son'] if r['gecen'] != r['toplam'] else ''}")
        hata += r["gecen"] != r["toplam"]
    return 1 if hata else 0


# ----------------------------------------------------------------- giriş
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("komut", choices=["hiz", "kalite", "hepsi", "puanla", "puan-sablon", "rapor", "oz-dogrula"])
    ap.add_argument("--profil", choices=list(PROFILLER), default="gpt-oss-120b")
    ap.add_argument("--url", help="servis adresi (profildekini ezer)")
    ap.add_argument("--servis", help="tepe bellek için systemd servis adı (profildekini ezer)")
    ap.add_argument("--pid", type=int, help="servis süreç kimliği (systemd dışı çalıştırma)")
    ap.add_argument("--efor", help="hız testi akıl yürütme düzeyleri, virgülle (yok = gönderme)")
    ap.add_argument("--efor-kalite", help="kalite testi düzeyi (yok = gönderme)")
    ap.add_argument("--seviye", help="yalnız bu seviyeler: 500,4k,16k,28k")
    ap.add_argument("--tekrar", type=int, default=TEKRAR)
    ap.add_argument("--soru", help="yalnız bu sorular: q01,q02")
    ap.add_argument("--max-tokens", type=int, default=12000, help="kalite yanıtı üst sınırı (akıl yürütme dahil)")
    ap.add_argument("--yeniden-kalibre", action="store_true", help="baglam.json'ı yeniden ölç (karşılaştırmayı bozar)")
    ap.add_argument("--sonuc", help="sonuç dosyası (devam ettirme ya da puanla/rapor için)")
    ap.add_argument("--uzerine", action="store_true")
    args = ap.parse_args()

    if args.komut == "puanla":
        return puanla(args)
    if args.komut == "puan-sablon":
        return puan_sablon(args)
    if args.komut == "rapor":
        return rapor(args)
    if args.komut == "oz-dogrula":
        return oz_dogrula(args)

    profil = dict(PROFILLER[args.profil])
    if args.url:
        profil["url"] = args.url
    if args.servis:
        profil["servis"] = args.servis
    istemci = Istemci(profil["url"], os.environ.get("LLAMA_KEY"))
    try:
        istemci.json("/health", zaman=10)
        istemci.json("/v1/models", zaman=10)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            sys.exit("HATA: servis API anahtarı istiyor; LLAMA_KEY ortam değişkenini verin (read -rs LLAMA_KEY && export LLAMA_KEY).")
        raise
    except urllib.error.URLError as e:
        sys.exit(f"HATA: servis yanıt vermiyor ({profil['url']}): {e}")

    SONUCLAR.mkdir(exist_ok=True)
    if args.sonuc:
        dosya = Path(args.sonuc)
        sonuc = json.loads(dosya.read_text())
    else:
        tarih = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
        dosya = SONUCLAR / f"{args.profil}-{tarih}.json"
        sonuc = {
            "model": args.profil, "tarih": tarih, "profil": profil,
            "sunucu_komutu": servis_komutu(profil["servis"]),
            "donanim": "2× Xeon E5-2620 v3 (12 çekirdek), 184 GB RAM, GPU yok",
        }
    log(f"sonuç dosyası: {dosya}")
    if args.komut in ("hiz", "hepsi"):
        hiz_testi(istemci, profil, sonuc, dosya, args)
    if args.komut in ("kalite", "hepsi"):
        kalite_testi(istemci, profil, sonuc, dosya, args)
    log("bitti")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
