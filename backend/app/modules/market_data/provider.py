from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass


@dataclass
class Quote:
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
    data_source: str = "CACHED"  # "LIVE" | "CACHED" | "SIMULATED"
    market_status: str = "CLOSED"  # "OPEN" | "CLOSED"


@dataclass
class OHLCVBar:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass
class InstrumentInfo:
    symbol: str
    name: str
    exchange: str
    sector: str | None
    instrument_type: str
    currency: str
    is_active: bool


class MarketDataProvider(ABC):
    @abstractmethod
    def search_instruments(self, query: str) -> list[InstrumentInfo]:
        ...

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote | None:
        ...

    @abstractmethod
    def get_history(
        self, symbol: str, start: datetime | None = None, end: datetime | None = None
    ) -> list[OHLCVBar]:
        ...

    @abstractmethod
    def get_all_instruments(self) -> list[InstrumentInfo]:
        ...
