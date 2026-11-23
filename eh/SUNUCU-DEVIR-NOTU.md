# Sunucu devir notu (23.11.2026)

Bu not, yapay zekâ sunucusunda çalışan Claude Code oturumunun önceki çalışmaları bilmesi içindir. Önce bunu oku, sonra `eh/veri-toplama/README.md` dosyasını oku.

## Sunucu

| Konu | Durum |
|---|---|
| Donanım | Fujitsu Celsius R940 Power (anakart D3358), 2 Xeon (NUMA), 6×32 GB RDIMM (1A,1B,1C,1E,1G,1H; 1D ve 1F boş), GPU yok (K4200 Kepler, CUDA için kullanılamaz) |
| İşletim sistemi | Ubuntu 26.04.1 LTS, makine adı `ai`, kullanıcı `ai-server` |
| Diskler | `sda` SSD (sistem, LVM), `/data` SAS disk (LABEL=data), `/depo` eski RAID birimi (LABEL=depo, ext4). fstab `nofail`. Disk harfleri açılışta değişebilir; LABEL kullan |
| PCIe | Slot6 x16 (CPU0): K4200, ilk GPU buraya. Slot3 x16 (CPU0): LSI SAS HBA. Slot2/4 x16 (CPU1) boş. İkinci GPU Slot3'e gidecekse SAS kartı Slot5'e taşınır |
| Ağ | USB WiFi: MediaTek MT7601U, arayüz `wlxe894f61f04e5`, netplan `/etc/netplan/60-wifi.yaml` (sürücü `mt7601u`, 2,4 GHz, yavaş). Yerel IP DHCP (son görülen 192.168.1.15). Kablolu yedek: `/etc/netplan/50-kablo.yaml` (enp*, dhcp, optional) kurulduysa |
| Uzaktan erişim | Tailscale, sunucu IP 100.92.128.33, anahtar süresi kapalı |
| sudo | `/etc/sudoers.d/claude-ai`: `ai-server` için şifresiz tam sudo (kullanıcının açık isteği). Geri almak: `sudo rm /etc/sudoers.d/claude-ai` |
| Claude Code | `~/.claude/settings.json`: `bypassPermissions`; API anahtarı ve netplan dosyalarını okuma yasak. Remote Control kullanıcı servisi: `systemctl --user status claude-rc` (çalışma klasörü `~/lab`, linger açık) |

## Yapay zekâ servisleri

| Servis | Model | Port | Önemli ayarlar |
|---|---|---|---|
| `llama-server.service` | Qwen3-Coder-30B | 8080 | `-t 12 --numa distribute -c 32768 --jinja --spec-type ngram-mod -fa off`, API anahtarı dosyadan |
| `llama-gptoss.service` | gpt-oss-120b MXFP4 (`/depo/models/gpt-oss-120b/gpt-oss-120b-MXFP4.gguf`, 59 GiB) | 8081 | `-t 12 --numa distribute -c 32768 --jinja -fa on --temp 1.0 --top-p 1.0`; ExecStartPre `numactl --interleave=all cat` ile önyükleme, TimeoutStartSec=1200 |

- llama.cpp: `/home/ai-server/llama.cpp/build/bin/`. Yeni bayrak adları: `--spec-type {draft-simple, ngram-mod}`, `--spec-draft-n-max`. Taslak model ile spekülatif çözme MoE'de 2,5 kat yavaş; ngram-mod daha iyi.
- gpt-oss hız ~7–8 t/s; reasoning Low/Medium önerilir.
- Sohbet uzadıkça t/s düşer; her konu için yeni sohbet.

## Kurallar (kullanıcıyla anlaşılanlar)

