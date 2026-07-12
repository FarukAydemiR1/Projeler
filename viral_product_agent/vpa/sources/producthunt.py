"""Product Hunt GraphQL API — ucretsiz developer token ister (PRODUCTHUNT_TOKEN).

Token yoksa kaynak kendini devre disi birakir; run etkilenmez."""
from __future__ import annotations

from .. import http
from ..models import Candidate
from .base import Source

API = "https://api.producthunt.com/v2/api/graphql"
QUERY = """
{ posts(order: VOTES, first: %d) {
    edges { node { name tagline url votesCount thumbnail { url } topics(first:2){edges{node{name}}} } } } }
"""


class ProductHuntSource(Source):
    name = "producthunt"
    reliability = "high"

    @property
    def enabled(self) -> bool:
        return super().enabled and bool(self.settings.producthunt_token)

    def safe_fetch(self):
        if self.cfg.get("enabled") and not self.settings.producthunt_token:
            return [], "devre disi (PRODUCTHUNT_TOKEN yok)"
        return super().safe_fetch()

    def fetch(self) -> list[Candidate]:
        limit = int(self.cfg.get("limit", 25))
        key = f"producthunt:{limit}"
        data = self.cache.get_or(key, lambda: self._query(limit))
        if not data:
            return []
        out = []
        for edge in data.get("data", {}).get("posts", {}).get("edges", []):
            node = edge["node"]
            topics = [t["node"]["name"] for t in node.get("topics", {}).get("edges", [])]
            out.append(Candidate(
                title=node["name"],
                description=node.get("tagline", ""),
                url=node.get("url", ""),
                source="producthunt",
                reliability=self.reliability,
                image_url=(node.get("thumbnail") or {}).get("url", ""),
                category=", ".join(topics),
                momentum_hints={"votes": node.get("votesCount", 0)},
            ))
        return out

    def _query(self, limit: int):
        r = http.session().post(
            API,
            json={"query": QUERY % limit},
            headers={"Authorization": f"Bearer {self.settings.producthunt_token}"},
            timeout=20,
        )
        return r.json() if r.status_code == 200 else None
