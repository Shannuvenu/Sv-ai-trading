from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.market_data.schemas import (
    InstrumentResponse,
    QuoteResponse,
    HistoryResponse,
    SearchResult,
)
from app.modules.market_data.utils import resolve_market_provider


def get_provider(db: Session = Depends(get_db)):
    return resolve_market_provider(db)


router = APIRouter(prefix="/market", tags=["Market Data"])


def _get_all_instruments(provider):
    return provider.get_all_instruments()


def _instrument_to_id(provider, symbol: str):
    instruments = _get_all_instruments(provider)
    for i, inst in enumerate(instruments):
        if inst.symbol == symbol:
            return i + 1
    return None


@router.get("/instruments", response_model=list[InstrumentResponse])
def list_instruments(provider=Depends(get_provider)):
    instruments = _get_all_instruments(provider)
    return [
        InstrumentResponse(
            id=i + 1,
            symbol=inst.symbol,
            name=inst.name,
            exchange=inst.exchange,
            sector=inst.sector,
            instrument_type=inst.instrument_type,
            currency=inst.currency,
            is_active=inst.is_active,
        )
        for i, inst in enumerate(instruments)
    ]


@router.get("/instruments/search", response_model=list[SearchResult])
def search_instruments(q: str = Query(..., min_length=1), provider=Depends(get_provider)):
    results = provider.search_instruments(q)
    instruments = _get_all_instruments(provider)
    symbol_to_id = {inst.symbol: i + 1 for i, inst in enumerate(instruments)}
    return [
        SearchResult(
            id=symbol_to_id.get(inst.symbol, 0),
            symbol=inst.symbol,
            name=inst.name,
            exchange=inst.exchange,
            sector=inst.sector,
            instrument_type=inst.instrument_type,
        )
        for inst in results
    ]


@router.get("/instruments/{symbol}", response_model=InstrumentResponse)
def get_instrument(symbol: str, provider=Depends(get_provider)):
    instruments = _get_all_instruments(provider)
    symbol = symbol.upper()
    for i, inst in enumerate(instruments):
        if inst.symbol == symbol:
            return InstrumentResponse(
                id=i + 1,
                symbol=inst.symbol,
                name=inst.name,
                exchange=inst.exchange,
                sector=inst.sector,
                instrument_type=inst.instrument_type,
                currency=inst.currency,
                is_active=inst.is_active,
            )
    raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found")


@router.get("/quote/{symbol}", response_model=QuoteResponse)
def get_quote(symbol: str, provider=Depends(get_provider)):
    quote = provider.get_quote(symbol.upper())
    if not quote:
        raise HTTPException(status_code=404, detail=f"No quote available for {symbol}")
    return QuoteResponse(
        symbol=quote.symbol,
        name=quote.name,
        exchange=quote.exchange,
        last_price=quote.last_price,
        change=quote.change,
        change_pct=quote.change_pct,
        open=quote.open,
        high=quote.high,
        low=quote.low,
        close=quote.close,
        volume=quote.volume,
        timestamp=quote.timestamp,
        data_source=getattr(quote, "data_source", "CACHED"),
        market_status=getattr(quote, "market_status", "CLOSED"),
    )


@router.get("/history/{symbol}", response_model=HistoryResponse)
def get_history(symbol: str, provider=Depends(get_provider)):
    bars = provider.get_history(symbol.upper())
    if not bars:
        raise HTTPException(status_code=404, detail=f"No history for {symbol}")
    return HistoryResponse(
        symbol=symbol.upper(),
        data=[
            {
                "timestamp": b.timestamp,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in bars
        ],
    )
