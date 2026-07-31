"""Data source utilities and caching."""
from datetime import datetime, timezone
from typing import Optional
import pytz

IST = pytz.timezone("Asia/Kolkata")
MARKET_OPEN = 9 * 60 + 15  # 9:15 AM IST
MARKET_CLOSE = 15 * 60 + 30  # 3:30 PM IST


def get_market_status() -> str:
    """Determine if NSE is currently open."""
    now = datetime.now(IST)
    if now.weekday() >= 5:  # Saturday or Sunday
        return "CLOSED"
    minutes = now.hour * 60 + now.minute
    if MARKET_OPEN <= minutes < MARKET_CLOSE:
        return "OPEN"
    return "CLOSED"


def get_data_source_label(quote: dict) -> str:
    """Return a human-readable data source label."""
    source = quote.get("data_source", quote.get("source", "UNKNOWN"))
    if source == "UPSTOX":
        status = get_market_status()
        return f"LIVE · {status}" if status == "OPEN" else f"CLOSED · {source}"
    if source == "CACHED":
        return f"CACHED · {source}"
    if source == "SIMULATED":
        return "SIMULATED"
    return "UNAVAILABLE"
