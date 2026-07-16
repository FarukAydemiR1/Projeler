"""Google Trends (pytrends) — momentum sinyali + TR'de yukselen sorgular.

pytrends resmi olmayan bir kutuphanedir ve zaman zaman kirilir; bu kaynak
her hatada sessizce bos doner (base.safe_fetch yutar), run asla durmaz."""
from __future__ import annotations

from ..models import Candidate
from .base import Source


class GoogleTrendsSource(Source):
    name = "google_trends"
    reliability = "medium"

    def fetch(self) -> list[Candidate]:
        geo = self.cfg.get("geo", "TR")
        key = f"trends:trending:{geo}"
        rows = self.cache.get_or(key, lambda: self._trending(geo))
        if not rows:
            return []
        out = []
        for term in rows:
            out.append(Candidate(
                title=str(term).strip(),
                description="Google Trends yukselen sorgu (urun olup olmadigini insan/LLM degerlendirir)",
                url=f"https://trends.google.com/trends/explore?geo={geo}&q={term}",
                source="google_trends",
                reliability=self.reliability,
                momentum_hints={"breakout": True},
            ))
        return out

    @staticmethod
    def _trending(geo: str) -> list[str] | None:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="tr-TR", tz=180)
        # trending_searches ulke bazli gunluk trendler; urun-disi sorgular da gelir,
        # bunlar dedup/LLM asamasinda elenir.
        country = {"TR": "turkey"}.get(geo, "united_states")
        df = pytrends.trending_searches(pn=country)
        return df[0].tolist()[:20] if df is not None and not df.empty else None
