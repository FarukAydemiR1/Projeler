# İçten Yanmalı Motorlarda Atık Isı Geri Kazanımı

İçten yanmalı motorlarda atık ısı geri kazanım yöntemleri üzerine Türkçe akademik araştırma ve tasarım raporu. İncelenen teknolojiler: ORC, su-buhar Rankine, TEG, turbo-kompaund ve egzoz ısı değiştiricileri.

| Dosya | İçerik |
|---|---|
| `RAPOR.md` | Ana rapor (Özet, Giriş, Literatür, Tasarım ve Metodoloji, Sonuçlar ve Tartışma, Sonuç, IEEE Kaynakça, Ekler) |
| `RAPOR.docx` | Raporun Word sürümü (`pandoc` ile üretilmiştir) |
| `sekiller/` | 11 şekil: literatür tablolarından yeniden çizilmiş grafikler ve bu çalışmanın hesaplarına ait grafikler |
| `hesap/hesaplar.py` | Bu çalışmanın tüm hesapları: LMTD/UA kontrolü, ORC enerji ve ekserji analizi, TEG ve güç türbini kestirimleri |
| `hesap/sonuclar.json` | Hesapların sayısal çıktıları |

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
