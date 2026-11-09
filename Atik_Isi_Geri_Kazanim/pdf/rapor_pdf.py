# -*- coding: utf-8 -*-
"""
RAPOR.md -> RAPOR.pdf (IEEE benzeri akademik düzen).

Adımlar:
  1. RAPOR.md ön işlenir (kapak bilgileri ayrılır, şekil/tablo başlıkları akademik biçime getirilir).
  2. pandoc ile HTML gövdesi üretilir (denklemler MathML).
  3. Chromium (Playwright) ile gövde PDF'i basılır (üst bilgi + sayfa numarası).
  4. Gövde PDF'inden bölüm başlıklarının sayfa numaraları okunur; kapak + içindekiler ayrı basılır.
  5. pdfunite ile birleştirilir.

Gerekenler: pandoc, poppler-utils (pdftotext, pdfunite), Node.js + playwright.
Çalıştırma:  python3 pdf/rapor_pdf.py
"""
import html
import json
import os
import re
import subprocess
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(KOK, "pdf")
CIKTI = os.path.join(KOK, "RAPOR.pdf")
GECICI = tempfile.mkdtemp(prefix="rapor_pdf_")

BASLIK = "İÇTEN YANMALI MOTORLARDA ATIK ISI GERİ KAZANIM YÖNTEMLERİ"
ALT_BASLIK = ("Literatür Taraması, Tasarım Verilerinin Derlenmesi, Enerji–Ekserji Analizi "
              "ve Mühendislik Değerlendirmesi")
UST_BILGI = "İYM'lerde Atık Isı Geri Kazanımı — Araştırma ve Tasarım Raporu"


def tr_upper(s):
    return s.replace("i", "İ").replace("ı", "I").upper()


def on_isle(md):
    # --- kapak bilgilerini ayır
    md = re.sub(r"\A# .*?\n\n", "", md, flags=re.S)
    meta = {}
    for anahtar in ("Rapor türü", "Tarih", "Kaynak sayısı", "Ekler"):
        m = re.search(r"^\*\*%s:\*\* (.*)$\n" % anahtar, md, flags=re.M)
        if m:
            meta[anahtar] = m.group(1)
            md = md.replace(m.group(0), "")
    md = md.lstrip("\n").lstrip("-").lstrip("\n")

    # --- şekiller: görüntü + başlık -> <figure>
    def sekil(m):
        yol, no, yazi = m.group(2), m.group(3), m.group(4)
        return ('<figure class="sekil"><img src="%s"/>'
                '<figcaption><span class="sno">Şekil %s.</span> %s</figcaption></figure>'
                % (os.path.join(KOK, yol), no, md_inline(yazi)))
    md = re.sub(r"!\[(Şekil \d+)\]\(([^)]+)\)\n\n\*\*Şekil (\d+)\.\*\* (.*)", sekil, md)

    # --- tablo başlıkları: "**Tablo N.** Başlık. Not..." -> TABLO N / BAŞLIK / not
    def tablo(m):
        no, yazi = m.group(1), m.group(2)
        parca = re.split(r"(?<=\.)\s+(?=\*\*\[|\S)", yazi, maxsplit=1)
        bas = parca[0].rstrip(".")
        notu = parca[1] if len(parca) > 1 else ""
        return ('<div class="tbaslik"><div class="tno">TABLO %s</div><div class="tad">%s</div>%s</div>'
                % (no, md_inline(tr_upper(bas)),
                   '<div class="tnot">%s</div>' % md_inline(notu) if notu else ""))
    md = re.sub(r"^\*\*Tablo (\d+)\.\*\* (.*)$", tablo, md, flags=re.M)

    # --- özet bölümünü kutu içine al
    md = re.sub(r"## ÖZET\n(.*?)\n---\n", lambda m: "## ÖZET {.unnumbered .ozet-h}\n\n::: ozet\n%s\n:::\n\n---\n" % m.group(1),
                md, count=1, flags=re.S)
    md = md.replace("## İçerik ve kaynak kullanımına ilişkin açıklama",
                    "## OKUYUCU İÇİN NOT {.unnumbered}")
    md = md.replace("## KAYNAKÇA", "## KAYNAKÇA {.kaynakca-h}")
    # liste öncesine boş satır (pandoc markdown bunu ister)
    md = re.sub(r"^((?![|>#\s-]|\d+\. ).+)\n((?:\d+\.|-) )", r"\1\n\n\2", md, flags=re.M)
    # alt simgeler: T_h,1 -> T<sub>h,1</sub> (kod, matematik ve bağlantı içermeyen satırlarda)
    def alt(satir):
        if "`" in satir or "$" in satir or "](" in satir or "<" in satir:
            return satir
        return re.sub(r"(?<=[A-Za-zηΔİİ])_\{?([A-Za-z0-9ığüşöçİIı,]+)\}?", r"<sub>\1</sub>", satir)
    md = "\n".join(alt(x) for x in md.split("\n"))
    # denklem numaraları: \tag{n} -> sırayla saklanır
    global DENKLEM_NO
    DENKLEM_NO = re.findall(r"\\tag\{(\d+)\}", md)
    md = re.sub(r"\s*\\tag\{\d+\}", "", md)
    # yatay çizgiler PDF'te gereksiz
    md = re.sub(r"^---$", "", md, flags=re.M)
    return md, meta


def md_inline(s):
    """Başlık içi küçük markdown: **kalın**, *italik*, `kod`."""
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"<i>\1</i>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def pandoc_html(md):
    giris = os.path.join(GECICI, "rapor.md")
    open(giris, "w", encoding="utf-8").write(md)
    return subprocess.run(
        ["pandoc", giris, "-f", "markdown+tex_math_dollars+fenced_divs+header_attributes-implicit_figures",
         "-t", "html5", "--mathml", "--wrap=none"],
        check=True, capture_output=True, text=True).stdout


