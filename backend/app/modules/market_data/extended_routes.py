"""Extended market routes — search, F&O, IPO, MTF, Mutual Funds, SIP."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.market_data.instrument_client import get_instrument_client
from app.modules.market_data.upstox_provider import get_upstox_provider

router = APIRouter(prefix="/market", tags=["Market Extended"])


# ─── INSTRUMENT SEARCH ───

@router.get("/search")
def search_instruments(
    q: str = Query(..., min_length=2),
    exchange: str = Query("NSE", description="NSE or BSE"),
    user: User = Depends(get_current_user),
):
    """Real-time instrument search using Upstox master. Debounced on frontend."""
    client = get_instrument_client()
    if not client.is_configured:
        return {"results": []}
    results = client.search_all(q)
    if exchange.upper() == "NSE":
        results = [r for r in results if r.get("exchange") == "NSE"]
    elif exchange.upper() == "BSE":
        results = [r for r in results if r.get("exchange") == "BSE"]
    # Add quote data if available
    if results[:5]:
        provider = get_upstox_provider()
        if provider and provider._configured:
            try:
                syms = [r["trading_symbol"] for r in results[:20]]
                quote_map = provider._inst_client.get_quote_batch(syms, exchange)
                for r in results:
                    q = quote_map.get(r["trading_symbol"], {})
                    if q:
                        r["last_price"] = q.get("last_price")
                        r["change"] = q.get("change")
                        r["change_pct"] = q.get("change_pct")
                        r["volume"] = q.get("volume")
            except Exception:
                pass
    return {"results": results[:50], "total": len(results)}


@router.get("/batch-quotes")
def batch_quotes(
    symbols: str = Query(..., description="Comma-separated symbols"),
    exchange: str = Query("NSE"),
    user: User = Depends(get_current_user),
):
    symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if len(symbols_list) > 50:
        raise HTTPException(400, "Max 50 symbols per request")
    client = get_instrument_client()
    if not client.is_configured:
        return {"quotes": {}}
    return {"quotes": client.get_quote_batch(symbols_list, exchange)}


# ─── INDICES ───

@router.get("/indices/list")
def list_indices(user: User = Depends(get_current_user)):
    """Full index list from Upstox."""
    client = get_instrument_client()
    if not client.is_configured:
        return {"indices": []}
    instruments = client.get_index_instruments()
    # Group by common names
    results = []
    seen = set()
    index_names = [
        "NIFTY 50", "NIFTY BANK", "NIFTY IT", "NIFTY AUTO", "NIFTY FMCG",
        "NIFTY PHARMA", "NIFTY METAL", "NIFTY REALTY", "NIFTY ENERGY",
        "NIFTY FIN SERVICE", "NIFTY MIDCAP 100", "NIFTY NEXT 50",
        "SENSEX", "BANKEX",
    ]
    for idx in instruments:
        name = idx.get("name", "")
        for n in index_names:
            if n.upper() in name.upper() and name not in seen:
                seen.add(name)
                results.append({
                    "name": name,
                    "instrument_key": idx.get("instrument_key"),
                    "exchange": idx.get("exchange", ""),
                    "segment": idx.get("segment", ""),
                })
                break
    # Add fallback hardcoded indices
    return {"indices": results if results else [
        {"name": name, "instrument_key": f"NSE_INDEX|{name}", "exchange": "NSE", "segment": "NSE_INDEX"}
        for name in ["NIFTY 50", "NIFTY BANK", "SENSEX"]
    ]}


@router.get("/indices/quotes")
def index_quotes(
    symbols: str = Query("NIFTY_50,NIFTY_BANK,SENSEX"),
    user: User = Depends(get_current_user),
):
    from app.modules.market_data.indices import fetch_index_quotes
    return {"indices": fetch_index_quotes()}


# ─── F&O ───

@router.get("/fo/search")
def search_fo(
    underlying: str = Query(..., min_length=1),
    expiry: str = Query(None),
    instrument_type: str = Query("ALL", description="CE, PE, FUT, ALL"),
    user: User = Depends(get_current_user),
):
    """Search F&O instruments by underlying symbol."""
    client = get_instrument_client()
    if not client.is_configured:
        return {"results": []}
    instruments = client.get_fo_instruments()
    ul = underlying.upper()
    results = []
    for i in instruments:
        name = (i.get("name") or "").upper()
        sym = (i.get("trading_symbol") or "").upper()
        if ul in name or ul in sym:
            inst_type = (i.get("instrument_type") or "").upper()
            if instrument_type != "ALL":
                if instrument_type.upper() == "FUT" and "FUT" not in inst_type:
                    continue
                if instrument_type == "CE" and "CE" not in inst_type:
                    continue
                if instrument_type == "PE" and "PE" not in inst_type:
                    continue
            results.append({
                "trading_symbol": i.get("trading_symbol", ""),
                "name": i.get("name", ""),
                "instrument_key": i.get("instrument_key", ""),
                "exchange": i.get("exchange", ""),
                "segment": i.get("segment", ""),
                "instrument_type": inst_type,
                "expiry": i.get("expiry", ""),
                "strike": i.get("strike", 0),
                "lot_size": i.get("lot_size", 0),
                "tick_size": i.get("tick_size", 0.05),
                "underlying": i.get("underlying", ""),
            })
            if len(results) >= 100:
                break
    return {"results": results, "total": len(results)}


@router.get("/fo/options-chain")
def options_chain(
    underlying: str = Query(...),
    expiry: str = Query(None),
    strike_start: float = Query(None),
    strike_end: float = Query(None),
    user: User = Depends(get_current_user),
):
    """Options chain for a given underlying."""
    client = get_instrument_client()
    if not client.is_configured:
        return {"calls": [], "puts": [], "underlying": underlying}
    instruments = client.get_fo_instruments()
    ul = underlying.upper()
    calls = []
    puts = []
    for i in instruments:
        name = (i.get("name") or "").upper()
        if ul not in name:
            continue
        strike = float(i.get("strike", 0))
        if strike_start is not None and strike < strike_start:
            continue
        if strike_end is not None and strike > strike_end:
            continue
        if expiry and i.get("expiry") != expiry:
            continue
        entry = {
            "trading_symbol": i.get("trading_symbol", ""),
            "instrument_key": i.get("instrument_key", ""),
            "expiry": i.get("expiry", ""),
            "strike": strike,
            "lot_size": i.get("lot_size", 0),
            "segment": i.get("segment", ""),
        }
        inst_type = (i.get("instrument_type") or "").upper()
        if "CE" in inst_type:
            calls.append(entry)
        elif "PE" in inst_type:
            puts.append(entry)
    return {"calls": calls, "puts": puts, "underlying": underlying}


# ─── MTF ───

@router.get("/mtf")
def mtf_stocks(
    force: bool = Query(False),
    user: User = Depends(get_current_user),
):
    """List MTF-eligible stocks."""
    client = get_instrument_client()
    if not client.is_configured:
        return {"results": [], "total": 0}
    results = client.get_mtf_eligible(force)
    # Enrich with quotes
    provider = get_upstox_provider()
    if provider and provider._configured:
        try:
            syms = [r["trading_symbol"] for r in results[:50]]
            quote_map = provider._inst_client.get_quote_batch(syms, "NSE")
            for r in results:
                q = quote_map.get(r["trading_symbol"], {})
                if q:
                    r["last_price"] = q.get("last_price")
                    r["change"] = q.get("change")
                    r["change_pct"] = q.get("change_pct")
        except Exception:
            pass
    return {"results": results, "total": len(results)}


# ─── IPO ───

@router.get("/ipo")
def ipo_list(user: User = Depends(get_current_user)):
    """List IPOs from Upstox."""
    client = get_instrument_client()
    if not client.is_configured:
        return {"ipos": []}
    ipos = client.get_ipo_list()
    grouped = {"upcoming": [], "open": [], "closed": [], "listed": []}
    for ipo in ipos:
        status = (ipo.get("status") or "").lower()
        if status in grouped:
            grouped[status].append({
                "company_name": ipo.get("company_name", ""),
                "instrument_key": ipo.get("instrument_key", ""),
                "issue_type": ipo.get("issue_type", ""),
                "status": status,
                "price_band_low": ipo.get("price_band_low"),
                "price_band_high": ipo.get("price_band_high"),
                "lot_size": ipo.get("lot_size"),
                "min_investment": ipo.get("min_investment"),
                "open_date": ipo.get("open_date"),
                "close_date": ipo.get("close_date"),
                "listing_date": ipo.get("listing_date"),
                "registrar": ipo.get("registrar"),
                "offer_size": ipo.get("offer_size"),
            })
    return {"ipos": grouped}


# ─── MUTUAL FUNDS ───

@router.get("/mf/search")
def search_mf(
    q: str = Query(..., min_length=2),
    user: User = Depends(get_current_user),
):
    """Search mutual funds."""
    client = get_instrument_client()
    if not client.is_configured:
        return {"results": []}
    instruments = client.get_mf_instruments()
    q = q.upper()
    results = []
    for i in instruments:
        name = (i.get("name") or "").upper()
        fund_name = (i.get("fund_name") or "").upper()
        if q in name or q in fund_name:
            results.append({
                "trading_symbol": i.get("trading_symbol", ""),
                "name": i.get("name", ""),
                "fund_name": i.get("fund_name", ""),
                "amc": i.get("amc", ""),
                "instrument_key": i.get("instrument_key", ""),
                "category": i.get("category", ""),
                "plan": i.get("plan", ""),
                "scheme_type": i.get("scheme_type", ""),
                "nav": i.get("nav"),
                "last_price_date": i.get("last_price_date"),
            })
            if len(results) >= 50:
                break
    return {"results": results}


# ─── SIP ───

@router.get("/sip")
def sip_registrations(user: User = Depends(get_current_user)):
    """List existing SIP registrations."""
    client = get_instrument_client()
    if not client.is_configured:
        return {"sips": []}
    sips = client.get_sip_registrations()
    return {
        "sips": [
            {
                "sip_id": s.get("sip_id"),
                "fund_name": s.get("fund_name", ""),
                "amount": s.get("amount"),
                "frequency": s.get("frequency", ""),
                "next_installment": s.get("next_installment"),
                "completed_installments": s.get("completed_installments"),
                "sip_type": s.get("sip_type", ""),
                "status": s.get("status", ""),
            }
            for s in sips
        ]
    }


# ─── MARKET CATEGORIES ───

@router.get("/top-movers")
def top_movers(
    category: str = Query("gainers", description="gainers, losers, active, volume"),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    """Get top gainers/losers/most active from real market data."""
    provider = get_upstox_provider()
    if not provider or not provider._configured:
        return {"results": []}
    client = get_instrument_client()
    # Get quotes for a large set of known liquid stocks
    liquid = [
        "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ITC","LT","BHARTIARTL",
        "AXISBANK","KOTAKBANK","HINDUNILVR","BAJFINANCE","MARUTI","TITAN","SUNPHARMA",
        "ASIANPAINT","HCLTECH","WIPRO","TECHM","NESTLE","ULTRACEMCO","POWERGRID",
        "NTPC","ONGC","COALINDIA","JSWSTEEL","TATASTEEL","ADANIPORTS","ADANIENT",
        "HDFCLIFE","BAJAJFINSV","INDUSINDBK","DRREDDY","CIPLA","DIVISLAB","APOLLOHOSP",
        "BRITANNIA","EICHERMOT","HEROMOTOCO","TATAMOTORS","M&M","BAJAJ-AUTO",
        "GRASIM","HINDALCO","SHREECEM","BPCL","IOC","GAIL","HDFC","DMART",
    ]
    quote_map = client.get_quote_batch(liquid, "NSE")
    stocks = []
    for sym, q in quote_map.items():
        if not q.get("last_price") or q["last_price"] <= 0:
            continue
        stocks.append(q)
    if category == "gainers":
        stocks.sort(key=lambda x: -x.get("change_pct", 0))
    elif category == "losers":
        stocks.sort(key=lambda x: x.get("change_pct", 0))
    elif category == "active" or category == "volume":
        stocks.sort(key=lambda x: -x.get("volume", 0))
    return {"results": stocks[:limit]}
