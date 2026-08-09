"""Portfolio Analytics — win rate, Sharpe ratio, drawdown, trade history metrics."""
import math
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.portfolio.models import Portfolio, Holding, Transaction, TransactionSide, PortfolioSnapshot

router = APIRouter(prefix="/portfolio/{portfolio_id}/analytics", tags=["Portfolio Analytics"])


@router.get("")
def get_analytics(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio or portfolio.user_id != user.id:
        raise HTTPException(403 if portfolio else 404, "Not found")

    transactions = (
        db.query(Transaction)
        .filter(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.executed_at.asc())
        .all()
    )
    snapshots = (
        db.query(PortfolioSnapshot)
        .filter(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .all()
    )
    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio_id).all()

    # Pairs of BUY→SELL for trade analysis
    trades = _extract_trades(transactions)
    total_trades = len(trades)
    winning_trades = [t for t in trades if t["pnl"] > 0]
    losing_trades = [t for t in trades if t["pnl"] <= 0]
    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

    total_pnl = sum(t["pnl"] for t in trades)
    total_invested = sum(t["buy_value"] for t in trades)
    avg_win = sum(t["pnl"] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t["pnl"] for t in losing_trades) / len(losing_trades) if losing_trades else 0

    gross_profit = sum(t["pnl"] for t in winning_trades)
    gross_loss = abs(sum(t["pnl"] for t in losing_trades))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999 if gross_profit > 0 else 0)

    # Max drawdown from snapshots
    max_drawdown = 0.0
    peak = 0.0
    for s in snapshots:
        eq = float(s.equity)
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak * 100
            if dd > max_drawdown:
                max_drawdown = dd

    # Sharpe ratio
    sharpe = _calculate_sharpe(snapshots, trades)

    # Monthly returns
    monthly = {}
    for t in trades:
        if t["sell_date"]:
            month_key = t["sell_date"].strftime("%Y-%m")
            monthly.setdefault(month_key, 0)
            monthly[month_key] += t["pnl"]

    # Sector allocation
    sector_map = {}
    for h in holdings:
        sector = _get_sector(h.symbol)
        sector_map[sector] = sector_map.get(sector, 0) + float(h.average_price * h.quantity)

    # AI vs Manual
    from app.modules.ai_trader.models import TradeDecision
    ai_decisions = (
        db.query(TradeDecision)
        .filter(TradeDecision.user_id == user.id, TradeDecision.decision == "EXECUTED")
        .count()
    )
    ai_trades = sum(1 for t in trades if t.get("is_ai"))
    manual_trades = total_trades - ai_trades

    return {
        "total_trades": total_trades,
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 2),
        "total_invested": round(total_invested, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != 999 else "∞",
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 3) if sharpe is not None else None,
        "initial_capital": float(portfolio.initial_cash),
        "current_equity": float(portfolio.cash_balance) + sum(
            float(h.average_price * h.quantity) for h in holdings
        ),
        "cash_balance": float(portfolio.cash_balance),
        "sector_allocation": sector_map,
        "monthly_returns": monthly,
        "recent_trades": trades[-20:],
        "ai_trades": ai_trades,
        "manual_trades": manual_trades,
    }


def _extract_trades(transactions: list[Transaction]) -> list[dict]:
    """Extract trade pairs (BUY→SELL or SELL→BUY) with P&L."""
    trades = []
    open_positions: dict[str, list[dict]] = {}  # symbol -> [open_buys]

    for txn in transactions:
        sym = txn.symbol
        if sym not in open_positions:
            open_positions[sym] = []

        if txn.side == TransactionSide.BUY:
            open_positions[sym].append({
                "buy_date": txn.executed_at,
                "buy_price": float(txn.price),
                "qty": txn.quantity,
                "buy_value": float(txn.total_value),
            })
        elif txn.side == TransactionSide.SELL:
            sell_qty = txn.quantity
            while sell_qty > 0 and open_positions[sym]:
                pos = open_positions[sym][0]
                match_qty = min(sell_qty, pos["qty"])
                pnl = (float(txn.price) - pos["buy_price"]) * match_qty
                trades.append({
                    "symbol": sym,
                    "buy_date": pos["buy_date"],
                    "buy_price": pos["buy_price"],
                    "sell_date": txn.executed_at,
                    "sell_price": float(txn.price),
                    "qty": match_qty,
                    "pnl": pnl,
                    "buy_value": pos["buy_price"] * match_qty,
                    "sell_value": float(txn.price) * match_qty,
                    "is_ai": False,
                })
                pos["qty"] -= match_qty
                sell_qty -= match_qty
                if pos["qty"] == 0:
                    open_positions[sym].pop(0)

    return trades


def _calculate_sharpe(snapshots, trades, risk_free=5.0) -> float | None:
    """Calculate annualized Sharpe ratio."""
    if len(snapshots) < 10:
        return None

    daily_returns = []
    for i in range(1, len(snapshots)):
        prev = float(snapshots[i - 1].equity)
        curr = float(snapshots[i].equity)
        if prev > 0:
            daily_returns.append((curr - prev) / prev)

    if not daily_returns:
        return None

    avg_return = sum(daily_returns) / len(daily_returns)
    variance = sum((r - avg_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    std_dev = math.sqrt(variance) if variance > 0 else 0

    if std_dev == 0:
        return None

    sharpe = ((avg_return * 252) - (risk_free / 100)) / (std_dev * math.sqrt(252))
    return sharpe


def _get_sector(symbol: str) -> str:
    sectors = {
        "RELIANCE": "Oil & Gas",
        "TCS": "IT",
        "INFY": "IT",
        "HDFCBANK": "Banking",
        "ICICIBANK": "Banking",
        "SBIN": "Banking",
        "HINDUNILVR": "FMCG",
        "KOTAKBANK": "Banking",
        "BHARTIARTL": "Telecom",
        "ITC": "FMCG",
    }
    return sectors.get(symbol, "Other")
