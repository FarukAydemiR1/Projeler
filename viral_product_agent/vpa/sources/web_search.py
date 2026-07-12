"""Web aramasi ile kesif — DuckDuckGo HTML arayuzu (anahtar gerektirmez).

DDG engellerse veya yapisi degisirse bos doner; run durmaz. Bir Claude Code
oturumunda calisirken operatorun WebSearch araciyla daha kaliteli sonuc alip
output/ altina rapor uretmesi onerilir (README'de anlatilir)."""
from __future__ import annotations

from urllib.parse import unquote, urlparse, parse_qs

from bs4 import BeautifulSoup

from .. import http
from ..models import Candidate
from .base import Source

DDG = "https://html.duckduckgo.com/html/"


def ddg_search(cache, query: str, max_results: int = 8) -> list[dict] | None:
    """DDG HTML sonuclari: [{title, url, snippet}].

    None = arama CEVAPSIZ (engel/hata) — "sonuc yok" ile karistirilmamali;
    turkey_availability bu ayrima gore guven etiketi dusurur."""
    def _fetch():
        r = http.get(DDG, params={"q": query})
        if not r:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for res in soup.select(".result")[:max_results]:
            a = res.select_one(".result__a")
            snippet = res.select_one(".result__snippet")
            if not a:
                continue
            href = a.get("href", "")
            # DDG yonlendirme linkini gercek URL'e cevir
            if "uddg=" in href:
                q = parse_qs(urlparse(href).query)
                href = unquote(q.get("uddg", [href])[0])
            results.append({
                "title": a.get_text(strip=True),
                "url": href,
                "snippet": snippet.get_text(" ", strip=True) if snippet else "",
            })
        return results

    return cache.get_or(f"ddg:{query}:{max_results}", _fetch)


class WebSearchSource(Source):
    name = "web_search"
    reliability = "medium"

    def fetch(self) -> list[Candidate]:
        out = []
        for query in self.cfg.get("queries", []):
            for res in ddg_search(self.cache, query) or []:
                out.append(Candidate(
                    title=res["title"],
                    description=res["snippet"][:500],
                    url=res["url"],
                    source=f"web_search:{query[:30]}",
                    reliability=self.reliability,
                ))
        return out
