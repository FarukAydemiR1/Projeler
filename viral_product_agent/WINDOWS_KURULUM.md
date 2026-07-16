# 🪟 Windows'ta Botu Çalıştırma — Adım Adım

Bot Telegram'da "sessiz" görünüyorsa sebebi: **`bot.py` programı çalışmıyor.** Botun
komutlara cevap vermesi için bu program bilgisayarında açık olmalı. Aşağıdaki adımları
sırayla yap; komut ezberlemene gerek yok, iki dosyaya çift tıklayacaksın.

---

## Adım 1 — Python'u kur (bir kez)

1. [python.org/downloads](https://www.python.org/downloads/) → **Download Python** butonuna bas.
2. İnen dosyayı çalıştır. **ÇOK ÖNEMLİ:** İlk ekranda alttaki
   **"Add python.exe to PATH"** kutusunu **işaretle**, sonra **Install Now**.
3. Kurulum bitince kapat.

## Adım 2 — Kodu bilgisayarına indir

1. GitHub'da kendi depona git: **Projeler** → dalı `claude/viral-product-agent-turkey-qwyqft` seç.
2. Yeşil **Code** butonu → **Download ZIP**.
3. İnen ZIP'e sağ tık → **Tümünü ayıkla** (ör. Masaüstü'ne).
4. İçindeki **`viral_product_agent`** klasörünü aç.

## Adım 3 — Kurulumu çalıştır (bir kez)

- `viral_product_agent` klasöründeki **`kur.bat`** dosyasına **çift tıkla**.
- Siyah bir pencere açılır, paketleri kurar (birkaç dakika). "KURULUM TAMAM" yazınca kapat.
  > "Python bulunamadi" derse Adım 1'i "Add to PATH" işaretli halde tekrar yap.

## Adım 4 — Token'ı gir

1. Aynı klasörde oluşan **`.env`** dosyasına sağ tık → **Birlikte aç → Not Defteri**.
2. `TELEGRAM_BOT_TOKEN=` satırının sonuna **BotFather'dan aldığın token'ı** yapıştır. Örnek:
   ```
   TELEGRAM_BOT_TOKEN=123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
3. **Kaydet** (Ctrl+S) ve kapat.

## Adım 5 — Botu başlat

- **`baslat.bat`** dosyasına **çift tıkla**.
- Pencerede şunu görmelisin: `[bot] @UrunuTAkibiBot calisiyor.`
- **Bu pencere açık kaldığı sürece bot çalışır.** Kapatırsan bot susar.

## Adım 6 — Telegram'da botu kullan

1. Telegram'da ara: **`@UrunuTAkibiBot`** (ya da `t.me/UrunuTAkibiBot` linkini aç).
2. **Başlat**'a bas, sonra **`/start`** yaz.
3. Bot sana **sohbet id'ni** söyler. Onu kopyala.
4. `.env` dosyasını tekrar aç, `TELEGRAM_CHAT_ID=` satırına o numarayı yaz, kaydet.
5. `baslat.bat` penceresini kapat, tekrar çift tıkla (yeni ayarı okusun).
6. Artık **`/tara`** yazınca ürünleri, **`/liste`** ile buton menüsünü alırsın. 🎉

---

### Sık takılınan yerler
- **"python bulunamadi / not recognized"** → Python "Add to PATH" işaretsiz kurulmuş. Python'u kaldırıp Adım 1'i tekrar yap.
- **Bot cevap vermiyor** → `baslat.bat` penceresi açık mı? Kapalıysa bot susar. Açık tut.
- **Token hatası (Unauthorized)** → `.env`'deki token yanlış/eski. BotFather → `/mybots` → botun → **API Token**'ı tekrar kopyala.
- **Ürün az geliyor** → Normal; en iyi sonuç için ev/ofis internetinde çalıştır. İstersen sonra `ANTHROPIC_API_KEY` ekleyince kalite artar.

> Bilgisayarını kapatınca bot durur. 7/24 açık kalmasını istersen bana söyle —
> ücretsiz bir bulut sunucuda (PythonAnywhere/Railway) çalıştırmayı birlikte kurarız.
