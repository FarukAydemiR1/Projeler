#!/usr/bin/env python3
"""Model kodunda kullanılan Python API adlarının gerçekten var olup olmadığını denetler.

Kodu ÇALIŞTIRMAZ: yalnızca ast ile okur, kurulu paketleri (test venv'i) import edip
getattr ile adları arar. calistir.py bu betiği test venv'inin Python'uyla çağırır.

Kullanım: python api_kontrol.py cozum.py  ->  JSON (stdout)
"""

import ast
import importlib
import inspect
import json
import sys

# Yalnızca bu paketler denetlenir (test venv'inde kurulu, surumler.toml sürümleri).
DENETLENEN = {"numpy", "scipy", "sigmf", "pyvisa", "adi", "iio"}

# Bir çağrının döndürdüğü nesnenin sınıfı (öznitelik denetimi için).
DONUS = {
    "pyvisa.highlevel.ResourceManager.open_resource": "pyvisa.resources.messagebased.MessageBasedResource",
    "pyvisa.ResourceManager.open_resource": "pyvisa.resources.messagebased.MessageBasedResource",
}


def coz(yol):
    parca = yol.split(".")
    if parca[0] not in DENETLENEN:
        return None, "denetlenmiyor"
    for i in range(len(parca), 0, -1):
        try:
            nesne = importlib.import_module(".".join(parca[:i]))
        except Exception:
            continue
        for ad in parca[i:]:
            if not hasattr(nesne, ad):
                return None, f"yok: {yol}"
            nesne = getattr(nesne, ad)
        return nesne, "var"
    return None, f"modül yok: {parca[0]}"


def tam_ad(nesne):
    if inspect.isclass(nesne):
        return f"{nesne.__module__}.{nesne.__qualname__}"
    return None


def zincir(dugum):
    adlar = []
    while isinstance(dugum, ast.Attribute):
        adlar.append(dugum.attr)
        dugum = dugum.value
    if isinstance(dugum, ast.Name):
        adlar.append(dugum.id)
        return list(reversed(adlar))
    return None


def main():
    kod = open(sys.argv[1], encoding="utf-8").read()
    sonuc = {"sozdizimi": True, "yok": [], "var": [], "denetlenemedi": [], "importlar": []}
    try:
        agac = ast.parse(kod)
    except SyntaxError as e:
        sonuc["sozdizimi"] = False
        sonuc["hata"] = str(e)
        print(json.dumps(sonuc, ensure_ascii=False))
        return

    takma = {}  # yerel ad -> tam yol
    for d in ast.walk(agac):
        if isinstance(d, ast.Import):
            for a in d.names:
                takma[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
                sonuc["importlar"].append(a.name)
        elif isinstance(d, ast.ImportFrom) and d.module and d.level == 0:
            sonuc["importlar"].append(d.module)
            for a in d.names:
                if a.name == "*":
                    continue
                yol = f"{d.module}.{a.name}"
                takma[a.asname or a.name] = yol
                if d.module.split(".")[0] not in DENETLENEN:
                    continue
                nesne, durum = coz(yol)
                if durum != "var":
                    try:  # alt modül olabilir (from scipy import signal)
                        importlib.import_module(yol)
                        durum = "var"
                    except Exception:
                        pass
                sonuc["var" if durum == "var" else "yok"].append(yol)

    for kok in {v.split(".")[0] for v in takma.values()} - DENETLENEN:
        sonuc["denetlenemedi"].append(kok)

    # değişken -> sınıf (v = paket.Sinif(...) ya da v = obj.open_resource(...))
    sinif = {}
    gorulen = set()
    for d in ast.walk(agac):
        if isinstance(d, ast.Assign) and isinstance(d.value, ast.Call) and len(d.targets) == 1 and isinstance(d.targets[0], ast.Name):
            z = zincir(d.value.func)
            if not z:
                continue
            if z[0] in takma:
                yol = ".".join([takma[z[0]]] + z[1:])
                nesne, _ = coz(yol)
                if inspect.isclass(nesne):
                    sinif[d.targets[0].id] = tam_ad(nesne)
            elif z[0] in sinif and len(z) == 2 and f"{sinif[z[0]]}.{z[1]}" in DONUS:
                sinif[d.targets[0].id] = DONUS[f"{sinif[z[0]]}.{z[1]}"]

    for d in ast.walk(agac):
        if not isinstance(d, ast.Attribute):
            continue
        z = zincir(d)
        if not z or len(z) < 2:
            continue
        if z[0] in takma:
            yol = ".".join([takma[z[0]]] + z[1:])
        elif z[0] in sinif:
            yol = ".".join([sinif[z[0]]] + z[1:2])
        else:
            continue
        if yol in gorulen:
            continue
        gorulen.add(yol)
        nesne, durum = coz(yol)
        if durum == "var":
            sonuc["var"].append(yol)
        elif durum.startswith(("yok", "modül")):
            # yalnızca en kısa eksik yolu raporla
            if not any(yol.startswith(y + ".") for y in sonuc["yok"]):
                sonuc["yok"].append(yol)
    sonuc["yok"] = sorted(set(sonuc["yok"]))
    sonuc["var"] = sorted(set(sonuc["var"]))
    print(json.dumps(sonuc, ensure_ascii=False))


if __name__ == "__main__":
    main()
