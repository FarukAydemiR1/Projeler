# Stock Signal Agent 📈

**Yükselmesi beklenen hisselerin yükselmeden önceki "parmak izini" geçmiş
veriden öğrenen ve aynı belirtileri gösteren güncel hisseleri yakalayıp
sinyal veren bir ajan.**

Fikir basit: Tarihte ciddi yükselen hisseler, ralliye başlamadan önce
genellikle benzer teknik izler bırakır — hacim artışı, volatilite sıkışmasının
çözülmesi, hareketli ortalama kesişimleri, direnç kırılımına yaklaşma, momentum.
Bu ajan bu izleri **hem bir makine öğrenmesi modeliyle öğrenir** hem de
**anlaşılır kural motoruyla** açıklar, sonra izleme listeni tarayıp aynı
belirtileri gösterenlere sinyal verir.

> ⚠️ **Yatırım tavsiyesi değildir.** Eğitim/araştırma amaçlı bir teknik analiz
> aracıdır. Sinyaller olasılıksaldır; kararların sorumluluğu sana aittir.

---

## Nasıl çalışır?

```
  OHLCV veri          teknik göstergeler        özellik matrisi
 (Yahoo/CSV/sentetik) → (RSI, MACD, hacim,   →  (lookahead YOK)
                         Bollinger, ATR...)         │
                                                     ├─► ML modeli (Gradient Boosting)
   geçmiş "yükseliş                                  │      → yükseliş olasılığı
    olayları" etiketi ──────────────────────────────┘
    (horizon içinde +%8)                             ├─► Kural motoru
                                                     │      → anlaşılır belirtiler + skor
                                                     ▼
                                              SİNYAL (skor + gerekçe)
```

1. **data** — BIST (`.IS`) ve ABD sembolleri için OHLCV çeker. Çekim `requests`
   ile yapılır, kurumsal proxy/CA ortamlarında da çalışır. İnternet yoksa CSV
   veya sentetik veri kullanılabilir.
2. **indicators / features** — nedensel (ileriye bakmayan) teknik göstergelerden
   ölçekten bağımsız özellikler üretir; böylece farklı fiyat seviyelerindeki
   BIST ve ABD hisseleri karşılaştırılabilir.
3. **labeling** — her günü geleceğe bakarak etiketler: `horizon` gün içinde
   `rise_threshold` (varsayılan %8) aşan yükseliş olmuş mu?
4. **model** — Gradient Boosting sınıflandırıcı bu etiketlerden öğrenir ve
   *hangi belirtilerin yükselişten önce önemli olduğunu* raporlar.
5. **rules** — RSI, hacim, kesişim, kırılım gibi insan-okuyabilir kurallara skor
   verir ve "neden sinyal verdi?"yi açıklar.
6. **screener** — model olasılığı ile kural skorunu ağırlıklı birleştirip
   nihai sinyal + gerekçe üretir.

---

## Kurulum

```bash
cd Stock_Signal_Agent
pip install -r requirements.txt
```

## Kullanım

Komutlar `stock_signal_agent.cli` modülü üzerinden çalışır. Her komut
`--market bist|us|all` hazır listelerini veya `--symbols "A,B,C"` özel listeni
kabul eder.

### 1) Modeli eğit (geçmişten "yükseliş sebeplerini" öğren)

```bash
python -m stock_signal_agent.cli train --market all --out signal_model.joblib
```

Çıktı, en önemli belirtileri (feature importance) ve doğrulama AUC'sini gösterir.

### 2) İzleme listesini tara, sinyal al

```bash
python -m stock_signal_agent.cli scan --market bist --model signal_model.joblib
```

```
SEMBOL        SKOR  MODEL  KURAL  SEVİYE       FİYAT  BELİRTİLER
THYAO.IS      0.76   0.71   0.76  GÜÇLÜ       344.50  Hacim ivmesi; Yükselen trend; MACD kesişim
AAPL          0.71   0.68   0.71  AL          315.32  Yükselen trend; Uzun vade yükseliş; MACD kesişim
```

### 3) Tek bir hisseyi gerekçeli analiz et

```bash
python -m stock_signal_agent.cli explain --symbol THYAO.IS --model signal_model.joblib
```

Tetiklenen tüm belirtileri, model olasılığını ve öne çıkan gösterge değerlerini
listeler.

### 4) Sinyalin geçmiş performansını test et (backtest)

```bash
python -m stock_signal_agent.cli backtest --symbol AAPL --threshold 0.5
```

Sinyal verilen günlerde `horizon` gün sonraki isabet oranını ve ortalama
getiriyi, taban (baseline) ile kıyaslayarak gösterir.

### 5) Günlük rutin: tara + Telegram bildirimi

