from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.market_data.utils import resolve_market_provider
from app.modules.technical_analysis.indicators import compute_indicators
from app.modules.technical_analysis.enhanced_indicators import compute_enhanced_indicators
from app.modules.technical_analysis.summary_engine import compute_summary
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


class TechnicalSummaryResponse(BaseModel):
    symbol: str
    name: str
    exchange: str
    last_price: float
    summary: dict
    indicators: dict
    moving_averages: dict


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
        "sma_20": indicators.get("sma_20"), "sma_50": indicators.get("sma_50"),
        "ema_20": indicators.get("ema_20"), "rsi_14": indicators.get("rsi_14"),
        "macd_line": indicators.get("macd_line"), "macd_signal": indicators.get("macd_signal"),
        "macd_histogram": indicators.get("macd_histogram"),
        "bb_upper": indicators.get("bb_upper"), "bb_middle": indicators.get("bb_middle"),
        "bb_lower": indicators.get("bb_lower"), "atr_14": indicators.get("atr_14"),
        "volume_sma_20": indicators.get("volume_sma_20"),
        "latest_close": indicators.get("latest_close"),
    }

    return AnalysisResponse(
        symbol=symbol.upper(), name=quote.name, exchange=quote.exchange,
        indicators=indicator_response, signal=signal.to_dict(), explanation=explanation,
    )


@router.get("/technical-summary/{symbol}", response_model=TechnicalSummaryResponse)
def technical_summary(
    symbol: str,
    days: int = Query(default=200, ge=20, le=365),
    db: Session = Depends(get_db),
):
    provider = resolve_market_provider(db)
    quote = provider.get_quote(symbol.upper())
    if not quote:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found")

    bars = provider.get_history(symbol.upper(), days=days)
    if len(bars) < 50:
        raise HTTPException(status_code=400, detail="Insufficient data for technical summary")

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]

    indicators = compute_enhanced_indicators(closes, highs, lows, volumes)
    summary = compute_summary(indicators)

    ma_list = {}
    for k in ["sma_5", "sma_10", "sma_20", "sma_50", "sma_100", "sma_200", "ema_10", "ema_20", "ema_50"]:
        v = indicators.get(k)
        ma_list[k.replace("_", " ").upper()] = round(v, 2) if v is not None else None

    ind_display = {}
    for k in ["rsi_14", "adx_14", "stoch_k", "vwap", "cci_20"]:
        v = indicators.get(k)
        ind_display[k.replace("_", " ").upper()] = round(v, 2) if v is not None else None

    return TechnicalSummaryResponse(
        symbol=symbol.upper(), name=quote.name, exchange=quote.exchange,
        last_price=float(quote.close), summary=summary,
        indicators=ind_display, moving_averages=ma_list,
    )
