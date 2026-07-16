"""Tum Claude prompt sablonlari tek yerde: trait-mining, puanlama, reklam uretimi."""
from __future__ import annotations

TRAIT_MINING = """\
Asagida son yillarda viral olmus urun ornekleri ve notlari var. Gorevin:
1) Bu urunlerin ORTAK ozelliklerini cikar (insanlar neden aliyor, hangi sorunu/duyguyu
   cozuyor, reklamda nasil gosteriliyor, fiyat bandi, boyut, "vay be" ani).
2) Bu ozelliklerden Turkiye pazarina uyarlanmis bir puanlama cetveli (rubric) oner:
   boyut adi, tanimi, 0-10 puanlama rehberi.
Sadece JSON don:
{{"traits": ["..."], "dimensions": [{{"name": "...", "definition": "...", "guide": "..."}}]}}

VERI:
{seed_data}
"""

SCORE_CANDIDATE = """\
Sen Turkiye e-ticaret pazari icin urun viralitesi degerlendiren skeptik bir analistsin.
Jenerik, doymus veya sikici urunleri acimasizca dusuk puanla.

URUN:
Baslik: {title}
Aciklama: {description}
Kaynak: {source} ({url})
Tahmini fiyat (USD): {price}

Su boyutlarda 0-10 puan ver ve her biri icin TEK cumle gerekce yaz:
- problem_or_emotion: gercek bir derdi cozuyor VEYA guclu duygusal/eglence/statü ihtiyacina hizmet ediyor mu?
- demonstrability: 5-15 saniyelik dikey videoda calisirken gosterilince "vay be" dedirtir mi?
- cultural_fit_tr: Turk zevkine, hediyelesme kulturune, mizahina uyar mi? Dini/kulturel hassasiyet riski var mi?
- seasonality: onumuzdeki TR takvimiyle (Ramazan/Bayram, okul acilisi, yaz, yilbasi) uyumu?
- shareability: "arkadasini etiketle" / hediye / meme potansiyeli?
- sourcing_feasibility: AliExpress/1688'den kolay tedarik edilir mi; IP/lisans/regulasyon engeli var mi?

Sadece JSON don:
{{"scores": {{"problem_or_emotion": 0, "demonstrability": 0, "cultural_fit_tr": 0,
"seasonality": 0, "shareability": 0, "sourcing_feasibility": 0}},
"rationale": {{"problem_or_emotion": "...", "demonstrability": "...", "cultural_fit_tr": "...",
"seasonality": "...", "shareability": "...", "sourcing_feasibility": "..."}}}}
"""

AD_CONCEPT = """\
Turkiye pazari icin kisa-video reklam konsepti uret. Urun:
Baslik: {title}
Aciklama: {description}
Neden secildi: {rationale}

Uret (Turkce):
1) hook: ilk 2 saniyede kaydirmayi durduran tek cumlelik kanca
2) video_script: 15 saniyelik dikey video senaryosu — sahne sahne (0-2sn, 2-7sn, 7-12sn, 12-15sn),
   her sahnede gorsel + ekran yazisi
3) platform: TikTok / Instagram Reels / Meta — hangisi ve neden (tek cumle)
4) audience: TR hedef kitle tanimi (yas, ilgi alanlari, davranis)

Sadece JSON don:
{{"hook": "...", "video_script": "...", "platform": "...", "audience": "..."}}
"""

AVAILABILITY_JUDGE = """\
Asagida "{title}" urunu icin Turkiye pazar yerlerinde yapilan arama sonucu ozetleri var.
Bu urun Turkiye'de ZATEN yaygin olarak satiliyor mu?
0.0 = hic yok/cok yeni, 1.0 = her yerde var. Sadece JSON don:
{{"availability": 0.0, "reason": "..."}}

SONUCLAR:
{snippets}
"""
