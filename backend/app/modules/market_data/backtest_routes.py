"""Backtest API routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.market_data.upstox_provider import get_upstox_provider
from app.modules.market_data.backtest_engine import run_backtest

router = APIRouter(prefix="/backtest-pine", tags=["Pine Backtest"])


class BacktestRunRequest(BaseModel):
    symbol: str
    script: str
    interval: str = "1D"
    days: int = 500
    initial_capital: float = 100000.0
    position_size_pct: float = 20.0
    stop_loss_pct: float = 3.0
    take_profit_pct: float = 6.0
    commission_pct: float = 0.1


@router.post("/strategy")
def run_strategy_backtest(
    payload: BacktestRunRequest,
    user: User = Depends(get_current_user),
):
    provider = get_upstox_provider()
    if not provider or not provider._configured:
        raise HTTPException(503, "Market data unavailable")

    symbol = payload.symbol.upper()
    instrument_key = provider._resolve_key(symbol)
    if not instrument_key:
        raise HTTPException(404, f"Instrument not found: {symbol}")

    bars = provider.get_history(symbol, days=min(payload.days, 500))
    if len(bars) < 50:
        raise HTTPException(400, "Insufficient historical data")

    ohlc = {
        "open": [float(b.open) for b in bars],
        "high": [float(b.high) for b in bars],
        "low": [float(b.low) for b in bars],
        "close": [float(b.close) for b in bars],
        "volume": [int(b.volume) for b in bars],
        "time": [b.timestamp.isoformat() for b in bars],
    }

    result = run_backtest(
        ohlc=ohlc,
        script=payload.script,
        initial_capital=payload.initial_capital,
        position_size_pct=payload.position_size_pct,
        stop_loss_pct=payload.stop_loss_pct,
        take_profit_pct=payload.take_profit_pct,
        commission_pct=payload.commission_pct,
    )
    result["symbol"] = symbol
    result["timeframe"] = payload.interval
    return result
