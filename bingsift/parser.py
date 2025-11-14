\
from __future__ import annotations
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup

def _extract_domain(url: str) -> str:
    """Return netloc/domain from a URL, or empty string on failure."""
    try:
        return urlparse(url).netloc
    except Exception:
        return ""

def _parse_relative_time(text: str, now_dt: datetime) -> datetime | None:
    """
    Parse relative time like '2 hours ago' (no regex).
    Returns an absolute datetime or None.
    """
    t = text.strip().lower()
    # normalize common variants
    t = t.replace("mins", "minutes").replace("min", "minute")
    t = t.replace("hrs", "hours").replace("hr", "hour")
    t = t.replace("sec", "second").replace("secs", "seconds")

    # Tokenize on whitespace
    parts = t.split()
    # Look for pattern: <int> <unit> ago
    for i in range(len(parts) - 2):
        num_str, unit, ago = parts[i], parts[i+1], parts[i+2]
        if not num_str.isdigit():
            continue
        if ago != "ago":
            continue
        n = int(num_str)
        if unit in ("second", "seconds"):
            delta = timedelta(seconds=n)
        elif unit in ("minute", "minutes"):
            delta = timedelta(minutes=n)
        elif unit in ("hour", "hours"):
            delta = timedelta(hours=n)
        elif unit in ("day", "days"):
            delta = timedelta(days=n)
        elif unit in ("week", "weeks"):
            delta = timedelta(weeks=n)
        elif unit in ("month", "months"):
            delta = timedelta(days=30*n)  # approximation
        elif unit in ("year", "years"):
            delta = timedelta(days=365*n)  # approximation
        else:
            continue
        return now_dt - delta
    return None

def _try_strptime(s: str, fmts: list[str]) -> datetime | None:
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def _parse_absolute_date(text: str) -> datetime | None:
    """
    Parse a few common absolute date patterns (no regex).
    Returns a datetime or None.
    """
    s = text.strip()
    # Quick passes with common formats
    fmts = [
        "%b %d, %Y",     # Oct 20, 2025
        "%B %d, %Y",     # October 20, 2025
        "%d %b %Y",      # 20 Oct 2025
        "%d %B %Y",      # 20 October 2025
        "%Y-%m-%d",      # 2025-10-20
        "%b %d %Y",      # Oct 20 2025
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y.%m.%d",
        "%d.%m.%Y",
    ]
    # Try as a whole
    dt = _try_strptime(s, fmts)
    if dt:
        return dt

    # Heuristic: split on separators and attempt pieces
    # e.g., "Published Oct 20, 2025 at ..." -> try contiguous tokens
    tokens = s.replace(",", " ").replace("|"," ").replace("•"," ").replace("·"," ").split()
    # Reassemble windows of up to 3 tokens and try
    for k in range(len(tokens)):
        for w in range(2, 4):  # 2 or 3 tokens
            seg = " ".join(tokens[k:k+w])
            if not seg:
                continue
            dt = _try_strptime(seg, fmts)
            if dt:
                return dt
    return None

def _guess_time(block_text: str, now_dt: datetime) -> datetime | None:
    dt = _parse_relative_time(block_text, now_dt)
    if dt:
        return dt
    return _parse_absolute_date(block_text)

def build_bing_url(query: str, *, when: str | None = None, site: str | None = None,
                   lang: str | None = None, country: str | None = None, safe: bool | None = None) -> str:
    """
    Build a Bing search URL with optional freshness ('day'/'week'/'month'/'year'),
    site restriction, language, market, and adult filter toggle.
    """
    q = query
    if site:
        q = f"site:{site} {q}"
    params = [("q", q)]
    when_map = {"day": 1440, "week": 10080, "month": 43200, "year": 525600}
    if when in when_map:
        params.append(("qft", f"+filterui:age-lt{when_map[when]}"))
    if lang:
        params.append(("setlang", lang))
    if country:
        params.append(("cc", country.split("-")[-1].lower()))
        params.append(("mkt", country))
    if safe is not None:
        params.append(("adlt", "off" if safe else "strict"))
    param_str = "&".join([f"{k}={quote_plus(v)}" for k,v in params])
    return f"https://www.bing.com/search?{param_str}"

