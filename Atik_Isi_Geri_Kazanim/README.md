# İçten Yanmalı Motorlarda Atık Isı Geri Kazanımı

İçten yanmalı motorlarda atık ısı geri kazanım yöntemleri üzerine Türkçe akademik araştırma ve tasarım raporu. İncelenen teknolojiler: ORC, su-buhar Rankine, TEG, turbo-kompaund ve egzoz ısı değiştiricileri.

| Dosya | İçerik |
|---|---|
| `RAPOR.md` | Ana rapor (Özet, Giriş, Literatür, Tasarım ve Metodoloji, Sonuçlar ve Tartışma, Sonuç, IEEE Kaynakça, Ekler) |
| `RAPOR.pdf` | Raporun IEEE benzeri düzende dizilmiş PDF sürümü (kapak, içindekiler, numaralı denklemler) |
| `RAPOR.docx` | Raporun Word sürümü (`pandoc` ile üretilmiştir) |
| `sekiller/` | 12 şekil: literatür tablolarından yeniden çizilmiş grafikler ve bu çalışmanın hesaplarına ait grafikler |
| `hesap/hesaplar.py` | Bu çalışmanın tüm hesapları: LMTD/UA kontrolü, ORC enerji ve ekserji analizi, TEG ve güç türbini kestirimleri |
| `hesap/sonuclar.json` | Hesapların sayısal çıktıları |
| `pdf/` | PDF üretim betiği (`rapor_pdf.py`), stil dosyası ve kapak şablonu |

Raporda literatürden aktarılan bulgular **[L]**, literatür verisinden çizilen grafikler **[L→Ç]**, bu çalışmada yapılan hesaplar ise **[H]** ile işaretlenmiştir.

## Yeniden üretme

```bash
pip install CoolProp matplotlib numpy
```

```bash
cd hesap && python3 hesaplar.py
```

```bash
pandoc RAPOR.md -o RAPOR.docx --resource-path=.
```

```bash
python3 pdf/rapor_pdf.py
```

PDF üretimi için pandoc, poppler-utils ve Node.js + Playwright (Chromium) gerekir.
