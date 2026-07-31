"""Risk engine — position sizing, stop loss, circuit breakers."""
from decimal import Decimal


def calculate_position_size(
    capital: float,
    entry_price: float,
    stop_loss: float,
    risk_pct: float = 1.0,
    max_position_pct: float = 20.0,
) -> int:
    """Risk-based position sizing."""
    if entry_price <= 0 or stop_loss <= 0 or stop_loss >= entry_price:
        return 0
    risk_amount = capital * (risk_pct / 100)
    risk_per_share = abs(entry_price - stop_loss)
    if risk_per_share <= 0:
        return 0
    qty_risk = int(risk_amount / risk_per_share)
    max_capital = capital * (max_position_pct / 100)
    qty_capital = int(max_capital / entry_price)
    return min(qty_risk, qty_capital)


def check_daily_loss_limit(
    today_pnl: float,
    capital: float,
    max_daily_loss_pct: float = 2.0,
) -> bool:
    """Returns True if daily loss limit is exceeded."""
    if capital <= 0:
        return True
    loss_pct = abs(today_pnl) / capital * 100 if today_pnl < 0 else 0
    return loss_pct >= max_daily_loss_pct


def check_drawdown_limit(
    current_equity: float,
    peak_equity: float,
    max_drawdown_pct: float = 15.0,
) -> bool:
    """Returns True if drawdown limit is exceeded."""
    if peak_equity <= 0:
        return True
    dd = (peak_equity - current_equity) / peak_equity * 100
    return dd >= max_drawdown_pct


def check_sector_exposure(
    portfolio_holdings: list,
    new_symbol_sector: str,
    max_sector_pct: float = 30.0,
    total_equity: float = 100000.0,
) -> bool:
    """Returns True if adding this trade would exceed sector exposure limit."""
    if total_equity <= 0:
        return True
    sector_value = sum(
        h.get("market_value", 0) for h in portfolio_holdings
        if h.get("sector") == new_symbol_sector
    )
    return (sector_value / total_equity * 100) >= max_sector_pct


def calculate_stop_loss(entry_price: float, stop_pct: float = 3.0) -> float:
    return round(entry_price * (1 - stop_pct / 100), 2)


def calculate_take_profit(entry_price: float, target_pct: float = 6.0) -> float:
    return round(entry_price * (1 + target_pct / 100), 2)
