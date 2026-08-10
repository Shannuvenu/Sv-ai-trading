"""Chart API — serves OHLCV data for chart frontend with multi-timeframe support."""
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.market_data.upstox_provider import get_upstox_provider
from app.modules.market_data.instrument_client import get_instrument_client

router = APIRouter(prefix="/chart", tags=["Chart Data"])
logger = logging.getLogger("chart_routes")

# Upstox interval mapping: our interval -> Upstox interval
INTERVAL_MAP = {
    "1m": "1minute",
    "3m": "3minute",
    "5m": "5minute",
    "10m": "10minute",
    "15m": "15minute",
    "30m": "30minute",
    "60m": "60minute",
    "1h": "60minute",
    "2h": "2hour",
    "4h": "4hour",
    "1D": "day",
    "1W": "week",
    "1M": "month",
}

HISTORY_URL = "https://api.upstox.com/v2/historical-candle"


@router.get("/{symbol}/candles")
def get_candles(
    symbol: str,
    interval: str = Query("1D", description="1m,3m,5m,15m,30m,1h,4h,1D,1W,1M"),
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

    upstox_interval = INTERVAL_MAP.get(interval, "day")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    key_encoded = instrument_key.replace("|", "%7C")
    to_date = end.strftime("%Y-%m-%d")
    from_date = start.strftime("%Y-%m-%d")

    url = f"{HISTORY_URL}/{key_encoded}/{upstox_interval}/{to_date}/{from_date}"
    resp = provider._http.get(url, headers=provider._headers())
    if resp.status_code != 200:
        logger.error(f"Chart history HTTP {resp.status_code} for {symbol} at {interval}")
        raise HTTPException(502, "Unable to fetch chart data from provider")

    data = resp.json()
    candles = data.get("data", {}).get("candles", [])
    result = []
    for c in candles:
        if isinstance(c, list) and len(c) >= 6:
            ts = c[0]
            try:
                ts = datetime.strptime(c[0], "%Y-%m-%dT%H:%M:%S%z").isoformat()
            except Exception:
                pass
            result.append({
                "time": ts,
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": int(c[5]),
            })
    return {
        "symbol": symbol,
        "instrument_key": instrument_key,
        "interval": interval,
        "candles": result,
        "total": len(result),
    }


@router.get("/{symbol}/quote")
def get_chart_quote(
    symbol: str,
    user: User = Depends(get_current_user),
):
    """Get real-time quote data for chart header."""
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
    indicators: str = Query("sma20,ema50,rsi14,macd,bb,sma50,sma200"),
    user: User = Depends(get_current_user),
):
    """Compute technical indicators server-side and return as arrays."""
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

    result_indicators = {}
    req = set([i.strip().lower() for i in indicators.split(",") if i.strip()])

    for ind in req:
        if ind.startswith("sma"):
            period = int(ind[3:]) if len(ind) > 3 else 20
            vals = sma(closes, period)
            result_indicators[f"sma_{period}"] = _format_series(times, vals)
        elif ind.startswith("ema"):
            period = int(ind[3:]) if len(ind) > 3 else 50
            vals = ema(closes, period)
            result_indicators[f"ema_{period}"] = _format_series(times, vals)
        elif ind == "rsi14" or ind == "rsi":
            vals = compute_rsi(closes, 14)
            result_indicators["rsi_14"] = _format_series(times, vals)
        elif ind == "macd":
            macd_line, sig_line, hist = compute_macd(closes)
            result_indicators["macd_line"] = _format_series(times, macd_line)
            result_indicators["macd_signal"] = _format_series(times, sig_line)
            result_indicators["macd_histogram"] = _format_series(times, hist)
        elif ind == "bb":
            upper, middle, lower = bollinger_bands(closes)
            result_indicators["bb_upper"] = _format_series(times, upper)
            result_indicators["bb_middle"] = _format_series(times, middle)
            result_indicators["bb_lower"] = _format_series(times, lower)
        elif ind == "atr":
            vals = compute_atr(highs, lows, closes, 14)
            result_indicators["atr_14"] = _format_series(times, vals)
        elif ind == "volume":
            result_indicators["volume"] = _format_series_volume(times, volumes)

    result_indicators["__close"] = _format_series(times, closes)
    return {"symbol": symbol, "indicators": result_indicators}


def _format_series(times, values):
    return [{"time": t, "value": round(v, 2) if v is not None else None} for t, v in zip(times, values) if v is not None]


def _format_series_volume(times, values):
    return [{"time": t, "value": v} for t, v in zip(times, values)]
