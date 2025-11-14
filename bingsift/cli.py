from __future__ import annotations
import argparse, json, sys
from .parser import parse_html, build_bing_url, extract_bing_click_target
from .filters import filter_results
from .net import fetch_serp_by_query, fetch_serp_by_url, fetch_click_and_extract

def main():
    parser = argparse.ArgumentParser(
        prog="bingsift",
        description="Parse/filter Bing SERP HTML, build URLs, extract click targets, and fetch over the network."
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # parse (local file)
    p_parse = subparsers.add_parser("parse", help="Parse a saved Bing SERP HTML file")
    p_parse.add_argument("html_path", help="Path to a saved bing.com/search HTML")
    p_parse.add_argument("--out", help="Output JSON path (default: stdout)")
    p_parse.add_argument("--include", nargs="*", help="Keywords that must appear (title+snippet)")
    p_parse.add_argument("--exclude", nargs="*", help="Keywords that must not appear")
    p_parse.add_argument("--allow-domain", dest="allow_domain", nargs="*", help="Only keep domains in this set")
    p_parse.add_argument("--deny-domain", dest="deny_domain", nargs="*", help="Drop domains in this set")

    # url builder
    p_url = subparsers.add_parser("url", help="Build a Bing URL with filters")
    p_url.add_argument("query", help="Query text")
    p_url.add_argument("--when", choices=["day", "week", "month", "year"], help="Freshness filter")
    p_url.add_argument("--site", help="Restrict to site:domain")
    p_url.add_argument("--lang", help="setlang (e.g., en-GB)")
    p_url.add_argument("--country", help="mkt & cc (e.g., en-GB)")
    p_url.add_argument("--safe", action="store_true", help="Set adlt=off")

    # click extractor (local file)
    p_click = subparsers.add_parser("bingclick", help="Extract 'var u = ...' target from a Bing click HTML (prints URL)")
    p_click.add_argument("html_path", help="Path to the Bing click HTML")

    # --- network-enabled ---
    p_fetch_parse = subparsers.add_parser("fetch-parse", help="Fetch a Bing SERP by query or URL, then parse and output JSON")
    g = p_fetch_parse.add_mutually_exclusive_group(required=True)
    g.add_argument("--query", help="Query string to build a Bing URL and fetch")
    g.add_argument("--url", help="Explicit Bing SERP URL to fetch")
    p_fetch_parse.add_argument("--when", choices=["day", "week", "month", "year"])
    p_fetch_parse.add_argument("--site")
    p_fetch_parse.add_argument("--lang")
    p_fetch_parse.add_argument("--country")
    p_fetch_parse.add_argument("--safe", action="store_true")
    p_fetch_parse.add_argument("--include", nargs="*", help="Keywords that must appear (title+snippet)")
    p_fetch_parse.add_argument("--exclude", nargs="*", help="Keywords that must not appear")
    p_fetch_parse.add_argument("--allow-domain", dest="allow_domain", nargs="*", help="Only keep domains in this set")
    p_fetch_parse.add_argument("--deny-domain", dest="deny_domain", nargs="*", help="Drop domains in this set")
    p_fetch_parse.add_argument("--out")
    p_fetch_parse.add_argument("--timeout", type=float, default=12.0)
    p_fetch_parse.add_argument("--retries", type=int, default=2)
    p_fetch_parse.add_argument("--delay", type=float, default=1.0)
    p_fetch_parse.add_argument("--ua")
    p_fetch_parse.add_argument("--proxy")

    p_fetch_click = subparsers.add_parser("fetch-click", help="Fetch a Bing click URL and print the original destination")
    p_fetch_click.add_argument("click_url")
    p_fetch_click.add_argument("--timeout", type=float, default=12.0)
    p_fetch_click.add_argument("--retries", type=int, default=2)
    p_fetch_click.add_argument("--delay", type=float, default=1.0)
    p_fetch_click.add_argument("--ua")
    p_fetch_click.add_argument("--proxy")

    args = parser.parse_args()

    if args.cmd == "parse":
        with open(args.html_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        rows = parse_html(html)
        rows = filter_results(rows, include=args.include, exclude=args.exclude,
                              allow_domains=args.allow_domain, deny_domains=args.deny_domain)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=2)
        else:
            json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)

    elif args.cmd == "url":
        print(build_bing_url(args.query, when=args.when, site=args.site, lang=args.lang,
                             country=args.country, safe=args.safe))

    elif args.cmd == "bingclick":
        with open(args.html_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        url = extract_bing_click_target(html)
        if url:
            print(url)
        else:
            sys.exit(1)

    elif args.cmd == "fetch-parse":
        headers = {"User-Agent": args.ua} if args.ua else None
        if args.query:
            rows = fetch_serp_by_query(query=args.query, when=args.when, site=args.site, lang=args.lang,
                                       country=args.country, safe=args.safe,
                                       include=args.include, exclude=args.exclude,
                                       allow_domains=args.allow_domain, deny_domains=args.deny_domain,
                                       timeout=args.timeout, retries=args.retries, delay=args.delay,
                                       headers=headers, proxy=args.proxy)
        else:
            rows = fetch_serp_by_url(args.url, include=args.include, exclude=args.exclude,
                                     allow_domains=args.allow_domain, deny_domains=args.deny_domain,
                                     timeout=args.timeout, retries=args.retries, delay=args.delay,
                                     headers=headers, proxy=args.proxy)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=2)
        else:
            json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)

    elif args.cmd == "fetch-click":
        headers = {"User-Agent": args.ua} if args.ua else None
        url = fetch_click_and_extract(args.click_url, timeout=args.timeout, retries=args.retries,
                                      delay=args.delay, headers=headers, proxy=args.proxy)
        if url:
            print(url)
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()
