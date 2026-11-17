# Laboratuvar örneği şablonu

Modelin en değerli verisi, **sizin donanımınızda çalıştırıp sonucunu gördüğünüz** örneklerdir. İnternetteki kod genel durumu anlatır; bu örnekler ise sizin kurulumunuzda neyin gerçekten çalıştığını öğretir.

Her örnek için `lab-ornekleri/` altında bir klasör açın ve aşağıdaki dosyaları koyun:

```
lab-ornekleri/
  pluto-iq-kayit-sigmf/
    ornek.md      # bu şablonun doldurulmuş hali
    kod.py        # çalıştırılan kodun kendisi
    cikti.txt     # kodun gerçek çıktısı (terminal)
    ekran.png     # varsa grafik
```

## ornek.md içeriği

```markdown
---
baslik: PlutoSDR ile 2,4 GHz'te 1 saniye I/Q kaydı ve SigMF olarak saklama
gorev_no: 1, 4          # kodlama görev kataloğundaki numaralar
donanim: ADALM-PLUTO (firmware v0.39), USB 2.0
yazilim: pyadi-iio 0.0.21, libiio 0.26, sigmf 1.14.0, numpy 2.5.5
surum_seti: eh-lab-2026-11
test_duzenegi: kablolu; sinyal üreteci -> 40 dB zayıflatıcı -> Pluto RX
dogrulayan: (ad soyad)
tarih: 2026-11-20
durum: dogrulandi       # dogrulandi | kismen | basarisiz
---

## Soru
(Bir mühendisin modele soracağı şekilde, doğal dille yazın.)
PlutoSDR ile 2,4 GHz'te 2 MS/s hızla 1 saniye I/Q kaydı almak ve bunu meta verisiyle birlikte SigMF olarak kaydetmek istiyorum. Nasıl yaparım?

## Cevap
(Kısa açıklama + kod.py'nin içeriği. Neden bu parametrelerin seçildiğini anlatın.)

## Doğrulama
- Beklenen: 2.000.000 karmaşık örnek, merkez frekansta tepe
- Gözlenen: (cikti.txt'den özet)

## Bilinen tuzaklar
- (ör. rx_buffer_size örnek sayısından küçükse kayıt eksik kalır)
- (ör. libiio 1.0 ile bu kod çalışmaz; 0.26 gerekli)
```

## Kurallar

1. **Yalnızca çalıştırdığınız kodu koyun.** Çıktısını görmediğiniz kod eksik bir örnek bile değildir; modele yanlış bilgi öğretir.
2. **Başarısız denemeleri de saklayın** (`durum: basarisiz`). "Bu yöntem bu sürümde çalışmıyor, şu hatayı veriyor" bilgisi en az başarılı örnek kadar değerlidir.
3. **Verici içeren her deney kablolu olmalı:** zayıflatıcı, dummy load veya ekranlı kutu. Düzeneği `test_duzenegi` alanına yazın.
4. **Gizli bilgi koymayın:** proje adı, platform, gerçek tehdit parametresi, sınıflandırılmış frekans planı. Örnekler genel laboratuvar becerisini öğretmeli.
5. **Sürüm setini yazın.** Kod hangi `surum_seti` etiketiyle denendiyse onu yazın; sürüm değişince örnek yeniden doğrulanmalı.

## İnce ayar veri setine dönüşüm

Yeterli sayıda örnek biriktiğinde (hedef: görev başına en az 5, toplam 100+), her `ornek.md` şu biçimde bir satıra dönüştürülür:

```json
{"messages": [
  {"role": "user", "content": "<Soru bölümü>"},
  {"role": "assistant", "content": "<Cevap bölümü + kod>"}
 ],
 "meta": {"surum_seti": "eh-lab-2026-11", "donanim": "ADALM-PLUTO", "durum": "dogrulandi"}}
```

Yalnızca `durum: dogrulandi` olanlar ince ayara girer. Bu dönüşüm için betik, ilk örnekler hazır olduğunda yazılacak.
