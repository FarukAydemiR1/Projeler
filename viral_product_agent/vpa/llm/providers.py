"""LLM saglayici katmani: Anthropic ve OpenAI-uyumlu uclar (NVIDIA Nemotron, OpenRouter, yerel).

Tek arayuz: Backend.complete(prompt) -> str | None (hata = None, run durmaz).
OpenAI-uyumlu uclar icin ek paket gerekmez; projedeki requests oturumu kullanilir.

Saglayici secimi (oncelik sirasi):
    run.py --provider  >  .env LLM_PROVIDER  >  config.yaml llm.provider  >  "auto"
"auto" = anahtari bulunan ilk saglayici: nvidia -> openrouter -> anthropic.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

import requests

from ..http import session


@dataclass(frozen=True)
class Preset:
    kind: str        # "openai" (OpenAI-uyumlu HTTP) | "anthropic" (resmi SDK)
    model: str
    base_url: str
    key_env: str
    note: str


# Nemotron 3 Ultra = 550B/A55B, 1M baglam, OpenAI-uyumlu. Yerel calistirmak icin 4x B200
# gerekir; pratikte barindirilan uclardan (nvidia/openrouter) kullanilir.
PRESETS: dict[str, Preset] = {
    "nvidia": Preset(
        kind="openai",
        model="nvidia/nemotron-3-ultra",
        base_url="https://integrate.api.nvidia.com/v1",
        key_env="NVIDIA_API_KEY",
        note="NVIDIA Nemotron 3 Ultra — build.nvidia.com anahtari (nvapi-...)",
    ),
    "openrouter": Preset(
        kind="openai",
        model="nvidia/nemotron-3-ultra-550b-a55b:free",
        base_url="https://openrouter.ai/api/v1",
        key_env="OPENROUTER_API_KEY",
        note="Nemotron 3 Ultra — OpenRouter ucretsiz uc (sikca kota siniri)",
    ),
    "anthropic": Preset(
        kind="anthropic",
        model="claude-sonnet-5",
        base_url="",
        key_env="ANTHROPIC_API_KEY",
        note="Claude Sonnet — anthropic SDK",
    ),
    "local": Preset(
        kind="openai",
        model="nvidia/nemotron-3-ultra",
        base_url="http://localhost:8000/v1",
        key_env="LLM_API_KEY",
        note="Yerel/self-host OpenAI-uyumlu uc (vLLM / SGLang / TRT-LLM)",
    ),
}

AUTO_ORDER = ("nvidia", "openrouter", "anthropic")
PROVIDER_NAMES = tuple(PRESETS) + ("auto",)


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    kind: str
    model: str
    base_url: str
    api_key: str
    thinking: bool
    max_tokens: int
    temperature: float
    timeout: int

    @property
    def fingerprint(self) -> str:
        """Cache anahtari: model degisince eski yanitlar kullanilmasin."""
        return f"{self.provider}:{self.model}"

    def describe(self) -> str:
        mode = "dusunme acik" if self.thinking else "dusunme kapali"
        return f"{self.provider} / {self.model} ({mode})"


def resolve(cfg: dict | None = None, *, provider_override: str = "") -> LLMConfig | None:
    """config.yaml llm bolumu + ortam degiskenlerinden calisir bir LLM ayari uretir.

    Anahtar bulunamazsa None doner -> LLM devre disi (pipeline deterministik moda duser).
    """
    cfg = cfg or {}
    provider = (provider_override or os.environ.get("LLM_PROVIDER", "")
                or cfg.get("provider") or "auto").strip().lower()
    if provider not in PROVIDER_NAMES:
        raise ValueError(
            f"Bilinmeyen LLM saglayici: {provider!r}. Secenekler: {', '.join(PROVIDER_NAMES)}")

    if provider == "auto":
        provider = next((name for name in AUTO_ORDER if _key_for(name)), "")
        if not provider:
            return None

    preset = PRESETS[provider]
    api_key = _key_for(provider)
    if not api_key:
        if provider == "local":
            api_key = "EMPTY"  # yerel uclar anahtar istemez
        else:
            return None

    thinking = _as_bool(os.environ.get("LLM_THINKING"), cfg.get("thinking", False))
    max_tokens = _as_int(os.environ.get("LLM_MAX_TOKENS"), cfg.get("max_tokens"))
    temperature = _as_float(os.environ.get("LLM_TEMPERATURE"), cfg.get("temperature"))
    return LLMConfig(
        provider=provider,
        kind=preset.kind,
        model=(os.environ.get("LLM_MODEL", "").strip() or cfg.get("model") or preset.model),
        base_url=(os.environ.get("LLM_BASE_URL", "").strip() or cfg.get("base_url")
                  or preset.base_url),
        api_key=api_key,
        thinking=thinking,
        # Dusunen modda cikti uzun olur; JSON'un kesilmemesi icin tavan yukseltilir.
        max_tokens=max_tokens if max_tokens else (16000 if thinking else 2000),
        # Nemotron dusunme modunda temperature 1.0 + top_p 0.95 onerilir; kapaliyken
        # dusuk temperature daha kararli JSON verir.
        temperature=temperature if temperature is not None else (1.0 if thinking else 0.6),
        timeout=_as_int(os.environ.get("LLM_TIMEOUT"), cfg.get("timeout_seconds")) or 180,
    )


def build(cfg: LLMConfig):
    return AnthropicBackend(cfg) if cfg.kind == "anthropic" else OpenAICompatBackend(cfg)


class AnthropicBackend:
    def __init__(self, cfg: LLMConfig):
        import anthropic  # sadece bu saglayici secilince import et

        self.cfg = cfg
        self._client = anthropic.Anthropic(api_key=cfg.api_key)

    def complete(self, prompt: str) -> str | None:
        try:
            msg = self._client.messages.create(
                model=self.cfg.model,
                max_tokens=self.cfg.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # SDK hatasi run'i durdurmasin
            print(f"[llm] anthropic hatasi: {type(exc).__name__}: {exc}")
            return None
        return "".join(b.text for b in msg.content if b.type == "text") or None


class OpenAICompatBackend:
    """NVIDIA integrate API, OpenRouter ve yerel vLLM/SGLang ayni govdeyle calisir."""

    RETRIES = 3

    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.url = cfg.base_url.rstrip("/") + "/chat/completions"

    def complete(self, prompt: str) -> str | None:
        body = {
            "model": self.cfg.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.cfg.max_tokens,
            "temperature": self.cfg.temperature,
            "top_p": 0.95,
            "stream": False,
        }
        body.update(self._thinking_params())
        headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        backoff = 2.0
        last = ""
        for attempt in range(self.RETRIES):
            try:
                r = session().post(self.url, json=body, headers=headers,
                                   timeout=self.cfg.timeout)
            except requests.RequestException as exc:
                last = f"{type(exc).__name__}: {exc}"
            else:
                if r.status_code == 200:
                    return self._text(r)
                last = f"HTTP {r.status_code}: {r.text[:200]}"
                if r.status_code in (400, 401, 403, 404):  # kalici hata: retry anlamsiz
                    print(f"[llm] {self.cfg.provider} reddetti — {last}")
                    return None
                if r.status_code == 429:  # kota: sunucunun onerdigi kadar bekle
                    backoff = max(backoff, _retry_after(r))
            if attempt < self.RETRIES - 1:
                time.sleep(backoff)
                backoff = min(backoff * 2, 60.0)
        print(f"[llm] {self.cfg.provider} yanit vermedi — {last}")
        return None

    def _thinking_params(self) -> dict:
        if self.cfg.provider == "openrouter":
            return {"reasoning": {"effort": "medium"} if self.cfg.thinking
                    else {"enabled": False}}
        # NVIDIA NIM / vLLM: sohbet sablonu anahtari
        return {"chat_template_kwargs": {"enable_thinking": self.cfg.thinking}}

    @staticmethod
    def _text(r: requests.Response) -> str | None:
        try:
            data = r.json()
        except ValueError:
            return None
        choices = data.get("choices") or []
        if not choices:
            print(f"[llm] bos yanit: {str(data)[:200]}")
            return None
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if isinstance(content, list):  # bazi uclar parca listesi doner
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        text = (content or "").strip()
        if not text:  # dusunme acikken cevap reasoning alanina dusebiliyor
            text = (msg.get("reasoning_content") or msg.get("reasoning") or "").strip()
        return text or None


def _retry_after(r: requests.Response) -> float:
    try:
        return min(float(r.headers.get("Retry-After", "")), 60.0)
    except ValueError:
        return 10.0


def _key_for(provider: str) -> str:
    """LLM_API_KEY tum saglayicilar icin genel gecer; yoksa saglayiciya ozel degisken."""
    generic = os.environ.get("LLM_API_KEY", "").strip()
    if generic:
        return generic
    return os.environ.get(PRESETS[provider].key_env, "").strip()


def _as_bool(env_value: str | None, fallback) -> bool:
    if env_value is not None and env_value.strip():
        return env_value.strip().lower() in ("1", "true", "yes", "evet", "acik", "on")
    return bool(fallback)


def _as_int(env_value: str | None, fallback) -> int:
    for raw in (env_value, fallback):
        try:
            if raw is not None and str(raw).strip():
                return int(str(raw).strip())
        except ValueError:
            continue
    return 0


def _as_float(env_value: str | None, fallback) -> float | None:
    for raw in (env_value, fallback):
        try:
            if raw is not None and str(raw).strip():
                return float(str(raw).strip())
        except ValueError:
            continue
    return None
