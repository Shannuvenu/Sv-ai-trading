"""
News routes — MarketAux (primary, free Indian stock news) + Finnhub (fallback, global).
Requires MARKETAUX_API_KEY in .env — get a free key at https://www.marketaux.com/
"""
import logging
import time as _time
from fastapi import APIRouter, Depends, Query
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.news.marketaux_client import get_marketaux_client
from app.modules.news.provider import get_news_provider as get_finnhub_provider

router = APIRouter(prefix="/news", tags=["News"])
logger = logging.getLogger("news_routes")
CACHE_TTL = 300

cache: dict[str, tuple[list[dict], float]] = {}


def _cached(key: str, ttl: int, fetch_fn):
    now = _time.time()
    if key in cache:
        data, ts = cache[key]
        if now - ts < ttl:
            return data
    data = fetch_fn()
    cache[key] = (data, now)
    return data


def _to_response(articles: list[dict], page: int, page_size: int) -> dict:
    items = []
    for a in articles:
        items.append({
            "id": hash(a.get("headline", "")),
            "headline": a.get("headline", ""),
            "summary": a.get("summary") or "",
            "source": a.get("source", ""),
            "url": a.get("url") or "",
            "image_url": a.get("image_url") or "",
            "published_at": a.get("published_at"),
            "sentiment": a.get("sentiment"),
            "category": a.get("category", ""),
            "symbol": a.get("symbol"),
        })
    start = (page - 1) * page_size
    return {"items": items[start:start + page_size], "page": page, "page_size": page_size, "total": len(items)}


def _get_news(symbol: str, limit: int = 30) -> list[dict]:
    results = []
    marketaux = get_marketaux_client()
    if marketaux.is_configured:
        try:
            news = marketaux.get_company_news(symbol, limit=max(limit, 50))
            for a in news:
                a["category"] = "company"
                a["symbol"] = symbol.upper()
            results = news
        except Exception as e:
            logger.error(f"MarketAux failed for {symbol}: {e}")
    if not results:
        finnhub = get_finnhub_provider()
        if finnhub.is_configured:
            news = finnhub.search_company_news(symbol, days_back=30, limit=limit)
            for a in news:
                a["category"] = "company"
                a["symbol"] = symbol.upper()
            results = news
    return results


@router.get("/company/{symbol}")
def get_company_news(
    symbol: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    symbol = symbol.upper()
    articles = _cached(f"news:company:{symbol}", CACHE_TTL, lambda: _get_news(symbol, 50))
    return _to_response(articles, page, page_size)


@router.get("/market")
def get_market_news(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    articles = []
    marketaux = get_marketaux_client()
    if marketaux.is_configured:
        articles = _cached("news:market:marketaux", CACHE_TTL, lambda: marketaux.get_market_news(100))
        for a in articles:
            a["category"] = "market"
    if not articles:
        finnhub = get_finnhub_provider()
        if finnhub.is_configured:
            news = finnhub.get_market_news("general")
            for a in news:
                a_norm = {
                    "headline": a.get("headline", ""),
                    "summary": a.get("summary", ""),
                    "source": a.get("source", ""),
                    "url": a.get("url", ""),
                    "image_url": a.get("image", ""),
                    "published_at": a.get("datetime"),
                    "category": "market",
                }
                articles.append(a_norm)
    return _to_response(articles, page, page_size)


@router.get("/search")
def search_news(
    q: str = Query(..., min_length=2),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    q = q.strip()
    articles = _cached(f"news:search:{q[:50]}", CACHE_TTL, lambda: _search_news(q, 50))
    return _to_response(articles, page, page_size)


def _search_news(query: str, limit: int = 50) -> list[dict]:
    results = []
    marketaux = get_marketaux_client()
    if marketaux.is_configured:
        try:
            results = marketaux.search_news(query, limit=limit)
            for a in results:
                a["category"] = "search"
        except Exception as e:
            logger.error(f"MarketAux search failed: {e}")
    return results
