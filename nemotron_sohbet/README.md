# Nemotron Sohbet

**NVIDIA Nemotron 3 Ultra** ile terminalden sohbet — Claude kotanı harcamadan.
Tek bağımlılık: `requests`. Tek dosya: `sohbet.py`.

## Neden?

Claude'u her şeye harcamak yerine, rutin işleri ücretsiz bir modele yıkmak için:
kod açıklatma, hata mesajı sorma, metin özetleme, çeviri, "bu regex ne yapıyor",
fikir listesi… Zor ve kritik işler Claude'da kalsın.

## Kurulum (Windows — çift tıkla)

1. `kur.bat` → çift tıkla (Python gerekir, [python.org](https://www.python.org/downloads/),
   kurulumda **"Add python.exe to PATH"** işaretli olmalı).
2. [build.nvidia.com](https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b) →
   **Get API Key** → `nvapi-...` ile başlayan anahtarı kopyala.
3. `.env` dosyasını Not Defteri ile aç, `NVIDIA_API_KEY=` satırına yapıştır, kaydet.
4. `sohbet.bat` → çift tıkla.

## Kurulum (Linux / macOS)

```bash
cd nemotron_sohbet
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # NVIDIA_API_KEY=nvapi-... satırını doldur
python sohbet.py
```

## Kullanım

```bash
python sohbet.py                      # sohbet başlat
python sohbet.py "bu regex ne yapar: ^\d{3}-\d{2}$"   # tek soru sor, cevabı yaz, çık
python sohbet.py --dusun              # reasoning modu açık başlat
cat hata.log | python sohbet.py "bu hatanın sebebi ne?"   # dosyayı borudan ver
cat main.py | python sohbet.py        # sadece dosya ver, soruyu içinden anlasın
```

Sohbet içindeki komutlar:

| Komut | Ne yapar |
|---|---|
| `/yeni` | Geçmişi unut, sıfırdan başla (uzun sohbet yavaşlayınca işe yarar) |
| `/dusun` | Reasoning modunu aç/kapa — yavaşlar ama zor sorularda daha isabetli |
| `/kaydet` | Sohbeti `kayitlar/` klasörüne `.md` olarak yaz |
| `/yardim` | Komut listesi |
| `/cik` | Çıkış (Ctrl+C de olur) |

## Düşünme (reasoning) modu

Nemotron bir *reasoning* modelidir. Varsayılan **kapalı**: hızlı, günlük sorular için
yeterli. `/dusun` ile açarsan model önce sesli düşünür (ekranda soluk gri akar), sonra
cevabı verir — matematik, hata ayıklama, çok adımlı akıl yürütme gerektiren işlerde aç.

## Bilmen gerekenler

- **Bu Claude değil.** Nemotron iyi bir açık model ama kod yazma ve uzun görevlerde
  Claude seviyesinde değil. Kritik iş için Claude'a dön.
- **Claude Code'u bu modele çeviremezsin** — [resmî dokümanda](https://code.claude.com/docs/en/llm-gateway)
  açıkça yazıyor: Anthropic, Claude Code'u Claude dışı modellere yönlendirmeyi
  desteklemiyor. Tasarruf, işi bu araca kaydırmaktan geçiyor, Claude Code'u kandırmaktan değil.
- **Anahtarın şifredir.** Kimseyle paylaşma, sohbete/foruma yapıştırma. `.env` dosyası
  `.gitignore`'da, git'e girmez. Sızdıysa build.nvidia.com'dan iptal edip yenisini al.
- **Ücretsiz uçta kota var.** `HTTP 429` görürsen birkaç dakika bekle.

## Sorun giderme

| Hata | Sebep / çözüm |
|---|---|
| `NVIDIA_API_KEY bulunamadi` | `.env` yok veya satır boş. Adım 2-3'ü tekrar yap. |
| `HTTP 401` / `403` | Anahtar yanlış veya iptal edilmiş. Yenisini al. |
| `HTTP 429` | Kota sınırı. Birkaç dakika bekle. |
| `baglanti kurulamadi` | İnternet yok ya da güvenlik duvarı engelliyor. |
