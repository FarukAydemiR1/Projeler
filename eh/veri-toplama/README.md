# EH laboratuvarı – model eğitim verisi toplama

Amaç: Yerel yapay zekâ modeline **hangi programı kullanacağını, nasıl kuracağını ve nasıl kod yazacağını** öğretecek verileri toplamak. Toplanan veri önce yerel bilgi bankasına (RAG, Open WebUI) yüklenir; yeterli laboratuvar örneği biriktiğinde ince ayar (fine-tuning) veri setine dönüştürülür.

## Dosyalar

| Dosya | Ne işe yarar |
|---|---|
| `surumler.toml` | Laboratuvarın **sabit yazılım sürüm seti**. Model yalnızca bu sürümlerin belgesini ve kodunu öğrenir. |
| `kaynaklar.toml` | İndirilecek 51 açık kaynak depo: hangi sürüm etiketi, hangi klasörler, lisans ve kategori. |
| `elle-indirilecekler.md` | Git ile indirilemeyen PDF ve web belgeleri: ölçüm cihazlarının SCPI kılavuzları, RAG ve Türkçe terim kaynakları. |
| `topla.py` | Toplama betiği. Depoları indirir, belge/örnek/test/not defteri dosyalarını seçer, her dosyayı sürüm etiketli bir JSONL kaydına çevirir. |
| `laboratuvar-yapilacaklar.md` | Yalnızca laboratuvarda üretilebilecek veriler: kalibrasyon, kablo kayıp tabloları, PDW ve darbe ayrıştırma örnekleri, terim listesi. |
| `eksikler-promptu.md` | Kalan internet kaynaklı eksikler ve bunları bulmak için araştırma promptu. |
| `ince-ayar-notlari.md` | Ekran kartı gelince kullanılacak ince ayar araçları, başlangıç ayarları ve adımlar. |
| `lab-ornek-sablonu.md` | Laboratuvarda çalıştırıp doğruladığınız örneklerin yazılacağı şablon. **En değerli veri bunlar.** |

## Neden sürüm sabitleme?

SDR yazılımlarında API sürümden sürüme değişir (ör. GNU Radio 3.8 → 3.10, libiio 0.x → 1.0). Model iki sürümün belgesini karışık öğrenirse **çalışmayan kod yazar**. Bu yüzden önce `surumler.toml` kesinleşir, sonra yalnızca o sürümlerin kaynakları toplanır. Sürüm seti değişirse `[kimlik] etiket` değeri de değiştirilir ve toplama yeniden çalıştırılır.

`surumler.toml` içinde `dogrula` notu olan satırlar (libiio, SoapySDR, RFSoC-PYNQ) laboratuvarda gerçek donanımla denendikten sonra kesinleşir.

## Sunucuda çalıştırma

Gereken: `git`, Python 3.11 veya üzeri, internet bağlantısı, yaklaşık 2 GB boş alan.

```bash
cd ~/Projeler/eh/veri-toplama        # ya da dosyaları kopyaladığınız klasör
python3 topla.py --hedef /depo/egitim-verisi --liste      # önce listeye bakın
nohup python3 topla.py --hedef /depo/egitim-verisi > /depo/egitim-verisi-toplama.log 2>&1 &
tail -f /depo/egitim-verisi-toplama.log                     # ilerlemeyi izleyin (Ctrl+C ile çıkın)
```

Tek bir kaynağı yenilemek için:

```bash
python3 topla.py --hedef /depo/egitim-verisi --sadece torchsig --yeniden
```

Bu ortamda yapılan denemede 29 kaynağın hepsi hatasız indi: **3.484 kayıt, yaklaşık 30 MB metin**; ham indirmeler 1,4 GB tuttu.

## Çıktı

```
/depo/egitim-verisi/
  ham/<kaynak>/            # indirilen depolar (sürüm etiketinde, depth=1)
  kayitlar/<kaynak>.jsonl  # her satır bir dosya: içerik + meta veri
  ozet.json                # kaynak başına dosya sayısı, commit, hatalar
  LISANSLAR.md             # kaynak başına lisans tablosu
```

Her JSONL kaydı:

```json
{"id": "...", "kaynak": "pyadi-iio", "ref": "v0.0.21", "commit": "b43c5cb...",
 "yol": "examples/pluto.py", "kaynak_link": "https://github.com/.../blob/<commit>/examples/pluto.py",
 "tur": "kod", "dil": "python", "kategori": "sdr", "lisans": "...",
 "surum_seti": "eh-lab-2026-11", "toplama_tarihi": "2026-11-17", "icerik": "..."}
```

`tur` değerleri: `kod`, `defter` (Jupyter; çıktılar atılır, markdown ve kod hücreleri kalır), `akis_semasi` (GNU Radio `.grc`), `belge`, `yapilandirma`.

## Sonraki adımlar

1. **Sürüm setini kesinleştirin.** `dogrula` notlu satırları PlutoSDR ve B210 ile deneyin.
2. **Toplamayı sunucuda çalıştırın** ve `LISANSLAR.md` dosyasını hukuk birimine gösterin. NC (ticari olmayan) ve GPL lisanslı içerikle ince ayar yapmadan önce onay alın. Yalnızca kurum içi RAG kullanımı genelde daha az sorunludur, ama yine de sorun.
3. **RAG'e yükleme.** Open WebUI kurulunca `kayitlar/` içeriği kategori bazlı koleksiyonlara aktarılacak (SDR, DSP, yapay zekâ, radar, yön bulma, ölçüm, EM, FPGA). Kod dosyaları bölünmeden, bütün olarak yüklenmeli. Aktarım betiği o aşamada yazılacak.
4. **Laboratuvar örnekleri.** Kodlama görev kataloğundaki işleri sırayla deneyip `lab-ornek-sablonu.md`'ye göre kaydedin. Hedef: görev başına en az 5 doğrulanmış örnek.
5. **Kaynak listesini genişletme.** Kodlama prompt'unun sonucu gelince eksik görevler için yeni depolar `kaynaklar.toml`'a eklenecek.

## Güvenlik

- Bu betik yalnızca kamuya açık depoları indirir; hiçbir veriyi dışarı göndermez.
- Laboratuvarın kendi kodu ve notları `lab-ornekleri/` altında, ağdan ayrılmış sistemde tutulmalı. Gizlilik dereceli bilgi bu klasöre konmaz.
- Verici içeren örnekler yalnızca kablolu düzenekle (zayıflatıcı, dummy load, ekranlı kutu) yapılır. 5809 sayılı Kanun gereği izinsiz yayın yapılmaz.
