"""Web Scraper tool: search via Tavily or SerperDev, then scrape the result pages."""
from __future__ import annotations

import os
import re

import requests
from bs4 import BeautifulSoup
from crewai.tools import tool

TIMEOUT = 15
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MarketResearchCrew/1.0)"}


def resolve_provider(preferred: str | None = None) -> str:
    """Pick the search provider, falling back to whichever API key is available."""
    preferred = (preferred or os.getenv("SEARCH_PROVIDER", "tavily")).lower()
    has = {"tavily": bool(os.getenv("TAVILY_API_KEY")), "serper": bool(os.getenv("SERPER_API_KEY"))}
    if has.get(preferred):
        return preferred
    for name, available in has.items():
        if available:
            return name
    raise RuntimeError("No search API key configured. Set TAVILY_API_KEY or SERPER_API_KEY in .env.")


def search_web(query: str, max_results: int = 3, provider: str | None = None) -> list[dict]:
    """Return normalised results: [{title, url, snippet}, ...]."""
    provider = resolve_provider(provider)
    if provider == "tavily":
        resp = requests.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}"},
            json={"query": query, "max_results": max_results},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
            for r in resp.json().get("results", [])[:max_results]
        ]

    resp = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": os.environ["SERPER_API_KEY"], "Content-Type": "application/json"},
        json={"q": query, "num": max_results},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return [
        {"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")}
        for r in resp.json().get("organic", [])[:max_results]
    ]


def extract_text(html: str, max_chars: int = 2500) -> str:
    """Strip scripts/styles/navigation and return readable page text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "svg"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()
    return text[:max_chars]


def scrape_url(url: str, max_chars: int = 2500) -> str:
    """Download a page and return its cleaned text (errors are returned, not raised)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return extract_text(resp.text, max_chars)
    except Exception as exc:
        return f"[scrape failed: {exc}]"


def search_and_scrape(query: str, max_results: int = 3, max_chars: int = 2500) -> str:
    """Search, scrape every hit and return a Markdown digest with source URLs."""
    results = search_web(query, max_results=max_results)
    if not results:
        return f"No results found for query: {query}"
    blocks = []
    for i, r in enumerate(results, start=1):
        page_text = scrape_url(r["url"], max_chars) if r["url"] else ""
        body = page_text if page_text and not page_text.startswith("[scrape failed") else r["snippet"]
        blocks.append(f"## Result {i}: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}\nPage text: {body}")
    return "\n\n".join(blocks)


@tool("Web Market Research Scraper")
def web_research(query: str) -> str:
    """Search the web (Tavily or SerperDev) for the query and scrape the top result pages.
    Returns a Markdown digest containing titles, URLs, snippets and page text.
    Input: query - a focused search query, e.g. 'Nvidia Q3 2025 revenue net income'."""
    try:
        return search_and_scrape(query)
    except Exception as exc:
        return f"ERROR: web research failed for '{query}': {exc}"