- **API anahtarını (`/etc/llama/api-key`) ve WiFi şifresini okuma, yazma, ekrana basma.**
- Gizlilik dereceli bilgi bu sunucuya konmaz (sunucu internete ve Tailscale'e bağlı).
- Karıştırıcı (jammer) yapımına yönelik içerik yok. Verici deneyleri yalnızca kablolu, zayıflatıcılı veya dummy load'lu düzenekte (5809 sayılı Kanun).
- **Onay bekleme, işi yap.** Kurulum, servis açma/kapama/yeniden başlatma, paket kurma, dosya yazma, betik yazma, indirme gibi işleri sormadan yap; sonunda kısa bir özet ver.
- **Yalnızca şu durumlarda önce sor:** `/depo/models` veya `/depo/egitim-verisi` altında **silme**; disk bölümlendirme/biçimlendirme; `fstab` değişikliği; uzaktan bağlantıyı koparabilecek ağ değişikliği (`netplan apply`, Tailscale ayarı). Bunların dışında kullanıcıyı bekletme.
- Sistem ayarı değiştirmeden önce `/etc` yedeği al: `sudo tar czf /depo/yedek-etc-$(date +%F).tgz /etc && sudo chmod 600 /depo/yedek-etc-*.tgz` (yedekte gizli bilgiler var).
- Kullanıcı Türkçe konuşur; kısa ve sade Türkçe kullan.
- tmux istemiyor; uzun işler için `nohup ... &` veya systemd.
- Commit ve PR metinlerine model adı yazma.

## Proje: EH laboratuvarı için yerel kod asistanı

Amaç: yerel modele SDR, RF ölçüm ve sinyal işleme için hangi yazılımı kullanacağını ve nasıl kod yazacağını öğretmek. Önce RAG (Open WebUI + llama.cpp), ileride ekran kartı gelince QLoRA ince ayar.

Depo: `FarukAydemiR1/Projeler`, dal `claude/ecstatic-planck-i06c11` (PR #6). Dosyalar `eh/veri-toplama/` altında:
- `surumler.toml`: sabit sürüm seti (etiket `eh-lab-2026-11`); libiio 0.26 ve SoapySDR 0.8.1 Ubuntu 26.04 apt ile aynı; UHD 4.11, GNSS-SDR 0.0.22, liquid-dsp 1.8.3 kaynaktan derlenir.
- `kaynaklar.toml`: 51 depo. `topla.py` bunları indirip JSONL kayda çevirir (yalnız standart kütüphane + git).
- `elle-indirilecekler.md`: betikle indirilemeyen PDF/web belgeleri (SCPI kılavuzları, GNU Radio wiki — Cloudflare engelli, veri setleri).
- `laboratuvar-yapilacaklar.md`, `lab-ornek-sablonu.md`: laboratuvarda üretilecek doğrulanmış örnekler.
- `eksikler-promptu.md`: araştırma durumu. `ince-ayar-notlari.md`: QLoRA başlangıç ayarları.

## Sıradaki işler (sırayla)

1. Depoyu `~/lab` altına indir: `git clone -b claude/ecstatic-planck-i06c11 https://github.com/FarukAydemiR1/Projeler.git` (depo gizliyse `gh auth login` gerekir).
2. Toplama: `cd ~/lab/Projeler/eh/veri-toplama && nohup python3 topla.py --hedef /depo/egitim-verisi > /depo/egitim-verisi-toplama.log 2>&1 &`. Beklenen: 51 kaynak, hata 0. Önceki denemelerde ~4.000+ kayıt, ~1,5 GB ham indirme. Bittiğinde `LISANSLAR.md` kontrol edilir.
3. `apt update && apt upgrade` (toplama bitince; çekirdek güncellenirse yeniden başlat ve servisleri doğrula).
4. Kablolu ağ yedeği (`50-kablo.yaml`) kurulmadıysa kur.
5. Embedding: `ggml-org/bge-m3-Q8_0-GGUF` indir, ayrı llama-server servisi (`--embedding --pooling cls` veya modelin varsayılanı; port 8082). İsteğe bağlı reranker `gpustack/bge-reranker-v2-m3-GGUF` (`--rerank`, port 8083). Servis adlarını `llama-*` diye ver.
6. Open WebUI kur (lisans: Open WebUI License; markayı değiştirme). Embedding motoru OpenAI uyumlu yerel uç nokta, LLM olarak 8080/8081. `OFFLINE_MODE` sonraya.
7. `kayitlar/*.jsonl` içeriğini Open WebUI bilgi tabanlarına kategori bazında (sdr, dsp, ml, gnss, radar, df, olcum, em, fpga, yayilim) yükleyen betiği yaz. Kod dosyaları bölünmeden yüklensin; her parçanın başında kaynak, sürüm ve lisans etiketi olsun.
8. Donanımsız test seti iskeleti (22 kodlama görevi; pytest-libiio + iio-emu, PyVISA-sim, gr_unittest).

## Açık sorunlar

- Yedekleme yok (modeller, /depo).
- Sabit yerel IP yok.
- Hukuk onayı bekleyenler: GPL/NC lisanslı içerikle eğitim, Open WebUI lisansı, Tailscale ve Claude Code kullanımı için BT onayı.
