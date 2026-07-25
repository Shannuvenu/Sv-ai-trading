from datetime import datetime, timedelta, timezone
from decimal import Decimal
import math
import hashlib
from app.modules.market_data.provider import (
    MarketDataProvider,
    Quote,
    OHLCVBar,
    InstrumentInfo,
)


STOCKS = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "sector": "Oil & Gas"},
    {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "sector": "IT"},
    {"symbol": "INFY", "name": "Infosys Ltd", "sector": "IT"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "sector": "Banking"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "sector": "Banking"},
    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking"},
    {"symbol": "ITC", "name": "ITC Ltd", "sector": "FMCG"},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd", "sector": "Infrastructure"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "sector": "Telecom"},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "sector": "Banking"},
]

BASE_PRICES = {
    "RELIANCE": Decimal("2450.00"),
    "TCS": Decimal("3850.00"),
    "INFY": Decimal("1520.00"),
    "HDFCBANK": Decimal("1680.00"),
    "ICICIBANK": Decimal("1080.00"),
    "SBIN": Decimal("780.00"),
    "ITC": Decimal("450.00"),
    "LT": Decimal("3200.00"),
    "BHARTIARTL": Decimal("1350.00"),
    "AXISBANK": Decimal("1120.00"),
}

VOLATILITIES = {
    "RELIANCE": Decimal("0.012"),
    "TCS": Decimal("0.010"),
    "INFY": Decimal("0.014"),
    "HDFCBANK": Decimal("0.011"),
    "ICICIBANK": Decimal("0.013"),
    "SBIN": Decimal("0.015"),
    "ITC": Decimal("0.009"),
    "LT": Decimal("0.013"),
    "BHARTIARTL": Decimal("0.012"),
    "AXISBANK": Decimal("0.014"),
}


def _deterministic_random(seed_str: str) -> float:
    h = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
    return (h % 10000) / 10000.0


def _generate_ohlcv(symbol: str, base_price: Decimal, volatility: Decimal, days: int = 252) -> list[OHLCVBar]:
    end_date = datetime.now(timezone.utc).replace(hour=15, minute=30, second=0, microsecond=0)
    bars = []
    price = float(base_price)

    for i in range(days, -1, -1):
        day = end_date - timedelta(days=i)
        if day.weekday() >= 5:
            continue

        seed = f"{symbol}_{day.strftime('%Y%m%d')}"
        r1 = _deterministic_random(seed + "_open")
        r2 = _deterministic_random(seed + "_high")
        r3 = _deterministic_random(seed + "_low")
        r4 = _deterministic_random(seed + "_close")
        r5 = _deterministic_random(seed + "_vol")

        daily_return = (r4 - 0.5) * 2 * float(volatility)
        price = price * (1 + daily_return)

        open_p = price * (1 + (r1 - 0.5) * float(volatility) * 0.3)
        high_p = price * (1 + abs(r2 - 0.3) * float(volatility) * 0.8)
        low_p = price * (1 - abs(r3 - 0.3) * float(volatility) * 0.8)
        close_p = price
        vol = int(500_000 + r5 * 2_000_000)

        bars.append(OHLCVBar(
            timestamp=day,
            open=Decimal(str(round(open_p, 2))),
            high=Decimal(str(round(high_p, 2))),
            low=Decimal(str(round(low_p, 2))),
            close=Decimal(str(round(close_p, 2))),
            volume=vol,
        ))

    return bars


class MockMarketDataProvider(MarketDataProvider):
    def __init__(self):
        self._instruments = [
            InstrumentInfo(
                symbol=s["symbol"],
                name=s["name"],
                exchange="NSE",
                sector=s["sector"],
                instrument_type="equity",
                currency="INR",
                is_active=True,
            )
            for s in STOCKS
        ]
        self._symbol_map = {i.symbol: i for i in self._instruments}
        self._cache: dict[str, list[OHLCVBar]] = {}

    def get_all_instruments(self) -> list[InstrumentInfo]:
        return self._instruments

    def search_instruments(self, query: str) -> list[InstrumentInfo]:
        q = query.lower()
        return [
            i for i in self._instruments
            if q in i.symbol.lower() or q in i.name.lower()
        ]

    def get_quote(self, symbol: str) -> Quote | None:
        symbol = symbol.upper()
        info = self._symbol_map.get(symbol)
        if not info:
            return None

        history = self.get_history(symbol, days=2)
        if not history:
            return None

        latest = history[-1]
        prev_close = history[-2].close if len(history) >= 2 else latest.open
        change = latest.close - prev_close
        change_pct = (change / prev_close * 100) if prev_close != 0 else Decimal("0")

        return Quote(
            symbol=symbol,
            name=info.name,
            exchange=info.exchange,
            last_price=latest.close,
            change=change,
            change_pct=change_pct,
            open=latest.open,
            high=latest.high,
            low=latest.low,
            close=latest.close,
            volume=latest.volume,
            timestamp=latest.timestamp,
        )

    def get_history(
        self, symbol: str, start: datetime | None = None, end: datetime | None = None, days: int = 252
    ) -> list[OHLCVBar]:
        symbol = symbol.upper()
        if symbol not in self._cache:
            bp = BASE_PRICES.get(symbol, Decimal("1000.00"))
            vol = VOLATILITIES.get(symbol, Decimal("0.01"))
            self._cache[symbol] = _generate_ohlcv(symbol, bp, vol, 252)

        bars = self._cache[symbol]

        if start:
            start = start.replace(tzinfo=timezone.utc)
            bars = [b for b in bars if b.timestamp >= start]
        if end:
            end = end.replace(tzinfo=timezone.utc)
            bars = [b for b in bars if b.timestamp <= end]

        return bars


_provider_instance: MockMarketDataProvider | None = None


def get_market_data_provider() -> MockMarketDataProvider:
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = MockMarketDataProvider()
    return _provider_instance
