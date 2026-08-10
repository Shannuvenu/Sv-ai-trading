"""Pine script execution API — safe interpreter for chart indicators."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.market_data.upstox_provider import get_upstox_provider
from app.modules.market_data.pine_interpreter import PineInterpreter, PineResult

router = APIRouter(prefix="/pine", tags=["Pine Script"])
logger = logging.getLogger("pine_routes")


class PineRequest(BaseModel):
    symbol: str
    script: str
    interval: str = "1D"
    days: int = 500


@router.post("/run")
def run_pine(
    payload: PineRequest,
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

    interpreter = PineInterpreter(ohlc)
    result = interpreter.execute(payload.script)

    return {
        "symbol": symbol,
        "success": len(result.errors) == 0,
        "plots": result.plots,
        "shapes": result.shapes,
        "hlines": result.hlines,
        "trades": result.trades,
        "strategy_name": result.strategy_name or "",
        "warnings": result.warnings,
        "errors": result.errors,
    }
