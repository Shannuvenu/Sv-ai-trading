from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.portfolio.models import Portfolio, Holding
from app.modules.risk.analyzer import analyze_risk

router = APIRouter(prefix="/risk", tags=["Risk"])


@router.get("/portfolio/{portfolio_id}")
def get_risk(
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
    return analyze_risk(holdings, portfolio.cash_balance, db)
