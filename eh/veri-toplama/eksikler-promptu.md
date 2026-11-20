# Kalan eksikler ve araştırma promptu (17.11.2026)

## İnternetten bulunabilecek eksikler

| # | Eksik | Neden önemli |
|---|---|---|
| 1 | GNU Radio 3.10 wiki eğitimleri (Embedded Python Block, OOT, grcc, PFB) | Wiki git deposu değil; görev 6, 7, 8 |
| 2 | Darbe tespiti ve PDW çıkarımı açık kodu | Görev 9; hiç örnek yok |
| 3 | TEXBAT ve FGI-GSRx veri setleri, aldatma tespiti kodu | Görev 14 |
| 4 | RadChar veri seti indirme linki | Görev 10, 11 test seti |
| 5 | radarsimpy kurulumu ve FMCW/CFAR örnekleri | Görev 15; PyPI'da yok |
| 6 | Geçiş rehberleri (GR 3.8→3.10, libiio 0.x→1.0, PyVISA, bladeRF v1→v2, UHD 3→4, TorchSig) | Yanlış sürümde kod üretmeyi önler |
| 7 | Çevrimdışı kurulum belgeleri | Ağdan ayrılınca şart |
| 8 | llama.cpp embedding + Open WebUI bağlantısı | RAG tamamen yerelde |
| 9 | İnce ayar araçları (Unsloth, Axolotl, LLaMA-Factory), A4000 QLoRA, GGUF | İkinci aşama |
| 10 | Kod üretimi değerlendirme düzeni (pytest, mock SDR, PyVISA-sim) | İlerlemeyi ölçmek |
| 11 | Türkçe DSP ve RF terim sözlükleri | Askeri sözlükler bulundu, DSP eksik |
| 12 | Embedding/reranker model lisansları | Raporda doğrulanamadı |

Laboratuvarda üretilecekler için: `laboratuvar-yapilacaklar.md`.

## Durum (20.11.2026, Claude Research sonucu + kendi doğrulamamız)

