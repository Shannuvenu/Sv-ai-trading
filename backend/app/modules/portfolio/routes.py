from decimal import Decimal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import io
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.portfolio.models import Portfolio, Holding, Transaction, TransactionSide, PortfolioSnapshot
from app.modules.portfolio.schemas import (
    PortfolioCreate,
    PortfolioResponse,
    HoldingResponse,
    TransactionResponse,
    TradeRequest,
    PortfolioSummary,
)
from app.modules.market_data.utils import resolve_market_provider

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


def _enrich_holding(holding: Holding, db: Session) -> HoldingResponse:
    provider = resolve_market_provider(db)
    quote = provider.get_quote(holding.symbol)
    current_price = float(quote.last_price) if quote else 0.0
    cost_basis = float(holding.average_price) * float(holding.quantity)
    market_value = current_price * float(holding.quantity)
    unrealised_pnl = market_value - cost_basis
    unrealised_pnl_pct = (unrealised_pnl / cost_basis * 100) if cost_basis > 0 else 0.0

    return HoldingResponse(
        id=holding.id,
        symbol=holding.symbol,
        quantity=holding.quantity,
        average_price=holding.average_price,
        current_price=current_price,
        cost_basis=cost_basis,
        market_value=market_value,
        unrealised_pnl=unrealised_pnl,
        unrealised_pnl_pct=unrealised_pnl_pct,
    )


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    payload: PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    portfolio = Portfolio(
        user_id=current_user.id,
        name=payload.name,
        initial_cash=payload.initial_cash,
        cash_balance=payload.initial_cash,
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.get("", response_model=list[PortfolioResponse])
def list_portfolios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()


@router.get("/{portfolio_id}", response_model=PortfolioSummary)
def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio_id).all()
    enriched = [_enrich_holding(h, db) for h in holdings]
    market_value = sum((h.market_value or 0.0) for h in enriched)
    invested_cost = sum((h.cost_basis or 0.0) for h in enriched)
    unrealised_pnl = market_value - invested_cost
    unrealised_pnl_pct = (unrealised_pnl / invested_cost * 100) if invested_cost > 0 else 0.0
    equity = float(portfolio.cash_balance) + market_value

    transactions = (
        db.query(Transaction)
        .filter(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.executed_at.desc())
        .limit(20)
        .all()
    )

    return PortfolioSummary(
        portfolio=PortfolioResponse.model_validate(portfolio),
        cash_balance=portfolio.cash_balance,
        invested_cost=invested_cost,
        market_value=market_value,
        equity=equity,
        unrealised_pnl=unrealised_pnl,
        unrealised_pnl_pct=unrealised_pnl_pct,
        holdings=enriched,
        recent_transactions=[
            TransactionResponse.model_validate(t) for t in transactions
        ],
    )


