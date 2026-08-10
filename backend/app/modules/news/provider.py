"""
News provider — abstracts Finnhub and provides Indian company news via market news + filtering.
"""
import logging
import json
from datetime import date, timedelta
from typing import Optional, List

import httpx
import redis as sync_redis
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("news_provider")

FINNHUB_BASE = "https://finnhub.io/api/v1"


class NewsProvider:
    """Unified news provider for market and company news."""

    def __init__(self):
        self._api_key = (settings.FINNHUB_API_KEY or "").strip()
        self._configured = bool(self._api_key)
        self._http = httpx.Client(timeout=15.0)
        self._redis = sync_redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        if not self._configured:
            logger.warning("FINNHUB_API_KEY not set — news will be unavailable.")

    @property
    def is_configured(self) -> bool:
        return self._configured

    def _headers(self) -> dict:
        return {"X-Finnhub-Token": self._api_key}

    def get_market_news(self, category: str = "general", min_id: int = 0) -> list[dict]:
        """Fetch market news from Finnhub."""
        if not self._configured:
            return []
        try:
            resp = self._http.get(
                f"{FINNHUB_BASE}/news",
                params={"category": category, "token": self._api_key, "minId": min_id},
            )
            resp.raise_for_status()
            return resp.json() or []
        except Exception as e:
            logger.error(f"Market news fetch failed ({category}): {e}")
            return []

    def search_company_news(self, symbol: str, days_back: int = 30, limit: int = 50) -> list[dict]:
        """Get company-specific news for Indian stocks.

        Strategy:
        1. Try Finnhub company-news endpoint (may work for some ADR-listed Indian stocks)
        2. Fetch market news with category='general' and filter by symbol/company name
        3. Search news by keyword matching company name
        """
        if not self._configured:
            return []

        symbol = symbol.upper()
        results = []

        # Attempt 1: Finnhub company news (works for US-listed stocks, rarely for Indian)
        company_news = self._fetch_company_news_direct(symbol, days_back)
        if company_news:
            results.extend(self._normalize_articles(company_news, "FINNHUB_COMPANY", symbol))

        # Attempt 2: Market news filtered by symbol
        if len(results) < limit:
            market_news = self.get_market_news("general", 0)
            filtered = self._filter_by_symbol(market_news, symbol)
            results.extend(self._normalize_articles(filtered, "FINNHUB_MARKET", symbol))

        # Attempt 3: Try additional market categories
        for cat in ["forex", "merger"]:
            if len(results) >= limit:
                break
            extra = self.get_market_news(cat, 0)
            filtered = self._filter_by_symbol(extra, symbol)
            if filtered:
                results.extend(self._normalize_articles(filtered, f"FINNHUB_{cat.upper()}", symbol))

        # Deduplicate by headline
        seen = set()
        unique = []
        for r in results:
            if r["headline"] not in seen:
                seen.add(r["headline"])
                unique.append(r)
                if len(unique) >= limit:
                    break

        return unique

    def search_company_news_named(self, company_name: str, limit: int = 50) -> list[dict]:
        """Search for company news by company name (not just symbol)."""
        if not self._configured or not company_name:
            return []

        all_news = self.get_market_news("general", 0)
        name_lower = company_name.lower()
        name_words = set(name_lower.split())
        name_words.discard("ltd")
        name_words.discard("limited")
        name_words.discard("ltd.")
        name_words.discard("inc")
        name_words.discard("inc.")

        results = []
        for article in all_news:
            headline = (article.get("headline") or "").lower()
            summary = (article.get("summary") or "").lower()
            # Check if at least 1 significant word matches
            text = headline + " " + summary
            matches = sum(1 for w in name_words if w in text)
            if matches >= 1:
                results.append(self._normalize_single(article, "FINNHUB_MARKET", company_name.upper()))

        seen = set()
        unique = []
        for r in sorted(results, key=lambda x: x.get("published_at", ""), reverse=True):
            if r["headline"] not in seen:
                seen.add(r["headline"])
                unique.append(r)
                if len(unique) >= limit:
                    break
        return unique

    def get_all_market_news(self, categories: list[str] = None, limit: int = 100) -> list[dict]:
        """Get all market news across multiple categories."""
        if categories is None:
            categories = ["general", "forex", "merger"]
        all_articles = []
        for cat in categories:
            news = self.get_market_news(cat, 0)
            all_articles.extend(self._normalize_articles(news, f"FINNHUB_{cat.upper()}", None))
        seen = set()
        unique = []
        for r in all_articles:
            if r["headline"] not in seen:
                seen.add(r["headline"])
                unique.append(r)
                if len(unique) >= limit:
                    break
        return unique

    def _fetch_company_news_direct(self, symbol: str, days_back: int) -> list[dict]:
        """Try Finnhub company-news endpoint (mostly US stocks)."""
        try:
            to_date = date.today()
            from_date = to_date - timedelta(days=days_back)
            resp = self._http.get(
                f"{FINNHUB_BASE}/company-news",
                params={"symbol": symbol, "from": from_date.isoformat(), "to": to_date.isoformat(), "token": self._api_key},
            )
            resp.raise_for_status()
            return resp.json() or []
        except Exception:
            return []

    def _filter_by_symbol(self, articles: list[dict], symbol: str) -> list[dict]:
        """Filter market news articles that mention the given symbol."""
        symbol = symbol.upper()
        filtered = []
        for a in articles:
            headline = (a.get("headline") or "").upper()
            summary = (a.get("summary") or "").upper()
            related = a.get("related", "") or ""
            if symbol in headline or symbol in summary or symbol in str(related).upper():
                filtered.append(a)
        return filtered

    def _normalize_articles(self, articles: list[dict], source: str, symbol: str | None) -> list[dict]:
        return [self._normalize_single(a, source, symbol) for a in articles]

    def _normalize_single(self, article: dict, source: str, symbol: str | None) -> dict:
        return {
            "id": article.get("id", hash(article.get("headline", ""))),
            "source": article.get("source", source),
            "provider": source,
            "headline": article.get("headline", ""),
            "summary": article.get("summary", ""),
            "url": article.get("url", ""),
            "image_url": article.get("image", ""),
            "published_at": _parse_ts(article.get("datetime")),
            "symbol": symbol,
            "category": "company" if symbol else "market",
        }


def _parse_ts(unix_ts) -> Optional[date]:
    if not unix_ts:
        return None
    from datetime import datetime, timezone
    try:
        return datetime.fromtimestamp(unix_ts, tz=timezone.utc)
    except Exception:
        return None


_news_provider: Optional[NewsProvider] = None


def get_news_provider() -> NewsProvider:
    global _news_provider
    if _news_provider is None:
        _news_provider = NewsProvider()
    return _news_provider
