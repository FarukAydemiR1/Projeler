#!/usr/bin/env python3
"""llama-embed önüne konan gömme (embedding) önbelleği.

Open WebUI bir belgeyi bilgi tabanına eklerken aynı parçaları iki kez gömer
(önce file-<id>, sonra bilgi tabanı koleksiyonu). Bu servis OpenAI uyumlu
/v1/embeddings isteklerini karşılar; her metnin SHA-256 özetini anahtar
olarak kullanır ve vektörü bellekte tutar. Önbellekte olmayan metinler tek
bir istekte llama-embed'e gönderilir.

- Yalnız 127.0.0.1 dinler.
- En fazla --sinir kayıt tutar; dolunca en eski kullanılan atılır (LRU).
- Vektörler float32 olarak saklanır ve yanıtlar her zaman bu kopyadan
  üretilir; böylece ilk yanıt ile önbellekten gelen yanıt birebir aynıdır.
- /v1/embeddings dışındaki istekler olduğu gibi llama-embed'e aktarılır.
- GET /onbellek/durum: isabet, ıska ve kayıt sayısı.

Yalnızca Python standart kütüphanesi kullanır.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from array import array
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Onbellek:
    def __init__(self, sinir: int):
        self.sinir = sinir
        self.veri: OrderedDict[bytes, bytes] = OrderedDict()
        self.kilit = threading.Lock()
        self.isabet = 0
        self.iska = 0

    def al(self, anahtar: bytes) -> bytes | None:
        with self.kilit:
            v = self.veri.get(anahtar)
            if v is not None:
                self.veri.move_to_end(anahtar)
            return v

    def koy(self, anahtar: bytes, vektor: bytes):
        with self.kilit:
            self.veri[anahtar] = vektor
            self.veri.move_to_end(anahtar)
            while len(self.veri) > self.sinir:
                self.veri.popitem(last=False)

    def say(self, isabet: int, iska: int):
        with self.kilit:
            self.isabet += isabet
            self.iska += iska

    def durum(self) -> dict:
        with self.kilit:
            return {"kayit": len(self.veri), "sinir": self.sinir, "isabet": self.isabet, "iska": self.iska}


def ozet(metin: str) -> bytes:
    return hashlib.sha256(metin.encode("utf-8")).digest()


def yap(sunucu_adresi: str, onbellek: Onbellek, zaman_asimi: float):
    class Isleyici(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):  # metin içeriği günlüğe yazılmaz
            pass

        def _yanit(self, kod: int, govde: bytes, tur="application/json"):
            self.send_response(kod)
            self.send_header("Content-Type", tur)
            self.send_header("Content-Length", str(len(govde)))
            self.end_headers()
            self.wfile.write(govde)

        def _aktar(self, yontem: str, govde: bytes | None):
            ist = urllib.request.Request(sunucu_adresi + self.path, data=govde, method=yontem)
            for b in ("Content-Type", "Authorization"):
                if self.headers.get(b):
                    ist.add_header(b, self.headers[b])
            try:
                with urllib.request.urlopen(ist, timeout=zaman_asimi) as y:
                    return y.status, y.read(), y.headers.get("Content-Type", "application/json")
            except urllib.error.HTTPError as h:
                return h.code, h.read(), h.headers.get("Content-Type", "application/json")

        def _govde(self) -> bytes:
            n = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(n) if n else b""

        def do_GET(self):
            if self.path == "/onbellek/durum":
                return self._yanit(200, json.dumps(onbellek.durum()).encode())
            try:
                self._yanit(*self._aktar("GET", None))
            except Exception as e:  # noqa: BLE001
                self._yanit(502, json.dumps({"error": str(e)}).encode())

        def do_POST(self):
            govde = self._govde()
            yol = self.path.split("?")[0]
            if yol not in ("/v1/embeddings", "/embeddings"):
                try:
                    return self._yanit(*self._aktar("POST", govde))
                except Exception as e:  # noqa: BLE001
                    return self._yanit(502, json.dumps({"error": str(e)}).encode())
            try:
                istek = json.loads(govde)
                girdi = istek.get("input")
                tek = isinstance(girdi, str)
                metinler = [girdi] if tek else girdi
                if not isinstance(metinler, list) or not all(isinstance(m, str) for m in metinler):
                    # belirteç (token) dizileri gibi biçimler önbelleğe alınmaz
                    return self._yanit(*self._aktar("POST", govde))
                bicim = istek.get("encoding_format", "float")

                anahtarlar = [ozet(m) for m in metinler]
                vektorler: list[bytes | None] = [onbellek.al(a) for a in anahtarlar]
                eksik = [i for i, v in enumerate(vektorler) if v is None]
                kullanim = 0
                if eksik:
                    # Aynı istekte tekrar eden metinler bir kez gönderilir.
                    tekil: dict[bytes, list[int]] = {}
                    for i in eksik:
                        tekil.setdefault(anahtarlar[i], []).append(i)
                    gonder = [metinler[ix[0]] for ix in tekil.values()]
                    alt = dict(istek, input=gonder)
                    alt.pop("encoding_format", None)
                    kod, cevap, tur = self._aktar("POST", json.dumps(alt).encode())
                    if kod != 200:
                        return self._yanit(kod, cevap, tur)
                    c = json.loads(cevap)
                    kullanim = (c.get("usage") or {}).get("prompt_tokens", 0)
                    sirali = sorted(c["data"], key=lambda d: d["index"])
                    for (anahtar, ix), d in zip(tekil.items(), sirali):
                        v = array("f", d["embedding"]).tobytes()
                        onbellek.koy(anahtar, v)
                        for i in ix:
                            vektorler[i] = v
                onbellek.say(len(metinler) - len(eksik), len(eksik))

                veri = []
                for i, v in enumerate(vektorler):
                    if bicim == "base64":
                        emb = base64.b64encode(v).decode()
                    else:
                        emb = array("f", v).tolist()
                    veri.append({"object": "embedding", "index": i, "embedding": emb})
                yanit = {
                    "object": "list",
                    "model": istek.get("model", ""),
                    "data": veri,
                    "usage": {"prompt_tokens": kullanim, "total_tokens": kullanim},
                }
                self._yanit(200, json.dumps(yanit).encode())
            except Exception as e:  # noqa: BLE001
                self._yanit(500, json.dumps({"error": f"onbellek: {e}"}).encode())

    return Isleyici


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dinle", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8084)
    ap.add_argument("--hedef", default="http://127.0.0.1:8082")
    ap.add_argument("--sinir", type=int, default=200_000)
    ap.add_argument("--zaman-asimi", type=float, default=900)
    a = ap.parse_args()
    if a.dinle not in ("127.0.0.1", "::1", "localhost"):
        print("Yalnız yerel adres dinlenebilir.", file=sys.stderr)
        return 2
    onbellek = Onbellek(a.sinir)
    sunucu = ThreadingHTTPServer((a.dinle, a.port), yap(a.hedef.rstrip("/"), onbellek, a.zaman_asimi))
    sunucu.daemon_threads = True
    print(f"{time.strftime('%F %T')} dinleniyor {a.dinle}:{a.port} -> {a.hedef}, sınır {a.sinir}", flush=True)
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
