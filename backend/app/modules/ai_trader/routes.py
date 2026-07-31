"""AI Trader routes — config, strategies, decisions, paper execution."""
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.portfolio.models import Portfolio, Holding, Transaction, TransactionSide
from app.modules.market_data.utils import resolve_market_provider
from app.modules.technical_analysis.indicators import compute_indicators
from app.modules.ai_trader.models import (
    AITraderConfig, Strategy, StrategyPerformance, TradeDecision, RiskEvent,
)
from app.modules.ai_trader.strategies import STRATEGIES, evaluate_strategy
from app.modules.ai_trader.risk_engine import (
    calculate_position_size, calculate_stop_loss, calculate_take_profit,
    check_daily_loss_limit, check_drawdown_limit,
)

router = APIRouter(prefix="/ai-trader", tags=["AI Trader"])


@router.get("/config")
def get_config(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cfg = db.query(AITraderConfig).filter(AITraderConfig.user_id == user.id).first()
    if not cfg:
        return {"is_active": False, "risk_profile": "MODERATE", "trading_mode": "PAPER"}
    return cfg


@router.put("/config")
def update_config(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cfg = db.query(AITraderConfig).filter(AITraderConfig.user_id == user.id).first()
    if not cfg:
        cfgs = db.query(AITraderConfig).filter(AITraderConfig.user_id == user.id).all()
        cfg = AITraderConfig(user_id=user.id)
        db.add(cfg)
    for k, v in payload.items():
        if hasattr(cfg, k):
            setattr(cfg, k, v)
    db.commit()
    db.refresh(cfg)
    return cfg


@router.get("/strategies")
def list_strategies():
    return STRATEGIES


@router.post("/scan")
def scan_market(
    symbol: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Scan a single symbol across all strategies with full risk assessment."""
    provider = resolve_market_provider(db)
    if not provider:
        raise HTTPException(503, "Market data unavailable")

    quote = provider.get_quote(symbol.upper())
    if not quote:
        raise HTTPException(404, f"Instrument {symbol} not found")

    bars = provider.get_history(symbol.upper(), days=252)
    if len(bars) < 50:
        raise HTTPException(400, "Insufficient data (need 50+ days)")

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]

    indicators = compute_indicators(closes, highs, lows, volumes)

    results = {}
    for name in STRATEGIES:
        results[name] = evaluate_strategy(name, indicators, float(quote.close))

    # Risk estimate
    entry_price = float(quote.close)
    stop_loss = calculate_stop_loss(entry_price, 3.0)
    take_profit = calculate_take_profit(entry_price, 6.0)

    # Get portfolio
    cfg = db.query(AITraderConfig).filter(AITraderConfig.user_id == user.id).first()
    capital = 100000.0
    portfolio_id = None
    if cfg and cfg.portfolio_id:
        pf = db.query(Portfolio).filter(Portfolio.id == cfg.portfolio_id).first()
        if pf and pf.user_id == user.id:
            capital = float(pf.cash_balance)
            portfolio_id = pf.id

    qty = calculate_position_size(capital, entry_price, stop_loss)

    # Check existing positions
    if portfolio_id:
        holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio_id).all()
        existing = [h for h in holdings if h.symbol == symbol.upper()]
    else:
        existing = []

    return {
        "symbol": symbol.upper(),
        "last_price": entry_price,
        "strategies": results,
        "risk": {
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "quantity": qty,
            "risk_amount": round(qty * (entry_price - stop_loss), 2),
            "capital": capital,
            "existing_position": bool(existing),
            "existing_quantity": existing[0].quantity if existing else 0,
        },
    }


@router.post("/execute")
def execute_trade(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Execute a paper trade through the AI trader (same BUY/SELL as manual)."""
    symbol = payload["symbol"].upper()
    direction = payload["direction"]  # BUY or SELL
    strategy_name = payload.get("strategy", "")
    reasoning = payload.get("reasoning", "")

    cfg = db.query(AITraderConfig).filter(AITraderConfig.user_id == user.id).first()
    if not cfg or not cfg.portfolio_id:
        raise HTTPException(400, "AI Trader not configured. Create a portfolio first.")

    portfolio = db.query(Portfolio).filter(
        Portfolio.id == cfg.portfolio_id, Portfolio.user_id == user.id
    ).first()
    if not portfolio:
        raise HTTPException(404, "Portfolio not found")

    provider = resolve_market_provider(db)
    quote = provider.get_quote(symbol)
    if not quote:
        raise HTTPException(404, f"Instrument {symbol} not found")

    ltp = float(quote.close)

    # Log the decision
    strategy_id = None
    if strategy_name:
        strat = db.query(Strategy).filter(Strategy.name == strategy_name).first()
        if strat:
            strategy_id = strat.id

    decision = TradeDecision(
        user_id=user.id,
        symbol=symbol,
        direction=direction,
        decision="APPROVED",
        strategy_id=strategy_id,
        ltp=ltp,
        reasoning=reasoning,
        market_regime="CLOSED",
        risk_score=payload.get("risk_score"),
    )

    if direction == "BUY":
        qty = int(payload.get("quantity", 1))
        price = float(payload.get("price", ltp))
        total_value = price * qty
        if portfolio.cash_balance < Decimal(str(total_value)):
            decision.decision = "REJECTED"
            decision.rejection_reason = "Insufficient cash"
            db.add(decision)
            db.commit()
            return {"decision": "REJECTED", "reason": "Insufficient cash"}

        portfolio.cash_balance -= Decimal(str(total_value))
        txn = Transaction(
            portfolio_id=portfolio.id, symbol=symbol, side=TransactionSide.BUY,
            quantity=qty, price=Decimal(str(price)), total_value=Decimal(str(total_value)),
        )
        db.add(txn)
        db.flush()
        decision.transaction_id = txn.id

        holding = db.query(Holding).filter(
            Holding.portfolio_id == portfolio.id, Holding.symbol == symbol
        ).first()
        if holding:
            total_cost = (holding.average_price * holding.quantity) + Decimal(str(total_value))
            holding.average_price = total_cost / (holding.quantity + qty)
            holding.quantity += qty
        else:
            db.add(Holding(
                portfolio_id=portfolio.id, symbol=symbol,
                quantity=qty, average_price=Decimal(str(price)),
            ))

    elif direction == "SELL":
        holding = db.query(Holding).filter(
            Holding.portfolio_id == portfolio.id, Holding.symbol == symbol
        ).first()
        qty = int(payload.get("quantity", 0))
        if not holding or holding.quantity < qty:
            decision.decision = "REJECTED"
            decision.rejection_reason = "Insufficient holdings"
            db.add(decision)
            db.commit()
            return {"decision": "REJECTED", "reason": "Insufficient holdings"}

        price = float(payload.get("price", ltp))
        total_value = price * qty
        holding.quantity -= qty
        portfolio.cash_balance += Decimal(str(total_value))
        txn = Transaction(
            portfolio_id=portfolio.id, symbol=symbol, side=TransactionSide.SELL,
            quantity=qty, price=Decimal(str(price)), total_value=Decimal(str(total_value)),
        )
        db.add(txn)
        db.flush()
        decision.transaction_id = txn.id
        if holding.quantity == 0:
            db.delete(holding)

    decision.decision = "EXECUTED"
    db.add(decision)
    db.commit()
    return {
        "decision": "EXECUTED",
        "symbol": symbol,
        "direction": direction,
        "quantity": qty,
        "price": price,
        "transaction_id": decision.transaction_id,
    }


@router.get("/decisions")
def get_decisions(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(TradeDecision)
        .filter(TradeDecision.user_id == user.id)
        .order_by(TradeDecision.timestamp.desc())
        .limit(limit)
        .all()
    )


@router.post("/risk-event")
def log_risk_event(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = RiskEvent(
        user_id=user.id,
        event_type=payload.get("event_type", "UNKNOWN"),
        description=payload.get("description", ""),
        details_json=str(payload.get("details", {})),
    )
    db.add(event)
    db.commit()
    return {"logged": True}
