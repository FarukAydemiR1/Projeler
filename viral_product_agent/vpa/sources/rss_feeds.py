"""RSS/Atom akislari: gadget bloglari + Kickstarter — ucuz erken-sinyal kaynagi."""
from __future__ import annotations

import feedparser

from .. import http
from ..models import Candidate
from .base import Source


class RssSource(Source):
    name = "rss_feeds"
    reliability = "high"

    def fetch(self) -> list[Candidate]:
        out: list[Candidate] = []
        limit = int(self.cfg.get("limit_per_feed", 20))
        for feed_url in self.cfg.get("feeds", []):
            raw = self.cache.get_or(f"rss:{feed_url}", lambda: self._fetch_raw(feed_url))
            if not raw:
                continue
            parsed = feedparser.parse(raw)
            for entry in parsed.entries[:limit]:
                summary = getattr(entry, "summary", "")
                out.append(Candidate(
                    title=getattr(entry, "title", "").strip(),
                    description=_strip_html(summary)[:500],
                    url=getattr(entry, "link", ""),
                    source=f"rss:{parsed.feed.get('title', feed_url)[:40]}",
                    reliability=self.reliability,
                ))
        return out

    @staticmethod
    def _fetch_raw(url: str) -> str | None:
        r = http.get(url)
        return r.text if r else None


def _strip_html(text: str) -> str:
    from bs4 import BeautifulSoup
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