DENKLEM_NO = []


def denklem_numarala(govde):
    sayac = iter(DENKLEM_NO)

    def sar(m):
        return ('<span class="denklem"><span class="dm">%s</span><span class="dn">(%s)</span></span>'
                % (m.group(0), next(sayac, "")))
    return re.sub(r'<math display="block".*?</math>', sar, govde, flags=re.S)


def kaynakca_duzenle(govde):
    """[n] ile başlayan kaynakça paragraflarını asılı girintili listeye çevir."""
    def oge(m):
        return '<p class="kay"><span class="kno">[%s]</span>%s</p>' % (m.group(1), m.group(2))
    return re.sub(r"<p>\[(\d+)\] (.*?)</p>", oge, govde)


def bas(html_yol, pdf_yol, ust_alt=True):
    js = os.path.join(GECICI, "bas.js")
    open(js, "w", encoding="utf-8").write(r"""
const { chromium } = require('playwright');
(async () => {
  const [html, pdf, ustAlt, ust] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + html, { waitUntil: 'networkidle' });
  const hdr = `<div style="width:100%;font-family:'Liberation Serif',serif;font-size:8px;color:#555;
      padding:0 18mm;display:flex;justify-content:space-between;">
      <span>${ust}</span><span>Kasım 2026</span></div>`;
  const ftr = `<div style="width:100%;font-family:'Liberation Serif',serif;font-size:9px;color:#333;text-align:center;">
      <span class="pageNumber"></span></div>`;
  await p.pdf({ path: pdf, format: 'A4', printBackground: true,
    displayHeaderFooter: ustAlt === '1', headerTemplate: hdr, footerTemplate: ftr,
    margin: { top: '22mm', bottom: '20mm', left: '20mm', right: '20mm' } });
  await b.close();
})();
""")
    subprocess.run(["node", js, html_yol, pdf_yol, "1" if ust_alt else "0", UST_BILGI],
                   check=True, cwd="/opt" if os.path.isdir("/opt/node_modules") else None,
                   env={**os.environ, "NODE_PATH": subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()})


def sayfa_numaralari(pdf_yol, basliklar):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf_yol], capture_output=True, text=True).stdout).group(1))
    sayfalar = []
    for i in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), pdf_yol, "-"], capture_output=True, text=True).stdout
        sayfalar.append(re.sub(r"\s+", " ", t))
    sonuc, bas_i = [], 0
    for seviye, metin in basliklar:
        anahtar = re.sub(r"\s+", " ", tr_upper(metin) if seviye == 2 else metin)[:45]
        bulunan = None
        for i in range(bas_i, n):
            if anahtar in sayfalar[i] or anahtar in tr_upper(sayfalar[i]):
                bulunan = i
                break
        if bulunan is None:
            bulunan = bas_i
        bas_i = bulunan
        sonuc.append((seviye, metin, bulunan + 1))
    return sonuc, n


def main():
    md = open(os.path.join(KOK, "RAPOR.md"), encoding="utf-8").read()
    md, meta = on_isle(md)
    govde = denklem_numarala(kaynakca_duzenle(pandoc_html(md)))
    css = open(os.path.join(PDF_DIR, "stil.css"), encoding="utf-8").read()

    govde_html = os.path.join(GECICI, "govde.html")
    open(govde_html, "w", encoding="utf-8").write(
        '<!doctype html><html lang="tr"><head><meta charset="utf-8"><style>%s</style></head><body>'
        '<main>%s</main></body></html>' % (css, govde))
    govde_pdf = os.path.join(GECICI, "govde.pdf")
    bas(govde_html, govde_pdf, ust_alt=True)

    # içindekiler için başlıklar (h2 + h3)
    basliklar = []
    for m in re.finditer(r"<h([23])[^>]*>(.*?)</h\1>", govde, flags=re.S):
        metin = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        metin = html.unescape(metin)
        basliklar.append((int(m.group(1)), metin))
    toc, toplam = sayfa_numaralari(govde_pdf, basliklar)

    satirlar = []
    for seviye, metin, sayfa in toc:
        satirlar.append('<div class="toc%d"><span class="tm">%s</span><span class="nokta"></span><span class="tn">%d</span></div>'
                        % (seviye, html.escape(metin), sayfa))
    kapak = open(os.path.join(PDF_DIR, "kapak.html"), encoding="utf-8").read()
    kapak = (kapak.replace("{{BASLIK}}", BASLIK).replace("{{ALT_BASLIK}}", ALT_BASLIK)
             .replace("{{TUR}}", meta.get("Rapor türü", "")).replace("{{TARIH}}", "Kasım 2026")
             .replace("{{KAYNAK}}", "52 kaynak · 12 şekil · 11 tablo · %d sayfa" % toplam)
             .replace("{{TOC}}", "\n".join(satirlar)).replace("{{CSS}}", css))
    kapak_html = os.path.join(GECICI, "kapak.html")
    open(kapak_html, "w", encoding="utf-8").write(kapak)
    kapak_pdf = os.path.join(GECICI, "kapak.pdf")
    bas(kapak_html, kapak_pdf, ust_alt=False)

    subprocess.run(["pdfunite", kapak_pdf, govde_pdf, CIKTI], check=True)
    print(json.dumps({"cikti": CIKTI, "govde_sayfa": toplam}, ensure_ascii=False))


if __name__ == "__main__":
    main()
