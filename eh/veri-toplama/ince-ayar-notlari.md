# İnce ayar (fine-tune) notları

Ekran kartı (RTX A4000, 16 GB) gelince kullanılacak başlangıç ayarları. Değerler resmi belgelerden alındı ve 21.11.2026'da kontrol edildi. Bunlar başlangıç noktası; kesin değerleri doğrulama kaybına bakarak seçeceğiz.

## Araçlar

| Araç | Sürüm (PyPI) | Lisans | Not |
|---|---|---|---|
| LLaMA-Factory | 0.9.5 | Apache-2.0 | Web arayüzü var; ilk tercih |
| Unsloth | 2026.11.7 | Apache-2.0 | Daha az bellek, daha hızlı |
| Axolotl | 0.21.1 | Apache-2.0 | YAML tabanlı |
| llama.cpp | — | MIT | GGUF'a çevirme ve kuantalama |

## Başlangıç ayarları (300–1000 örnek için)

| Ayar | Değer | Kaynak |
|---|---|---|
| Yöntem | QLoRA, 4-bit | LLaMA-Factory `train_qlora` örnekleri |
| LoRA rank (r) | 8–16 | LLaMA-Factory örneği 8; Unsloth "16 veya 32" |
| lora_alpha | r veya 2×r | Unsloth: "lora_alpha = 2 * lora_rank or lora_alpha = lora_rank" |
| Öğrenme oranı | 1e-4 – 2e-4 | LLaMA-Factory 1e-4; Unsloth 2e-4 |
| Epoch | 1–3 | Unsloth: 3'ten fazlası aşırı öğrenme riski |
| Zamanlayıcı | cosine, %10 ısınma | LLaMA-Factory örneği |
| Weight decay | 0.01 | Unsloth |
| Doğrulama | Verinin %10'u ayrılır (`val_size: 0.1`) | Doğrulama kaybı yükselmeye başlayınca durdur |
| Hassasiyet | bf16 | A4000 (Ampere) destekler |
| Batch | 1, gradient accumulation 8 | LLaMA-Factory örneği |

## Adımlar

1. Laboratuvar örnekleri JSONL'e çevrilir (`messages` biçimi). Bu betik sonra yazılacak.
2. LLaMA-Factory'de `dataset_info.json`'a veri seti eklenir (sharegpt biçimi, `messages` sütun eşlemesi).
3. Eğitim: `llamafactory-cli train <ayar>.yaml`
4. Birleştirme: `llamafactory-cli export <birlestir>.yaml`. **Dikkat:** Birleştirmede kuantalanmış model veya `quantization_bit` KULLANILMAZ; 16-bit taban model kullanılır (LLaMA-Factory resmi uyarısı).
5. llama.cpp ile `convert_hf_to_gguf.py`, ardından `llama-quantize`.
6. Test seti: aynı sorular hem eğitilmiş hem eğitilmemiş modele (ikisinde de RAG açık) sorulur.

## Kaynaklar

- Unsloth hiperparametre rehberi: https://unsloth.ai/docs/get-started/fine-tuning-llms-guide/lora-hyperparameters-guide
- LLaMA-Factory örnekleri: https://raw.githubusercontent.com/hiyouga/LLaMA-Factory/main/examples/README.md
- Qwen belgesi, LLaMA-Factory ile eğitim ve veri biçimi: https://qwen.readthedocs.io/en/latest/training/llama_factory.html
- "LoRA Learns Less and Forgets Less" (kod verisinde LoRA): https://arxiv.org/abs/2405.09673

## Lisans hatırlatması

- RadioML ve RadChar **CC BY-NC-SA** (ticari olmayan). PySDR, WiSig ve RadChar ile eğitilen model ticari bir ürüne girecekse hukuk görüşü alınmalı.
- GPL lisanslı kodla eğitim için de hukuk birimine danışılmalı (`LISANSLAR.md`).
