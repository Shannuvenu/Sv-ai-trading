"""
AI Trader models — configs, strategies, decisions, risk events.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, ForeignKey, Float, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class AITraderConfig(Base):
    __tablename__ = "ai_trader_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    trading_mode = Column(String(20), default="PAPER", nullable=False)  # PAPER only
    risk_profile = Column(String(20), default="MODERATE", nullable=False)
    max_capital_per_trade = Column(Numeric(12, 2), default=5000)
    max_open_positions = Column(Integer, default=3)
    max_daily_loss_pct = Column(Float, default=2.0)
    max_portfolio_drawdown_pct = Column(Float, default=15.0)
    max_consecutive_losses = Column(Integer, default=5)
    stop_loss_pct = Column(Float, default=3.0)
    take_profit_pct = Column(Float, default=6.0)
    position_size_pct = Column(Float, default=20.0)
    allowed_symbols = Column(Text, nullable=True)  # comma-separated
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    version = Column(Integer, default=1)
    status = Column(String(20), default="DRAFT", nullable=False)
    description = Column(Text, nullable=True)
    timeframe = Column(String(10), default="1D", nullable=False)
    params_json = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StrategyPerformance(Base):
    __tablename__ = "strategy_performance"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    environment = Column(String(10), nullable=False)  # BACKTEST, PAPER, LIVE
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    total_pnl = Column(Numeric(12, 2), default=0)
    max_drawdown_pct = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


class TradeDecision(Base):
    __tablename__ = "trade_decisions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    direction = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    decision = Column(String(20), nullable=False)  # APPROVED, REJECTED, EXECUTED
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    ltp = Column(Numeric(12, 2), nullable=True)
    quantity = Column(Integer, nullable=True)
    entry_price = Column(Numeric(12, 2), nullable=True)
    stop_loss = Column(Numeric(12, 2), nullable=True)
    take_profit = Column(Numeric(12, 2), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)
    market_regime = Column(String(20), nullable=True)
    risk_score = Column(Float, nullable=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    event_type = Column(String(30), nullable=False)
    description = Column(Text, nullable=True)
    details_json = Column(Text, default="{}")
