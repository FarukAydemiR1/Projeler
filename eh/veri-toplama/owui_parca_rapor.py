#!/usr/bin/env python3
"""Open WebUI bilgi tabanlarının parça (chunk) istatistikleri.

Open WebUI veritabanını (webui.db) ve Chroma vektör veritabanını yalnızca
okuma kipinde açar; hiçbir şey yazmaz. API anahtarı gerekmez.

Her bilgi tabanı için: dosya sayısı, parça sayısı, ortalama parça boyu,
200 karakterden kısa parça sayısı ve kaynak/surum/lisans meta verisi taşıyan
parçaların oranı.

Kullanım:
    python3 owui_parca_rapor.py                  # EH- ile başlayan tüm bilgi tabanları
    python3 owui_parca_rapor.py --ad TEST-standart
    python3 owui_parca_rapor.py --ornek 2        # her bilgi tabanından 2 kısa parça örneği
"""

from __future__ import annotations

import argparse
import sqlite3
import statistics
import sys
from pathlib import Path

META_ANAHTARLARI = ("kaynak", "surum", "lisans", "kaynak_link")


def baglan(yol: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{yol}?mode=ro", uri=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--veri", type=Path, default=Path("/data/open-webui"))
    ap.add_argument("--ad", nargs="+", help="bilgi tabanı adları (varsayılan: --onek ile başlayanlar)")
    ap.add_argument("--onek", default="EH-")
    ap.add_argument("--kisa", type=int, default=200, help="kısa parça sınırı (karakter)")
    ap.add_argument("--ornek", type=int, default=0, help="gösterilecek kısa parça örneği sayısı")
    a = ap.parse_args()

    web = baglan(a.veri / "webui.db")
    chroma = baglan(a.veri / "vector_db" / "chroma.sqlite3")

    bt = web.execute("select id, name from knowledge order by name").fetchall()
    bt = [(i, n) for i, n in bt if (n in a.ad if a.ad else n.startswith(a.onek))]
    if not bt:
        print("Eşleşen bilgi tabanı yok.", file=sys.stderr)
        return 1

    print(f"{'bilgi tabanı':<18}{'dosya':>7}{'parça':>8}{'ort.kr':>8}{'<' + str(a.kisa):>7}{'meta %':>8}")
    for bt_id, ad in bt:
        dosya = web.execute("select count(*) from knowledge_file where knowledge_id=?", (bt_id,)).fetchone()[0]
        satir = chroma.execute(
            """
            select e.id,
                   max(case when m.key='chroma:document' then m.string_value end),
                   sum(case when m.key in (?,?,?,?) then 1 else 0 end)
            from collections c
            join segments s on s.collection = c.id and s.scope = 'METADATA'
            join embeddings e on e.segment_id = s.id
            left join embedding_metadata m on m.id = e.id
            where c.name = ?
            group by e.id
            """,
            (*META_ANAHTARLARI, bt_id),
        ).fetchall()
        boy = [len(d or "") for _, d, _ in satir]
        kisa = [d for _, d, _ in satir if len(d or "") < a.kisa]
        meta = sum(1 for *_, m in satir if m == len(META_ANAHTARLARI))
        ort = statistics.mean(boy) if boy else 0
        oran = 100 * meta / len(satir) if satir else 0
        print(f"{ad:<18}{dosya:>7}{len(satir):>8}{ort:>8.0f}{len(kisa):>7}{oran:>7.0f}%")
        for d in kisa[: a.ornek]:
            print(f"    kısa: {d!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
