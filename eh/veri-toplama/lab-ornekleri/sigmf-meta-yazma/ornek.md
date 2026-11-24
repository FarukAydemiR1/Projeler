---
baslik: SigMF kaydı için meta veri dosyası (.sigmf-meta) yazma
gorev_no:               # kodlama görev kataloğu depoda yok; katalog gelince doldurulacak
donanim: yok (sentetik veri)
yazilim: sigmf 1.14.0, numpy 2.5.5, Python 3.14.4
surum_seti: eh-lab-2026-11
test_duzenegi: yok; donanımsız, sıfırlardan oluşan sentetik complex64 dizi
dogrulayan: Claude Code oturumu (sunucu `ai`, geçici sanal ortam)
tarih: 2026-11-24
durum: dogrulandi       # dogrulandi | kismen | basarisiz
kaynak: sigmf-python v1.14.0 (commit 9cdefc8421c1), docs/source/quickstart.rst, LGPL-3.0
kaynak_link: https://github.com/sigmf/sigmf-python/blob/9cdefc8421c1f133403a691717dbd69c8725a532/docs/source/quickstart.rst
---

## Soru
Elimde numpy dizisi olarak I/Q örnekleri var. Bunları SigMF olarak saklamak istiyorum: örnek hızı, merkez frekans, kayıt zamanı ve ilgi çeken bir bölge için not içeren bir `.sigmf-meta` dosyası nasıl yazarım?

## Cevap
SigMF kaydı iki dosyadan oluşur: ham örnekler `.sigmf-data`, açıklamalar `.sigmf-meta` (JSON). `sigmf` paketinde `SigMFFile` nesnesi kurulur, üç bölüm doldurulur ve `tofile()` ile yazılır:

- **global**: tüm kayıt için geçerli alanlar. `core:datatype` dosyadaki örnek tipiyle aynı olmalı; `get_data_type_str(data)` bunu numpy dizisinden çıkarır (complex64 → `cf32_le`, complex128 → `cf64_le`). `core:sample_rate` Hz cinsinden.
- **captures**: `add_capture(baslangic_ornegi, ...)` ile; merkez frekans (`core:frequency`) ve zaman (`core:datetime`, ISO 8601, UTC). Frekans veya ayar kayıt ortasında değişirse yeni bir capture eklenir.
- **annotations**: isteğe bağlı; `add_annotation(baslangic, uzunluk, ...)` ile bir örnek aralığına frekans sınırları ve yorum eklenir.

`tofile()` yazmadan önce meta veriyi şemaya göre doğrular ve `core:sha512` (veri dosyasının özeti), `core:num_channels`, `core:version` alanlarını kendisi ekler. Tek dosyalık arşiv için `meta.tofile("kayit.sigmf")` kullanılabilir.

Kod: `kod.py` (sonunda dosyayı geri okuyup doğrulayan bölüm var).

## Doğrulama
- Beklenen: `.sigmf-meta` şemaya uygun yazılır; `sigmf.fromfile("kayit")` ile geri okunur; `cf32_le`, 2.000.000 Hz, 1.024 complex64 örnek, 1 capture, 1 annotation; okunan örnekler yazılanla aynı.
- Gözlenen (`cikti.txt`): hepsi beklenen gibi; `core:version` 1.2.6, `kayit.sigmf-data` 8.192 bayt (1.024 × 8 bayt), `kayit.sigmf-meta` 886 bayt, "örnekler yazılanla aynı: True".

## Bilinen tuzaklar
- **Meta yazıldıktan sonra veri dosyası değişirse okuma hata verir.** `tofile()` veri dosyasının SHA-512 özetini meta veriye yazar; dosya sonradan değişirse `sigmf.fromfile()` `SigMFFileError: Calculated file hash does not match associated metadata.` verir (denendi). Önce veriyi tamamen yazın, sonra meta veriyi.
- **`core:datatype` elle yazılırsa tiple uyuşmayabilir.** complex128 dizi `cf32_le` diye işaretlendiğinde hata çıkmaz ama 1.024 örnek 2.048 örnek olarak (yanlış) okunur (denendi). `get_data_type_str(data)` kullanın veya diziyi önce `astype(np.complex64)` ile dönüştürün.
- Bu örnek donanımsızdır; gerçek kayıtta `core:frequency` ve örnek hızı alıcıdan okunan gerçek değerlerle doldurulmalıdır.
