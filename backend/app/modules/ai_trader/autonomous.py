"""Autonomous AI Trader — background scheduler for continuous market monitoring."""
import logging
import json
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.modules.market_data.utils import resolve_market_provider
from app.modules.technical_analysis.indicators import compute_indicators
from app.modules.ai_trader.gemini_service import get_gemini_service
from app.modules.ai_trader.strategies import STRATEGIES, evaluate_strategy
from app.modules.ai_trader.risk_engine import (
    calculate_position_size, calculate_stop_loss, calculate_take_profit,
    check_daily_loss_limit, check_drawdown_limit,
)
from app.modules.ai_trader.models import (
    AITraderConfig, TradeDecision, RiskEvent, StrategyPerformance,
)
from app.modules.portfolio.models import Portfolio, Holding, Transaction, TransactionSide
from app.modules.news.models import NewsArticle
from app.modules.market_data.models import Instrument

settings = get_settings()
logger = logging.getLogger("autonomous_trader")

# Symbols to monitor
WATCH_SYMBOLS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "HINDUNILVR", "KOTAKBANK", "BHARTIARTL", "ITC"]

COOLDOWN_MINUTES = 15  # Don't trade same symbol within cooldown


def run_autonomous_cycle():
    """Main autonomous trading cycle — called by APScheduler every N minutes."""
    db = SessionLocal()
    try:
        active_configs = db.query(AITraderConfig).filter(
            AITraderConfig.is_active == True
        ).all()

        if not active_configs:
            logger.debug("No active AI Trader configs.")
            return

        for cfg in active_configs:
            if cfg.trading_mode != "PAPER":
                logger.warning(f"User {cfg.user_id} has LIVE trading mode — blocking for safety.")
                _log_risk_event(db, cfg.user_id, "KILL_SWITCH", "LIVE trading mode blocked — only PAPER allowed")
                continue

            _process_config(db, cfg)

    except Exception as e:
        logger.error(f"Autonomous cycle failed: {e}", exc_info=True)
    finally:
        db.close()


def _process_config(db: Session, cfg: AITraderConfig):
    """Process one user's AI Trader config — scan all symbols, find opportunities."""
    if not cfg.portfolio_id:
        return

    portfolio = db.query(Portfolio).filter(Portfolio.id == cfg.portfolio_id).first()
    if not portfolio or portfolio.user_id != cfg.user_id:
        return

    provider = resolve_market_provider(db)
    if not provider:
        return

    capital = float(portfolio.cash_balance)
    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio.id).all()
    open_symbols = {h.symbol for h in holdings}
    max_open = cfg.max_open_positions or 3

    gemini = get_gemini_service()
    opportunities = []

    for symbol in WATCH_SYMBOLS:
        if len(open_symbols) >= max_open and symbol not in open_symbols:
            continue

        if not _check_cooldown(db, cfg.user_id, symbol):
            continue

        quote = provider.get_quote(symbol)
        if not quote:
            continue

        bars = provider.get_history(symbol, days=200)
        if len(bars) < 50:
            continue

        closes = [b.close for b in bars]
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        volumes = [b.volume for b in bars]
        indicators = compute_indicators(closes, highs, lows, volumes)

        news = (
            db.query(NewsArticle)
            .filter(NewsArticle.symbol == symbol)
            .order_by(NewsArticle.published_at.desc())
            .limit(10)
            .all()
        )
        headlines = [n.headline for n in news]

        try:
            analysis = gemini.analyze(
                symbol=symbol,
                last_price=float(quote.close),
                change_pct=float(quote.change_pct),
                indicators=indicators,
                news_headlines=headlines,
                portfolio_context={
                    "current_capital": capital,
                    "max_capital_per_trade": float(cfg.max_capital_per_trade or 5000),
                    "max_daily_loss_pct": cfg.max_daily_loss_pct,
                    "open_positions": list(open_symbols),
                    "stop_loss_pct": cfg.stop_loss_pct,
                    "take_profit_pct": cfg.take_profit_pct,
                },
            )
        except Exception as e:
            logger.error(f"Gemini analysis failed for {symbol}: {e}")
            continue

        if analysis["decision"] == "HOLD" or analysis["confidence"] < 50:
            continue

        opportunities.append({
            "symbol": symbol,
            "analysis": analysis,
            "last_price": float(quote.close),
        })

    if not opportunities:
        return

    # Sort by confidence, pick best
    opportunities.sort(key=lambda x: x["analysis"]["confidence"], reverse=True)

    best = opportunities[0]
    symbol = best["symbol"]
    analysis = best["analysis"]

    ltp = float(analysis["entry"])
    stop_loss = float(analysis["stop_loss"])
    take_profit = float(analysis["take_profit"])
    max_capital_per_trade = float(cfg.max_capital_per_trade or 5000)

    # Risk checks
    qty = calculate_position_size(capital, ltp, stop_loss, risk_pct=1.0, max_position_pct=cfg.position_size_pct)
    if qty <= 0:
        return

    total_value = qty * ltp
    if total_value > max_capital_per_trade:
        qty = max(1, int(max_capital_per_trade / ltp))
        total_value = qty * ltp

    if total_value > capital:
        return

    # Execute paper trade
    decision = TradeDecision(
        user_id=cfg.user_id,
        symbol=symbol,
        direction=analysis["decision"],
        decision="APPROVED",
        ltp=ltp,
        quantity=qty,
        entry_price=ltp,
        stop_loss=stop_loss,
        take_profit=take_profit,
        reasoning=analysis.get("reasoning", ""),
        market_regime=analysis.get("market_context", "NEUTRAL"),
        risk_score=100 - analysis.get("confidence", 50),
    )

    try:
        portfolio.cash_balance -= Decimal(str(total_value))
        txn = Transaction(
            portfolio_id=portfolio.id,
            symbol=symbol,
            side=TransactionSide.BUY if analysis["decision"] == "BUY" else TransactionSide.SELL,
            quantity=qty,
            price=Decimal(str(ltp)),
            total_value=Decimal(str(total_value)),
        )
        db.add(txn)
        db.flush()
        decision.transaction_id = txn.id

        existing = db.query(Holding).filter(
            Holding.portfolio_id == portfolio.id,
            Holding.symbol == symbol
        ).first()
        if existing:
            total_cost = (existing.average_price * existing.quantity) + Decimal(str(total_value))
            existing.average_price = total_cost / (existing.quantity + qty)
            existing.quantity += qty
        else:
            db.add(Holding(
                portfolio_id=portfolio.id, symbol=symbol,
                quantity=qty, average_price=Decimal(str(ltp)),
            ))

        decision.decision = "EXECUTED"
        logger.info(f"[AUTONOMOUS] {analysis['decision']} {symbol} x{qty} @ ₹{ltp:.2f} — Confidence: {analysis['confidence']}%")

    except Exception as e:
        decision.decision = "REJECTED"
        decision.rejection_reason = str(e)
        logger.error(f"Autonomous trade failed for {symbol}: {e}")

    db.add(decision)
    db.commit()