def parse_html(html: str) -> list[dict]:
    """
    Parse a saved Bing SERP HTML into a list of dictionaries with
    title/url/domain/display_url/snippet/attribution/guessed_time_iso.
    """
    soup = BeautifulSoup(html, "html.parser")
    now = datetime.now()
    out: list[dict] = []

    # Standard organic results
    for li in soup.select("#b_results li.b_algo"):
        a = li.select_one("h2 a")
        if not a:
            continue
        href = a.get("href","").strip()
        title = a.get_text(" ", strip=True)

        # Snippet
        snippet = ""
        p = li.select_one(".b_caption p") or li.find("p")
        if p:
            snippet = p.get_text(" ", strip=True)

        # Display URL
        display_url = ""
        cite = li.select_one("cite")
        if cite:
            display_url = cite.get_text(" ", strip=True)

        # Attribution (may contain time hints)
        attrib_text = ""
        attrib = li.select_one(".b_attribution") or li.select_one(".b_tpcn")
        if attrib:
            attrib_text = attrib.get_text(" ", strip=True)

        block_text = f"{attrib_text} {snippet}".strip()
        dt = _guess_time(block_text, now)

        out.append({
            "title": title,
            "url": href,
            "domain": _extract_domain(href),
            "display_url": display_url,
            "snippet": snippet,
            "attribution": attrib_text,
            "guessed_time_iso": dt.isoformat() if dt else None,
        })

    # News-like cards (best-effort)
    for card in soup.select(".news-card, .news-card__item, .b_pressItem"):
        a = card.select_one("a")
        if not a:
            continue
        href = a.get("href","").strip()
        title = a.get_text(" ", strip=True)
        text = card.get_text(" ", strip=True)
        dt = _guess_time(text, now)
        out.append({
            "title": title,
            "url": href,
            "domain": _extract_domain(href),
            "display_url": "",
            "snippet": "",
            "attribution": "",
            "guessed_time_iso": dt.isoformat() if dt else None,
        })

    return out

def extract_bing_click_target(html: str) -> str | None:
    """
    Extract the original target URL from a Bing click/redirect HTML where a script sets:
        var u = "https://example.com/...";
    No regular expressions are used. We scan the JS text and parse the string literal.
    Returns the URL string or None if not found.
    """
    soup = BeautifulSoup(html, "html.parser")
    for sc in soup.find_all("script"):
        script_text = sc.string if sc.string is not None else sc.get_text("", strip=False)
        if not script_text:
            continue

        src = script_text
        i = 0
        n = len(src)

        while i < n:
            # Skip whitespace
            while i < n and src[i].isspace():
                i += 1
            if i >= n:
                break

            # Look for "var"
            if i + 3 <= n and src[i:i+3] == "var":
                j = i + 3
                # Skip spaces
                while j < n and src[j].isspace():
                    j += 1
                # Read identifier
                ident_start = j
                while j < n and (src[j].isalnum() or src[j] in ['_','$']):
                    j += 1
                ident = src[ident_start:j]

                while j < n and src[j].isspace():
                    j += 1

                # Only care when identifier is 'u' and followed by '='
                if ident == "u" and j < n and src[j] == "=":
                    j += 1
                    while j < n and src[j].isspace():
                        j += 1
                    if j >= n:
                        return None
                    quote = src[j]
                    if quote not in ['"', "'"]:
                        i = j + 1
                        continue
                    j += 1
                    buf: list[str] = []
                    while j < n:
                        c = src[j]
                        if c == "\\":
                            if j + 1 < n:
                                j += 1
                                buf.append(src[j])  # keep escaped char
                                j += 1
                                continue
                            else:
                                break
                        if c == quote:
                            return "".join(buf)
                        buf.append(c)
                        j += 1
                    i = j + 1
                    continue
                else:
                    i = j + 1
                    continue
            else:
                i += 1
    return None
