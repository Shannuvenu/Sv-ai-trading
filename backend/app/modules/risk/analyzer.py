from decimal import Decimal
from sqlalchemy.orm import Session
from app.modules.market_data.utils import resolve_market_provider


def analyze_risk(holdings: list, cash_balance: Decimal, db: Session) -> dict:
    provider = resolve_market_provider(db)
    instruments_list = provider.get_all_instruments()
    instruments = {i.symbol: i for i in instruments_list}

    total_equity = cash_balance
    sector_exposure: dict[str, Decimal] = {}
    position_values: list[dict] = []

    for h in holdings:
        symbol = h.symbol
        quote = provider.get_quote(symbol)
        current_price = quote.last_price if quote else Decimal("0")
        market_value = current_price * h.quantity
        total_equity += market_value
        inst = instruments.get(symbol)
        sector = inst.sector if inst else "Unknown"

        position_values.append({
            "symbol": symbol,
            "market_value": float(market_value),
            "sector": sector,
            "weight_pct": 0.0,
        })
        sector_exposure[sector] = sector_exposure.get(sector, Decimal("0")) + market_value

    if total_equity == 0:
        total_equity = Decimal("1")

    for pv in position_values:
        pv["weight_pct"] = round(float(Decimal(str(pv["market_value"])) / total_equity * 100), 2)

    concentration = max((pv["weight_pct"] for pv in position_values), default=0.0)

    sector_breakdown = {}
    for sector, val in sector_exposure.items():
        sector_breakdown[sector] = {
            "value": float(val),
            "weight_pct": round(float(val / total_equity * 100), 2),
        }

    position_sizing = {
        "max_position_pct": 20.0,
        "suggested_max_per_symbol": round(float(total_equity) * 0.2, 2),
        "total_equity": float(total_equity),
    }

    recommendations = []
    if concentration > 20:
        recommendations.append(f"High concentration ({concentration:.1f}%) in a single position. Consider diversifying.")
    if total_equity > 0:
        cash_pct = float(cash_balance / total_equity * 100)
        if cash_pct > 80:
            recommendations.append(f"High cash allocation ({cash_pct:.1f}%). Consider deploying capital.")
        elif cash_pct < 5:
            recommendations.append(f"Very low cash buffer ({cash_pct:.1f}%). Maintain reserves.")

    return {
        "total_equity": float(total_equity),
        "cash_balance": float(cash_balance),
        "num_positions": len(holdings),
        "concentration": {
            "max_single_position_pct": concentration,
            "positions": position_values,
        },
        "sector_concentration": sector_breakdown,
        "position_sizing": position_sizing,
        "recommendations": recommendations,
        "disclaimer": "These are analytical risk metrics calculated from a rule-based model. They do not guarantee protection against losses.",
    }
