from __future__ import annotations
from typing import List, Optional
from ..schema import SearchDoc

class SearchProvider:
    async def search(self, q: str, *, per_query_limit: int = 8,
                     recency_days: Optional[int] = None, site_filters: Optional[list[str]] = None,
                     lang: Optional[str] = None) -> List[SearchDoc]:
        raise NotImplementedError

    async def search_multi(self, queries: list[dict], *, per_query_limit: int = 8) -> List[SearchDoc]:
        pooled: list[SearchDoc] = []
        for qi in queries:
            items = await self.search(
                qi.get("q", ""),
                per_query_limit=per_query_limit,
                recency_days=qi.get("recency_days"),
                site_filters=qi.get("site_filters"),
                lang=qi.get("lang"),
            )
            pooled.extend(items)
        # Remove duplicates by URL
        seen = set()
        uniq: list[SearchDoc] = []
        for d in pooled:
            if d.url in seen:
                continue
            seen.add(d.url)
            uniq.append(d)
        return uniq