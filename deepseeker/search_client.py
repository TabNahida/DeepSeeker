from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

import requests

from bingsift import filter_results  # type: ignore
from bingsift.net import fetch_serp_by_query  # type: ignore

from .types import SearchFilters, SearchRequest, SearchResult


class SearchClient:
    """
    Thin wrapper on top of BingSift.

    Responsibilities:
    - Execute Bing search according to SearchRequest.
    - Map BingSift rows -> DeepSeeker SearchResult objects.
    - Fetch article HTML for LLM1.
    """

    def __init__(self, timeout: int = 12):
        self.timeout = timeout

    def search(self, req: SearchRequest) -> List[SearchResult]:
        """
        Run a Bing search using BingSift with optional filters.
        """
        # 1) Fetch SERP via BingSift
        rows = fetch_serp_by_query(query=req.query, when=req.when)

        # 2) Apply filters if provided
        f: SearchFilters = req.filters

        # BingSift filter_results supports include / exclude / allow_domains / deny_domains
        if any(
            [
                f.include,
                f.exclude,
                f.allow_domains,
                f.deny_domains,
            ]
        ):
            rows = filter_results(
                rows,
                include=f.include or None,
                exclude=f.exclude or None,
                allow_domains=f.allow_domains or None,
                deny_domains=f.deny_domains or None,
            )

        # 3) Map to SearchResult and assign IDs r1, r2, ...
        results: List[SearchResult] = []
        for idx, row in enumerate(rows[: req.max_results], start=1):
            # BingSift rows are simple dicts, see README.
            # We defensively access keys.
            r = SearchResult(
                id=f"r{idx}",
                title=row.get("title", ""),
                url=row.get("url", ""),
                snippet=row.get("snippet", ""),
                domain=row.get("domain"),
                display_url=row.get("display_url"),
                guessed_time=row.get("guessed_time"),
                attribution=row.get("attribution"),
            )
            results.append(r)

        return results

    def fetch_page_excerpt(
        self,
        url: str,
        max_chars: int = 8000,
        user_agent: Optional[str] = None,
    ) -> str:
        """
        Fetch a web page and return at most max_chars of HTML text.

        This is intentionally simple. You can later replace it with
        a proper readability / boilerplate removal library.
        """
        headers = {}
        if user_agent:
            headers["User-Agent"] = user_agent

        resp = requests.get(url, timeout=self.timeout, headers=headers)
        resp.raise_for_status()
        text = resp.text

        if len(text) > max_chars:
            return text[:max_chars]
        return text

    @staticmethod
    def to_dict_list(results: List[SearchResult]) -> List[dict]:
        return [asdict(r) for r in results]
