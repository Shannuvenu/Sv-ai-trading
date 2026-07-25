from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class TransactionSide(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    initial_cash = Column(Numeric(18, 2), nullable=False)
    cash_balance = Column(Numeric(18, 2), nullable=False)
    is_paper = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    average_price = Column(Numeric(18, 2), nullable=False)

    portfolio = relationship("Portfolio", back_populates="holdings")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    side = Column(SAEnum(TransactionSide), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(18, 2), nullable=False)
    total_value = Column(Numeric(18, 2), nullable=False)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

    portfolio = relationship("Portfolio", back_populates="transactions")


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_date = Column(DateTime(timezone=True), nullable=False, index=True)
    equity = Column(Numeric(18, 2), nullable=False)
    cash_balance = Column(Numeric(18, 2), nullable=False)
    invested_cost = Column(Numeric(18, 2), nullable=False)
    market_value = Column(Numeric(18, 2), nullable=False)
    unrealised_pnl = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
