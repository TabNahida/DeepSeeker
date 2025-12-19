from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional
import asyncio

import requests

from bingsift import filter_results  # type: ignore
from bingsift.net import fetch_serp_by_query  # type: ignore
from bingsift.net import fetch_click_and_extract_async  # type: ignore

from .types import SearchFilters, SearchRequest, SearchResult
from .text_extractor import extract_text_from_html


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
        
        async def fetch_all_urls():
            tasks = [
                fetch_click_and_extract_async(row.get("url", ""))
                for row in rows
            ]
            return await asyncio.gather(*tasks)

        fetched_urls = asyncio.run(fetch_all_urls())
        
        for idx, (real_url, row) in enumerate(zip(fetched_urls, rows), start=1):
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
        Fetch a web page and extract key text content.
        
        This method now extracts readable text from HTML instead of sending
        raw HTML to the LLM, significantly reducing token usage while
        preserving the important information.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Cache-Control": "no-cache",
        }

        resp = requests.get(url, timeout=self.timeout, headers=headers)
        resp.raise_for_status()
        html = resp.text

        # Extract text from HTML
        extracted_text = extract_text_from_html(html, max_chars=max_chars, use_importance=True)
        
        return extracted_text

    @staticmethod
    def to_dict_list(results: List[SearchResult]) -> List[dict]:
        return [asdict(r) for r in results]
