# Laboratuvarda üretilecek veriler

Bu veriler internette yok; yalnızca sizin donanımınızda ve düzeneğinizde üretilebilir. Model için en değerli veri bunlardır. Her biri `lab-ornek-sablonu.md`'deki şablona göre `lab-ornekleri/` altına kaydedilir.

Durum: 17.11.2026 itibarıyla hiçbiri başlamadı.

## 1. Kalibrasyon dosyaları

| İş | Cihaz | Çıktı | Not |
|---|---|---|---|
| CN0566 kazanç, faz ve kanal kalibrasyonu | ADALM-PHASER (EVAL-CN0566) + Pluto | `gain_cal_val.pkl`, `phase_cal_val.pkl`, `channel_cal_val.pkl` ve kalibrasyon adımlarının anlatımı | pyadi-iio 0.0.21, `examples/phaser/` betikleriyle. Her kart için ayrı dosya üretilir |
| B210 iki kanal arası faz ve zaman kayması | USRP B210 | Ölçüm betiği, kayma değerleri, telafi kodu | Aynı sinyal bölücü (splitter) ile iki kanala kablolu verin |
| B210 ilk frekans ayarındaki DC offset sorunu | USRP B210 | Sorunun nasıl göründüğü, telafi yöntemi | UHD #892 ile ilgili; UHD 4.11.0.0 ile deneyin |
| KrakenSDR faz uyumu | KrakenSDR | heimdall_daq_fw kalibrasyon kaydı, sonuçlar | Ayrı conda ortamı (Python 3.9.7) |

## 2. Kablo ve zayıflatıcı kayıp tabloları

| İş | Cihaz | Çıktı |
|---|---|---|
| Her koaksiyel kablonun frekansa göre kaybı | R&S ZNL3 (S21) veya Siglent SSG3021X + Mini-Circuits PWR-6GHS | Touchstone (`.s2p`) dosyası + CSV kayıp tablosu |
| Sabit zayıflatıcıların gerçek değerleri | Aynı düzenek | Nominal ve ölçülen dB değerleri |
| Ölçüm betiği | Python (RsInstrument / PyVISA / pyminicircuits) | Kodlama görevi 22'nin doğrulanmış örneği |

Kablolara ve zayıflatıcılara etiket (K01, Z01...) verin; tablolarda bu adları kullanın.

## 3. Açık kaynakta karşılığı olmayan görevler

| Görev | Ne yapılacak | Düzenek |
|---|---|---|
| 9. Darbe tespiti ve PDW çıkarımı | Sentetik darbe dizisiyle başlayın, sonra sinyal üretecinden darbe modülasyonlu sinyal alın; TOA, PW, RF, PA hatalarını ölçün | Siglent SSG3021X (darbe modu) → zayıflatıcı → Pluto/B210 RX, kablolu |
| 10. Darbe ayrıştırma (deinterleaving) | Birden fazla PRI'li sentetik dizi; CDIF/SDIF/PRI dönüşümü | Önce yalnızca sentetik veri |
| 22. Güç sensörüyle ölçüm ve kayıp karakterizasyonu | Yukarıdaki 2. bölüm | Kablolu |

Hedef: görev başına en az 5 doğrulanmış örnek. Başarısız denemeleri de `durum: basarisiz` ile kaydedin.

## 4. Türkçe terim listesi

`lab-ornekleri/terimler.md` dosyasında Türkçe ile İngilizce karşılıkları tutun. Ekibin gerçekte kullandığı terimleri yazın; resmi sözlükler DSP ve RF terimlerini tam kapsamıyor.

```
| Türkçe | İngilizce | Kısaltma | Not |
|---|---|---|---|
| darbe tanımlama kelimesi | pulse descriptor word | PDW | |
| darbe tekrarlama aralığı | pulse repetition interval | PRI | |
| varış zamanı | time of arrival | TOA | |
```

## Kurallar (hatırlatma)

- Verici içeren her deney kablolu olmalı: zayıflatıcı, dummy load veya ekranlı kutu. 5809 sayılı Kanun gereği izinsiz yayın yapılmaz.
- Proje adı, platform, gerçek tehdit parametresi veya gizlilik dereceli bilgi konmaz.
- Örnekler ağdan ayrılmış sistemde tutulur.
