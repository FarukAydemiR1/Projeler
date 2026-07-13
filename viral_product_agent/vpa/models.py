"""Pipeline'in tum asamalarinin uzerinde anlastigi veri modelleri."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class Candidate:
    """Herhangi bir kaynaktan gelen tek bir urun adayi."""
    title: str
    description: str = ""
    url: str = ""
    source: str = ""                 # reddit / producthunt / rss / web_search / trends
    reliability: str = "medium"      # kaynak guvenilirlik etiketi: high/medium/low
    image_url: str = ""
    price_usd: Optional[float] = None
    category: str = ""
    # kaynaga ozgu ham momentum ipuclari (upvote, yas, breakout bayragi...)
    momentum_hints: dict[str, Any] = field(default_factory=dict)
    # dedup sonrasi: ayni urunun gorundugu diger kaynak URL'leri
    also_seen: list[str] = field(default_factory=list)

    # pipeline'in doldurdugu alanlar
    signals: dict[str, float] = field(default_factory=dict)        # 0..1
    llm_scores: dict[str, float] = field(default_factory=dict)     # 0..10
    llm_rationale: dict[str, str] = field(default_factory=dict)
    availability_confidence: str = "low"   # TR kontrolunun guveni: high/low
    final_score: float = 0.0
    eliminated: bool = False
    elimination_reason: str = ""

    def key(self) -> str:
        """Dedup icin normalize edilmis baslik anahtari."""
        return "".join(ch for ch in self.title.lower() if ch.isalnum() or ch == " ").strip()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Candidate":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class AdConcept:
    product_title: str
    hook: str = ""
    video_script: str = ""      # 15 sn dikey video: sahne sahne
    platform: str = ""          # TikTok / Instagram Reels / Meta
    audience: str = ""          # TR hedef kitle tanimi
    note: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "AdConcept":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Report:
    generated_at: str
    ranked: list[Candidate] = field(default_factory=list)
    eliminated: list[Candidate] = field(default_factory=list)
    ads: list[AdConcept] = field(default_factory=list)
    source_status: dict[str, str] = field(default_factory=dict)   # kaynak -> ok/hata/devre disi
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Report":
        return cls(
            generated_at=d.get("generated_at", ""),
            ranked=[Candidate.from_dict(c) for c in d.get("ranked", [])],
            eliminated=[Candidate.from_dict(c) for c in d.get("eliminated", [])],
            ads=[AdConcept.from_dict(a) for a in d.get("ads", [])],
            source_status=d.get("source_status", {}),
            notes=d.get("notes", []),
        )
