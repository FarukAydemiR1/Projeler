# Elle indirilecek belgeler (PDF ve web)

`topla.py` yalnızca git depolarını indirir. Aşağıdaki belgeler PDF veya web sayfası olduğu için elle indirilip `/depo/egitim-verisi/belgeler/<kategori>/` altına konmalı ve RAG'e ayrıca yüklenmeli. Linkler 17.11.2026'da kontrol edildi.

## Laboratuvar ölçüm cihazları (SCPI programlama kılavuzları)

| Cihaz | Belge | Link | Durum |
|---|---|---|---|
| Rigol DSA815-TG | DSA800 Series Programming Guide (EN, Ağu 2016) | https://people.ece.ubc.ca/~eng-services/files/manuals/Man_dsa800programerGuide.pdf | Çalışıyor (üniversite aynası; Rigol sitesinde yalnız Çince sürüm bulundu) |
| Siglent SSG3021X | SSG3000X Programming Guide PG0803X-E01B | https://www.int.siglent.com/u_file/document/SSG3000X_Programming%20Guide-PG0803X-E01B.pdf | Çalışıyor (resmi) |
| Mini-Circuits PWR-6GHS | Power Meter yazılım ve programlama sayfası (Linux: USB HID komutları; Python örnekleri) | https://www.minicircuits.com/softwaredownload/pm.html | Çalışıyor (resmi) |
| Mini-Circuits PWR-6GHS | Veri sayfası | https://www.minicircuits.com/pdfs/PWR-6GHS.pdf | Çalışıyor |
| R&S ZNL3 | ZNL/ZNLE kullanım kılavuzu (uzaktan kontrol komutları dahil) | https://www.rohde-schwarz.com/manual/znl | Çalışıyor (resmi). Cihazın firmware sürümüne uygun kılavuzu seçin |

Python örnekleri depo olarak toplanıyor: `Rohde-Schwarz-Examples` (ZNL için `RsInstrument_ZNL_S21_Magnitude_write_to_csv.py` dahil), `pyminicircuits` (PWR-6GHS'yi destekliyor; resmi değil), `pyvisa`, `pyvisa-sim`.

## SDR ve sinyal işleme

| Belge | Link |
|---|---|
| pyadi-iio: libiio doğrudan erişim (v0.x önerisi) | https://developer.analog.com/docs/pyadi-iio/libiio.html |
| pyadi-iio CN0566 (ADALM-PHASER) API | https://analogdevicesinc.github.io/pyadi-iio/devices/adi.cn0566.html |
| ADALM-PHASER platform rehberi | https://analogdevicesinc.github.io/system-level/solutions/platforms/phaser/ |
| PySDR "Hands-on with Phaser" bölümü (CC BY-NC-SA) | https://pysdr.org/content/phaser.html |
| libbladeRF API belgesi | https://www.nuand.com/bladeRF-doc/libbladeRF/ |
| GNU Radio 4.0.0-RC3 duyurusu (3.10 ile karıştırmamak için) | https://www.gnuradio.org/news/2026-10-13-gr4-rc3-release/ |
| TorchSig GRCon 2026 çalıştay sunumu | https://events.gnuradio.org/event/28/contributions/880/attachments/275/713/2026_grcon_torchsig_workshop.pdf |
| SigMF Python hızlı başlangıç | https://sigmf.readthedocs.io/en/latest/quickstart.html |
| RsInstrument adım adım rehber (çevrimdışı kurulum dahil) | https://rsinstrument.readthedocs.io/en/latest/StepByStepGuide.html |
| PyVISA belgeleri | https://pyvisa.readthedocs.io/ |
| RFSoC 4x2 base overlay | http://www.rfsoc-pynq.io/rfsoc_4x2_base_overlay.html |
| PYNQ.remote ile RFSoC | https://discuss.pynq.io/t/tutorial-using-rfsoc-with-pynq-remote/9128 |
| MEEP kurulum (conda) | https://meep.readthedocs.io/en/latest/Installation/ |
| openEMS Python eklentileri kurulumu | https://docs.openems.de/en/stable/install/manual_install.html |
| Radioconda (HamSCI 2026 sunumu) | https://hamsci.org/sites/default/files/article/Workshop_2026/2026_HamSCI_Radioconda.pdf |

## RAG ve değerlendirme

| Belge | Link | Not |
|---|---|---|
| Open WebUI RAG belgesi | https://docs.openwebui.com/features/chat-conversations/rag/ | Embedding modeli değişince Reindex gerekir |
| BAAI/bge-m3 (çok dilli embedding) | https://huggingface.co/BAAI/bge-m3 | Türkçe+İngilizce için ilk aday |
| BAAI/bge-reranker-v2-m3 | https://huggingface.co/BAAI/bge-reranker-v2-m3 | |
| intfloat/multilingual-e5-large | https://huggingface.co/intfloat/multilingual-e5-large | Sorgu/pasaj öneki gerekir |
| DS-1000 (kütüphane odaklı kod değerlendirme) | https://huggingface.co/datasets/xlangai/DS-1000 | CC-BY-SA-4.0; test seti tasarımı için örnek |
| Hugging Face RAG değerlendirme rehberi | https://huggingface.co/learn/cookbook/rag_evaluation | |

## Türkçe terim kaynakları

| Belge | Link | Durum |
|---|---|---|
| Dışişleri Bakanlığı Askeri Terminoloji (TR-EN) | https://www.mfa.gov.tr/data/Terminoloji/askeri-terminoloji-(turkce-ingilizce).pdf | Çalışıyor |
| İletişim Başkanlığı Kamu Kurumları Sözlüğü | https://www.iletisim.gov.tr/images/uploads/dosyalar/Kamu_Kurumlar%C4%B1_So%CC%88zlu%CC%88g%CC%86u%CC%88.pdf | Çalışıyor |
| SSB Savunma Sanayii 360 Terimler Sözlüğü | https://ssb.gov.tr/savunmasanayii360/terimler-sozlugu | Buradan açılmadı (yurt dışı erişim); kurumdan kontrol edin |
| MSÜ Güvenlik Stratejileri Dergisi Sayı 52, EH makalesi | https://gsd.msu.edu.tr/Content/sayilar/dokuman/GSD_52/GSD_52_Art_4_122025.pdf | Buradan açılmadı; kurumdan kontrol edin |

Kendi Türkçe-İngilizce EH/RF/DSP terim listenizi `lab-ornekleri/` yanında bir `terimler.md` dosyasında tutmanız önerilir. Hazır kaynakların hiçbiri DSP terimlerini tam kapsamıyor.

## Bilerek eklenmeyenler

| Depo | Neden |
|---|---|
| osqzss/gps-sdr-sim | Arşivlenmiş, CVE-2021-37778 açığı var |
| IQTLabs/rfml | Arşivlenmiş |
| MohamoudAli12/simpleEMS | AGPL-3.0 lisans ve çok küçük proje (6 yıldız); hukuk onayı olmadan alınmadı |
| matthuszagh/pyems | README'sinde tamamlanmamış olduğu yazıyor; 2024'ten beri güncellenmiyor |
| myriadrf/LimeSuiteNG | Laboratuvarda LimeSDR yok |
| krakenrf/krakensdr_docs | Lisans belirtilmemiş; wiki elle okunabilir |
