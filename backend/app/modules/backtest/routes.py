from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.modules.market_data.utils import resolve_market_provider
from app.modules.backtest.runner import run_backtest

router = APIRouter(prefix="/backtest", tags=["Backtest"])


class BacktestRequest(BaseModel):
    symbol: str
    initial_capital: float = 100000.0
    position_size_pct: float = 0.2
    commission: float = 0.1
    slippage: float = 0.001


@router.post("")
def execute_backtest(
    payload: BacktestRequest,
    days: int = Query(default=252, ge=50, le=365),
    db: Session = Depends(get_db),
):
    provider = resolve_market_provider(db)
    bars = provider.get_history(payload.symbol.upper(), days=days)

    if len(bars) < 50:
        raise HTTPException(status_code=400, detail="Insufficient data for backtesting (need at least 50 days)")

    result = run_backtest(
        symbol=payload.symbol.upper(),
        bars=bars,
        initial_capital=payload.initial_capital,
        position_size_pct=payload.position_size_pct,
        commission_pct=payload.commission,
        slippage_pct=payload.slippage,
    )
    return result.to_dict()
