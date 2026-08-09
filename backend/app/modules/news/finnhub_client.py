"""Finnhub API client — company & market news fetch."""
import logging
from datetime import date, timedelta
import httpx
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("finnhub_client")

BASE_URL = "https://finnhub.io/api/v1"


class FinnhubClient:
    def __init__(self):
        self._api_key = settings.FINNHUB_API_KEY.strip()
        self._configured = bool(self._api_key)
        if not self._configured:
            logger.warning("FINNHUB_API_KEY not set — news module will return empty results.")
        self._http = httpx.Client(timeout=10.0)

    @property
    def is_configured(self) -> bool:
        return self._configured

    def get_company_news(self, symbol: str, days_back: int = 14) -> list[dict]:
        if not self._configured:
            return []
        to_date = date.today()
        from_date = to_date - timedelta(days=days_back)
        try:
            resp = self._http.get(
                f"{BASE_URL}/company-news",
                params={
                    "symbol": symbol,
                    "from": from_date.isoformat(),
                    "to": to_date.isoformat(),
                    "token": self._api_key,
                },
            )
            resp.raise_for_status()
            return resp.json() or []
        except httpx.HTTPError as e:
            logger.error(f"Finnhub company-news failed for {symbol}: {e}")
            return []

    def get_market_news(self, category: str = "general") -> list[dict]:
        if not self._configured:
            return []
        try:
            resp = self._http.get(
                f"{BASE_URL}/news",
                params={"category": category, "token": self._api_key},
            )
            resp.raise_for_status()
            return resp.json() or []
        except httpx.HTTPError as e:
            logger.error(f"Finnhub market-news failed ({category}): {e}")
            return []


_client: "FinnhubClient | None" = None


def get_finnhub_client() -> FinnhubClient:
    global _client
    if _client is None:
        _client = FinnhubClient()
    return _client