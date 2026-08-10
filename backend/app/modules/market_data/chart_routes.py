"""
Chart API — serves OHLCV data with intelligent timeframe mapping.
Upstox supports: 1minute, 30minute, day, week, month directly.
For unsupported intervals, we fetch 1m data and aggregate mathematically.
"""
import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.market_data.upstox_provider import get_upstox_provider
from app.modules.market_data.instrument_client import get_instrument_client

router = APIRouter(prefix="/chart", tags=["Chart Data"])
logger = logging.getLogger("chart_routes")

HISTORY_URL = "https://api.upstox.com/v2/historical-candle"

# Upstox actually supports these directly
UPSTOX_DIRECT = {"1": "1minute", "30": "30minute", "D": "day", "W": "week", "M": "month"}

# Our UI intervals mapped to aggregation rules (source, multiplier, max_days)
AGGREGATE_MAP = {
    "1m":  ("1minute", 1, 7),      # 1m = 1x 1min candle
    "3m":  ("1minute", 3, 15),     # 3m = aggregate 3x 1min
    "5m":  ("1minute", 5, 30),     # 5m = aggregate 5x 1min
    "15m": ("1minute", 15, 60),    # 15m = aggregate 15x 1min
    "30m": ("30minute", 1, 90),    # 30m = direct
    "1h":  ("1minute", 60, 90),    # 1h = aggregate 60x 1min
    "4h":  ("1minute", 240, 120),  # 4h = aggregate 240x 1min
    "1D":  ("day", 1, 730),        # 1D = direct
    "1W":  ("week", 1, 1825),      # 1W = direct
    "1M":  ("month", 1, 7300),     # 1M = direct
}

def _aggregate_candles(bars: list[dict], multiplier: int) -> list[dict]:
    """Aggregate 1-minute candles into N-minute OHLCV candles. Open=first, High=max, Low=min, Close=last, Volume=sum."""
    if multiplier <= 1:
        return bars
    result = []
    bucket = []
    for bar in bars:
        bucket.append(bar)
        if len(bucket) >= multiplier:
            result.append({
                "time": bucket[0]["time"],
                "open": bucket[0]["open"],
                "high": max(b["high"] for b in bucket),
                "low": min(b["low"] for b in bucket),
                "close": bucket[-1]["close"],
                "volume": sum(b["volume"] for b in bucket),
            })
            bucket = []
    if bucket and len(bucket) > 1:
        result.append({
            "time": bucket[0]["time"],
            "open": bucket[0]["open"],
            "high": max(b["high"] for b in bucket),
            "low": min(b["low"] for b in bucket),
            "close": bucket[-1]["close"],
            "volume": sum(b["volume"] for b in bucket),
        })
    return result


@router.get("/{symbol}/candles")
def get_candles(
    symbol: str,
    interval: str = Query("1D"),
    days: int = Query(365, ge=1, le=730),
    user: User = Depends(get_current_user),
):
    symbol = symbol.upper()
    provider = get_upstox_provider()
    if not provider or not provider._configured:
        raise HTTPException(503, "Market data provider unavailable")

    instrument_key = provider._resolve_key(symbol)
    if not instrument_key:
        inst_client = get_instrument_client()
        inst = inst_client.get_instrument_by_symbol(symbol, "NSE")
        if inst and inst.get("instrument_key"):
            instrument_key = inst["instrument_key"]
    if not instrument_key:
        raise HTTPException(404, f"Instrument not found: {symbol}")

    mapping = AGGREGATE_MAP.get(interval)
    if not mapping:
        mapping = ("day", 1, 365)
    source_interval, multiplier, max_days = mapping
    fetch_days = min(days, max_days)

    key_encoded = instrument_key.replace("|", "%7C")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=fetch_days)
    to_date = end.strftime("%Y-%m-%d")
    from_date = start.strftime("%Y-%m-%d")

    url = f"{HISTORY_URL}/{key_encoded}/{source_interval}/{to_date}/{from_date}"
    resp = provider._http.get(url, headers=provider._headers(), timeout=30.0)

    if resp.status_code != 200:
        logger.error(f"Chart HTTP {resp.status_code} for {symbol} interval={interval} mapped={source_interval}")
        raise HTTPException(502, f"Provider returned {resp.status_code} for interval {interval}")

    data = resp.json()
    raw_candles = data.get("data", {}).get("candles", [])
    if not raw_candles:
        return {"symbol": symbol, "instrument_key": instrument_key, "interval": interval, "candles": [], "total": 0}

    bars = []
    for c in raw_candles:
        if isinstance(c, list) and len(c) >= 6 and c[0]:
            try:
                ts = datetime.strptime(c[0], "%Y-%m-%dT%H:%M:%S%z")
            except Exception:
                ts = datetime.now(timezone.utc)
            bars.append({
                "time": ts.isoformat(),
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": int(c[5]),
            })

    bars.sort(key=lambda x: x["time"])
    aggregated = _aggregate_candles(bars, multiplier) if multiplier > 1 else bars

    return {
        "symbol": symbol,
        "instrument_key": instrument_key,
        "interval": interval,
        "candles": aggregated,
        "total": len(aggregated),
    }


