from __future__ import annotations
import time
from typing import Optional
import requests
from .parser import build_bing_url, parse_html, extract_bing_click_target
from .filters import filter_results

_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Cache-Control": "no-cache",
}

def _sleep(delay: float):
    if delay and delay > 0:
        time.sleep(delay)

def _fetch(url: str, *, timeout: float = 12.0, retries: int = 2, delay: float = 1.0,
           headers: Optional[dict] = None, proxy: Optional[str] = None) -> str:
    """
    Fetch a URL with basic retries, timeouts, and polite pre-delay.
    Returns response text (decoded by requests) or raises the last exception.
    """
    sess = requests.Session()
    if proxy:
        sess.proxies = {"http": proxy, "https": proxy}

    hdrs = dict(_DEFAULT_HEADERS)
    if headers:
        hdrs.update(headers)

    last_exc = None
    for attempt in range(retries + 1):
        try:
            _sleep(delay if attempt == 0 else delay * (attempt + 1))
            r = sess.get(url, headers=hdrs, timeout=timeout, allow_redirects=True)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last_exc = e
            continue
    raise last_exc if last_exc else RuntimeError("Request failed without an exception")

def fetch_serp_by_query(*, query: str, when: str | None = None, site: str | None = None,
                        lang: str | None = None, country: str | None = None, safe: bool | None = None,
                        include: list[str] | None = None, exclude: list[str] | None = None,
                        allow_domains: list[str] | None = None, deny_domains: list[str] | None = None,
                        timeout: float = 12.0, retries: int = 2, delay: float = 1.0,
                        headers: Optional[dict] = None, proxy: Optional[str] = None) -> list[dict]:
    """
    Build a Bing URL from query + filters, fetch the SERP page, parse it,
    and optionally apply in-memory filters on the result set.
    """
    url = build_bing_url(query, when=when, site=site, lang=lang, country=country, safe=safe)
    html = _fetch(url, timeout=timeout, retries=retries, delay=delay, headers=headers, proxy=proxy)
    rows = parse_html(html)
    rows = filter_results(rows, include=include, exclude=exclude, allow_domains=allow_domains, deny_domains=deny_domains)
    return rows

def fetch_serp_by_url(url: str, *, include: list[str] | None = None, exclude: list[str] | None = None,
                      allow_domains: list[str] | None = None, deny_domains: list[str] | None = None,
                      timeout: float = 12.0, retries: int = 2, delay: float = 1.0,
                      headers: Optional[dict] = None, proxy: Optional[str] = None) -> list[dict]:
    """
    Fetch a concrete Bing SERP URL and parse + filter the results.
    """
    html = _fetch(url, timeout=timeout, retries=retries, delay=delay, headers=headers, proxy=proxy)
    rows = parse_html(html)
    rows = filter_results(rows, include=include, exclude=exclude, allow_domains=allow_domains, deny_domains=deny_domains)
    return rows

def fetch_click_and_extract(click_url: str, *, timeout: float = 12.0, retries: int = 2, delay: float = 1.0,
                            headers: Optional[dict] = None, proxy: Optional[str] = None) -> str | None:
    """
    Fetch a Bing click/redirect page and extract the original destination via script `var u = "..."`.
    Returns the URL string or None if not found.
    """
    html = _fetch(click_url, timeout=timeout, retries=retries, delay=delay, headers=headers, proxy=proxy)
    return extract_bing_click_target(html)
