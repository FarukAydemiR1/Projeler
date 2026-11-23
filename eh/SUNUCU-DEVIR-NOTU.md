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
| `llama-embed.service` | bge-m3 Q8_0 (`~/models/bge-m3-q8_0.gguf`) | 8082 | `--embedding --pooling cls -t 4 -c 8192 -ub 8192`, yalnız 127.0.0.1, API anahtarı yok |
| `llama-rerank.service` | bge-reranker-v2-m3 Q8_0 (`~/models/`) | 8083 | `--rerank -t 4 -c 8192 -ub 8192`, yalnız 127.0.0.1, API anahtarı yok |
| `open-webui.service` | Open WebUI 0.13.4 (uv, Python 3.11, `~/open-webui/venv`) | 3000 | yalnız 127.0.0.1; ayarlar `/etc/open-webui.env` (600), veri `/data/open-webui`, `DEFAULT_USER_ROLE=pending`, hibrit arama + harici reranker |
| `open-webui-tailscale.service` | socat yönlendirme | 100.92.128.33:3000 | Tailscale IP → 127.0.0.1:3000; LAN IP'den erişim yok |

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

1–6. **Tamamlandı (23.11.2026).** Toplama: 51 kaynak, 4.229 kayıt, hata 0, ham 2,1 GB (`/depo/egitim-verisi`). apt upgrade yapıldı; yeni çekirdek 7.0.0-44 `apt upgrade` ile gelmedi (`full-upgrade` + yeniden başlatma, kullanıcı laboratuvardayken yapılacak). `50-kablo.yaml` yazıldı (enp0s25, enp5s0 DHCP, optional), `netplan apply` yapılmadı; yeniden başlatmada devreye girer. Not: `llama-server` hız testi (llama-bench) için durdurulup yeniden başlatıldı. Test sonucu: uzun bağlamda `-fa on` üretimi yarıya düşürüyor (16K'da 4,1 → 1,8 t/s); Qwen'de `-fa off` kalacak.
7. **Sürüyor:** `eh/veri-toplama/owui_yukle.py` yazıldı (standart kütüphane; kategori başına `EH-<kategori>` bilgi tabanı; her kayıt tek `.md`, başında kaynak/sürüm/lisans/kaynak_link; durum dosyası `/depo/egitim-verisi/owui-durum.json`). Lisanssız kaynaklar atlanır (360 kayıt). Kuru deneme: 3.766 belge, 32,6 MB. Gerçek yükleme için Open WebUI'de API anahtarları açılıp `OWUI_API_KEY` tanımlanmalı. `standart` kategorisi (gr-difi, sigmf-python) de yüklenecek.
8. Donanımsız test seti iskeleti (22 kodlama görevi; pytest-libiio + iio-emu, PyVISA-sim, gr_unittest).

## Açık sorunlar

- Yedekleme yok (modeller, /depo).
- Sabit yerel IP yok.
- Hukuk onayı bekleyenler: GPL/NC lisanslı içerikle eğitim, Open WebUI lisansı, Tailscale ve Claude Code kullanımı için BT onayı.