@router.get("/{symbol}/quote")
def get_chart_quote(
    symbol: str,
    user: User = Depends(get_current_user),
):
    symbol = symbol.upper()
    provider = get_upstox_provider()
    if not provider or not provider._configured:
        raise HTTPException(503, "Market data provider unavailable")
    quote = provider.get_quote(symbol)
    if not quote:
        raise HTTPException(404, f"No quote for {symbol}")
    return {
        "symbol": quote.symbol,
        "name": quote.name,
        "exchange": quote.exchange,
        "last_price": float(quote.last_price),
        "change": float(quote.change),
        "change_pct": float(quote.change_pct),
        "open": float(quote.open),
        "high": float(quote.high),
        "low": float(quote.low),
        "close": float(quote.close),
        "volume": quote.volume,
        "timestamp": quote.timestamp.isoformat() if quote.timestamp else None,
        "source": "UPSTOX",
    }


@router.get("/{symbol}/indicators")
def get_indicators(
    symbol: str,
    indicators: str = Query("sma20,ema50,rsi14,macd,volume"),
    user: User = Depends(get_current_user),
):
    symbol = symbol.upper()
    provider = get_upstox_provider()
    if not provider or not provider._configured:
        raise HTTPException(503, "Market data unavailable")
    bars = provider.get_history(symbol, days=500)
    if len(bars) < 20:
        raise HTTPException(400, "Insufficient data")
    closes = [float(b.close) for b in bars]
    highs = [float(b.high) for b in bars]
    lows = [float(b.low) for b in bars]
    volumes = [int(b.volume) for b in bars]
    times = [b.timestamp.isoformat() for b in bars]

    from app.modules.technical_analysis.indicators import sma, ema, rsi as compute_rsi, macd as compute_macd, bollinger_bands, atr as compute_atr

    result = {}
    req = set(i.strip().lower() for i in indicators.split(",") if i.strip())

    for ind in req:
        if ind.startswith("sma"):
            p = int(ind[3:]) if len(ind) > 3 else 20
            result[f"sma_{p}"] = _fmt(times, sma(closes, p))
        elif ind.startswith("ema"):
            p = int(ind[3:]) if len(ind) > 3 else 50
            result[f"ema_{p}"] = _fmt(times, ema(closes, p))
        elif ind in ("rsi14", "rsi"):
            result["rsi_14"] = _fmt(times, compute_rsi(closes, 14))
        elif ind == "macd":
            ml, sl, h = compute_macd(closes)
            result["macd_line"] = _fmt(times, ml)
            result["macd_signal"] = _fmt(times, sl)
            result["macd_histogram"] = _fmt(times, h)
        elif ind == "bb":
            u, m, l = bollinger_bands(closes)
            result["bb_upper"] = _fmt(times, u)
            result["bb_middle"] = _fmt(times, m)
            result["bb_lower"] = _fmt(times, l)
        elif ind == "atr":
            result["atr_14"] = _fmt(times, compute_atr(highs, lows, closes, 14))
        elif ind == "volume":
            result["volume"] = [{"time": t, "value": v} for t, v in zip(times, volumes)]

    result["__close"] = _fmt(times, closes)
    return {"symbol": symbol, "indicators": result}


def _fmt(times, values):
    return [{"time": t, "value": round(v, 2) if v is not None else None} for t, v in zip(times, values) if v is not None]
