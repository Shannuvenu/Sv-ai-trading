from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal


class InstrumentResponse(BaseModel):
    id: int
    symbol: str
    name: str
    exchange: str
    sector: str | None
    instrument_type: str
    currency: str
    is_active: bool

    model_config = {"from_attributes": True}


class QuoteResponse(BaseModel):
    symbol: str
    name: str
    exchange: str
    last_price: Decimal
    change: Decimal
    change_pct: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    timestamp: datetime


class OHLCVPoint(BaseModel):
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class HistoryResponse(BaseModel):
    symbol: str
    data: list[OHLCVPoint]


class SearchResult(BaseModel):
    id: int
    symbol: str
    name: str
    exchange: str
    sector: str | None
    instrument_type: str

    model_config = {"from_attributes": True}
