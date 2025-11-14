\
from __future__ import annotations

def _to_lower_list(x):
    if not x: return []
    return [s.lower() for s in x]

def filter_results(rows: list[dict], *, include: list[str] | None = None, exclude: list[str] | None = None,
                   allow_domains: list[str] | None = None, deny_domains: list[str] | None = None) -> list[dict]:
    """
    Basic in-memory filter for parsed SERP rows.
    - include: all words must appear (case-insensitive) in title+snippet
    - exclude: any word appearing will drop the row
    - allow_domains: only keep rows whose domain matches or endswith item
    - deny_domains: drop rows whose domain matches or endswith item
    """
    inc = _to_lower_list(include)
    exc = _to_lower_list(exclude)
    allow = _to_lower_list(allow_domains)
    deny = _to_lower_list(deny_domains)

    def ok(row: dict) -> bool:
        title = (row.get("title") or "").lower()
        snippet = (row.get("snippet") or "").lower()
        text = f"{title} {snippet}"
        domain = (row.get("domain") or "").lower()

        if allow and not any(domain.endswith(a) or domain == a for a in allow):
            return False
        if deny and any(domain.endswith(d) or domain == d for d in deny):
            return False
        if inc and not all(w in text for w in inc):
            return False
        if exc and any(w in text for w in exc):
            return False
        return True

    return [r for r in rows if ok(r)]
