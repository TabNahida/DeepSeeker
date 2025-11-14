from __future__ import annotations
import httpx
from typing import List, Optional
from ..schema import SearchDoc
from .provider import SearchProvider

from bingsift.net import fetch_serp_by_query
from bingsift import filter_results

class BingSiftProvider(SearchProvider):
    def __init__(self, when: str = "week", country: str = "en-US", timeout: float = 12.0, retries: int = 2):
        self.when = when
        self.country = country
        self.timeout = timeout
        self.retries = retries

    async def search(self, q: str, *, per_query_limit: int = 8,
                     recency_days: Optional[int] = None, site_filters: Optional[list[str]] = None,
                     lang: Optional[str] = None) -> List[SearchDoc]:
        # recency_days → translate to BingSift `when` heuristic
        when = self.when
        if recency_days:
            if recency_days <= 1:
                when = "day"
            elif recency_days <= 7:
                when = "week"
            else:
                when = "month"

        rows = fetch_serp_by_query(
            query=q,
            when=when,
            country=self.country,
            timeout=self.timeout,
            retries=self.retries,
        )

        # Apply domain filtering if present
        if site_filters:
            rows = filter_results(rows, allow_domains=site_filters)

        docs: List[SearchDoc] = []
        for r in rows[:per_query_limit]:
            docs.append(SearchDoc(
                doc_id=str(hash(r.url)),
                title=r.title or "(untitled)",
                url=r.url,
                snippet=r.snippet,
                source=r.domain,
                published=r.guessed_time,
            ))
        return docs