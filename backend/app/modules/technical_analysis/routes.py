from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.market_data.utils import resolve_market_provider
from app.modules.technical_analysis.indicators import compute_indicators
from app.modules.signals.engine import generate_signal
from app.modules.explainability.explainer import explain_signal
from pydantic import BaseModel

router = APIRouter(prefix="/analysis", tags=["Analysis"])


class AnalysisResponse(BaseModel):
    symbol: str
    name: str
    exchange: str
    indicators: dict
    signal: dict
    explanation: dict


@router.get("/{symbol}", response_model=AnalysisResponse)
def analyze(
    symbol: str,
    days: int = Query(default=100, ge=20, le=365),
    db: Session = Depends(get_db),
):
    provider = resolve_market_provider(db)
    quote = provider.get_quote(symbol.upper())
    if not quote:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found")

    bars = provider.get_history(symbol.upper(), days=days)
    if len(bars) < 20:
        raise HTTPException(status_code=400, detail="Insufficient historical data (need at least 20 days)")

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]

    indicators = compute_indicators(closes, highs, lows, volumes)

    signal = generate_signal(symbol.upper(), indicators)
    explanation = explain_signal(signal.to_dict())

    indicator_response = {
        "sma_20": indicators.get("sma_20"),
        "sma_50": indicators.get("sma_50"),
        "ema_20": indicators.get("ema_20"),
        "rsi_14": indicators.get("rsi_14"),
        "macd_line": indicators.get("macd_line"),
        "macd_signal": indicators.get("macd_signal"),
        "macd_histogram": indicators.get("macd_histogram"),
        "bb_upper": indicators.get("bb_upper"),
        "bb_middle": indicators.get("bb_middle"),
        "bb_lower": indicators.get("bb_lower"),
        "atr_14": indicators.get("atr_14"),
        "volume_sma_20": indicators.get("volume_sma_20"),
        "latest_close": indicators.get("latest_close"),
    }

    return AnalysisResponse(
        symbol=symbol.upper(),
        name=quote.name,
        exchange=quote.exchange,
        indicators=indicator_response,
        signal=signal.to_dict(),
        explanation=explanation,
    )
