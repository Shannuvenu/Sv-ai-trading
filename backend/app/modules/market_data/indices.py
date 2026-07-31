"""Indian market indices via Upstox. Uses the same quote endpoint as equities."""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from app.core.config import get_settings
from app.modules.market_data.provider import Quote

settings = get_settings()
logger = logging.getLogger("indices")

NSE_INDICES = {
    "NIFTY_50": {"key": "NSE_INDEX|Nifty 50", "name": "NIFTY 50"},
    "NIFTY_BANK": {"key": "NSE_INDEX|Nifty Bank", "name": "BANK NIFTY"},
    "NIFTY_IT": {"key": "NSE_INDEX|Nifty IT", "name": "NIFTY IT"},
    "NIFTY_AUTO": {"key": "NSE_INDEX|Nifty Auto", "name": "NIFTY AUTO"},
    "NIFTY_FMCG": {"key": "NSE_INDEX|Nifty FMCG", "name": "NIFTY FMCG"},
    "NIFTY_PHARMA": {"key": "NSE_INDEX|Nifty Pharma", "name": "NIFTY PHARMA"},
    "NIFTY_METAL": {"key": "NSE_INDEX|Nifty Metal", "name": "NIFTY METAL"},
    "NIFTY_REALTY": {"key": "NSE_INDEX|Nifty Realty", "name": "NIFTY REALTY"},
    "NIFTY_MIDCAP_100": {"key": "NSE_INDEX|Nifty Midcap 100", "name": "MIDCAP 100"},
    "NIFTY_SMALLCAP_100": {"key": "NSE_INDEX|Nifty Smallcap 100", "name": "SMALLCAP 100"},
    "SENSEX": {"key": "BSE_INDEX|SENSEX", "name": "SENSEX"},
    "INDIA_VIX": {"key": "NSE_INDEX|INDIA VIX", "name": "INDIA VIX"},
}

IDX_TO_SYMBOL = {v["key"]: k for k, v in NSE_INDICES.items()}


def get_indices_provider():
    from app.modules.market_data.upstox_provider import get_upstox_provider
    return get_upstox_provider()


def fetch_index_quotes() -> list[dict]:
    """Fetch all configured indices from Upstox."""
    provider = get_indices_provider()
    if not provider or not provider._configured:
        return []

    keys = [v["key"] for v in NSE_INDICES.values()]
    url_key = ",".join(k.replace("|", "%7C") for k in keys)
    quote_url = "https://api.upstox.com/v2/market-quote/quotes"

    import httpx
    try:
        resp = provider._http.get(
            f"{quote_url}?instrument_key={url_key}",
            headers=provider._headers(),
        )
        if resp.status_code != 200:
            logger.error(f"Index quote HTTP {resp.status_code}")
            return []

        data = resp.json()
        results = []
        for name, info in NSE_INDICES.items():
            entry = data.get("data", {}).get(info["key"])
            if not entry:
                entry = data.get("data", {}).get(f"NSE_INDEX:{info['name']}")
            if entry:
                results.append({
                    "symbol": name,
                    "name": info["name"],
                    "last_price": float(entry.get("last_price", 0)),
                    "change": float(entry.get("net_change", 0)) if "net_change" in entry else 0.0,
                    "change_pct": 0.0,
                    "timestamp": entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "source": "UPSTOX",
                })
        return results
    except Exception as e:
        logger.error(f"Index fetch error: {e}")
        return []