```bash
python -m stock_signal_agent.cli daily --market all --train-if-missing
```

Tek komutla izleme listesini tarar, raporu oluşturur ve Telegram'a gönderir
(yapılandırılmamışsa konsola basar). `--train-if-missing` model dosyası yoksa
önce eğitir.

**Telegram kurulumu:**

1. Telegram'da **@BotFather**'a `/newbot` yaz, bot token'ını al.
2. Botunla bir konuşma başlat (herhangi bir mesaj gönder), sonra chat id'ni öğren:
   `https://api.telegram.org/bot<TOKEN>/getUpdates` → `chat.id`
3. Ortam değişkenlerini ver (token'ı asla config dosyasına yazma):

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-..."
export TELEGRAM_CHAT_ID="987654321"
python -m stock_signal_agent.cli daily --market bist
```

**Otomatik günlük çalıştırma:** Repo, her iş günü 18:17 TSİ'de taramayı çalıştırıp
Telegram'a gönderen bir GitHub Actions workflow'u içerir
(`.github/workflows/daily_scan.yml`). Aktifleştirmek için repo ayarlarından iki
secret eklemen yeterli: **Settings → Secrets and variables → Actions** →
`TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID`. İstersen **Actions** sekmesinden
"Daily Stock Signal Scan" workflow'unu elle de tetikleyebilirsin
(workflow_dispatch). Kendi makinende cron da kullanabilirsin:

```cron
17 18 * * 1-5  cd /path/to/Projeler/Stock_Signal_Agent && python -m stock_signal_agent.cli daily --market all --train-if-missing
```

### İnternet yoksa? (sentetik demo)

Her komuta `--synthetic` ekleyerek sentetik veriyle deneyebilirsin; ya da canlı
çekim başarısız olursa `--fallback-synthetic` ile otomatik sentetiğe düşer.

```bash
python -m stock_signal_agent.cli train --synthetic --symbols "S1,S2,S3,S4,S5,S6"
python -m stock_signal_agent.cli scan  --synthetic --symbols "S1,S2,S3" --model signal_model.joblib
```

---

## Yapılandırma (`config.yaml`)

İzleme listelerini ve parametreleri buradan değiştir:

| Ayar | Anlamı | Varsayılan |
|------|--------|-----------|
| `horizon` | kaç iş günü ileriye bakılıyor | 10 |
| `rise_threshold` | "yükseliş" sayılması için gereken getiri | 0.08 (%8) |
| `model_weight` / `rule_weight` | model ve kural skorunun birleşim ağırlığı | 0.6 / 0.4 |
| `train_period` / `scan_period` | veri aralığı | 5y / 1y |
| `min_score` | tarama sinyal eşiği | 0.45 |

---

## Python API

```python
from stock_signal_agent import Screener, SignalModel, load_prices
from stock_signal_agent.dataset import build_training_set

# Eğit
X, y, meta, failed = build_training_set(["AAPL", "NVDA", "THYAO.IS"], period="5y")
model = SignalModel()
print(model.train(X, y).summary())
model.save("signal_model.joblib")

# Tara
screener = Screener(model=model)
for sig in screener.scan(["THYAO.IS", "ASELS.IS", "AAPL"], min_score=0.5):
    print(sig.symbol, sig.level, sig.score, "→", "; ".join(sig.reasons))
```

---

## Proje yapısı

```
Stock_Signal_Agent/
├── config.yaml                 # izleme listeleri + parametreler
├── requirements.txt
├── stock_signal_agent/
│   ├── data.py                 # OHLCV çekme (Yahoo / CSV / sentetik)
│   ├── indicators.py           # teknik göstergeler (nedensel)
│   ├── features.py             # "yükseliş öncesi parmak izi" özellikleri
│   ├── labeling.py             # yükseliş olayı etiketleme
│   ├── dataset.py              # çok sembollü eğitim seti
│   ├── model.py                # Gradient Boosting modeli
│   ├── rules.py                # anlaşılır kural motoru
│   ├── screener.py             # model + kural → sinyal
│   ├── backtest.py             # ileri-yönlü backtest
│   ├── notify.py               # rapor formatı + Telegram bildirimi
│   └── cli.py                  # komut satırı arayüzü
└── tests/
    └── test_agent.py           # sentetik veriyle uçtan uca testler
```

## Testler

```bash
python -m pytest tests/ -q
```

Testler tamamen sentetik veriyle çalışır — internet gerektirmez.

---

## Yol haritası (fikirler)

- Sektör/endeks görece güç (relative strength) özelliği
- Temel veri (kazanç sürprizi, F/K) katmanı
- Pozisyon boyutlandırma + stop-loss öneren risk katmanı