| # | Durum | Ne yapıldı |
|---|---|---|
| 1 | Kapandı (elle) | Sayfalar `elle-indirilecekler.md`'de. Wiki Cloudflare arkasında, tarayıcıdan PDF alınacak. Eski sayfalar işaretlendi |
| 2 | Kısmen | `gr-pdw` (GPL-3.0, **GNU Radio 3.8 OOT**; 3.10'a taşınmalı) ve `pulse-pdw-simulator` (Apache-2.0) toplamaya eklendi. Ders materyali niteliğinde CFAR + PDW kodu hâlâ yok. Laboratuvar görevi 9 önemini koruyor |
| 3 | Kapandı (elle) | TEXBAT ve FGI-SpoofRepo linkleri, formatları, lisansları doğrulandı. Yeniden dağıtım yasak; RAG'e veri değil talimat konacak. Resmi GNSS-SDR yapılandırması yok, laboratuvarda yazılacak |
| 4 | Kapandı | RadChar: Kaggle, CC BY-NC-SA 4.0, HDF5 |
| 5 | Kapandı | radarsimpy 15.5.0 (pip yok, free tier sınırlı); örnek defterler `radarsimnb` olarak toplamaya eklendi |
| 6 | Büyük ölçüde | libiio 0→1 rehberi `libiio-wiki` olarak toplanıyor. bladeRF 2.0, PyVISA, GNU Radio porting guide'lar listelendi. TorchSig 1.1→2.0 rehberinin içeriği ve UHD `multi_usrp` 3→4 kod rehberi bulunamadı |
| 7 | Açık | Yalnızca pip download linki doğrulandı (çalışıyor). Diğerleri sunucu kurulumu sırasında belgelenecek |
| 8 | Kapandı | llama-server: `--embedding`, `--pooling {none,mean,cls,last,rank}`, `--rerank`; uç noktalar `/v1/embeddings`, `/v1/rerank`. GGUF: `ggml-org/bge-m3-Q8_0-GGUF`, `gpustack/bge-reranker-v2-m3-GGUF`, `Qwen/Qwen3-Embedding-0.6B-GGUF` |
| 9 | Kısmen | Sürümler (PyPI): Unsloth 2026.11.7 (Apache-2.0), LLaMA-Factory 0.9.5 (Apache-2.0), Axolotl 0.21.1. QLoRA yapılandırması ekran kartı gelince yazılacak |
| 10 | Açık | gr-pdw'nin `virtual_pdw.grc` ve `qa_*.py` dosyaları donanımsız test için örnek. Test seti bizim tarafımızdan yazılacak |
| 11 | Açık | Türkçe DSP/RF terim sözlüğü bulunamadı. Ekip kendi `terimler.md` listesini tutacak |
| 12 | Kapandı | HF model kartları: bge-m3 MIT, bge-reranker-v2-m3 Apache-2.0, multilingual-e5-large/base MIT, nomic-embed-text-v2-moe Apache-2.0, Qwen3-Embedding-0.6B ve Qwen3-Reranker-0.6B Apache-2.0 |

**Ek bulgular**
- **libiio v1.0.0 21.09.2026'da çıktı.** README'ye göre v0.x programları v1.0 üzerinde uyumluluk katmanıyla çalışır. Ubuntu 26.04 ve pyadi-iio hâlâ 0.26'da; sabit sette 0.26 kalıyor.
- **Open WebUI 0.13.4'ün lisansı "Open WebUI License"** (özel lisans, marka koruma şartları var). Kurumsal kullanım öncesi hukuk birimine gösterilmeli.
- `topla.py` düzeltildi: Jupyter defterleri artık çıktıları atıldıktan sonra boyut sınırına tabi. Önceden büyük defterler (radarsimnb'de 36 defterin 14'ü) atlanıyordu.

## Prompt

```
Bir Ar-Ge laboratuvarı için yerel bir yapay zekâ modeline SDR, RF ölçüm ve sinyal işleme kodlamasını öğretecek kaynakları topluyorum. Ana yazılım yığını ve sürümleri sabit; bunlar için ayrıca araştırma YAPMA:
GNU Radio 3.10.12.0 · UHD 4.11.0.0 · libiio 0.26 · pyadi-iio 0.0.21 · SoapySDR 0.8.1 · gr-osmosdr 0.2.6 · bladeRF 2024.05 · HackRF 2026.01.3 · GNSS-SDR 0.0.22 · NumPy 2.5.5 · SciPy 1.18.1 · PyTorch 2.15.0 · TorchSig 2.2.0 · sigmf 1.14.0 · scikit-rf 2.2.0 · PyVISA 1.16.2 · Ubuntu 26.04 · Python 3.12.
Bilgi bankası Open WebUI + llama.cpp üzerinde çalışacak. Aşağıdaki 12 başlıkta YALNIZCA eksik olanları bul.

1) GNU RADIO 3.10 WIKI EĞİTİMLERİ: wiki.gnuradio.org üzerindeki şu sayfaların doğrudan linklerini ve hangi GNU Radio sürümüne göre yazıldıklarını ver: Guided Tutorials dizisi, Embedded Python Block, Creating Python OOT with gr-modtool, Creating C++ OOT with gr-modtool, Polyphase Filterbanks / PFB Channelizer, Python Block with Vectors, Message Passing, Tags, .grc dosyasından Python üretimi (grcc). 3.7/3.8 dönemine ait olup 3.10'da çalışmayan sayfaları ayrıca işaretle. Wikinin toplu indirme veya çevrimdışı kopyalama yöntemi varsa yaz.

2) DARBE TESPİTİ VE PDW ÇIKARIMI: Radar darbesi tespiti (eşik, CFAR), PDW (TOA, PW, RF, PA, AOA) çıkarımı ve PRI analizi yapan açık kaynak kodları bul (Python veya MATLAB; GitHub, akademik makale ekleri, ders materyalleri). Her biri için yıldız sayısı, son güncelleme tarihi, lisans ve sentetik veriyle çalışıp çalışmadığını yaz. Şu depoları zaten topluyorum, tekrar etme: turing-deinterleaving-challenge, RadSeg, RadCharSSL, emitter-detection-python, radarsimpy, RadarBook.

3) GNSS VERİ SETLERİ: TEXBAT (UT Austin) ve FGI-GSRx/FGI-SpoofRepo veri setlerinin resmi indirme sayfaları, dosya formatı, örnekleme hızı ve lisansı. GNSS-SDR ile bu kayıtları işleyen yapılandırma dosyası örnekleri. Kayıtlı veri üzerinde aldatma tespiti yapan açık kod.

4) RADCHAR VERİ SETİ: RadChar'ın (radar sinyali karakterizasyonu) resmi indirme linki, boyutu, formatı ve lisansı. Benzer kamuya açık radar darbe veri setleri.

5) RADARSIMPY: radarsimpy'nin güncel sürümü, nasıl kurulduğu (PyPI'da yok), örnek defterlerin bulunduğu depo (ör. radarsimx altındaki diğer depolar), FMCW menzil-Doppler ve CFAR örneklerinin dosya yolları, lisansı ve NumPy 2.x uyumu.

6) GEÇİŞ REHBERLERİ (eski API → yeni API): Resmi linkleriyle şunları bul: GNU Radio 3.7→3.8 ve 3.8→3.9/3.10 porting guide; libiio 0.x→1.0 migration; PyVISA'da "import visa"dan "import pyvisa"ya geçiş ve kaldırılan API'ler; bladeRF libbladeRF v1→v2 (bladerf_module→bladerf_channel); UHD 3.x→4.x değişiklikleri; TorchSig 0.x→1.x→2.x API değişiklikleri. Her biri için "eski kod → yeni kod" örneği içerip içermediğini belirt.

7) ÇEVRİMDIŞI KURULUM: Resmi belge linkleriyle şunları anlat: pip download + pip install --no-index --find-links; apt-offline veya yerel apt aynası (apt-mirror, aptly); conda-pack ve radioconda çevrimdışı yükleyici; uhd_images_downloader ile FPGA imajlarını önceden indirme; Hugging Face modellerini ve veri setlerini yerel kopyalama (huggingface-cli download, HF_HUB_OFFLINE); Sphinx belgelerini yerelde derleme.

8) LLAMA.CPP İLE YEREL EMBEDDING: llama.cpp'nin llama-server --embedding modu (veya --embeddings), pooling ayarları ve OpenAI uyumlu /v1/embeddings uç noktası için resmi belgeler. bge-m3 ve multilingual-e5 modellerinin GGUF sürümleri (Hugging Face linkleri). Open WebUI'de embedding motoru olarak OpenAI uyumlu yerel sunucu ve reranker bağlama adımları.

9) İNCE AYAR ARAÇLARI: Unsloth, Axolotl ve LLaMA-Factory'nin güncel sürümleri, lisansları, 16 GB VRAM'li tek GPU'da (NVIDIA RTX A4000) 7–8B model için QLoRA örnek yapılandırmaları, sohbet ("messages") biçimindeki JSONL veri formatı ve eğitilen modeli llama.cpp için GGUF'a çevirme adımları (convert_hf_to_gguf.py, LoRA birleştirme). Kod odaklı ince ayar için önerilen veri miktarı ve aşırı öğrenmeyi önleme yöntemleri.

10) KOD ÜRETİMİ DEĞERLENDİRME DÜZENİ: Kütüphaneye özgü kod üretimini otomatik test eden açık projeler (DS-1000, BigCodeBench, ClassEval vb.) ve yöntemleri. Donanım olmadan SDR kodu test etmek için mock/sahte cihaz yaklaşımları (ör. pyadi-iio veya UHD için sahte sınıf, GNU Radio'da file source ile test, PyVISA-sim YAML cihaz tanımı örnekleri). pytest ile "kod çalıştı mı ve doğru sonuç verdi mi" kontrolü yapan örnek altyapılar.

11) TÜRKÇE DSP VE RF TERİMLERİ: Sayısal sinyal işleme, RF, anten ve radar için Türkçe-İngilizce terim sözlükleri: TSE terim standartları, TDK Bilim ve Sanat Terimleri, üniversite (ODTÜ, İTÜ, Bilkent, Hacettepe) ders sözlükleri, EMO yayınları, TÜBİTAK terim çalışmaları. Linki ve lisansıyla.

12) MODEL LİSANSLARI: Şu modellerin Hugging Face model kartındaki lisanslarını doğrula: BAAI/bge-m3, BAAI/bge-reranker-v2-m3, intfloat/multilingual-e5-large, intfloat/multilingual-e5-base, nomic-ai/nomic-embed-text-v2-moe, Qwen3-Embedding-0.6B, Qwen3-Reranker-0.6B. Her biri için CPU'da kullanılabilirlik notu ver.

ÇIKTI:
- En başa 10 maddelik özet.
- Her başlık için tablo: Kaynak | Tür | Sürüm | Link (doğrudan sayfa) | Lisans | Son güncelleme | Not.
- Sonda "Hâlâ bulunamayanlar" listesi.
- Rapor Türkçe olsun.

KURALLAR: Kaynak uydurma. Her link, belgenin kendisine gitsin (ana sayfa değil). Doğrulayamadığın her şeye "DOĞRULANAMADI" yaz. Her satıra lisans ekle. Karıştırıcı yapımına yönelik içerik verme. Verici içeren örneklerde yalnızca kablolu, zayıflatıcılı veya dummy load'lu düzenekleri kabul et. Arşivlenmiş ya da 3 yıldan uzun süredir güncellenmeyen depoları "ESKİ" diye işaretle.
```
