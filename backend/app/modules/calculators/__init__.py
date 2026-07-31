"""Financial calculators — deterministic math, no external data needed."""

def sip_calculator(monthly: float, years: int, rate_pct: float) -> dict:
    """SIP (Systematic Investment Plan) calculator."""
    n = years * 12
    r = rate_pct / 100 / 12
    if r == 0:
        total = monthly * n
        return {"invested": round(total, 2), "maturity": round(total, 2), "gain": 0.0}
    fv = monthly * (((1 + r) ** n - 1) / r) * (1 + r)
    invested = monthly * n
    return {"invested": round(invested, 2), "maturity": round(fv, 2), "gain": round(fv - invested, 2)}


def lumpsum_calculator(principal: float, years: int, rate_pct: float) -> dict:
    """Lumpsum investment calculator."""
    fv = principal * (1 + rate_pct / 100) ** years
    return {"invested": round(principal, 2), "maturity": round(fv, 2), "gain": round(fv - principal, 2)}


def cagr_calculator(initial: float, final: float, years: float) -> dict:
    """CAGR (Compound Annual Growth Rate) calculator."""
    if initial <= 0 or years <= 0:
        return {"cagr": 0.0, "absolute_return": 0.0}
    cagr = ((final / initial) ** (1 / years) - 1) * 100
    absolute = ((final - initial) / initial) * 100
    return {"cagr": round(cagr, 2), "absolute_return": round(absolute, 2)}


def emi_calculator(principal: float, years: int, rate_pct: float) -> dict:
    """EMI calculator."""
    n = years * 12
    r = rate_pct / 100 / 12
    if r == 0:
        emi = principal / n
        return {"emi": round(emi, 2), "total_payment": round(principal, 2), "total_interest": 0.0}
    emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    total = emi * n
    return {"emi": round(emi, 2), "total_payment": round(total, 2), "total_interest": round(total - principal, 2)}


def compound_interest(principal: float, years: int, rate_pct: float, compounding: int = 1) -> dict:
    """Compound interest calculator."""
    fv = principal * (1 + rate_pct / 100 / compounding) ** (compounding * years)
    return {"invested": round(principal, 2), "maturity": round(fv, 2), "gain": round(fv - principal, 2)}


def fd_calculator(principal: float, years: float, rate_pct: float) -> dict:
    """Fixed Deposit calculator (quarterly compounding)."""
    return compound_interest(principal, int(years), rate_pct, 4)


def rd_calculator(monthly: float, months: int, rate_pct: float) -> dict:
    """Recurring Deposit calculator."""
    n = months
    r = rate_pct / 100 / 4
    q = months / 3
    if r == 0:
        total = monthly * n
        return {"invested": round(total, 2), "maturity": round(total, 2), "gain": 0.0}
    fv = monthly * (((1 + r) ** q - 1) / (1 - (1 + r) ** (-1 / 3)))
    invested = monthly * n
    return {"invested": round(invested, 2), "maturity": round(fv, 2), "gain": round(fv - invested, 2)}
