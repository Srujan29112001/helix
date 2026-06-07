"""Real-time web research for the Researcher agent.

Uses Tavily (purpose-built for AI agents) when ``TAVILY_API_KEY`` is set, and
falls back to keyless DuckDuckGo otherwise. Returns ``[{title, snippet, url}]``
and never raises — if everything fails the Researcher degrades to the LLM's own
domain knowledge.
"""

from __future__ import annotations

import os


def _tavily(query: str, key: str, k: int) -> list[dict]:
    import httpx

    r = httpx.post(
        "https://api.tavily.com/search",
        json={"api_key": key, "query": query, "max_results": k, "include_answer": False},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return [
        {"title": h.get("title", ""), "snippet": (h.get("content", "") or "")[:240], "url": h.get("url", "")}
        for h in data.get("results", [])[:k]
    ]


def _ddg(query: str, k: int) -> list[dict]:
    from ddgs import DDGS  # keyless DuckDuckGo (pip: ddgs)

    out: list[dict] = []
    with DDGS() as d:
        for h in d.text(query, max_results=k):
            out.append({
                "title": h.get("title", ""),
                "snippet": (h.get("body", "") or "")[:240],
                "url": h.get("href", ""),
            })
    return out


def web_research(queries: list[str], k: int = 5) -> list[dict]:
    """Return up to ``k`` web results for the first query that yields hits."""
    key = os.getenv("TAVILY_API_KEY")
    for q in queries:
        if not q or not q.strip():
            continue
        try:
            hits = _tavily(q, key, k) if key else _ddg(q, k)
        except Exception:  # noqa: BLE001 — network / rate-limit / missing dep
            hits = []
        if hits:
            return hits
    return []
