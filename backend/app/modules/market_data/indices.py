"""
Market indices via Upstox. Fetches individually to handle index key format.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger("indices")

NSE_INDICES = {
    "NIFTY_50": {"key": "NSE_INDEX|Nifty 50", "name": "NIFTY 50"},
    "NIFTY_BANK": {"key": "NSE_INDEX|Nifty Bank", "name": "BANK NIFTY"},
    "SENSEX": {"key": "BSE_INDEX|SENSEX", "name": "SENSEX"},
}

IDX_TO_SYMBOL = {v["key"]: k for k, v in NSE_INDICES.items()}


def fetch_index_quotes() -> list[dict]:
    from app.modules.market_data.upstox_provider import get_upstox_provider
    provider = get_upstox_provider()
    if not provider or not provider._configured:
        return []

    quote_url = "https://api.upstox.com/v2/market-quote/quotes"
    results = []

    for name, info in NSE_INDICES.items():
        try:
            key = info["key"].replace("|", "%7C")
            resp = provider._http.get(
                f"{quote_url}?instrument_key={key}",
                headers=provider._headers(),
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            entry = data.get("data", {}).get(info["key"])
            if not entry:
                for k, v in data.get("data", {}).items():
                    if info["name"].lower().replace(" ", "") in k.lower().replace(" ", ""):
                        entry = v
                        break
            if entry:
                change = float(entry.get("net_change", entry.get("change", 0) or 0))
                results.append({
                    "symbol": name, "name": info["name"],
                    "last_price": float(entry.get("last_price", 0)),
                    "change": change,
                    "change_pct": 0.0,
                    "timestamp": entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "source": "UPSTOX",
                })
        except Exception as e:
            logger.error(f"Index fetch error {name}: {e}")

    return results
