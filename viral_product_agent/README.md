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
```

Çıktı: `output/YYYY-MM-DD_report.md` (insan için, Türkçe) + `.json` (makine için).

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