def _check_cooldown(db: Session, user_id: int, symbol: str) -> bool:
    """Prevent duplicate trades within cooldown period."""
    from datetime import timedelta
    recent = (
        db.query(TradeDecision)
        .filter(
            TradeDecision.user_id == user_id,
            TradeDecision.symbol == symbol,
            TradeDecision.decision.in_(["EXECUTED", "APPROVED"]),
        )
        .order_by(TradeDecision.timestamp.desc())
        .first()
    )
    if not recent:
        return True
    if recent.timestamp:
        elapsed = (datetime.now(timezone.utc) - recent.timestamp).total_seconds() / 60
        return elapsed >= COOLDOWN_MINUTES
    return True


def _log_risk_event(db: Session, user_id: int, event_type: str, description: str):
    event = RiskEvent(
        user_id=user_id,
        event_type=event_type,
        description=description,
    )
    db.add(event)
    db.commit()


def run_position_monitor():
    """Monitor open positions — check stop loss, take profit, trailing stops."""
    db = SessionLocal()
    try:
        configs = db.query(AITraderConfig).filter(AITraderConfig.is_active == True).all()
        provider = resolve_market_provider(db)

        for cfg in configs:
            if not cfg.portfolio_id:
                continue
            portfolio = db.query(Portfolio).filter(Portfolio.id == cfg.portfolio_id).first()
            if not portfolio:
                continue

            holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio.id).all()
            if not holdings:
                continue

            recent_decisions = (
                db.query(TradeDecision)
                .filter(TradeDecision.user_id == cfg.user_id, TradeDecision.decision == "EXECUTED")
                .order_by(TradeDecision.timestamp.desc())
                .limit(len(holdings) * 2)
                .all()
            )
            decision_map = {}
            for d in recent_decisions:
                if d.symbol not in decision_map:
                    decision_map[d.symbol] = d

            for holding in holdings:
                quote = provider.get_quote(holding.symbol)
                if not quote:
                    continue

                ltp = float(quote.close)
                avg_price = float(holding.average_price)
                pnl_pct = ((ltp - avg_price) / avg_price) * 100

                decision = decision_map.get(holding.symbol)
                if not decision:
                    continue

                stop_loss = float(decision.stop_loss or 0)
                take_profit = float(decision.take_profit or 0)
                direction = decision.direction

                should_exit = False
                exit_reason = ""

                if direction == "BUY":
                    if stop_loss > 0 and ltp <= stop_loss:
                        should_exit = True
                        exit_reason = f"Stop loss hit: ₹{stop_loss:.2f}"
                    elif take_profit > 0 and ltp >= take_profit:
                        should_exit = True
                        exit_reason = f"Take profit hit: ₹{take_profit:.2f}"
                elif direction == "SELL":
                    if stop_loss > 0 and ltp >= stop_loss:
                        should_exit = True
                        exit_reason = f"Stop loss hit: ₹{stop_loss:.2f}"
                    elif take_profit > 0 and ltp <= take_profit:
                        should_exit = True
                        exit_reason = f"Take profit hit: ₹{take_profit:.2f}"

                if should_exit:
                    total_value = ltp * holding.quantity
                    exit_side = TransactionSide.SELL if direction == "BUY" else TransactionSide.BUY

                    portfolio.cash_balance += Decimal(str(total_value))
                    txn = Transaction(
                        portfolio_id=portfolio.id, symbol=holding.symbol,
                        side=exit_side, quantity=holding.quantity,
                        price=Decimal(str(ltp)), total_value=Decimal(str(total_value)),
                    )
                    db.add(txn)
                    db.delete(holding)

                    exit_decision = TradeDecision(
                        user_id=cfg.user_id, symbol=holding.symbol,
                        direction=exit_side.value, decision="EXECUTED",
                        ltp=ltp, quantity=holding.quantity,
                        reasoning=f"AUTO EXIT: {exit_reason} (P&L: {pnl_pct:.1f}%)",
                    )
                    db.add(exit_decision)
                    logger.info(f"[MONITOR] Auto-exit {holding.symbol}: {exit_reason} (P&L: {pnl_pct:.1f}%)")

        db.commit()
    except Exception as e:
        logger.error(f"Position monitor failed: {e}", exc_info=True)
    finally:
        db.close()
