from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    exchange = Column(String(50), nullable=False, default="NSE")
    sector = Column(String(100), nullable=True)
    instrument_type = Column(String(20), nullable=False, default="equity")
    currency = Column(String(10), nullable=False, default="INR")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OHLCVData(Base):
    __tablename__ = "ohlcv_data"

    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Numeric(15, 2), nullable=False)
    high = Column(Numeric(15, 2), nullable=False)
    low = Column(Numeric(15, 2), nullable=False)
    close = Column(Numeric(15, 2), nullable=False)
    volume = Column(Integer, nullable=False)
