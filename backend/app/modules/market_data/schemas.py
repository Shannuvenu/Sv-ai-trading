from pydantic import BaseModel, field_serializer, ConfigDict
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

    model_config = ConfigDict(from_attributes=True)


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
    data_source: str = "CACHED"
    market_status: str = "CLOSED"

    @field_serializer("last_price", "change", "change_pct", "open", "high", "low", "close")
    def serialize_dec(self, v: Decimal) -> float:
        return round(float(v), 2)


class OHLCVPoint(BaseModel):
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    @field_serializer("open", "high", "low", "close")
    def serialize_dec(self, v: Decimal) -> float:
        return round(float(v), 2)


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

    model_config = ConfigDict(from_attributes=True)
