from datetime import datetime
from tavily import TavilyClient
from wedding_planner.config import settings


def search_web(query: str, location: str, max_results: int | None = None):
    """Search the web and return source-backed snippets; price/availability are not inferred."""
    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY is not configured. Add it to your .env file.")
    data = TavilyClient(api_key=settings.tavily_api_key).search(
        query=f"{query} in {location}",
        max_results=max_results or settings.app_max_search_results,
        search_depth="advanced",
        include_answer=False,
    )
    now = datetime.utcnow().isoformat(timespec="seconds")
    results = []
    for item in data.get("results", []):
        content = item.get("content", "") or ""
        # Do not manufacture a quote. If the search snippet has no clear price, mark it unpublished.
        import re
        match = re.search(r"(?:₹|INR|Rs\\.?\\s*)[\\d,]+(?:\\s*(?:/|per)\\s*[\\w -]+)?", content, re.I)
        results.append({
            "title": item.get("title", "") or "Untitled result",
            "url": item.get("url", "") or "",
            "content": content,
            "price_text": match.group(0) if match else "Not published — request a quotation",
            "researched_at": now,
        })
    return results
