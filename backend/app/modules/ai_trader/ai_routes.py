"""AI Intelligence routes — Gemini-powered market analysis."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.market_data.utils import resolve_market_provider
from app.modules.technical_analysis.indicators import compute_indicators
from app.modules.news.models import NewsArticle
from app.modules.ai_trader.gemini_service import get_gemini_service
from app.modules.ai_trader.strategies import STRATEGIES

router = APIRouter(prefix="/ai", tags=["AI Intelligence"])


class AIAnalysisRequest(BaseModel):
    symbol: str


@router.post("/analyze")
def ai_analyze(
    payload: AIAnalysisRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get Gemini-powered AI analysis for a stock with technical + news context."""
    symbol = payload.symbol.upper()
    provider = resolve_market_provider(db)
    quote = provider.get_quote(symbol)
    if not quote:
        raise HTTPException(404, f"Instrument {symbol} not found")

    bars = provider.get_history(symbol, days=200)
    if len(bars) < 20:
        raise HTTPException(400, "Insufficient data for analysis")

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]
    indicators = compute_indicators(closes, highs, lows, volumes)

    news = (
        db.query(NewsArticle)
        .filter(NewsArticle.symbol == symbol)
        .order_by(NewsArticle.published_at.desc())
        .limit(10)
        .all()
    )
    headlines = [n.headline for n in news]

    gemini = get_gemini_service()
    result = gemini.analyze(
        symbol=symbol,
        last_price=float(quote.close),
        change_pct=float(quote.change_pct),
        indicators=indicators,
        news_headlines=headlines,
    )
    result["name"] = quote.name
    result["exchange"] = quote.exchange
    result["last_price"] = float(quote.close)
    result["change_pct"] = float(quote.change_pct)
    return result


@router.get("/strategy-select")
def select_strategy(
    symbol: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Let Gemini choose the best strategy for current market conditions."""
    symbol = symbol.upper()
    provider = resolve_market_provider(db)
    quote = provider.get_quote(symbol)
    if not quote:
        raise HTTPException(404, f"Instrument {symbol} not found")

    bars = provider.get_history(symbol, days=200)
    if len(bars) < 50:
        raise HTTPException(400, "Insufficient data")

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]
    indicators = compute_indicators(closes, highs, lows, volumes)

    news = (
        db.query(NewsArticle)
        .filter(NewsArticle.symbol == symbol)
        .order_by(NewsArticle.published_at.desc())
        .limit(5)
        .all()
    )
    headlines = [n.headline for n in news]

    gemini = get_gemini_service()
    return gemini.analyze_strategy(
        symbol=symbol,
        last_price=float(quote.close),
        indicators=indicators,
        strategies=STRATEGIES,
        news_headlines=headlines,
    )


@router.get("/news-summary")
def ai_news_summary(
    symbol: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get Gemini AI summary and sentiment for recent stock news."""
    symbol = symbol.upper()
    news = (
        db.query(NewsArticle)
        .filter(NewsArticle.symbol == symbol)
        .order_by(NewsArticle.published_at.desc())
        .limit(15)
        .all()
    )
    if not news:
        return {"sentiment": "NEUTRAL", "summary": "No recent news to analyze", "impact_score": 0}

    headlines = [n.headline for n in news]
    gemini = get_gemini_service()
    return gemini.summarize_news(headlines)
