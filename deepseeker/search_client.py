from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from bingsift import filter_results  # type: ignore
from bingsift.net import fetch_serp_by_query  # type: ignore
from bingsift.net import fetch_click_and_extract  # type: ignore

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
        rows = fetch_serp_by_query(query=req.query, when=req.when, country="en-US")

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
        rows = rows[: req.max_results]
        max_workers = 10
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(fetch_click_and_extract, row.get("url", "")): (idx, row)
                for idx, row in enumerate(rows, start=1)
            }

            for future in as_completed(future_to_idx):
                idx, row = future_to_idx[future]
                real_url = future.result()

                r = SearchResult(
                    id=f"r{idx}",
                    title=row.get("title", ""),
                    url=real_url,
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
    ) -> str:
        """
        Fetch a web page and return at most max_chars of HTML text.

        This is intentionally simple. You can later replace it with
        a proper readability / boilerplate removal library.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Cache-Control": "no-cache",
        }

        resp = requests.get(url, timeout=self.timeout, headers=headers)
        resp.raise_for_status()
        text = resp.text

        if len(text) > max_chars:
            return text[:max_chars]
        return text

    @staticmethod
    def to_dict_list(results: List[SearchResult]) -> List[dict]:
        return [asdict(r) for r in results]
