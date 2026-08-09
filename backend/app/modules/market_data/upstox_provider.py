"""
Upstox Market Data Provider — uses raw HTTP/WebSocket (no SDK dependency).
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import httpx
import redis.asyncio as aioredis
from app.core.config import get_settings
from app.modules.market_data.provider import (
    MarketDataProvider, Quote, OHLCVBar, InstrumentInfo,
)
from app.modules.market_data.upstox_instruments import (
    UPSTOX_INSTRUMENTS, SYMBOL_TO_KEY, KEY_TO_SYMBOL,
)
from app.modules.market_data.instrument_client import get_instrument_client

settings = get_settings()
logger = logging.getLogger("upstox_provider")

QUOTE_URL = "https://api.upstox.com/v2/market-quote/quotes"
HISTORY_URL = "https://api.upstox.com/v2/historical-candle"


class UpstoxMarketDataProvider(MarketDataProvider):
    def __init__(self):
        self._access_token = settings.UPSTOX_ACCESS_TOKEN.strip()
        if not self._access_token:
            logger.warning("UPSTOX_ACCESS_TOKEN not set.")
            self._configured = False
            return
        self._configured = True
        self._http = httpx.Client(timeout=15.0)
        self._redis: Optional[aioredis.Redis] = None
        self._running = False
        self._inst_client = get_instrument_client()

        # Fallback to hardcoded list, then enrich from API
        self._instruments_list = [
            InstrumentInfo(
                symbol=i["symbol"], name=i["name"], exchange=i["exchange"],
                sector=i["sector"], instrument_type="equity", currency="INR", is_active=True,
            )
            for i in UPSTOX_INSTRUMENTS
        ]
        self._symbol_info = {i.symbol: i for i in self._instruments_list}
        self._dynamic_symbols = dict(SYMBOL_TO_KEY)

    def _resolve_key(self, symbol: str) -> str | None:
        """Get instrument key from API or fallback."""
        symbol = symbol.upper()
        if symbol in self._dynamic_symbols:
            return self._dynamic_symbols[symbol]
        # Try fetching from API
        try:
            inst = self._inst_client.get_instrument_by_symbol(symbol, "NSE")
            if inst and inst.get("instrument_key"):
                self._dynamic_symbols[symbol] = inst["instrument_key"]
                return inst["instrument_key"]
        except Exception:
            pass
        return SYMBOL_TO_KEY.get(symbol)

    async def _ensure_redis(self):
        if self._redis is None:
            self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def _get_cached_quote(self, symbol: str) -> Optional[dict]:
        await self._ensure_redis()
        data = await self._redis.get(f"market:NSE_EQ:{symbol}")
        return json.loads(data) if data else None

    async def _set_cached_quote(self, symbol: str, data: dict, ttl: int = 60):
        await self._ensure_redis()
        await self._redis.setex(f"market:NSE_EQ:{symbol}", ttl, json.dumps(data))

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }

    def get_quote(self, symbol: str) -> Quote | None:
        if not self._configured:
            return None
        symbol = symbol.upper()
        info = self._symbol_info.get(symbol)
        if not info:
            return None

        instrument_key = self._resolve_key(symbol)
        if not instrument_key:
            return None

        for attempt in range(3):
            try:
                url = f"{QUOTE_URL}?instrument_key={instrument_key.replace('|','%7C')}"
                resp = self._http.get(url, headers=self._headers())
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning(f"Quote 429 for {symbol}, retry {attempt+1} in {wait}s")
                    time.sleep(wait)
                    continue
                if resp.status_code != 200:
                    logger.error(f"Quote HTTP {resp.status_code} for {symbol}")
                    return None
                data = resp.json()
                data_map = data.get("data", {})
                entry = None
                if instrument_key in data_map:
                    entry = data_map[instrument_key]
                else:
                    alt_key = f"NSE_EQ:{symbol}"
                    entry = data_map.get(alt_key)
                if not entry:
                    logger.error(f"Quote: key not found in response for {symbol}")
                    return None

                last_price = float(entry.get("last_price", 0))
                ohlc = entry.get("ohlc", {})
                prev_close = float(ohlc.get("close", last_price))
                change = last_price - prev_close
                change_pct = (change / prev_close * 100) if prev_close > 0 else 0.0
                ts_str = entry.get("timestamp", "")
                ts = datetime.fromisoformat(ts_str) if ts_str else datetime.now(timezone.utc)

                return Quote(
                    symbol=symbol, name=info.name, exchange=info.exchange,
                    last_price=Decimal(str(last_price)),
                    change=Decimal(str(round(change, 2))),
                    change_pct=Decimal(str(round(change_pct, 2))),
                    open=Decimal(str(float(ohlc.get("open", 0)))),
                    high=Decimal(str(float(ohlc.get("high", 0)))),
                    low=Decimal(str(float(ohlc.get("low", 0)))),
                    close=Decimal(str(last_price)),
                    volume=int(entry.get("volume", 0)),
                    timestamp=ts,
                )
            except Exception as e:
                logger.error(f"Quote error {symbol}: {e}")
                return None
        return None

    def get_history(
        self, symbol: str, start: datetime | None = None, end: datetime | None = None, days: int = 252
    ) -> list[OHLCVBar]:
        if not self._configured:
            return []
        symbol = symbol.upper()
        instrument_key = self._resolve_key(symbol)
        if not instrument_key:
            return []

        if not end:
            end = datetime.now(timezone.utc)
        if not start:
            start = end - timedelta(days=days)

        to_date = end.strftime("%Y-%m-%d")
        from_date = start.strftime("%Y-%m-%d")

        try:
            url = f"{HISTORY_URL}/{instrument_key.replace('|','%7C')}/day/{to_date}/{from_date}"
            resp = self._http.get(url, headers=self._headers())
            if resp.status_code != 200:
                logger.error(f"History HTTP {resp.status_code} for {symbol}")
                return []
            data = resp.json()
            candles = data.get("data", {}).get("candles", [])
            bars = []
            for c in candles:
                if isinstance(c, list) and len(c) >= 6:
                    ts = datetime.strptime(c[0], "%Y-%m-%dT%H:%M:%S%z")
                    bars.append(OHLCVBar(
                        timestamp=ts, open=Decimal(str(c[1])),
                        high=Decimal(str(c[2])), low=Decimal(str(c[3])),
                        close=Decimal(str(c[4])), volume=int(c[5]),
                    ))
            return bars
        except Exception as e:
            logger.error(f"History error {symbol}: {e}")
            return []

    def get_all_instruments(self) -> list[InstrumentInfo]:
        return self._instruments_list

    def search_instruments(self, query: str) -> list[InstrumentInfo]:
        q = query.upper()
        return [i for i in self._instruments_list if q in i.symbol or q.upper() in i.name.upper()]

    async def fetch_quotes_async(self, symbols: list[str]):
        if not self._configured:
            return
        for symbol in symbols:
            quote = self.get_quote(symbol)
            if quote:
                await self._set_cached_quote(symbol, {
                    "symbol": symbol, "ltp": float(quote.last_price),
                    "previous_close": float(quote.close),
                    "change": float(quote.change),
                    "change_pct": float(quote.change_pct),
                    "volume": quote.volume,
                    "last_trade_time": quote.timestamp.isoformat(),
                    "last_update": datetime.now(timezone.utc).isoformat(),
                    "source": "UPSTOX",
                }, ttl=5)

    async def poll_loop(self):
        symbols = [i["symbol"] for i in UPSTOX_INSTRUMENTS]
        self._running = True
        while self._running:
            try:
                await self.fetch_quotes_async(symbols)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Poll error: {e}")
                await asyncio.sleep(5)

    async def disconnect(self):
        self._running = False
        if self._redis:
            await self._redis.close()
            self._redis = None


_upstox_provider: Optional[UpstoxMarketDataProvider] = None


def get_upstox_provider() -> Optional[UpstoxMarketDataProvider]:
    global _upstox_provider
    if _upstox_provider is None:
        _upstox_provider = UpstoxMarketDataProvider()
    return _upstox_provider
