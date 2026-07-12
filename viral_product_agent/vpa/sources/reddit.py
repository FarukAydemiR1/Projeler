"""Reddit public JSON API — anahtar gerektirmez, en saglam kesif kaynagi.

Secilen subreddit'ler "insanlarin gorunce almak istedigi" urunleri toplayan
topluluklar; upvote sayisi dogal bir on-viralite sinyalidir."""
from __future__ import annotations

import time

from .. import http
from ..models import Candidate
from .base import Source


class RedditSource(Source):
    name = "reddit"
    reliability = "high"

    def fetch(self) -> list[Candidate]:
        out: list[Candidate] = []
        listing = self.cfg.get("listing", "top")
        timeframe = self.cfg.get("timeframe", "month")
        limit = int(self.cfg.get("limit_per_sub", 25))
        for sub in self.cfg.get("subreddits", []):
            url = f"https://www.reddit.com/r/{sub}/{listing}.json"
            key = f"reddit:{sub}:{listing}:{timeframe}:{limit}"
            data = self.cache.get_or(key, lambda: self._fetch_json(url, timeframe, limit))
            if not data:
                continue
            for post in data.get("data", {}).get("children", []):
                d = post.get("data", {})
                if d.get("stickied") or d.get("is_self"):
                    continue
                age_days = max(1.0, (time.time() - d.get("created_utc", time.time())) / 86400)
                out.append(Candidate(
                    title=d.get("title", "").strip(),
                    description=(d.get("selftext") or "")[:500],
                    url="https://www.reddit.com" + d.get("permalink", ""),
                    source=f"reddit/r/{sub}",
                    reliability=self.reliability,
                    image_url=d.get("url_overridden_by_dest", "") if str(
                        d.get("url_overridden_by_dest", "")).endswith((".jpg", ".png", ".gif")) else "",
                    momentum_hints={
                        "upvotes": d.get("ups", 0),
                        "upvotes_per_day": d.get("ups", 0) / age_days,
                        "comments": d.get("num_comments", 0),
                    },
                ))
        return out

    @staticmethod
    def _fetch_json(url: str, timeframe: str, limit: int):
        r = http.get(url, params={"t": timeframe, "limit": limit},
                     headers={"Accept": "application/json"})
        return r.json() if r else None
