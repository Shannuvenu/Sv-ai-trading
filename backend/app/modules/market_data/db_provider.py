from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from app.modules.market_data.models import Instrument as DBInstrument, OHLCVData
from app.modules.market_data.provider import (
    MarketDataProvider, Quote, OHLCVBar, InstrumentInfo,
)


class DatabaseMarketDataProvider(MarketDataProvider):
    def __init__(self, db: Session):
        self._db = db

    def get_all_instruments(self) -> list[InstrumentInfo]:
        rows = self._db.query(DBInstrument).filter(DBInstrument.is_active == True).all()
        return [
            InstrumentInfo(
                symbol=r.symbol,
                name=r.name,
                exchange=r.exchange,
                sector=r.sector,
                instrument_type=r.instrument_type,
                currency=r.currency,
                is_active=r.is_active,
            )
            for r in rows
        ]

    def search_instruments(self, query: str) -> list[InstrumentInfo]:
        q = query.lower()
        rows = self._db.query(DBInstrument).filter(
            DBInstrument.is_active == True,
            (DBInstrument.symbol.ilike(f"%{q}%")) | (DBInstrument.name.ilike(f"%{q}%"))
        ).all()
        return [
            InstrumentInfo(
                symbol=r.symbol,
                name=r.name,
                exchange=r.exchange,
                sector=r.sector,
                instrument_type=r.instrument_type,
                currency=r.currency,
                is_active=r.is_active,
            )
            for r in rows
        ]

    def get_quote(self, symbol: str) -> Quote | None:
        symbol = symbol.upper()
        inst = self._db.query(DBInstrument).filter(DBInstrument.symbol == symbol).first()
        if not inst:
            return None

        bars = (
            self._db.query(OHLCVData)
            .filter(OHLCVData.instrument_id == inst.id)
            .order_by(OHLCVData.timestamp.desc())
            .limit(2)
            .all()
        )
        if len(bars) < 2:
            return None

        latest = bars[0]
        prev = bars[1]
        change = latest.close - prev.close
        change_pct = (change / prev.close * 100) if prev.close != 0 else Decimal("0")

        return Quote(
            symbol=symbol,
            name=inst.name,
            exchange=inst.exchange,
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
        inst = self._db.query(DBInstrument).filter(DBInstrument.symbol == symbol).first()
        if not inst:
            return []

        q = self._db.query(OHLCVData).filter(OHLCVData.instrument_id == inst.id)

        if start:
            start = start.replace(tzinfo=timezone.utc)
            q = q.filter(OHLCVData.timestamp >= start)
        if end:
            end = end.replace(tzinfo=timezone.utc)
            q = q.filter(OHLCVData.timestamp <= end)

        bars = q.order_by(OHLCVData.timestamp.asc()).all()
        return [
            OHLCVBar(
                timestamp=b.timestamp,
                open=b.open,
                high=b.high,
                low=b.low,
                close=b.close,
                volume=b.volume,
            )
            for b in bars
        ]
