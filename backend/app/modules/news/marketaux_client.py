"""
MarketAux news provider — free API with Indian stock market news, entity tagging, and sentiment.
Sign up at https://www.marketaux.com/ to get a free API key.
Set MARKETAUX_API_KEY in .env.
"""
import logging
import json
from typing import Optional, List
import httpx
import redis as sync_redis
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("marketaux_news")

MARKETAUX_BASE = "https://api.marketaux.com/v1"


class MarketAuxClient:
    """News provider with Indian stock market coverage."""

    def __init__(self):
        self._api_key = getattr(settings, 'MARKETAUX_API_KEY', '').strip() or ""
        self._configured = bool(self._api_key)
        if not self._configured:
            logger.warning("MARKETAUX_API_KEY not set — Indian stock news will be limited.")
        self._http = httpx.Client(timeout=15.0)
        self._redis = sync_redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    @property
    def is_configured(self) -> bool:
        return self._configured

    def _cached(self, key: str, ttl: int, fetch_fn):
        cached = self._redis.get(key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass
        data = fetch_fn()
        if data:
            try:
                self._redis.setex(key, ttl, json.dumps(data))
            except Exception:
                pass
        return data or []

    def get_company_news(self, symbol: str, limit: int = 50) -> list[dict]:
        """Get news for an Indian stock ticker. MarketAux supports entity filtering by symbol."""
        if not self._configured:
            return []

        symbol_upper = symbol.upper()
        cache_key = f"marketaux:company:{symbol_upper}"

        def fetch():
            results = []
            try:
                resp = self._http.get(
                    f"{MARKETAUX_BASE}/news/all",
                    params={
                        "symbols": f"{symbol_upper}.NS,{symbol_upper}",
                        "filter_entities": "true",
                        "limit": min(limit, 100),
                        "language": "en",
                        "api_token": self._api_key,
                    },
                )
                if resp.status_code == 429:
                    logger.warning(f"MarketAux rate limited for {symbol}")
                    return []
                if resp.status_code != 200:
                    logger.error(f"MarketAux HTTP {resp.status_code} for {symbol}")
                    return []
                data = resp.json()
                articles = data.get("data", [])
                for a in articles:
                    results.append({
                        "headline": a.get("title", ""),
                        "summary": a.get("description", "") or a.get("snippet", ""),
                        "source": a.get("source", ""),
                        "url": a.get("url", ""),
                        "image_url": a.get("image_url", ""),
                        "published_at": a.get("published_at"),
                        "entities": a.get("entities", []),
                        "sentiment": _extract_sentiment(a),
                    })
                return results
            except Exception as e:
                logger.error(f"MarketAux error for {symbol}: {e}")
                return []
        return self._cached(cache_key, 900, fetch)

    def get_market_news(self, limit: int = 100) -> list[dict]:
        """Get general Indian market news."""
        if not self._configured:
            return []
        cache_key = "marketaux:indian_market"

        def fetch():
            results = []
            try:
                # Indian market-focused entities
                symbols = "NIFTY50.NS,SENSEX.BO,NIFTY_BANK.NS"
                resp = self._http.get(
                    f"{MARKETAUX_BASE}/news/all",
                    params={
                        "symbols": symbols,
                        "filter_entities": "true",
                        "limit": min(limit, 100),
                        "language": "en",
                        "api_token": self._api_key,
                    },
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
                for a in data.get("data", []):
                    results.append({
                        "headline": a.get("title", ""),
                        "summary": a.get("description", "") or a.get("snippet", ""),
                        "source": a.get("source", ""),
                        "url": a.get("url", ""),
                        "image_url": a.get("image_url", ""),
                        "published_at": a.get("published_at"),
                        "entities": a.get("entities", []),
                        "sentiment": _extract_sentiment(a),
                    })
                return results
            except Exception as e:
                logger.error(f"MarketAux market news error: {e}")
                return []
        return self._cached(cache_key, 600, fetch)

    def search_news(self, query: str, limit: int = 50) -> list[dict]:
        """Search news by keyword."""
        if not self._configured:
            return []
        cache_key = f"marketaux:search:{query[:50]}"

        def fetch():
            results = []
            try:
                resp = self._http.get(
                    f"{MARKETAUX_BASE}/news/all",
                    params={
                        "search": query,
                        "filter_entities": "true",
                        "limit": min(limit, 100),
                        "language": "en",
                        "api_token": self._api_key,
                    },
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
                for a in data.get("data", []):
                    results.append({
                        "headline": a.get("title", ""),
                        "summary": a.get("description", "") or a.get("snippet", ""),
                        "source": a.get("source", ""),
                        "url": a.get("url", ""),
                        "image_url": a.get("image_url", ""),
                        "published_at": a.get("published_at"),
                        "entities": a.get("entities", []),
                        "sentiment": _extract_sentiment(a),
                    })
                return results
            except Exception as e:
                logger.error(f"MarketAux search error for '{query}': {e}")
                return []
        return self._cached(cache_key, 600, fetch)


def _extract_sentiment(article: dict) -> dict | None:
    entities = article.get("entities", [])
    if not entities:
        return None
    scores = [e.get("sentiment_score", 0) or 0 for e in entities]
    avg = sum(scores) / len(scores) if scores else 0
    return {
        "score": round(avg, 3),
        "label": "positive" if avg > 0.1 else "negative" if avg < -0.1 else "neutral",
    }


_client: Optional[MarketAuxClient] = None


def get_marketaux_client() -> MarketAuxClient:
    global _client
    if _client is None:
        _client = MarketAuxClient()
    return _client
