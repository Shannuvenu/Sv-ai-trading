from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from app.modules.market_data.models import Instrument as DBInstrument, OHLCVData
from app.modules.market_data.provider import (
    MarketDataProvider, Quote, OHLCVBar, InstrumentInfo,
)
from app.modules.market_data.mock_provider import (
    STOCKS, BASE_PRICES, VOLATILITIES, _generate_ohlcv,
)


def seed_instruments(db: Session):
    for i, stock in enumerate(STOCKS):
        existing = db.query(DBInstrument).filter(DBInstrument.symbol == stock["symbol"]).first()
        if not existing:
            db.add(DBInstrument(
                symbol=stock["symbol"],
                name=stock["name"],
                exchange="NSE",
                sector=stock["sector"],
                instrument_type="equity",
                currency="INR",
                is_active=True,
            ))
    db.commit()


def seed_ohlcv_data(db: Session, days: int = 365):
    instruments = db.query(DBInstrument).all()
    inst_map = {i.symbol: i for i in instruments}

    for symbol in [s["symbol"] for s in STOCKS]:
        inst = inst_map.get(symbol)
        if not inst:
            continue
        existing_count = db.query(OHLCVData).filter(
            OHLCVData.instrument_id == inst.id
        ).count()
        if existing_count > 0:
            continue

        bp = BASE_PRICES.get(symbol, Decimal("1000.00"))
        vol = VOLATILITIES.get(symbol, Decimal("0.01"))
        bars = _generate_ohlcv(symbol, bp, vol, days)

        batch = []
        for bar in bars:
            batch.append(OHLCVData(
                instrument_id=inst.id,
                timestamp=bar.timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
            ))
            if len(batch) >= 500:
                db.bulk_save_objects(batch)
                db.commit()
                batch = []
        if batch:
            db.bulk_save_objects(batch)
            db.commit()


def seed_all(db: Session):
    seed_instruments(db)
    seed_ohlcv_data(db)
    print("Seed complete: instruments and OHLCV data populated.")
