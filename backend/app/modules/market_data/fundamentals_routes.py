"""Fundamentals routes — company profile, financials, peers."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.market_data.fundamentals_client import get_fundamentals_client

router = APIRouter(prefix="/fundamentals", tags=["Fundamentals"])


@router.get("/profile/{symbol}")
def company_profile(
    symbol: str,
    user: User = Depends(get_current_user),
):
    client = get_fundamentals_client()
    if not client.is_configured:
        raise HTTPException(503, "Finnhub fundamentals not configured")
    result = client.get_company_profile(symbol.upper())
    if not result:
        raise HTTPException(404, f"No profile data for {symbol}")
    return result


@router.get("/financials/{symbol}")
def financial_metrics(
    symbol: str,
    user: User = Depends(get_current_user),
):
    client = get_fundamentals_client()
    if not client.is_configured:
        raise HTTPException(503, "Finnhub fundamentals not configured")
    result = client.get_basic_financials(symbol.upper())
    if not result:
        raise HTTPException(404, f"No financial data for {symbol}")
    return result


@router.get("/peers/{symbol}")
def peers(
    symbol: str,
    user: User = Depends(get_current_user),
):
    client = get_fundamentals_client()
    if not client.is_configured:
        raise HTTPException(503, "Finnhub fundamentals not configured")
    return {"peers": client.get_peers(symbol.upper())}