@router.get("/{portfolio_id}/transactions", response_model=list[TransactionResponse])
def get_transactions(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return (
        db.query(Transaction)
        .filter(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.executed_at.desc())
        .all()
    )


@router.post("/{portfolio_id}/buy", response_model=TransactionResponse)
def buy(
    portfolio_id: int,
    payload: TradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    provider = resolve_market_provider(db)
    quote = provider.get_quote(payload.symbol.upper())
    if not quote:
        raise HTTPException(status_code=404, detail=f"Instrument {payload.symbol} not found")

    total_value = Decimal(str(payload.price * payload.quantity))

    if portfolio.cash_balance < total_value:
        raise HTTPException(status_code=400, detail="Insufficient cash balance")

    symbol = payload.symbol.upper()

    portfolio.cash_balance -= total_value

    txn = Transaction(
        portfolio_id=portfolio_id,
        symbol=symbol,
        side=TransactionSide.BUY,
        quantity=payload.quantity,
        price=payload.price,
        total_value=total_value,
    )
    db.add(txn)

    holding = db.query(Holding).filter(
        Holding.portfolio_id == portfolio_id,
        Holding.symbol == symbol,
    ).first()

    if holding:
        total_cost = (holding.average_price * holding.quantity) + total_value
        new_quantity = holding.quantity + payload.quantity
        holding.average_price = total_cost / new_quantity
        holding.quantity = new_quantity
    else:
        holding = Holding(
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity=payload.quantity,
            average_price=payload.price,
        )
        db.add(holding)

    db.commit()
    db.refresh(txn)
    return txn


@router.post("/{portfolio_id}/sell", response_model=TransactionResponse)
def sell(
    portfolio_id: int,
    payload: TradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    symbol = payload.symbol.upper()

    provider = resolve_market_provider(db)
    quote = provider.get_quote(symbol)
    if not quote:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found")

    holding = db.query(Holding).filter(
        Holding.portfolio_id == portfolio_id,
        Holding.symbol == symbol,
    ).first()

    if not holding or holding.quantity < payload.quantity:
        raise HTTPException(status_code=400, detail="Insufficient holdings to sell")

    total_value = Decimal(str(payload.price * payload.quantity))

    holding.quantity -= payload.quantity

    portfolio.cash_balance += total_value

    txn = Transaction(
        portfolio_id=portfolio_id,
        symbol=symbol,
        side=TransactionSide.SELL,
        quantity=payload.quantity,
        price=payload.price,
        total_value=total_value,
    )
    db.add(txn)

    if holding.quantity == 0:
        db.delete(holding)

    db.commit()
    db.refresh(txn)
    return txn


@router.post("/{portfolio_id}/snapshot")
def create_snapshot(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    provider = resolve_market_provider(db)
    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio_id).all()

    market_value = Decimal("0")
    for h in holdings:
        q = provider.get_quote(h.symbol)
        if q:
            market_value += q.last_price * h.quantity

    invested_cost = sum((h.average_price * h.quantity) for h in holdings)
    equity = portfolio.cash_balance + market_value
    unrealised_pnl = market_value - invested_cost

    snapshot = PortfolioSnapshot(
        portfolio_id=portfolio_id,
        snapshot_date=datetime.now(timezone.utc),
        equity=equity,
        cash_balance=portfolio.cash_balance,
        invested_cost=invested_cost,
        market_value=market_value,
        unrealised_pnl=unrealised_pnl,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {"id": snapshot.id, "equity": float(snapshot.equity), "snapshot_date": snapshot.snapshot_date.isoformat()}


@router.get("/{portfolio_id}/snapshots")
def list_snapshots(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    snapshots = (
        db.query(PortfolioSnapshot)
        .filter(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .all()
    )
    return [
        {
            "snapshot_date": s.snapshot_date.isoformat(),
            "equity": float(s.equity),
            "cash_balance": float(s.cash_balance),
            "invested_cost": float(s.invested_cost),
            "market_value": float(s.market_value),
            "unrealised_pnl": float(s.unrealised_pnl),
        }
        for s in snapshots
    ]


@router.get("/{portfolio_id}/export")
def export_csv(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["type", "symbol", "side", "quantity", "price", "total_value", "executed_at"])
    transactions = (
        db.query(Transaction)
        .filter(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.executed_at.asc())
        .all()
    )
    for t in transactions:
        writer.writerow(["transaction", t.symbol, t.side.value, t.quantity, float(t.price), float(t.total_value), t.executed_at.isoformat()])

    writer.writerow([])
    writer.writerow(["type", "snapshot_date", "equity", "cash_balance", "invested_cost", "market_value", "unrealised_pnl"])
    snapshots = (
        db.query(PortfolioSnapshot)
        .filter(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .all()
    )
    for s in snapshots:
        writer.writerow(["snapshot", s.snapshot_date.isoformat(), float(s.equity), float(s.cash_balance), float(s.invested_cost), float(s.market_value), float(s.unrealised_pnl)])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=portfolio_{portfolio_id}_export.csv"},
    )


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete(portfolio)
    db.commit()
