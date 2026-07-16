# Viral Ürün Keşif Ajanı (Türkiye)

Türkiye pazarına **henüz gelmemiş**, viral olma potansiyeli yüksek ürünleri erkenden
keşfeden, puanlayan ve en iyileri için **reklam konsepti** üreten Python ajanı.

Bu klasör kendi içinde bağımsızdır — repodaki diğer projelerle hiçbir bağı yoktur.

## Ne yapar?

```
KEŞFET (Reddit, Product Hunt, RSS, Google Trends, web araması)
  → TEKİLLEŞTİR (aynı ürün birden çok kaynakta = güçlü sinyal)
  → TÜRKİYE KAPISI (Trendyol/Hepsiburada/Amazon.tr/N11'de zaten yaygınsa ELE)
  → SİNYALLER (yenilik, momentum, fiyat uyumu, marj tahmini — deterministik)
  → LLM PUAN (problem/duygu, gösterilebilirlik, kültürel uyum, mevsimsellik, paylaşılabilirlik)
  → SIRALI RAPOR (output/YYYY-MM-DD_report.md + .json)
  → REKLAM KONSEPTLERİ (kanca + 15sn video senaryosu + platform + hedef kitle)
```

Puanlama cetveli (rubric) `data/seed_viral_products.yaml` içindeki gerçek viral ürün
örneklerinden **öğrenilir** (`--learn`) ve `data/rubric.json` olarak saklanır —
kara kutu değildir, elle düzeltilebilir.

## Kurulum

```bash
cd viral_product_agent
python3 -m venv .venv && source .venv/bin/activate   # önerilir
pip install -r requirements.txt
cp .env.example .env    # anahtarları doldur (opsiyonel, aşağıya bak)
```

## Çalıştırma

```bash
python run.py                # tam pipeline
python run.py --no-llm       # LLM'siz, deterministik taslak rapor
python run.py --learn        # önce rubric'i yeniden öğren
python run.py --inject-test  # Türkiye kapısını bilinen yaygın ürünle test et
python run.py --repeat-ok    # geçmiş filtresini kapat (eski ürünler de gelebilsin)
```

Çıktı: `output/YYYY-MM-DD_report.md` (insan için, Türkçe) + `.json` (makine için).

## Her tarama FARKLI ürün getirir

Ajan tek bir ürün etrafında dönmez — **her tarama öncekilerden farklı, yeni ürünler** verir:

