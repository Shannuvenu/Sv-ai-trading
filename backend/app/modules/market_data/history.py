"""
Enhanced historical data with intraday candle support.
Upstox supports: 1minute, 30minute, day, week, month intervals.
"""
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app.modules.market_data.provider import OHLCVBar
from app.modules.market_data.upstox_instruments import SYMBOL_TO_KEY

logger = logging.getLogger("history")

INTERVALS = {
    "1m": "1minute",
    "5m": "5minute",
    "15m": "15minute",
    "30m": "30minute",
    "1H": "60minute",
    "1D": "day",
    "1W": "week",
    "1M": "month",
}

RANGE_DAYS = {
    "1D": 1, "5D": 5, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "3Y": 1095, "5Y": 1825, "MAX": 3650,
}


def fetch_candles(
    symbol: str, interval: str = "1D", range_key: str = "3M"
) -> list[OHLCVBar]:
    """Fetch candles from Upstox for any interval + range combination."""
    from app.modules.market_data.upstox_provider import get_upstox_provider
    provider = get_upstox_provider()
    if not provider or not provider._configured:
        return []

    instrument_key = SYMBOL_TO_KEY.get(symbol.upper())
    if not instrument_key:
        return []

    upstox_interval = INTERVALS.get(interval, "day")
    days = RANGE_DAYS.get(range_key, 90)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    to_date = end.strftime("%Y-%m-%d")
    from_date = start.strftime("%Y-%m-%d")

    history_url = "https://api.upstox.com/v2/historical-candle"
    url = f"{history_url}/{instrument_key.replace('|','%7C')}/{upstox_interval}/{to_date}/{from_date}"

    try:
        resp = provider._http.get(url, headers=provider._headers())
        if resp.status_code != 200:
            logger.error(f"Candles HTTP {resp.status_code} for {symbol} {interval}")
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
        return sorted(bars, key=lambda b: b.timestamp)
    except Exception as e:
        logger.error(f"Candles error {symbol}: {e}")
        return []
