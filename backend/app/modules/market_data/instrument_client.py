"""
Upstox master instruments — fetches real instrument universe from Upstox API.
Caches in Redis with 24h TTL since instruments change rarely.
"""
import json
import logging
from typing import Optional
import time

import httpx
import redis as sync_redis
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("upstox_instruments")
INST_CACHE_TTL = 86400  # 24 hours

BASE_URL = "https://api.upstox.com/v2"


class UpstoxInstrumentClient:
    """Fetches instrument master data from Upstox and caches in Redis."""

    def __init__(self):
        self._access_token = settings.UPSTOX_ACCESS_TOKEN.strip()
        self._configured = bool(self._access_token)
        self._http = httpx.Client(timeout=30.0)
        self._redis = sync_redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    @property
    def is_configured(self) -> bool:
        return self._configured

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}", "Accept": "application/json"}

    def _cached_fetch(self, cache_key: str, fetch_fn, ttl: int = INST_CACHE_TTL, force: bool = False) -> list[dict]:
        if not force:
            cached = self._redis.get(cache_key)
            if cached:
                try:
                    return json.loads(cached)
                except json.JSONDecodeError:
                    pass
        data = fetch_fn()
        if data:
            try:
                self._redis.setex(cache_key, ttl, json.dumps(data))
            except Exception:
                pass
        return data or []

    def _download_instrument_file(self, otype: str) -> list[dict]:
        """Download and parse Upstox gzipped JSON instrument file."""
        import gzip
        import json
        try:
            url = f"https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz?otype={otype}"
            resp = self._http.get(url, timeout=60.0)
            if resp.status_code != 200:
                logger.error(f"Instrument download {otype} HTTP {resp.status_code}")
                return []
            data = gzip.decompress(resp.content)
            items = json.loads(data)
            if not isinstance(items, list):
                return []
            result = [
                {
                    "trading_symbol": item.get("trading_symbol", ""),
                    "name": item.get("name", ""),
                    "exchange": item.get("exchange", ""),
                    "segment": item.get("segment", ""),
                    "instrument_key": item.get("instrument_key", ""),
                    "isin": item.get("isin", ""),
                    "instrument_type": item.get("instrument_type", ""),
                    "lot_size": item.get("lot_size", 1),
                    "tick_size": item.get("tick_size", 0.05),
                    "expiry": item.get("expiry", ""),
                    "strike": item.get("strike", 0),
                    "underlying_symbol": item.get("underlying_symbol", ""),
                }
                for item in items
            ]
            logger.info(f"Loaded {len(result)} instruments for {otype}")
            return result
        except Exception as e:
            logger.error(f"Instrument download error {otype}: {e}")
            return []

    def get_all_equities(self, exchange: str = "NSE", force: bool = False) -> list[dict]:
        """Get all equity instruments from NSE or BSE."""
        cache_key = f"upstox:instruments:{exchange}_EQ"
        otype = "NSE" if exchange.upper() == "NSE" else "BSE"
        return self._cached_fetch(cache_key, lambda: self._download_instrument_file(otype), INST_CACHE_TTL, force)

    def get_fo_instruments(self, force: bool = False) -> list[dict]:
        """Get all F&O instruments."""
        cache_key = "upstox:instruments:NSE_FO"
        return self._cached_fetch(cache_key, lambda: self._download_instrument_file("NSE_FO"), INST_CACHE_TTL, force)

    def get_index_instruments(self, force: bool = False) -> list[dict]:
        """Get all index instruments from NSE and BSE."""
        cache_key = "upstox:instruments:indices"

        def fetch():
            results = []
            for otype in ["NSE_INDEX", "BSE_INDEX"]:
                data = self._download_instrument_file(otype)
                results.extend(data)
            return results

        return self._cached_fetch(cache_key, fetch, INST_CACHE_TTL, force)

    def search_all(self, query: str) -> list[dict]:
        if not self._configured or len(query) < 2:
            return []
        q = query.upper()
        nse = self.get_all_equities("NSE")
        bse = self.get_all_equities("BSE")
        all_inst = nse + bse
        equity_segments = {"nse_eq", "bse_eq"}
        seen = set()
        results = []
        for i in all_inst:
            seg = (i.get("segment") or "").lower()
            if seg not in equity_segments:
                continue
            sym = (i.get("trading_symbol") or "").upper()
            name = (i.get("name") or "").upper()
            isin = (i.get("isin") or "").upper()
            if q in sym or q in name or q in isin:
                key = i.get("instrument_key", "")
                if key and key not in seen:
                    seen.add(key)
                    results.append({
                        "trading_symbol": i.get("trading_symbol", ""),
                        "name": i.get("name", ""),
                        "exchange": i.get("exchange", ""),
                        "segment": i.get("segment", ""),
                        "instrument_key": i.get("instrument_key", ""),
                        "isin": i.get("isin", ""),
                        "instrument_type": i.get("instrument_type", "equity"),
                        "lot_size": i.get("lot_size", 1),
                        "tick_size": i.get("tick_size", 0.05),
                    })
                    if len(results) >= 50:
                        return results
        return results

    def get_mtf_eligible(self, force: bool = False) -> list[dict]:
        """Get MTF-eligible stocks."""
        nse = self.get_all_equities("NSE", force)
        return [
            {
                "trading_symbol": i.get("trading_symbol", ""),
                "name": i.get("name", ""),
                "exchange": i.get("exchange", ""),
                "instrument_key": i.get("instrument_key", ""),
                "isin": i.get("isin", ""),
                "lot_size": i.get("lot_size", 1),
            }
            for i in nse
            if isinstance(i, dict) and i.get("is_mtf_eligible")
        ]

    def get_instrument_by_key(self, instrument_key: str) -> dict | None:
        """Get a single instrument by its key."""
        all_equities = self.get_all_equities("NSE") + self.get_all_equities("BSE")
        for i in all_equities:
            if i.get("instrument_key") == instrument_key:
                return i
        return None

    def get_instrument_by_symbol(self, symbol: str, exchange: str = "NSE") -> dict | None:
        """Get instrument info by trading symbol."""
        equities = self.get_all_equities(exchange)
        symbol = symbol.upper()
        for i in equities:
            if (i.get("trading_symbol") or "").upper() == symbol:
                return i
        return None

    def get_symbol_map(self, exchange: str = "NSE") -> dict:
        """Build symbol -> instrument_key mapping."""
        equities = self.get_all_equities(exchange)
        return {
            i.get("trading_symbol", "").upper(): i.get("instrument_key", "")
            for i in equities if i.get("trading_symbol")
        }

    def get_quote_batch(self, symbols: list[str], exchange: str = "NSE") -> dict:
        """Get quotes for multiple symbols."""
        if not self._configured or not symbols:
            return {}

        # Build instrument keys
        sym_map = self.get_symbol_map(exchange)
        keys = []
        key_to_sym = {}
        for s in symbols:
            k = sym_map.get(s.upper())
            if k:
                keys.append(k)
                key_to_sym[k] = s.upper()

        if not keys:
            return {}

        # Batch query
        key_param = ",".join(k.replace("|", "%7C") for k in keys[:200])
        try:
            resp = self._http.get(
                f"{BASE_URL}/market-quote/quotes?instrument_key={key_param}",
                headers=self._headers(),
            )
            if resp.status_code != 200:
                return {}
            data = resp.json()
            data_map = data.get("data", {})
            result = {}
            for k in keys:
                entry = data_map.get(k) or data_map.get(f"NSE_EQ:{key_to_sym.get(k, '')}")
                if entry:
                    sym = key_to_sym.get(k, "")
                    last = float(entry.get("last_price", 0))
                    ohlc = entry.get("ohlc", {})
                    prev = float(ohlc.get("close", last))
                    chg = last - prev
                    chg_pct = (chg / prev * 100) if prev > 0 else 0
                    result[sym] = {
                        "symbol": sym,
                        "name": "",  # will be filled from search
                        "last_price": last,
                        "open": float(ohlc.get("open", 0)),
                        "high": float(ohlc.get("high", 0)),
                        "low": float(ohlc.get("low", 0)),
                        "close": prev,
                        "change": round(chg, 2),
                        "change_pct": round(chg_pct, 2),
                        "volume": int(entry.get("volume", 0)),
                        "source": "UPSTOX",
                    }
            return result
        except Exception as e:
            logger.error(f"Batch quote error: {e}")
            return {}


    def get_ipo_list(self) -> list[dict]:
        """Get IPO list from Upstox."""
        if not self._configured:
            return []
        cache_key = "upstox:ipos"
        cached = self._redis.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass
        try:
            resp = self._http.get(
                f"{BASE_URL}/ipo/get-ipo-list",
                headers=self._headers(),
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            ipos = data.get("data", [])
            if ipos:
                try:
                    self._redis.setex(cache_key, 3600, json.dumps(ipos))  # 1 hour
                except Exception:
                    pass
            return ipos if isinstance(ipos, list) else []
        except Exception as e:
            logger.error(f"IPO fetch error: {e}")
            return []

    def get_mf_instruments(self, force: bool = False) -> list[dict]:
        """Get mutual fund instruments."""
        cache_key = "upstox:mf:instruments"
        if not force:
            cached = self._redis.get(cache_key)
            if cached:
                try:
                    return json.loads(cached)
                except json.JSONDecodeError:
                    pass
        try:
            resp = self._http.get(
                f"{BASE_URL}/mf/instruments",
                headers=self._headers(),
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            instruments = data.get("data", [])
            if instruments:
                try:
                    self._redis.setex(cache_key, INST_CACHE_TTL, json.dumps(instruments))
                except Exception:
                    pass
            return instruments if isinstance(instruments, list) else []
        except Exception as e:
            logger.error(f"MF instruments error: {e}")
            return []

    def get_sip_registrations(self) -> list[dict]:
        """Get existing SIP registrations from Upstox."""
        if not self._configured:
            return []
        try:
            resp = self._http.get(
                f"{BASE_URL}/sip/get-sip-registrations",
                headers=self._headers(),
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            return data.get("data", []) if isinstance(data.get("data", []), list) else []
        except Exception as e:
            logger.error(f"SIP fetch error: {e}")
            return []


_client: Optional[UpstoxInstrumentClient] = None


def get_instrument_client() -> UpstoxInstrumentClient:
    global _client
    if _client is None:
        _client = UpstoxInstrumentClient()
    return _client