- **Geçmiş hafızası** (`data/history.json`): daha önce gösterilen ürünler bir daha getirilmez.
  (Yerel/kişisel durum dosyasıdır, git'e girmez.)
- **Satılabilirlik filtresi**: "En iyi 8 mutfak aleti" gibi liste/haber başlıklarını eler,
  yalnızca satılabilir **tek somut ürünleri** tutar.
- **Çeşitlilik**: her tarama farklı arama sorgularını ve subreddit'leri karıştırır →
  her sefer farklı nişler (mutfak, evcil hayvan, güzellik, araç, kamp, bebek…) yüzeye çıkar.

Eskileri de tekrar görmek istersen: `python run.py --repeat-ok` (veya hafızayı sıfırlamak için
`data/history.json` dosyasını sil).

## Telegram Botu (@UrunuTAkibiBot)

Ajan bulduğu ürünleri ve reklam konseptlerini **Telegram'dan telefonuna** gönderebilir;
telefondan `/tara` yazarak anlık tarama başlatabilir, ürünleri buton menüsüyle gezebilirsin.

**Kurulum:**
1. [@BotFather](https://t.me/BotFather)'dan bir bot oluştur ve **token** al.
   > ⚠️ **Token'ı kimseyle paylaşma, sohbete yapıştırma.** Sızarsa @BotFather → `/revoke`
   > ile hemen iptal edip yenisini al. Token yalnızca `.env`'de durur, git'e **asla** girmez.
2. `.env` dosyasına ekle:
   ```
   TELEGRAM_BOT_TOKEN=BotFather'dan_aldığın_token
   TELEGRAM_CHAT_ID=            # aşağıda /start ile öğreneceksin
   TELEGRAM_ALLOWED_USERS=      # (opsiyonel) botu kullanabilecek ek kullanıcı id'leri
   ```
3. Botu başlat: `python bot.py`
4. Telegram'da botuna `/start` yaz → sana **sohbet id'ni** söyler → onu `.env`'deki
   `TELEGRAM_CHAT_ID`'ye yaz (otomatik gönderim ve günlük tarama bunu kullanır).

**Komutlar:**
| Komut | Ne yapar |
|---|---|
| `/tara` | Yeni tarama başlatır, en iyi ürünleri + reklam konseptlerini gönderir |
| `/liste` | Son taramanın ürünlerini buton menüsüyle gezersin (dokun → detay + reklam) |
| `/rapor` | Son raporu `.md` dosyası olarak gönderir |
| `/help` | Komut listesi + sohbet id'n |

**Otomatik günlük tarama:** `config.yaml` → `telegram.daily_scan.enabled: true` ve `hour`
ayarlanırsa bot her gün o saatte tarayıp sonucu `TELEGRAM_CHAT_ID`'ye gönderir (bot açık kalmalı).

**Tek seferlik push (bot'suz):** `python run.py --telegram` → tarama yapıp raporu Telegram'a gönderir
(cron/zamanlayıcıya uygun).

**Güvenlik:** Botu yalnızca yetkili kullanıcılar (`TELEGRAM_CHAT_ID` / `TELEGRAM_ALLOWED_USERS`)
komutlayabilir; yabancılar `/tara` ile tarama tetikleyemez.

**Not:** Bot uzun süreli bir süreçtir — kendi bilgisayarında/sunucunda çalıştır. Kaynaklar
(Reddit/arama) ev/ofis IP'sinde bulut sunuculara göre çok daha iyi çalışır.

## API anahtarı olmadan çalışır mı?

**Evet.** `ANTHROPIC_API_KEY` yoksa (veya `--no-llm` verilirse):
- Deterministik sinyallerle **taslak sıralama** üretilir.
- LLM'in dolduracağı promptlar `output/pending_llm_prompts.md` dosyasına yazılır;
  anahtar eklendiğinde (veya bir Claude Code oturumunda elle) tamamlanabilir.
- Reklam konseptleri şablon-iskelet olarak üretilir ve "ŞABLON" diye işaretlenir.

Anahtar varsa öznel viralite boyutları (gösterilebilirlik, kültürel uyum...) Claude
tarafından gerekçeli puanlanır ve reklam konseptleri gerçek üretim kalitesinde olur.

## Kaynak güvenilirlik matrisi

| Kaynak | Güvenilirlik | Not |
|---|---|---|
| Reddit (public JSON) | Yüksek | Anahtar gerektirmez; upvote = doğal ön-viralite sinyali |
| Product Hunt (GraphQL) | Yüksek | Ücretsiz `PRODUCTHUNT_TOKEN` ister; yoksa devre dışı |
| RSS (Yanko, GadgetFlow, Kickstarter) | Yüksek | Ucuz erken sinyal |
| Google Trends (pytrends) | Orta | Resmi olmayan kütüphane, ara sıra kırılır; run durmaz |
| Web araması (DuckDuckGo HTML) | Orta | Engellenirse boş döner |
| TikTok / Instagram | — (Faz 3) | Ücretsiz API yok; Apify gibi ücretli servis + bayrakla eklenecek |

**Bilinen kısıtlar (Temmuz 2026):** Reddit ve DDG/Bing, datacenter IP'lerini engeller —
ajanı kendi bilgisayarınızda (ev interneti) çalıştırın; bulut konteynerlerde bu kaynaklar
boş döner ve rapor ⚠️ düşük-güven moduna geçer. `pytrends`'in günlük trend ucu Google
tarafında 404 veriyor; kaynak durumu raporda görünür, run etkilenmez.

**Dürüst sınırlar:** Gerçek viral motor TikTok/Instagram'dır ve MVP bunları ancak
dolaylı yakalar. "Türkiye'de yok" kontrolü arama-tabanlı sezgiseldir; düşük güvenli
adaylar raporda ⚠️ ile işaretlenir — satın alma/reklam kararı öncesi **manuel doğrulayın**.
Maliyet/marj rakamları kaba tahmindir. Ajan karar-desteği verir, kâhin değildir.

## Ayarlar

Tüm ağırlıklar, kaynaklar ve eşikler `config.yaml` içindedir — kod değişmeden ayarlanır.
Önemli: `turkey_availability.novelty_gate` (varsayılan 0.35) — bu eşiğin altındaki
adaylar "Türkiye'de zaten yaygın" diye elenir.

## Yol haritası

- **Faz 2:** Playwright ile AliExpress hareketlileri/Etsy, TR pazar yeri gerçek scrape,
  embedding tabanlı dedup, run geçmişi ("bu hafta yeni").
- **Faz 3:** Apify TikTok/Instagram adaptörü (ücretli, bayrak arkasında), zamanlanmış
  çalıştırma + fark raporu.
